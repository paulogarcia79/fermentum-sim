"""
actions.py — Módulo de Acciones de Jugador (Fase II) de Fermentum
==================================================================
Implementa la clase ActionManager, que encapsula la lógica completa de todas
las acciones que un jugador puede ejecutar durante la Fase II: Acción.

Contenido:
  · Constantes: COSTOS_TECNOLOGIA
  · ActionManager: 11 métodos de acción + validadores internos

Estándares aplicados (ARCHITECTURE.md):
  · Separación de Responsabilidades: este módulo solo resuelve acciones de
    jugador. La orquestación del bucle y la cinética biológica pertenecen al
    engine.py. El motor inyecta ActionManager vía TurnCallback.
  · Strict Type Hinting (PEP 484) en todos los atributos y retornos.
  · Principio Fail-Fast: cada método de acción valida TODAS las precondiciones
    antes de modificar cualquier estado. Si alguna falla, se lanza una
    excepción semántica sin efecto secundario.
  · Inyección de Dependencias: ActionManager recibe GameEngine (para acceder
    al mercado y al método resolver_horneado) en su constructor.
  · Sin importaciones circulares: GameEngine se referencia solo como tipo
    (TYPE_CHECKING) gracias a `from __future__ import annotations`.

Patrón de uso::

    manager = ActionManager(engine)

    def turno_jugador(engine: GameEngine, player: Player) -> None:
        manager.accion_A_alimentar(player, usar_harina=True, usar_agua=True)
        manager.accion_F_hornear(player, slot_index=0)

    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno_jugador)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    # Evita importación circular en tiempo de ejecución.
    # GameEngine solo se usa como anotación de tipo en __init__.
    from engine import GameEngine

from engine import (
    AGUA_TOKENS_POR_LOTE,
    CANTIDAD_BOLSA_PCT,
    CANTIDAD_MEDIA_BOLSA_PCT,
    PRECIO_AGUA,
    PRECIO_PLIEGUES,
    PRECIO_PLIEGUES_VITALIDAD,
    PRECIO_RECETA,
)
from exceptions import (
    CarpetaFullError,
    EspacioAccionYaUsadoError,
    InvalidActionError,
    MarketSlotEmptyError,
    MissingResourceError,
    NotEnoughActionPointsError,
    RuleViolationError,
    StationBlockedError,
)
from models import (
    EfectoClimatico,
    FermentationSlot,
    HorneadoRecord,
    Player,
    Recipe,
    TecnologiaID,
    TipoHarina,
)

# ===========================================================================
# SECCIÓN 1: CONSTANTES DE COSTE
# ===========================================================================

COSTOS_TECNOLOGIA: Dict[TecnologiaID, int] = {
    TecnologiaID.INCUBADORA: 3,
    TecnologiaID.CAMARA_B: 4,
    TecnologiaID.MODULO_ANALITICO: 4,
    TecnologiaID.CRIOPRESERVACION: 2,
}
"""
Coste en Datos de Investigación de cada mejora de laboratorio (Acción D).
Fuente: ACTIONS_REGISTRY.md §2D.
"""

TIPOS_HARINA_VALIDOS: Dict[str, TipoHarina] = {t.value: t for t in TipoHarina}
"""Lookup de string → TipoHarina, usado para validar transacciones de mercado."""

LOTES_AGUA_VALIDOS = (10, 30, 60, 100)
"""Tamaños de lote válidos (%) para Comprar Lote de Agua en Visitar el Mercado."""

OPERACIONES_HARINA: Dict[str, Tuple[str, int]] = {
    "comprar": ("comprar", CANTIDAD_BOLSA_PCT),
    "comprar_media": ("comprar", CANTIDAD_MEDIA_BOLSA_PCT),
    "vender": ("vender", CANTIDAD_BOLSA_PCT),
    "vender_media": ("vender", CANTIDAD_MEDIA_BOLSA_PCT),
}
"""
Operación del wire → (dirección, cantidad en %). Existe como tabla única porque
``accion_C_visitar_mercado`` recorre las transacciones TRES veces (validar,
simular saldos, aplicar): con la cantidad escrita a mano en cada bucle, añadir
un tamaño de bolsa sería una invitación a que los tres dejasen de coincidir.
"""


# ===========================================================================
# SECCIÓN 2: ACTION MANAGER
# ===========================================================================


class ActionManager:
    """
    Gestiona todas las acciones disponibles durante la Fase II de Fermentum.

    Recibe el GameEngine por inyección de dependencias para:
      · Acceder al mercado central (``engine.market``) en las Acciones C y G.
      · Delegar el horneado a ``engine.resolver_horneado()`` en la Acción F.

    Principio Fail-Fast (ARCHITECTURE.md §3):
      Cada método público valida la totalidad de sus precondiciones antes de
      aplicar cualquier cambio de estado. Si alguna condición falla, el método
      lanza la excepción semántica correspondiente y el estado del jugador
      permanece intacto.

    Acciones implementadas:
      Principales (1 PA):
        A — Alimentar / Refrescar el Cultivo
        B — Iniciar Receta
        C — Visitar el Mercado (comprar/vender harina, comprar agua)
        D — Implementar Mejora de Laboratorio
        E — Técnica / Pliegues
        F — Hornear y Vender
        G — Investigar Protocolo
        Simposio Técnico — Generación de Datos
      Auxiliares / Emergencia:
        Horas Extras (0 PA + 1 Dato)
        Pedido de Urgencia (0 PA + 1 Dato)
        H — Re-cultivo Manual (emergencia)
        I — Inóculo de Emergencia (emergencia)
    """

    def __init__(self, engine: "GameEngine") -> None:
        """
        Args:
            engine: Instancia del motor de juego activo.
                Provee acceso al mercado y al método de resolución de horneado.
        """
        self._engine = engine

    # ==================================================================
    # VALIDADORES INTERNOS (helpers de precondición, sin efectos)
    # ==================================================================

    def _require_pa(self, player: Player, costo: int) -> None:
        """
        Verifica que el jugador tenga al menos `costo` Puntos de Acción.

        Raises:
            NotEnoughActionPointsError: Si ``player.puntos_accion < costo``.
        """
        if player.puntos_accion < costo:
            raise NotEnoughActionPointsError(
                f"'{player.nombre}' necesita {costo} PA pero solo tiene "
                f"{player.puntos_accion}. Considera usar Horas Extras."
            )

    def _require_espacio_disponible(self, player: Player, accion_id: str) -> None:
        """
        Verifica que el jugador no haya visitado ya este espacio de acción
        hoy -- cada espacio con costo de PA solo puede usarse una vez por
        Día de Laboratorio (PLAYER_STATE.md, acciones_pa_usadas_hoy).

        Raises:
            EspacioAccionYaUsadoError: Si ``accion_id`` ya está en
                ``player.acciones_pa_usadas_hoy``.
        """
        if accion_id in player.acciones_pa_usadas_hoy:
            raise EspacioAccionYaUsadoError(
                f"'{player.nombre}' ya usó el espacio de acción '{accion_id}' hoy."
            )

    def _require_harinas(self, player: Player, receta: Recipe) -> None:
        """
        Verifica que el jugador tenga TODAS las harinas que la receta imprime.

        ``receta.requisito_harina`` tiene la misma forma que ``player.reserva_harina``
        (``{nombre_tipo: porcentaje}``), así que la comprobación es un único bucle
        sobre claves que coinciden, sea la receta de una harina (Básica/Avanzada,
        100%) o de dos (Intermedia, 50% + 50%).

        Informa de TODOS los tipos que faltan, no solo del primero: con una receta
        Intermedia, saber que falta una de las dos mitades no dice cuál comprar.

        Raises:
            MissingResourceError: Si falta cualquiera de las harinas requeridas.
        """
        faltantes = [
            f"{pct}% de Harina {tipo} (tiene {player.reserva_harina.get(tipo, 0)}%)"
            for tipo, pct in receta.requisito_harina.items()
            if player.reserva_harina.get(tipo, 0) < pct
        ]
        if faltantes:
            raise MissingResourceError(
                f"'{player.nombre}' no puede iniciar '{receta.nombre}': "
                f"necesita {'; '.join(faltantes)}."
            )

    def _require_cualquier_harina(self, player: Player, pct_minimo: int) -> None:
        """
        Verifica que el jugador tenga al menos ``pct_minimo`` de porcentaje
        total de harina sumando todos los tipos.

        Raises:
            MissingResourceError: Si la reserva total de harina es insuficiente.
        """
        total = sum(player.reserva_harina.values())
        if total < pct_minimo:
            raise MissingResourceError(
                f"'{player.nombre}' necesita al menos {pct_minimo}% de harina "
                f"(cualquier tipo) pero tiene {total}% en total."
            )

    def _require_agua(self, player: Player, cantidad: int) -> None:
        """
        Verifica que el jugador tenga al menos `cantidad` tokens de agua.

        Raises:
            MissingResourceError: Si la reserva de agua es insuficiente.
        """
        if player.reserva_agua < cantidad:
            raise MissingResourceError(
                f"'{player.nombre}' necesita {cantidad} tokens de agua "
                f"pero tiene {player.reserva_agua}."
            )

    def _require_datos(self, player: Player, cantidad: int) -> None:
        """
        Verifica que el jugador tenga al menos `cantidad` Datos de Investigación.

        Raises:
            MissingResourceError: Si los datos son insuficientes.
        """
        if player.datos_investigacion < cantidad:
            raise MissingResourceError(
                f"'{player.nombre}' necesita {cantidad} Datos de Investigación "
                f"pero tiene {player.datos_investigacion}."
            )

    def _require_monedas(self, player: Player, cantidad: int) -> None:
        """
        Verifica que el jugador tenga al menos `cantidad` Monedas.

        Raises:
            MissingResourceError: Si las Monedas son insuficientes.
        """
        if player.monedas < cantidad:
            raise MissingResourceError(
                f"'{player.nombre}' necesita {cantidad} Monedas "
                f"pero tiene {player.monedas}."
            )

    def _require_contaminado(self, player: Player, nombre_protocolo: str) -> None:
        """
        Verifica que el jugador esté en estado de Contaminación (vitalidad=0).
        Solo para los Protocolos de Emergencia (H e I), que requieren
        activación previa.

        Raises:
            InvalidActionError: Si el jugador NO está contaminado.
        """
        if not player.en_estado_contaminacion:
            raise InvalidActionError(
                f"'{player.nombre}' no está en estado de Contaminación. "
                f"El {nombre_protocolo} solo puede ejecutarse cuando Vitalidad == 0."
            )

    # ==================================================================
    # ACCIONES PRINCIPALES (Costo: 1 PA)
    # ==================================================================

    def accion_A_alimentar(
        self,
        player: Player,
        usar_harina: bool = True,
        tipo_harina: Optional[str] = None,
        usar_agua: bool = True,
    ) -> None:
        """
        Acción A: Alimentar / Refrescar el Cultivo (ACTIONS_REGISTRY.md §3).

        Costo:      0 PA (acción auxiliar gratuita, una vez por Fase II).
        Recursos:   Según combinación elegida.
        Efecto:     +1 Vitalidad si se consume 10% de harina del tipo indicado.
                    +1 Acidez si se consumen 2 tokens de agua (10%).
                    Ambos efectos son simultáneos en la alimentación completa.

        Alimentación parcial:
          ``usar_harina=False, usar_agua=True``  → solo +1 Acidez.
          ``usar_harina=True, usar_agua=False``  → solo +1 Vitalidad.

        Solo puede ejecutarse una vez por Fase II («accion_alimentar_usada»).

        Args:
            player: Jugador que ejecuta la acción.
            usar_harina: True para consumir 10% de harina y ganar +1 Vitalidad.
            tipo_harina: Clave del tipo de harina a consumir ("Blanca", "Centeno"
                o "Integral"). Requerido si usar_harina=True.
            usar_agua: True para consumir 2 tokens de agua y ganar +1 Acidez.

        Raises:
            InvalidActionError: Sin recurso activo, ya usada este turno, o
                tipo_harina inválido.
            MissingResourceError: Si se solicita un recurso que el jugador no posee.
        """
        if not usar_harina and not usar_agua:
            raise InvalidActionError(
                "Acción A requiere al menos un recurso (harina o agua). "
                "Especifica usar_harina=True y/o usar_agua=True."
            )

        if player.accion_alimentar_usada:
            raise InvalidActionError(
                f"'{player.nombre}' ya usó la Acción A este turno de Fase II. "
                "Solo puede alimentarse una vez por fase."
            )

        # --- Bloque de validaciones (Fail-Fast) ---
        if usar_harina:
            tipos_validos = {"Blanca", "Centeno", "Integral"}
            if tipo_harina not in tipos_validos:
                raise InvalidActionError(
                    f"tipo_harina debe ser uno de {sorted(tipos_validos)}. "
                    f"Recibido: {tipo_harina!r}"
                )
            if player.reserva_harina.get(tipo_harina, 0) < 10:
                raise MissingResourceError(
                    f"'{player.nombre}' necesita al menos 10% de Harina {tipo_harina} "
                    f"pero tiene {player.reserva_harina.get(tipo_harina, 0)}%."
                )
        if usar_agua:
            self._require_agua(player, 2)

        # --- Aplicar efectos (0 PA) ---
        if usar_harina:
            player.reserva_harina[tipo_harina] -= 10
            player.ajustar_vitalidad(+1)

        if usar_agua:
            player.reserva_agua -= 2
            player.ajustar_acidez(+1)

        player.accion_alimentar_usada = True

    def accion_B_iniciar_receta(
        self,
        player: Player,
        receta: Recipe,
        modificador_incubadora: int = 0,
    ) -> FermentationSlot:
        """
        Acción B: Iniciar Receta (ACTIONS_REGISTRY.md §2B).

        Costo:   1 PA
                 + las harinas impresas en la carta (``receta.requisito_harina``),
                   siempre 100% en total: una bolsa entera de un tipo (Básica /
                   Avanzada) o media bolsa de cada uno de dos tipos (Intermedia)
                 + receta.tokens_agua tokens de agua (pago exacto), o
                   receta.tokens_agua - 1 si "Alta Humedad" es el efecto
                   pasivo vigente (CLIMATE_LOGIC.md §2).

        Memoria Biológica sellada al inicio (ACTIONS_REGISTRY.md §2B):
          · Dado de Inóculo ← player.vitalidad actual (sellado fijo en la masa).
          · Cubo de Acidez  ← True si player.acidez ∈ receta.acidez_diana.
            El Cubo activa el Bono de Sabor al hornear.

        Precondiciones:
          · La receta debe estar en player.carpeta_proyectos.
          · player.vitalidad >= 1 (dado_inoculo no puede ser 0).
          · player.dados_inoculo >= 1 (hay dados disponibles para sellar).
          · Debe existir una estación de fermentación libre.
            (Estación 03 solo con Cámara B activa.)
          · modificador_incubadora ≠ 0 solo si Incubadora está instalada.

        Efectos sobre el estado:
          1. Consume 1 PA, las harinas impresas en la carta, tokens_agua exactos.
          2. Consume 1 dado de inóculo (dados_inoculo -= 1).
          3. Crea y coloca el FermentationSlot en la primera estación libre.
          4. Retira la receta de carpeta_proyectos.

        Args:
            player: Jugador que inicia la fermentación.
            receta: Carta a iniciar; debe estar en player.carpeta_proyectos.
            modificador_incubadora: Ajuste local de avance (-1, 0 o +1).
                Solo válido si player.tecnologias.incubadora == True.

        Returns:
            El FermentationSlot creado con la memoria biológica sellada.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            RuleViolationError: Receta no en carpeta, vitalidad=0, o sin
                estación de fermentación disponible. Ninguna receta está restringida
                por tecnología: el freno es el coste en insumos.
            StationBlockedError: Todas las estaciones están ocupadas o
                la única libre (03) requiere Cámara B.
            MissingResourceError: Harina, agua o dados de inóculo insuficientes.
            InvalidActionError: modificador_incubadora inválido o usado sin Incubadora.
        """
        # --- Bloque de validaciones completo (Fail-Fast) ---

        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "B")

        if player.vitalidad < 1:
            raise RuleViolationError(
                f"'{player.nombre}' tiene Vitalidad 0 (contaminado). "
                "No se puede iniciar una receta hasta ejecutar un "
                "Protocolo de Emergencia (Acción H o I)."
            )

        if receta not in player.carpeta_proyectos:
            raise RuleViolationError(
                f"La receta '{receta.nombre}' no está en la Carpeta de "
                f"Proyectos de '{player.nombre}'. Investígala primero (Acción G)."
            )

        indice_estacion: Optional[int] = player.indice_estacion_disponible
        if indice_estacion is None:
            raise StationBlockedError(
                f"'{player.nombre}' no tiene estaciones de fermentación "
                "disponibles. Las estaciones 01 y 02 están ocupadas. "
                "La Estación 03 requiere Cámara B activa."
            )

        if player.dados_inoculo < 1:
            raise MissingResourceError(
                f"'{player.nombre}' no tiene dados de inóculo disponibles. "
                "Hornea una masa activa para recuperar un dado."
            )

        tokens_agua_requeridos = receta.tokens_agua
        if self._engine.environment.efecto_pasivo_activo == EfectoClimatico.ALTA_HUMEDAD:
            tokens_agua_requeridos -= 1

        self._require_harinas(player, receta)
        self._require_agua(player, tokens_agua_requeridos)

        if modificador_incubadora not in (-1, 0, 1):
            raise InvalidActionError(
                f"modificador_incubadora debe ser -1, 0 o 1. "
                f"Recibido: {modificador_incubadora}"
            )
        if modificador_incubadora != 0 and not player.tecnologias.incubadora:
            raise InvalidActionError(
                f"No se puede usar modificador_incubadora={modificador_incubadora} "
                "sin tener la tecnología Incubadora instalada."
            )

        # --- Todas las validaciones pasaron; aplicar efectos ---

        player.consumir_punto_accion("B")

        # Consumir las harinas impresas en la carta (100% en total: una bolsa
        # entera, o media bolsa de cada uno de dos tipos si es Intermedia)
        for tipo, pct in receta.requisito_harina.items():
            player.reserva_harina[tipo] -= pct

        # Consumir tokens de agua (pago exacto; -1 con Alta Humedad activa)
        player.reserva_agua -= tokens_agua_requeridos

        # Sellar Memoria Biológica: dado = Vitalidad actual; bono = acidez en diana
        dado_inoculo: int = player.vitalidad
        bono_sabor: bool = receta.acidez_activa_bono(player.acidez)

        # Crear FermentationSlot con los valores sellados
        slot = FermentationSlot(
            recipe=receta,
            dado_inoculo=dado_inoculo,
            posicion_track=0,
            bono_sabor=bono_sabor,
            modificador_incubadora=modificador_incubadora,
            acidez_inicial=player.acidez,
        )

        # Colocar en la estación disponible y consumir dado de inóculo
        player.estaciones_fermentacion[indice_estacion] = slot
        player.dados_inoculo -= 1

        # Retirar receta de la carpeta de proyectos
        player.carpeta_proyectos.remove(receta)

        return slot

    def accion_C_visitar_mercado(
        self,
        player: Player,
        transacciones: List[Dict[str, Any]],
    ) -> None:
        """
        Acción C: Visitar el Mercado (GDD v0.0.2, Módulo III §C).

        Costo:   1 PA (una sola vez por visita, sin importar cuántas
                 transacciones incluya el lote).

        Cada elemento de ``transacciones`` es un dict:
          · ``tipo_recurso``: ``"Blanca" | "Integral" | "Centeno" | "agua"``.
          · ``operacion``: para harina, una de ``OPERACIONES_HARINA``
            (``"comprar" | "comprar_media" | "vender" | "vender_media"``).
            El agua solo admite ``"comprar"`` (no existe venta de agua, y
            tampoco medio lote: ya tiene cuatro tamaños propios).
          · ``lote_pct``: requerido solo para agua, uno de
            ``LOTES_AGUA_VALIDOS`` (10, 30, 60, 100).

        Regla de Exclusividad (GDD v0.0.2 §C): una visita puede incluir como
        máximo UNA transacción por tipo de recurso — comprar Blanca y vender
        Centeno y comprar un lote de agua en la misma visita está permitido;
        comprar Blanca dos veces, o comprar y vender Blanca, no lo está.

        Comprar harina: paga el precio de Compra visible (según la posición
        actual del visor de ese tipo en ``Market.posiciones_harina``), recibe
        una bolsa entera —10 tokens, 100%— de esa harina, y el visor se mueve
        1 casilla hacia el extremo caro (tope en posición 5).
        Vender harina: cobra el precio de Venta visible, entrega una bolsa
        entera, y el visor se mueve 1 casilla hacia el extremo barato (tope en
        posición 1).
        Media bolsa (``comprar_media`` / ``vender_media``): 5 tokens (50%) al
        precio de ``Market.precio_compra_harina``/``precio_venta_harina`` con
        ``cantidad_pct=50``, es decir la mitad redondeada hacia ARRIBA al
        comprar y hacia ABAJO al vender. **El visor se mueve 1 casilla igual
        que con una bolsa entera**: una transacción es una señal de mercado,
        sin importar su tamaño. Una venta que redondea a 0 Monedas (Blanca en
        posición 1) es legal.
        Comprar lote de agua: paga el costo de ``PRECIO_AGUA`` según la
        temperatura actual y el tamaño de lote elegido, recibe los tokens de
        agua correspondientes (``AGUA_TOKENS_POR_LOTE``).

        Toda la operación se valida en conjunto ANTES de aplicar ningún
        cambio (fail-fast): una venta puede financiar una compra en la misma
        visita, así que los saldos se simulan sobre una copia de las
        reservas del jugador en el orden dado, y solo si el lote completo es
        viable se consume el PA y se aplican todas las transacciones.

        Args:
            player: Jugador que visita el mercado.
            transacciones: Lista de 1 o más transacciones (ver formato arriba).

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            InvalidActionError: Lista vacía, transacción malformada, o
                más de una transacción sobre el mismo tipo de recurso.
            MissingResourceError: Monedas o harina insuficientes en algún
                punto de la simulación de la visita completa.
        """
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "C")

        if not transacciones:
            raise InvalidActionError(
                "Visitar el Mercado requiere al menos una transacción."
            )

        tipos_vistos: set = set()
        for t in transacciones:
            tipo_recurso = t.get("tipo_recurso")
            operacion = t.get("operacion")

            if tipo_recurso not in TIPOS_HARINA_VALIDOS and tipo_recurso != "agua":
                raise InvalidActionError(
                    f"tipo_recurso inválido: {tipo_recurso!r}. Debe ser "
                    f"'agua' o uno de {sorted(TIPOS_HARINA_VALIDOS)}."
                )
            if tipo_recurso in tipos_vistos:
                raise InvalidActionError(
                    f"Regla de Exclusividad: solo se permite una transacción "
                    f"por tipo de recurso por visita. '{tipo_recurso}' repetido."
                )
            tipos_vistos.add(tipo_recurso)

            if tipo_recurso == "agua":
                if operacion != "comprar":
                    raise InvalidActionError(
                        "El agua solo admite operacion='comprar' (no se vende)."
                    )
                lote_pct = t.get("lote_pct")
                if lote_pct not in LOTES_AGUA_VALIDOS:
                    raise InvalidActionError(
                        f"lote_pct inválido para agua: {lote_pct!r}. "
                        f"Debe ser uno de {LOTES_AGUA_VALIDOS}."
                    )
            else:
                if operacion not in OPERACIONES_HARINA:
                    raise InvalidActionError(
                        f"operacion inválida: {operacion!r}. Debe ser una de "
                        f"{sorted(OPERACIONES_HARINA)}."
                    )

        # --- Simulación de saldos (sin aplicar todavía) ---
        monedas_sim: int = player.monedas
        harina_sim: Dict[str, int] = dict(player.reserva_harina)
        market = self._engine.market
        temp_actual = self._engine.environment.temperatura_actual

        for t in transacciones:
            tipo_recurso = t["tipo_recurso"]
            operacion = t["operacion"]

            if tipo_recurso == "agua":
                lote_pct = t["lote_pct"]
                costo = PRECIO_AGUA[temp_actual][lote_pct]
                monedas_sim -= costo
            else:
                tipo = TIPOS_HARINA_VALIDOS[tipo_recurso]
                direccion, cantidad = OPERACIONES_HARINA[operacion]
                if direccion == "comprar":
                    monedas_sim -= market.precio_compra_harina(tipo, cantidad)
                else:
                    harina_sim[tipo_recurso] -= cantidad
                    monedas_sim += market.precio_venta_harina(tipo, cantidad)

            if monedas_sim < 0:
                raise MissingResourceError(
                    f"'{player.nombre}' no tiene suficientes Monedas para "
                    "completar esta visita al mercado."
                )
            if harina_sim.get(tipo_recurso, 0) < 0:
                raise MissingResourceError(
                    f"'{player.nombre}' no tiene suficiente Harina "
                    f"{tipo_recurso} para vender en esta visita."
                )

        # --- Toda la visita es viable: aplicar de verdad ---
        player.consumir_punto_accion("C")

        for t in transacciones:
            tipo_recurso = t["tipo_recurso"]
            operacion = t["operacion"]

            if tipo_recurso == "agua":
                lote_pct = t["lote_pct"]
                costo = PRECIO_AGUA[temp_actual][lote_pct]
                player.monedas -= costo
                player.reserva_agua += AGUA_TOKENS_POR_LOTE[lote_pct]
            else:
                tipo = TIPOS_HARINA_VALIDOS[tipo_recurso]
                direccion, cantidad = OPERACIONES_HARINA[operacion]
                comprando = direccion == "comprar"
                if comprando:
                    player.monedas -= market.precio_compra_harina(tipo, cantidad)
                    player.reserva_harina[tipo_recurso] += cantidad
                else:
                    player.monedas += market.precio_venta_harina(tipo, cantidad)
                    player.reserva_harina[tipo_recurso] -= cantidad
                # El visor reacciona igual a media bolsa que a una entera.
                market.mover_visor_harina(tipo, hacia_caro=comprando)

    def accion_D_implementar_mejora(
        self,
        player: Player,
        tecnologia: TecnologiaID,
    ) -> None:
        """
        Acción D: Implementar Mejora de Laboratorio (ACTIONS_REGISTRY.md §2D).

        Costos por tecnología:
          · Incubadora:       3 Datos  → ajuste ±5°C local en Fase III.
          · Cámara B:         4 Datos  → desbloquea Estación 03 y mejora Acción E.
          · Módulo Analítico: 4 Datos  → ensancha la zona óptima ±1 casilla (y
            retrasa el colapso) y sube los Datos del horneado a 2 (3 en centro exacto)
                                         y habilita recetas Avanzadas (Acción B).
          · Criopreservación: 2 Datos  → ignora el desgaste metabólico de
                                         Fase III (Estasis Biológica).

        Reglas (ACTIONS_REGISTRY.md §2D, GDD v0.0.2):
          · Cada mejora individual solo puede instalarse UNA vez por partida,
            pero un jugador puede llegar a instalar varias mejoras distintas
            a lo largo de la partida (no hay tope global de "una mejora total").
          · El beneficio se activa de forma inmediata al instalarse.
          · No se puede reinstalar una mejora ya activa.

        Args:
            player: Jugador que instala la mejora.
            tecnologia: Identificador de la tecnología a instalar.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            MissingResourceError: Datos de Investigación insuficientes.
            RuleViolationError: La tecnología ya estaba activa para este jugador.
        """
        if player.tecnologias.esta_activa(tecnologia):
            raise RuleViolationError(
                f"La tecnología '{tecnologia.value}' ya está activa "
                f"para '{player.nombre}'."
            )

        costo_datos: int = COSTOS_TECNOLOGIA[tecnologia]

        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "D")
        self._require_datos(player, costo_datos)

        # Aplicar
        player.consumir_punto_accion("D")
        player.datos_investigacion -= costo_datos
        player.tecnologias.activar(tecnologia)

    def accion_E_tecnica_pliegues(
        self,
        player: Player,
        opcion: str = "avanzar",
        reparto: Optional[Dict[int, int]] = None,
    ) -> None:
        """
        Acción E: Técnica / Pliegues (ACTIONS_REGISTRY.md §3E).

        Costo: 0 PA + Monedas. NO termina el turno del jugador (acción gratuita
        encadenable), pero SÍ ocupa su espacio de acción "E" una vez por día,
        compartido por todas sus variantes.

        Dos variantes, seleccionadas por ``opcion``:

          · ``"avanzar"`` (default): compra entre 1 y 3 espacios de avance de
            fermentación y los reparte entre sus masas activas según ``reparto``
            (un mapa ``slot_index -> espacios``). El precio depende del TOTAL
            comprado, no del número de masas: ver ``PRECIO_PLIEGUES``
            (1 espacio = 1 Moneda, 2 = 3, 3 = 6 — creciente al margen).
            Sin Cámara B el reparto debe recaer sobre una sola masa; la mejora
            no cambia cuántos espacios puedes comprar, sino que permite
            repartirlos entre dos masas distintas.
          · ``"recuperar_vitalidad"``: +1 Vitalidad en el cultivo base por un
            precio fijo (``PRECIO_PLIEGUES_VITALIDAD``). Requiere Cámara B e
            ignora ``reparto``.

        El avance NO se limita por arriba: comprar 3 espacios puede empujar una
        masa más allá de su zona óptima hasta la zona sobrefermentada, que la
        Fase III hornea automáticamente con penalización. Ese riesgo es el
        freno deliberado del escalón más caro (ver el módulo `disponibilidad`
        y `PistaMedida` en el cliente, que muestran la posición proyectada).

        Args:
            player: Jugador que ejecuta la técnica.
            opcion: "avanzar" | "recuperar_vitalidad".
            reparto: Mapa ``{slot_index: espacios}`` para "avanzar". La suma de
                espacios debe estar en PRECIO_PLIEGUES (1-3).

        Raises:
            InvalidActionError: ``opcion`` inválida, o ``reparto`` ausente /
                malformado / con un total fuera de la escalera de precios.
            MissingResourceError: Monedas insuficientes.
            EspacioAccionYaUsadoError: El espacio "E" ya se usó hoy.
            RuleViolationError: Variante o reparto que requieren Cámara B sin
                la tecnología instalada, o estación vacía / índice fuera de [0, 2].
        """
        opciones_validas = {"avanzar", "recuperar_vitalidad"}
        if opcion not in opciones_validas:
            raise InvalidActionError(
                f"opcion debe ser una de {opciones_validas}. Recibido: '{opcion}'"
            )

        # --- Rama: recuperar vitalidad (no usa reparto) ---
        if opcion == "recuperar_vitalidad":
            if not player.tecnologias.camara_b:
                raise RuleViolationError(
                    "La opción 'recuperar_vitalidad' de la Acción E requiere "
                    "la tecnología Cámara B instalada."
                )
            self._require_monedas(player, PRECIO_PLIEGUES_VITALIDAD)
            self._require_espacio_disponible(player, "E")

            player.monedas -= PRECIO_PLIEGUES_VITALIDAD
            player.ocupar_espacio_accion("E")
            player.ajustar_vitalidad(+1)
            return

        # --- Rama: avanzar (reparto de espacios comprados) ---
        if not reparto:
            raise InvalidActionError(
                "La opción 'avanzar' de la Acción E requiere 'reparto': un mapa "
                "{slot_index: espacios} indicando dónde aplicar los pliegues."
            )
        if any(not isinstance(n, int) or n < 1 for n in reparto.values()):
            raise InvalidActionError(
                f"Cada valor de 'reparto' debe ser un entero >= 1. Recibido: {reparto}"
            )

        total: int = sum(reparto.values())
        if total not in PRECIO_PLIEGUES:
            raise InvalidActionError(
                f"El total de espacios a plegar debe estar entre "
                f"{min(PRECIO_PLIEGUES)} y {max(PRECIO_PLIEGUES)}. Recibido: {total}"
            )
        precio: int = PRECIO_PLIEGUES[total]

        if len(reparto) > 1 and not player.tecnologias.camara_b:
            raise RuleViolationError(
                "Repartir los pliegues entre varias masas requiere la "
                "tecnología Cámara B instalada."
            )
        if len(reparto) > 2:
            raise RuleViolationError(
                f"La Cámara B permite repartir los pliegues entre 2 masas como "
                f"máximo. Recibido: {len(reparto)}."
            )

        self._require_monedas(player, precio)
        self._require_espacio_disponible(player, "E")

        # Validar todos los slots ANTES de mutar ninguno (fail-fast).
        pliegues: List[Tuple[FermentationSlot, int]] = []
        for slot_index, espacios in reparto.items():
            if not (0 <= slot_index <= 2):
                raise RuleViolationError(
                    f"slot_index debe estar en [0, 2]. Recibido: {slot_index}"
                )
            slot = player.estaciones_fermentacion[slot_index]
            if slot is None:
                raise RuleViolationError(
                    f"La estación {slot_index} de '{player.nombre}' está vacía. "
                    "No hay masa activa que plegar."
                )
            pliegues.append((slot, espacios))

        # Aplicar. Sin tope superior: el sobrepliegue hacia la zona
        # sobrefermentada es legal y es el riesgo que equilibra la escalera.
        player.monedas -= precio
        player.ocupar_espacio_accion("E")
        for slot, espacios in pliegues:
            slot.posicion_track += espacios

    def accion_F_hornear(
        self,
        player: Player,
        slot_index: int,
    ) -> HorneadoRecord:
        """
        Acción F: Hornear y Vender — Finalización de Protocolo
        (GDD v0.0.2, Módulo III §F; antes «Hornear», ACTIONS_REGISTRY.md §2F).

        Costo:   1 PA.
        Efecto:  Finaliza la fermentación de la masa en ``slot_index`` y la
                 vende de inmediato. Los puntos, datos, monedas y archivado se
                 delegan a ``engine.resolver_horneado()``, que implementa la
                 tabla completa de puntuación/venta por zona.

        Tabla de resolución (engine._calcular_puntos_zona / _calcular_monedas_zona):
          · Zona óptima      → puntos_optimos + monedas_optima
                               (+ bono_sabor_pts y +2 Monedas si el cubo estaba
                               sellado). Acredita Datos de Investigación.
          · Pre-fermento     → puntos_pre_fermento + monedas_pre_fermento (sin Datos).
                               El bono de sabor SÍ aplica en esta zona.
          · Colapso          → penalizacion_colapso + monedas_colapso (sin bono
                               ni Datos — venta de recuperación de coste).

        Nota: El PA se consume aquí antes de delegar para mantener la semántica
        de que la Acción F tiene costo 1 PA. El engine.resolver_horneado()
        es agnóstico al costo de PA (también lo llama la Fase III con 0 PA).

        Args:
            player: Jugador que hornea.
            slot_index: Índice de la estación con la masa a hornear (0, 1 o 2).

        Returns:
            HorneadoRecord con el resultado completo del horneado.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            RuleViolationError: La estación está vacía.
        """
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "F")

        if not (0 <= slot_index <= 2):
            raise RuleViolationError(
                f"slot_index debe estar en [0, 2]. Recibido: {slot_index}"
            )
        if player.estaciones_fermentacion[slot_index] is None:
            raise RuleViolationError(
                f"La estación {slot_index} de '{player.nombre}' está vacía. "
                "No hay masa activa para hornear."
            )

        # Una masa en CRECIMIENTO todavía no es pan: no se puede hornear. Se mide
        # contra las zonas EFECTIVAS del propietario (el Módulo Analítico ensancha la
        # óptima), aunque el crecimiento en sí nunca se amplía — de modo que esta
        # frontera no se mueve bajo los pies del jugador. Ver Recipe.zonas_efectivas.
        slot = player.estaciones_fermentacion[slot_index]
        ampliacion = self._engine.ampliacion_zona_optima(player)
        if slot.recipe.esta_en_crecimiento(slot.posicion_track, ampliacion):
            _, pre_fermento, _, _ = slot.recipe.zonas_efectivas(ampliacion)
            raise RuleViolationError(
                f"'{slot.recipe.nombre}' está en la zona de Crecimiento "
                f"(posición {slot.posicion_track}): la masa todavía no es pan y no "
                f"se puede hornear. Podrá hornearse a partir de la casilla "
                f"{pre_fermento[0]}. Para abandonarla, usa el Simposio Técnico."
            )

        # Consumir PA antes de delegar (la delegación no consume PA)
        player.consumir_punto_accion("F")

        # Delegar resolución de puntuación, archivado y recuperación de dado
        return self._engine.resolver_horneado(
            player, slot_index, fue_colapso=False
        )

    def accion_G_investigar_protocolo(
        self,
        player: Player,
        indice_mercado: int,
        indice_descartar: Optional[int] = None,
    ) -> None:
        """
        Acción G: Investigar Protocolo (ACTIONS_REGISTRY.md §2G).

        Costo:   1 PA + ``PRECIO_RECETA[receta.grado]`` Monedas (Básica 1,
                 Intermedia 2, Avanzada 3). El precio es aditivo: el PA y el
                 espacio de acción siguen siendo la escasez real.
        Efecto:  Toma una carta de receta del mercado central y la coloca en
                 estado inactivo («boca arriba») en la Carpeta de Proyectos.
                 El slot del mercado queda vacío hasta el próximo Protocolo
                 de Refresco (CORE_MECHANICS.md §2, Fase I).

        Límite de carpeta: máximo 3 recetas (PLAYER_STATE.md §1).
          · Si hay espacio (< 3): la receta se añade directamente.
          · Si está llena (== 3): se DEBE especificar ``indice_descartar``
            para reemplazar una receta existente.

        Args:
            player: Jugador que investiga.
            indice_mercado: Posición en ``market.recetas_visibles`` (0 = más nueva).
            indice_descartar: Índice en ``player.carpeta_proyectos`` a eliminar
                antes de añadir la nueva. Requerido si la carpeta está llena.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            MissingResourceError: Monedas insuficientes para esa receta.
            CarpetaFullError: Carpeta llena y sin especificar descarte, o
                ``indice_descartar`` fuera de rango.
            InvalidActionError: ``indice_mercado`` fuera de rango.
            MarketSlotEmptyError: El slot de mercado está vacío (ya fue tomado).
        """
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "G")

        # Validar índice de mercado (semántico; el mercado también valida)
        num_slots = len(self._engine.market.recetas_visibles)
        if not (0 <= indice_mercado < num_slots):
            raise InvalidActionError(
                f"indice_mercado={indice_mercado} fuera de rango. "
                f"El mercado tiene {num_slots} slots (0 a {num_slots - 1})."
            )

        # Validar estado de carpeta antes de tomar la receta
        carpeta_llena: bool = len(player.carpeta_proyectos) >= 3
        if carpeta_llena:
            if indice_descartar is None:
                raise CarpetaFullError(
                    f"La Carpeta de Proyectos de '{player.nombre}' está llena "
                    "(3/3). Especifica indice_descartar para reemplazar una "
                    "receta antes de investigar la nueva."
                )
            if not (0 <= indice_descartar < len(player.carpeta_proyectos)):
                raise CarpetaFullError(
                    f"indice_descartar={indice_descartar} fuera de rango. "
                    f"La carpeta tiene {len(player.carpeta_proyectos)} recetas "
                    f"(índices 0-{len(player.carpeta_proyectos) - 1})."
                )

        # Validar el precio ANTES de tomar la carta. `tomar_receta` la RETIRA del
        # mercado, así que cobrar después significaría que un jugador sin Monedas
        # destruye una carta al fallar: fail-fast obliga a mirar sin tocar primero.
        en_slot: Optional[Recipe] = self._engine.market.recetas_visibles[indice_mercado]
        if en_slot is None:
            raise MarketSlotEmptyError(
                f"El slot {indice_mercado} del mercado está vacío. "
                "Se repone en el Protocolo de Refresco del día siguiente."
            )
        precio: int = PRECIO_RECETA[en_slot.grado]
        self._require_monedas(player, precio)

        # Tomar receta del mercado (puede lanzar MarketSlotEmptyError)
        receta: Recipe = self._engine.market.tomar_receta(indice_mercado)

        # Aplicar efectos
        player.consumir_punto_accion("G")
        player.monedas -= precio

        if carpeta_llena and indice_descartar is not None:
            descartada: Recipe = player.carpeta_proyectos.pop(indice_descartar)
            self._engine.market.descarte_recetas.append(descartada)

        player.carpeta_proyectos.append(receta)

    def accion_simposio_tecnico(
        self,
        player: Player,
        origen: str,
        indice: int,
    ) -> None:
        """
        Simposio Técnico — Generación de Datos (ACTIONS_REGISTRY.md §2 «Simposio»).

        Costo:   1 PA.
        Efecto:  Descarta una carta de receta de la carpeta de proyectos o
                 de una estación de fermentación activa para obtener
                 +1 Dato de Investigación inmediatamente.

        Cuando se descarta desde una estación:
          · La masa en fermentación se pierde sin puntos ni penalización.
            (Distinto al horneado de emergencia, que sí aplica penalización.)
          · El dado de inóculo se recupera (dados_inoculo += 1, máx 3).

        Args:
            player: Jugador que ejecuta el simposio.
            origen: ``"carpeta"`` para descartar de carpeta_proyectos;
                    ``"estacion"`` para descartar una masa activa.
            indice: Índice en la lista correspondiente.

        Raises:
            InvalidActionError: ``origen`` inválido o ``indice`` fuera de rango.
            NotEnoughActionPointsError: PA insuficientes.
            RuleViolationError: La estación indicada está vacía.
        """
        if origen not in ("carpeta", "estacion"):
            raise InvalidActionError(
                f"origen debe ser 'carpeta' o 'estacion'. Recibido: '{origen}'"
            )

        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "simposio")

        if origen == "carpeta":
            if not (0 <= indice < len(player.carpeta_proyectos)):
                raise InvalidActionError(
                    f"Índice {indice} fuera de rango para carpeta_proyectos "
                    f"(tamaño actual: {len(player.carpeta_proyectos)})."
                )
            player.consumir_punto_accion("simposio")
            descartada: Recipe = player.carpeta_proyectos.pop(indice)
            self._engine.market.descarte_recetas.append(descartada)
            player.datos_investigacion += 1

        else:  # "estacion"
            if not (0 <= indice <= 2):
                raise InvalidActionError(
                    f"Índice de estación debe ser 0, 1 o 2. Recibido: {indice}"
                )
            slot = player.estaciones_fermentacion[indice]
            if slot is None:
                raise RuleViolationError(
                    f"La estación {indice} de '{player.nombre}' está vacía. "
                    "No hay masa activa que descartar en el Simposio Técnico."
                )
            player.consumir_punto_accion("simposio")
            self._engine.market.descarte_recetas.append(slot.recipe)
            player.estaciones_fermentacion[indice] = None
            player.dados_inoculo = min(3, player.dados_inoculo + 1)
            player.datos_investigacion += 1

    # ==================================================================
    # ACCIONES AUXILIARES
    # ==================================================================

    def accion_auxiliar_horas_extras(self, player: Player) -> None:
        """
        Acción Auxiliar: Horas Extras (ACTIONS_REGISTRY.md §3 «Horas Extras»).

        Tipo:    Acción gratuita (0 PA).
        Costo:   1 Dato de Investigación.
        Efecto:  +1 Punto de Acción inmediato al jugador.
        Límite:  Solo 1 vez por ronda (por jugador). ``player.horas_extras_usadas``
                 se resetea automáticamente al inicio de cada Fase II.

        Args:
            player: Jugador que activa las Horas Extras.

        Raises:
            InvalidActionError: Ya se usó esta acción en el día actual.
            MissingResourceError: Datos de Investigación insuficientes.
        """
        if player.horas_extras_usadas:
            raise InvalidActionError(
                f"'{player.nombre}' ya usó Horas Extras en este día. "
                "Solo está permitido una vez por ronda."
            )

        self._require_datos(player, 1)

        # Aplicar: consumir dato y otorgar PA extra (Player marca horas_extras_usadas)
        player.datos_investigacion -= 1
        player.otorgar_punto_accion_extra()

    def accion_auxiliar_pedido_urgencia(
        self,
        player: Player,
        harina_urgencia: Optional[TipoHarina] = None,
        agua_tokens_urgencia: int = 0,
    ) -> None:
        """
        Acción Auxiliar: Pedido de Urgencia (GDD v0.0.2, Módulo V §2 «Logística»).

        Tipo:    Acción gratuita (0 PA) — no consume un Punto de Acción y no
                 termina el turno del jugador.
        Costo:   1 Dato de Investigación.
        Efecto:  Ignora el mercado y el precio vigente por completo: obtiene
                 directamente un recurso de la reserva general.
        Límite:  Ninguno (a diferencia de Horas Extras, el GDD no impone un
                 tope por ronda; se autolimita por Datos de Investigación
                 disponibles).

        Requiere: ``harina_urgencia`` (tipo de harina, otorga 100%) XOR
                  ``agua_tokens_urgencia > 0`` (tokens de agua, 5% c/u).

        Args:
            player: Jugador que activa el Pedido de Urgencia.
            harina_urgencia: Tipo de harina a obtener (100% directo).
            agua_tokens_urgencia: Tokens de agua a obtener.

        Raises:
            InvalidActionError: Ni harina ni agua especificadas, o ambas a la vez.
            MissingResourceError: Datos de Investigación insuficientes.
        """
        tiene_harina = harina_urgencia is not None
        tiene_agua = agua_tokens_urgencia > 0

        if not tiene_harina and not tiene_agua:
            raise InvalidActionError(
                "Pedido de Urgencia: especifica harina_urgencia "
                "o agua_tokens_urgencia > 0 para indicar el recurso deseado."
            )
        if tiene_harina and tiene_agua:
            raise InvalidActionError(
                "Pedido de Urgencia: elige UN solo tipo de recurso. "
                "No puedes pedir harina y agua en el mismo pedido."
            )

        self._require_datos(player, 1)

        # Aplicar (0 PA — no se consume punto de acción)
        player.datos_investigacion -= 1

        if harina_urgencia is not None:
            player.reserva_harina[harina_urgencia.value] += 100
        else:
            player.reserva_agua += agua_tokens_urgencia

    # ==================================================================
    # PROTOCOLOS DE EMERGENCIA (solo cuando Vitalidad == 0)
    # ==================================================================

    def accion_H_recultivo_manual(self, player: Player) -> None:
        """
        Protocolo de Emergencia H: Re-cultivo Manual (ACTIONS_REGISTRY.md §3).

        Precondición: ``player.en_estado_contaminacion == True``
            (Vitalidad llegó a 0 en algún punto del juego).

        Costo:   1 PA + 50% Harina (cualquier tipo). Sin costo de agua
                 (GDD v0.0.2, Módulo III §3H).
        Efecto:  · Retira el estado de Contaminación.
                 · Establece Vitalidad = 1 y Acidez = 1 directamente
                   (sin pasar por los clamps de ajustar_vitalidad para
                   evitar re-activar la penalización).

        Nota de diseño: se asignan directamente ``vitalidad = 1`` y ``acidez = 1``
        en lugar de usar ``ajustar_*`` para no incrementar ``contador_contaminaciones``
        de nuevo. La penalización (-3 PM) ya fue contabilizada cuando la vitalidad
        llegó a 0 por primera vez.

        Args:
            player: Jugador en estado de Contaminación.

        Raises:
            InvalidActionError: El jugador NO está contaminado.
            NotEnoughActionPointsError: PA insuficientes.
            MissingResourceError: Harina insuficiente.
        """
        self._require_contaminado(player, "Protocolo H (Re-cultivo Manual)")
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "H")
        self._require_cualquier_harina(player, 50)

        # Aplicar
        player.consumir_punto_accion("H")

        # Consumir 50% de harina (deduce de los tipos con mayor reserva primero)
        harina_a_consumir = 50
        for tipo in ("Blanca", "Centeno", "Integral"):
            if harina_a_consumir <= 0:
                break
            consumible = min(player.reserva_harina[tipo], harina_a_consumir)
            player.reserva_harina[tipo] -= consumible
            harina_a_consumir -= consumible

        # Restablecer cultivo base y limpiar contaminación
        player.vitalidad = 1
        player.acidez = 1
        player.en_estado_contaminacion = False

    def accion_I_inoculo_emergencia(self, player: Player) -> None:
        """
        Protocolo de Emergencia I: Inóculo de Emergencia (ACTIONS_REGISTRY.md §3).

        Precondición: ``player.en_estado_contaminacion == True``
            (Vitalidad llegó a 0 en algún punto del juego).

        Costo:   1 PA + 1 Dato de Investigación (GDD v0.0.2, Módulo III §3I).
        Efecto:  · Retira el estado de Contaminación.
                 · Establece Vitalidad = 2 y Acidez = 2 directamente.
                   (Resultado superior al Re-cultivo Manual.)

        Nota de diseño: se asignan directamente los valores por la misma razón
        que en accion_H: evitar re-contabilizar la penalización de contaminación.

        Args:
            player: Jugador en estado de Contaminación.

        Raises:
            InvalidActionError: El jugador NO está contaminado.
            NotEnoughActionPointsError: PA insuficientes.
            MissingResourceError: Datos de Investigación insuficientes.
        """
        self._require_contaminado(player, "Protocolo I (Inóculo de Emergencia)")
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "I")
        self._require_datos(player, 1)

        # Aplicar
        player.consumir_punto_accion("I")
        player.datos_investigacion -= 1

        # Restablecer cultivo base y limpiar contaminación
        player.vitalidad = 2
        player.acidez = 2
        player.en_estado_contaminacion = False
