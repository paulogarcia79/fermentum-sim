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
    engine.py.
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

    engine.iniciar_dia()
    while (player := engine.jugador_activo) is not None:
        manager.accion_A_alimentar(player, tipo_harina="Blanca")
        manager.accion_F_hornear(player, slot_index=0)   # cierra la visita
    engine.resolver_fase_III()
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
    COSTE_REFRESCO_AGUA,
    DATOS_JEFATURA,
    DATOS_SIMPOSIO,
    MAX_DATOS_PONENCIA,
    MONEDAS_MOSTRADOR,
    PRECIO_AGUA,
    PRECIO_CONTRATO_MOLINO,
    PRECIO_DATO_SIMPOSIO,
    PRECIO_DESCARTE,
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
    TecnologiaID.COMERCIANTE: 3,
}
"""
Coste en Datos de Investigación de cada mejora de laboratorio (Acción D).
Fuente: ACTIONS_REGISTRY.md §2D.

Comerciante vale 3 (el escalón de la Incubadora) porque su beneficio es un goteo:
una visita al mercado toca entre una y tres compras, así que devuelve 1-3 Monedas
por día de compras y se amortiza en dos o tres visitas si se compra pronto —
claramente comprable en la apertura y bastante mediocre al final, que es la
decisión de tempo que se quiere. No 2, porque a precio de Criopreservación sería
la primera compra obvia de todas las partidas y aplanaría la elección; no 4,
porque un goteo de -1 difícilmente amortiza el precio de las dos mejoras que
tocan la puntuación directamente, y esa es exactamente la trampa aritmética que
hubo que rescatar en el Módulo Analítico.
"""

DESCUENTO_COMERCIANTE: int = 1
"""
Monedas que la tecnología Comerciante descuenta de **cada transacción de compra**
de la Acción C: bolsa y media bolsa de harina, lote de agua y la firma del
Contrato con el Molino. Tres reglas la delimitan, y las tres son estructurales:

  · **Sólo compras, nunca ventas.** Mejorar también la venta duplicaría el
    problema de abajo en vez de dejarlo acotado, y no hay ninguna razón temática
    para que un comprador cobre más al vender.

    **Lo que el ciclo comprar→vender hace de verdad, medido y aceptado**, porque
    es contraintuitivo y la primera versión de este comentario lo tenía mal:
    comprar sube el visor una casilla, así que la venta posterior cobra el precio
    de la casilla siguiente. En Blanca la horquilla compra/venta es de 1 Moneda
    *y* el visor se mueve 1, de modo que los dos se cancelan **exactamente**: la
    ida y vuelta en Blanca ya era de saldo CERO sin ninguna tecnología. Por eso
    «no tocar la venta» no basta por sí solo para cerrar el arbitraje — con el
    descuento, el ciclo de Blanca pasa a dar **+1 Moneda** (Integral queda en 0 y
    Centeno sigue en -1; `tests/test_comerciante.py` recorre las 15 celdas).

    Lo que sí lo acota es **el espacio de acción, no el precio**: la Regla de
    Exclusividad prohíbe comprar y vender la misma harina en una visita, y el
    espacio C se agota una vez al día, así que el ciclo completo cuesta **dos
    días** de acceso al mercado para ganar 1 Moneda. Cualquier otra cosa que se
    haga con esos dos PA rinde más — vender una bolsa que el Molino produjo
    gratis paga 5 en un solo PA —, así que es una jugada estrictamente dominada,
    no una bomba. Se acepta a ojos abiertos y queda medido en el test; si algún
    día la Bolsa deja de moverse 1 casilla por transacción, o el espacio C deja
    de ser único por día, hay que rehacer esta cuenta.
  · **Suelo de 1 Moneda**, nunca 0. Una compra gratuita movería el visor sin
    coste, y con media bolsa de Blanca en posición 1 eso sería un empujón
    ilimitado del mercado con el que castigar a los demás. Que toda compra
    cueste algo es lo que mantiene el visor ligado a un gasto real.
  · **El visor se mueve exactamente igual.** Una transacción es una señal de
    mercado con independencia de su precio — el mismo argumento por el que media
    bolsa mueve el visor tanto como una entera.

Nótese que en las tres filas de ``engine.PRECIOS_HARINA`` el precio de compra
sube de 1 en 1 por posición, así que para una bolsa entera el descuento equivale
a comprar una casilla más barata; se expresa como un descuento plano y no como
un desplazamiento del visor porque así cubre también el agua y el molino, que no
tienen visor, con una sola regla en vez de tres.
"""

TIPOS_HARINA_VALIDOS: Dict[str, TipoHarina] = {t.value: t for t in TipoHarina}
"""Lookup de string → TipoHarina, usado para validar transacciones de mercado."""

LOTES_AGUA_VALIDOS = (10, 30, 60, 100)
"""Tamaños de lote válidos (%) para Comprar Lote de Agua en Visitar el Mercado."""

RECURSO_MOLINO = "molino"
"""
Clave de ``tipo_recurso`` con la que una transacción de la Acción C firma el
Contrato con el Molino, en lugar de nombrar una harina.

Es una clave propia y no el tipo de harina contratado **a propósito**: la Regla
de Exclusividad de la visita se aplica sobre ``tipo_recurso``, así que darle la
suya hace que dos contratos en la misma visita choquen entre sí (que es lo que
queremos: un contrato por jugador y para siempre) sin impedir firmar el contrato
de Centeno y comprar Centeno en esa misma visita — que es justo la jugada natural
el día que firmas, porque el molino no entrega hasta la noche.
"""

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


OPERACIONES_ACIDEZ: Dict[str, Tuple[int, str, Dict[int, int]]] = {
    "subir": (+1, "agua", COSTE_REFRESCO_AGUA),
    "bajar": (-1, "monedas", PRECIO_DESCARTE),
}
"""
Operación del wire → (signo, recurso que se paga, escalera de coste).

Los dos sentidos del Descarte cobran en recursos DISTINTOS — subir es añadir agua,
bajar es tirar cultivo y reponerlo — así que sin esta tabla el método tendría dos
ramas paralelas donde hoy tiene una sola: validar el saldo, cobrarlo y mover la
acidez leen todos la misma fila. Es el mismo motivo por el que existe
``OPERACIONES_HARINA``: si un sentido nuevo (o una escalera nueva) obliga a tocar
tres sitios, tarde o temprano se tocan dos.
"""


# ===========================================================================
# SECCIÓN 2: ACTION MANAGER
# ===========================================================================


HARINA_RECULTIVO_MANUAL: int = 30
"""
Porcentaje de harina (cualquier tipo) que cuesta el Protocolo H: Re-cultivo Manual.

Bajó de 50 a 30 al endurecerse el resto del juego alrededor de la contaminación. El
Protocolo I cuesta 1 Dato, y los Datos salen de hornear bien, de reclamar la Jefatura o
del Simposio Técnico (sacrificando un horneado o comprándolos en una ponencia, que
también exige tener ya un pan en el Archivo), así que un jugador contaminado temprano
puede no tener ninguno; H es la vía comprable y tiene que seguir siéndolo. A 30% queda
dentro de la bolsa inicial de Patrocinio incluso después de varias Acciones A, de modo
que rescatarse nunca obliga a gastar antes una visita entera en el mercado.

Sigue siendo el rescate peor de los dos (Vitalidad/Acidez a 1, frente a 2 del Protocolo I).
"""


HARINA_PEDIDO_URGENCIA: int = 50
"""
Porcentaje de harina (media bolsa, 5 tokens) que entrega el Pedido de Urgencia.

Bajó de 100 a 50 porque el Pedido era, además de un rescate logístico, el mejor
arbitraje del juego: 1 Dato entregaba una bolsa entera de CUALQUIER harina, y una
bolsa entera de Centeno en posición 5 se revende en el acto por 7 Monedas. Con el
Contrato con el Molino haciendo que vender harina sea por fin una línea económica
real, ese bucle habría escalado antes que ninguna otra cosa.

Media bolsa conserva la función de emergencia (2 Datos siguen completando una bolsa
para una receta Básica, y una Intermedia sólo pide 50% de cada harina, o sea un
Pedido exacto por mitad) y parte el arbitraje por más de la mitad: la venta de media
bolsa redondea hacia ABAJO (``Market.precio_venta_harina``), así que el Centeno en
posición 5 pasa de 7 a 3 Monedas por Dato.

No añade estado persistido: sigue siendo un número que la acción entrega.
"""


AGUA_PEDIDO_URGENCIA: int = 6
"""
Tokens de agua (5% c/u, o sea un 30%) que entrega el Pedido de Urgencia.

Es una cantidad FIJA, y ese es el arreglo: antes el jugador escribía cuántos tokens
quería y nada acotaba el número. Una receta pide entre 10 y 17 tokens y un lote del
100% cuesta de 7 a 14 Monedas en el mercado, así que 1 Dato compraba toda el agua de
la partida entera. El agua no se puede revender, de modo que no había arbitraje en
Monedas como con la harina, pero el único freno real era la penalización por
desperdicio del final (-1 PM por cada 3 tokens sin usar), que es un precio ridículo
por saltarse el Suministro Hídrico durante toda la partida.

Por qué 6 y no otro número: es el tamaño del lote del 30%, que cuesta entre 2 y 6
Monedas según la temperatura — el mismo orden de magnitud que la media bolsa de
harina (1 a 3 Monedas), de modo que el Dato compra lo mismo elijas lo que elijas. Y
mantiene la historia que ya cuenta la harina: igual que dos Pedidos completan una
bolsa, dos Pedidos cubren aproximadamente el agua de una receta.

Coincide hoy con ``engine.AGUA_TOKENS_POR_LOTE[30]`` pero NO se deriva de él a
propósito, por el mismo motivo que ``DATOS_SIMPOSIO`` no se deriva de
``PRECIO_RENTA`` pese a valer lo mismo: son dos reglas distintas, y redimensionar
los lotes del mercado no debería rebalancear en silencio una acción de rescate.
"""


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

    @staticmethod
    def _precio_compra_efectivo(player: Player, precio: int) -> int:
        """
        Precio final (en Monedas) que paga `player` por UNA transacción de compra
        de la Acción C, aplicando la tecnología Comerciante si la tiene instalada.

        Se aplica a las tres compras de la visita — harina, agua y la firma del
        Molino — y **a ninguna venta**; ver ``DESCUENTO_COMERCIANTE`` para por qué
        el lado de venta queda fuera y por qué el suelo es 1 y no 0.

        Existe como función y no como dos restas escritas en los dos bucles de
        ``accion_C_visitar_mercado`` (simular saldos / aplicar) por la misma razón
        que existe ``OPERACIONES_HARINA``: los dos bucles tienen que cobrar
        exactamente lo mismo, y con un único sitio donde vive la cuenta no pueden
        desviarse. Un descuento que sólo estuviera en el bucle de simulación
        dejaría comprar sin Monedas suficientes; sólo en el de aplicación,
        rechazaría compras que el jugador sí puede pagar.
        """
        if not player.tecnologias.comerciante:
            return precio
        return max(1, precio - DESCUENTO_COMERCIANTE)

    # ==================================================================
    # ACCIONES PRINCIPALES (Costo: 1 PA)
    # ==================================================================

    def accion_A_alimentar(
        self,
        player: Player,
        tipo_harina: Optional[str] = None,
    ) -> None:
        """
        Acción A: Alimentar / Refrescar el Cultivo (ACTIONS_REGISTRY.md §3).

        Costo:      0 PA (acción auxiliar gratuita, una vez por Fase II).
        Recursos:   10% de harina del tipo indicado.
        Efecto:     +1 Vitalidad (máx. 6).

        Solo puede ejecutarse una vez por Fase II («accion_alimentar_usada»), y
        repone exactamente el -1 que el desgaste metabólico resta cada Fase III:
        un jugador que alimenta a diario ORBITA su Vitalidad inicial.

        Nota de diseño: esta acción **ya no toca la Acidez**. Tuvo una mitad de
        agua que daba +1 Acidez, pero mientras la Acidez sólo sabía subir esa
        mitad era un trinquete — y peor, uno que convenía accionar siempre,
        porque la Madurez premiaba el nivel bruto. Todo el control voluntario de
        la Acidez vive ahora en la acción «Descarte»
        (``accion_descarte_acidez``), que la mueve en los dos sentidos; la
        Acción A quedó reducida a lo único que hacía sin ambigüedad, que es el
        mantenimiento de la Vitalidad.

        Args:
            player: Jugador que ejecuta la acción.
            tipo_harina: Clave del tipo de harina a consumir ("Blanca", "Centeno"
                o "Integral").

        Raises:
            InvalidActionError: Ya usada este turno, o tipo_harina inválido.
            MissingResourceError: Si el jugador no tiene la harina pedida.
        """
        if player.accion_alimentar_usada:
            raise InvalidActionError(
                f"'{player.nombre}' ya usó la Acción A este turno de Fase II. "
                "Solo puede alimentarse una vez por fase."
            )

        # --- Bloque de validaciones (Fail-Fast) ---
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

        # --- Aplicar efectos (0 PA) ---
        player.reserva_harina[tipo_harina] -= 10
        player.ajustar_vitalidad(+1)
        player.accion_alimentar_usada = True

    def accion_descarte_acidez(
        self,
        player: Player,
        operacion: str,
        niveles: int,
    ) -> None:
        """
        Acción «Descarte»: ajustar la Acidez del cultivo base en ambos sentidos.

        Costo:      0 PA, pero OCUPA su espacio de acción (una vez por día).
        Recursos:   según el sentido, ver ``OPERACIONES_ACIDEZ``.
                      · ``"subir"``: ``COSTE_REFRESCO_AGUA[niveles]`` tokens de agua
                        (2 / 5 / 9 por +1 / +2 / +3).
                      · ``"bajar"``: ``PRECIO_DESCARTE[niveles]`` Monedas
                        (1 / 3 / 6 por -1 / -2 / -3).
        Efecto:     Acidez ± ``niveles``, con el clamp [0, 6] de ``ajustar_acidez``.

        Un solo sentido por visita: mezclar los dos en la misma llamada no
        significaría nada que no signifique ya su diferencia.

        Notas de diseño, las tres load-bearing:

        · **No cuesta PA pero sí ocupa espacio.** Es el mismo argumento que la
          Acción E: las Monedas son RENOVABLES (la Acción C vende harina cada
          día), así que "el precio lo limita" es falso — sin el tope de una vez
          por día, un jugador rico compraría visitas hasta vaciar la bolsa. Por
          eso llama a ``ocupar_espacio_accion`` y no a ``consumir_punto_accion``.

        · **No emite ningún GameEvent.** Al ser gratuita en PA ocurre dentro de
          la ventana de deshacer, y ``GameSession.restaurar_checkpoint`` repone
          el motor entero desde un pickle: si esta acción escribiera en
          ``engine.eventos``, la lista ENCOGERÍA al deshacer y los punteros
          ``since`` / ``Last-Event-ID`` de cada cliente quedarían más allá del
          final. Ver el comentario del checkpoint en ``server/sessions.py``.

        · **Subir cuesta agua y bajar cuesta Monedas**, no al revés y no las dos
          lo mismo. Bajar la acidez es descartar parte del cultivo y reponerlo:
          se tira producto, y por eso se paga en la moneda del juego. Subirla es
          sólo añadir agua. La asimetría también protege al jugador arruinado,
          que conserva un sentido del dial cuando no le queda ni una Moneda.

        Args:
            player: Jugador que ejecuta la acción.
            operacion: ``"subir"`` o ``"bajar"`` (claves de ``OPERACIONES_ACIDEZ``).
            niveles: Casillas de acidez a mover, 1-3.

        Raises:
            EspacioAccionYaUsadoError: El espacio ya se ocupó hoy.
            InvalidActionError: Operación desconocida o ``niveles`` fuera de la escalera.
            MissingResourceError: Sin agua / sin Monedas para el escalón pedido.
        """
        if "descarte" in player.acciones_pa_usadas_hoy:
            raise EspacioAccionYaUsadoError(
                f"'{player.nombre}' ya ocupó el espacio de Descarte hoy. "
                "Solo puede ajustar su Acidez una vez por día."
            )

        if operacion not in OPERACIONES_ACIDEZ:
            raise InvalidActionError(
                f"operacion debe ser una de {sorted(OPERACIONES_ACIDEZ)}. "
                f"Recibido: {operacion!r}"
            )
        signo, recurso, escalera = OPERACIONES_ACIDEZ[operacion]

        if niveles not in escalera:
            raise InvalidActionError(
                f"niveles debe ser uno de {sorted(escalera)} para '{operacion}'. "
                f"Recibido: {niveles!r}"
            )
        coste = escalera[niveles]

        # --- Bloque de validaciones (Fail-Fast) ---
        if recurso == "agua":
            self._require_agua(player, coste)
        else:
            self._require_monedas(player, coste)

        # --- Aplicar efectos (0 PA, ocupa el espacio) ---
        if recurso == "agua":
            player.reserva_agua -= coste
        else:
            player.monedas -= coste
        player.ajustar_acidez(signo * niveles)
        player.ocupar_espacio_accion("descarte")

    def accion_B_iniciar_receta(
        self,
        player: Player,
        receta: Recipe,
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

        Lo que NO se sella aquí: el ``modificador_incubadora`` de la masa nace en 0
        y se fija noche a noche con la acción gratuita ``incubadora``
        (``accion_auxiliar_incubadora``). Antes se elegía en esta misma acción y
        quedaba clavado para siempre, de modo que instalar la Incubadora con una
        masa ya fermentando no servía de nada: el dial de esa masa era un 0 que
        nadie podía tocar. Un solo escritor para el campo, y ese escritor es la
        acción gratuita.

        Precondiciones:
          · La receta debe estar en player.carpeta_proyectos.
          · player.vitalidad >= 1 (dado_inoculo no puede ser 0).
          · player.dados_inoculo >= 1 (hay dados disponibles para sellar).
          · Debe existir una estación de fermentación libre.
            (Estación 03 solo con Cámara B activa.)

        Efectos sobre el estado:
          1. Consume 1 PA, las harinas impresas en la carta, tokens_agua exactos.
          2. Consume 1 dado de inóculo (dados_inoculo -= 1).
          3. Crea y coloca el FermentationSlot en la primera estación libre.
          4. Retira la receta de carpeta_proyectos.

        Args:
            player: Jugador que inicia la fermentación.
            receta: Carta a iniciar; debe estar en player.carpeta_proyectos.

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

        # El descuento de Alta Humedad lo aplica el engine, no esta línea: la
        # UI enseña el coste antes de decidir (`disponibilidad.insumos_receta`)
        # y debe salir el mismo número que aquí se cobra.
        tokens_agua_requeridos = self._engine.agua_requerida(receta)

        self._require_harinas(player, receta)
        self._require_agua(player, tokens_agua_requeridos)

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
          · ``tipo_recurso``: ``"Blanca" | "Integral" | "Centeno" | "agua" |
            "molino"``.
          · ``operacion``: para harina, una de ``OPERACIONES_HARINA``
            (``"comprar" | "comprar_media" | "vender" | "vender_media"``).
            El agua solo admite ``"comprar"`` (no existe venta de agua, y
            tampoco medio lote: ya tiene cuatro tamaños propios). El molino
            solo admite ``"contratar"``.
          · ``lote_pct``: requerido solo para agua, uno de
            ``LOTES_AGUA_VALIDOS`` (10, 30, 60, 100).
          · ``tipo_harina``: requerido solo para el molino, la harina que
            producirá el contrato.

        Regla de Exclusividad (GDD v0.0.2 §C): una visita puede incluir como
        máximo UNA transacción por tipo de recurso — comprar Blanca y vender
        Centeno y comprar un lote de agua en la misma visita está permitido;
        comprar Blanca dos veces, o comprar y vender Blanca, no lo está. El
        molino cuenta como su propio tipo de recurso (``RECURSO_MOLINO``), de
        modo que firmar el contrato de Centeno y comprar Centeno en la misma
        visita sí es legal — el molino no entrega hasta la noche.

        Contratar el Molino: paga ``PRECIO_CONTRATO_MOLINO[tipo]`` una sola vez
        y, desde esa misma noche, recibe ``RENDIMIENTO_MOLINO_PCT`` de esa
        harina en cada Fase III, para siempre. Un contrato por jugador y por
        partida: no se cancela, no se cambia de harina y no se revende. **No
        mueve el visor** — el molino produce fuera de la Bolsa, y que la
        producción propia no sea una señal de mercado es precisamente lo que
        hace que vender esa harina más tarde valga la pena.

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

        Tecnología **Comerciante**: si el jugador la tiene instalada, cada
        transacción de COMPRA de la visita — harina (bolsa o media), agua y la
        firma del Molino — cuesta ``DESCUENTO_COMERCIANTE`` Monedas menos, con
        suelo de 1. Las ventas cobran exactamente lo mismo que sin la tecnología
        y el visor se mueve igual en una compra con descuento que sin él; ver
        ``DESCUENTO_COMERCIANTE`` para el razonamiento de las tres reglas.

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
            RuleViolationError: Ya tiene un Contrato con el Molino firmado.
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

            if (
                tipo_recurso not in TIPOS_HARINA_VALIDOS
                and tipo_recurso != "agua"
                and tipo_recurso != RECURSO_MOLINO
            ):
                raise InvalidActionError(
                    f"tipo_recurso inválido: {tipo_recurso!r}. Debe ser "
                    f"'agua', {RECURSO_MOLINO!r} o uno de "
                    f"{sorted(TIPOS_HARINA_VALIDOS)}."
                )
            if tipo_recurso in tipos_vistos:
                raise InvalidActionError(
                    f"Regla de Exclusividad: solo se permite una transacción "
                    f"por tipo de recurso por visita. '{tipo_recurso}' repetido."
                )
            tipos_vistos.add(tipo_recurso)

            if tipo_recurso == RECURSO_MOLINO:
                if operacion != "contratar":
                    raise InvalidActionError(
                        "El Molino solo admite operacion='contratar' "
                        "(un contrato no se cancela ni se revende)."
                    )
                if player.contrato_molino is not None:
                    raise RuleViolationError(
                        f"'{player.nombre}' ya tiene un Contrato con el Molino "
                        f"de Harina {player.contrato_molino}. Solo se firma uno "
                        "por partida, y no puede cambiarse."
                    )
                tipo_harina = t.get("tipo_harina")
                if tipo_harina not in TIPOS_HARINA_VALIDOS:
                    raise InvalidActionError(
                        f"tipo_harina inválido para el Contrato con el Molino: "
                        f"{tipo_harina!r}. Debe ser uno de "
                        f"{sorted(TIPOS_HARINA_VALIDOS)}."
                    )
            elif tipo_recurso == "agua":
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

            if tipo_recurso == RECURSO_MOLINO:
                tipo = TIPOS_HARINA_VALIDOS[t["tipo_harina"]]
                monedas_sim -= self._precio_compra_efectivo(
                    player, PRECIO_CONTRATO_MOLINO[tipo]
                )
            elif tipo_recurso == "agua":
                lote_pct = t["lote_pct"]
                costo = self._precio_compra_efectivo(
                    player, PRECIO_AGUA[temp_actual][lote_pct]
                )
                monedas_sim -= costo
            else:
                tipo = TIPOS_HARINA_VALIDOS[tipo_recurso]
                direccion, cantidad = OPERACIONES_HARINA[operacion]
                if direccion == "comprar":
                    monedas_sim -= self._precio_compra_efectivo(
                        player, market.precio_compra_harina(tipo, cantidad)
                    )
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

            if tipo_recurso == RECURSO_MOLINO:
                tipo = TIPOS_HARINA_VALIDOS[t["tipo_harina"]]
                player.monedas -= self._precio_compra_efectivo(
                    player, PRECIO_CONTRATO_MOLINO[tipo]
                )
                player.contrato_molino = tipo.value
            elif tipo_recurso == "agua":
                lote_pct = t["lote_pct"]
                costo = self._precio_compra_efectivo(
                    player, PRECIO_AGUA[temp_actual][lote_pct]
                )
                player.monedas -= costo
                player.reserva_agua += AGUA_TOKENS_POR_LOTE[lote_pct]
            else:
                tipo = TIPOS_HARINA_VALIDOS[tipo_recurso]
                direccion, cantidad = OPERACIONES_HARINA[operacion]
                comprando = direccion == "comprar"
                if comprando:
                    player.monedas -= self._precio_compra_efectivo(
                        player, market.precio_compra_harina(tipo, cantidad)
                    )
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
          · Incubadora:       3 Datos  → dial ±1 casilla por masa y por noche
                                           (acción gratuita ``incubadora``).
          · Cámara B:         4 Datos  → desbloquea Estación 03 y mejora Acción E.
          · Módulo Analítico: 4 Datos  → ensancha la zona óptima ±1 casilla (y
                                         retrasa el colapso con ella) y sube los
                                         Datos del horneado a 2, o 3 en el centro
                                         exacto. **No** abre recetas: ninguna carta
                                         está restringida por tecnología desde que
                                         se borró `Recipe.req_tecnologico`.
          · Criopreservación: 2 Datos  → ignora el desgaste metabólico de
                                         Fase III (Estasis Biológica).
          · Comerciante:      3 Datos  → -1 Moneda (suelo 1) en cada compra de
                                         la Acción C; no toca las ventas ni el
                                         movimiento del visor.

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
                f"{pre_fermento[0]}. Iniciar una receta es un compromiso: no hay forma de "
                "abandonar una masa, así que fermentará hasta hornearse o colapsar."
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
        modo: str,
        indice: Optional[int] = None,
        datos: Optional[int] = None,
    ) -> int:
        """
        Simposio Técnico — Generación de Datos (ACTIONS_REGISTRY.md §2 «Simposio»).

        Costo:   1 PA + **uno de dos pagos, a elegir con ``modo``**:
                 · ``"sacrificar"``: un horneado exitoso del archivo.
                 · ``"ponencia"``:   ``PRECIO_DATO_SIMPOSIO`` (5) Monedas por cada
                   Dato, de 1 a ``MAX_DATOS_PONENCIA`` (3) por visita.
        Efecto:  · ``"sacrificar"``: retira un ``HorneadoRecord`` de
                   ``archivo_horneado_exitoso`` y acredita ``DATOS_SIMPOSIO[grado]``
                   Datos (Básica 1, Intermedia 2, Avanzada 3).
                 · ``"ponencia"``: acredita ``datos`` Datos y cobra las Monedas. **El
                   archivo no se toca.**

        **Los dos modos exigen un archivo no vacío**, y el espacio es uno por día, así
        que una visita elige un modo y sólo uno. La puerta compartida es lo que impide
        que las Monedas del Patrocinio se conviertan en un grifo de Datos el Día 1: sigue
        sin haber ningún Dato en la mesa hasta el primer horneado. Es también la razón de que
        ``disponibilidad.py`` no necesita cláusula nueva: su condición (archivo no
        vacío + PA + espacio libre) ya vale para los dos modos.

        **El sacrificio** es la acción más destructiva del juego y la ÚNICA que saca un
        registro del archivo de horneados. Como ``puntos_horneados``,
        ``puntos_variedad`` y ``recetas_distintas_horneadas`` son ``@property`` sobre
        esa misma lista, sacrificar un registro le quita automáticamente:
          · sus Puntos de Maestría base (9-20 según la carta),
          · su renta diaria (``engine.PRECIO_RENTA``) para el resto de la partida,
          · posiblemente un escalón entero de «Variedad de Recetas» (hasta -5 PM),
          · y un paso del contador X/5 que dispara el fin de partida.
        Ningún rendimiento en Datos hace eso *eficiente*: es una palanca de emergencia,
        no una jugada de motor. Un jugador en 4/5 puede además usarla para bajar a 3/5 y
        retrasar el final — carísimo, pero legítimo. La carta física vuelve a
        ``market.descarte_recetas`` y puede reaparecer al rebarajar.

        **La ponencia** es el otro lado: no destruye nada y se paga con el dinero que
        «Ingresos de Panadería» acumula al final de la partida. El precio y el tope son
        cifras de equilibrio y su razonamiento vive en las docstrings de
        ``engine.PRECIO_DATO_SIMPOSIO`` (5 = la tasa de «Conversión de Riqueza», y por
        encima de lo que revende una media bolsa, así que no hay bucle) y
        ``engine.MAX_DATOS_PONENCIA`` (3 = lo que paga el mejor sacrificio, y la
        Jefatura sigue dominando el primer escalón). La tecnología **Comerciante no
        descuenta** aquí: sólo abarata las compras de la Acción C.

        Args:
            player: Jugador que ejecuta el simposio.
            modo: ``"sacrificar"`` o ``"ponencia"``. Sin valor por defecto a
                propósito: cada modo pide un parámetro distinto y un defecto
                silencioso escondería la migración de las llamadas antiguas.
            indice: Índice en ``player.archivo_horneado_exitoso``. Obligatorio con
                ``"sacrificar"`` y prohibido con ``"ponencia"``.
            datos: Datos a comprar (1..``MAX_DATOS_PONENCIA``). Obligatorio con
                ``"ponencia"`` y prohibido con ``"sacrificar"``.

        Returns:
            Datos de Investigación acreditados.

        Raises:
            InvalidActionError: ``modo`` desconocido, parámetro del modo contrario,
                ``indice`` fuera de rango o ``datos`` fuera de 1..3.
            NotEnoughActionPointsError: PA insuficientes.
            RuleViolationError: El archivo de horneados exitosos está vacío.
            MissingResourceError: Monedas insuficientes para la ponencia.
        """
        # --- 1. Forma de la llamada (antes que nada: no depende del estado) ---
        if modo not in ("sacrificar", "ponencia"):
            raise InvalidActionError(
                f"Simposio Técnico: modo {modo!r} inválido. "
                "Debe ser 'sacrificar' o 'ponencia'."
            )
        if modo == "sacrificar":
            if indice is None:
                raise InvalidActionError(
                    "Simposio Técnico: sacrificar necesita el 'indice' del horneado "
                    "en el Archivo."
                )
            if datos is not None:
                raise InvalidActionError(
                    "Simposio Técnico: elige UN solo modo por visita. Un sacrificio "
                    "no lleva cantidad de Datos: la paga el grado de la carta."
                )
        else:
            if datos is None:
                raise InvalidActionError(
                    "Simposio Técnico: una ponencia necesita cuántos 'datos' comprar "
                    f"(1..{MAX_DATOS_PONENCIA})."
                )
            if indice is not None:
                raise InvalidActionError(
                    "Simposio Técnico: elige UN solo modo por visita. Una ponencia no "
                    "retira ningún horneado del Archivo, así que no lleva 'indice'."
                )

        # --- 2. Coste común: PA y espacio ---
        self._require_pa(player, 1)
        self._require_espacio_disponible(player, "simposio")

        # --- 3. Puerta común: hace falta un pan en el Archivo en los DOS modos ---
        if not player.archivo_horneado_exitoso:
            raise RuleViolationError(
                f"'{player.nombre}' no tiene ningún horneado exitoso en el Archivo. El "
                "Simposio Técnico exige uno, sea para sacrificarlo o para presentar "
                "una ponencia sobre él."
            )

        # --- 4. Validación propia de cada modo ---
        coste_monedas: int = 0
        if modo == "sacrificar":
            assert indice is not None  # garantizado por la validación de forma
            if not (0 <= indice < len(player.archivo_horneado_exitoso)):
                raise InvalidActionError(
                    f"Índice {indice} fuera de rango para archivo_horneado_exitoso "
                    f"(tamaño actual: {len(player.archivo_horneado_exitoso)})."
                )
        else:
            # `bool` es subclase de `int`: True colándose como "1 Dato" sería un
            # parámetro que nadie escribió a propósito.
            if isinstance(datos, bool) or not isinstance(datos, int):
                raise InvalidActionError(
                    f"Simposio Técnico: 'datos' debe ser un entero, no {datos!r}."
                )
            if not (1 <= datos <= MAX_DATOS_PONENCIA):
                raise InvalidActionError(
                    f"Simposio Técnico: una ponencia compra entre 1 y "
                    f"{MAX_DATOS_PONENCIA} Datos. Recibido: {datos}."
                )
            coste_monedas = datos * PRECIO_DATO_SIMPOSIO
            self._require_monedas(player, coste_monedas)

        # --- 5. Aplicar (ya no puede fallar nada) ---
        player.consumir_punto_accion("simposio")
        if modo == "sacrificar":
            assert indice is not None
            record = player.archivo_horneado_exitoso.pop(indice)
            datos_ganados: int = DATOS_SIMPOSIO[record.recipe.grado]
            self._engine.market.descarte_recetas.append(record.recipe)
        else:
            assert datos is not None
            player.monedas -= coste_monedas
            datos_ganados = datos

        player.datos_investigacion += datos_ganados
        return datos_ganados

    def accion_reclamar_jefatura(self, player: Player) -> None:
        """
        Reclamar la Jefatura de Investigación (ACTIONS_REGISTRY.md §2 «Jefatura»).

        Costo:   1 PA. Termina la visita, como toda acción principal.
        Efecto:  +``DATOS_JEFATURA`` Datos de Investigación **ahora**, y el
                 jugador abre la Fase II **de mañana** como Investigador Jefe.
        Límite:  **Uno por día en toda la mesa** — no uno por jugador. Es el
                 único espacio global del tablero.

        El espacio es global porque el recurso también lo es: la primera
        posición del orden de turno es una sola, y dos jugadores no pueden
        comprarla el mismo día. Por eso la marca vive en el motor
        (``GameEngine.jefatura_reclamada_por``) y no en
        ``player.acciones_pa_usadas_hoy``, que es por jugador.

        Sustituye a la regla automática que daba la Jefatura a quien tuviera más
        Vitalidad. Aquella no era una decisión de nadie — el orden de turno se
        deducía del estado — y dejaba al Investigador Jefe sin más contenido que
        salir primero. Ahora ir primero se paga, y quien paga se lleva además el
        Dato: es la fuente RENOVABLE de Datos que faltaba, la que sostiene a las
        acciones que se pagan en Datos (Horas Extras, Pedido de Urgencia) sin
        depender de hornear en Zona Óptima. Está limitada por rotación, no por
        riqueza: un solo jugador la cobra cada día.

        El efecto llega mañana porque el orden de turno se calcula una sola vez
        al día, en la Fase I, y no se rebaraja a media jornada. Reclamar siendo
        ya Jefe es legal: es la forma de retener la Jefatura, y cuesta lo mismo.

        Args:
            player: Jugador que reclama la Jefatura.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
            RuleViolationError: Otro jugador ya la reclamó hoy.
        """
        # `reclamar_jefatura` valida y muta a la vez, así que va PRIMERO: es lo
        # único que puede lanzar aquí, y detrás de ella solo quedan mutaciones
        # que no fallan nunca. Al revés — cobrar el PA y descubrir después que
        # el espacio estaba ocupado — sería aplicar la acción a medias.
        self._require_pa(player, 1)
        self._engine.reclamar_jefatura(player)

        player.consumir_punto_accion("jefatura")
        player.datos_investigacion += DATOS_JEFATURA

    def accion_turno_mostrador(self, player: Player) -> None:
        """
        Turno de Mostrador (ACTIONS_REGISTRY.md §2 «Mostrador»).

        Costo:   1 PA. Termina la visita, como toda acción principal.
        Efecto:  +``MONEDAS_MOSTRADOR`` Moneda.
        Límite:  **Ninguno.** Es la única acción con costo de PA que NO ocupa
                 espacio: se repite mientras queden PA.

        Es el **suelo del tablero**, la acción que existe para que un turno nunca
        esté hueco. Antes de ella, un jugador con PA pero sin ninguna jugada útil
        — carpeta vacía, masa aún en Crecimiento, 0 Monedas, 0 Datos y la
        Jefatura ya reclamada por otro — no tenía más salida que ``pasar_turno``,
        que además renuncia a las acciones gratuitas del resto del día. Los PA
        sobrantes se perdían en silencio: la Fase III nunca lee ``puntos_accion``.

        Las tres decisiones que la sostienen están documentadas en
        ``engine.MONEDAS_MOSTRADOR``: paga en Monedas (no en Datos, que formaría
        bucle con Horas Extras, ni en Vitalidad, que pisa a la Acción A), paga 1
        (el valor exacto de la Acción E retirada, la que nadie tomaba), y no está
        condicionada a «no tener nada mejor que hacer» porque esa condición no es
        observable — la Acción C figura habilitada casi siempre. Se autolimita
        siendo débil, no estando cerrada.

        **No ocupa espacio a propósito.** Un jugador tiene 2 PA y el hueco puede
        darse dos veces el mismo día; un espacio de una visita por día resolvería
        medio problema. Por eso llama a ``consumir_punto_accion`` con
        ``ocupa_espacio=False`` y ``"mostrador"`` nunca entra en
        ``acciones_pa_usadas_hoy`` (PLAYER_STATE.md §1).

        Args:
            player: Jugador que atiende el mostrador.

        Raises:
            NotEnoughActionPointsError: PA insuficientes.
        """
        self._require_pa(player, 1)

        player.consumir_punto_accion("mostrador", ocupa_espacio=False)
        player.monedas += MONEDAS_MOSTRADOR

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

    def accion_auxiliar_estasis(self, player: Player, suspender: bool) -> None:
        """
        Acción Auxiliar: Estasis Biológica (ACTIONS_REGISTRY.md §3 «Estasis Biológica»).

        Tipo:    Acción gratuita (0 PA). No ocupa espacio de acción.
        Costo:   Ninguno.
        Requiere: Tecnología Criopreservación instalada.
        Efecto:  Fija ``player.estasis_suspendida``. Con la Estasis SUSPENDIDA el
                 cultivo base sufre esta noche el desgaste metabólico normal
                 (-1, o -2 con Aletargamiento Invernal); reactivada, lo ignora.
        Límite:  Ninguno — la bandera la limpia la Fase III tras aplicar el
                 desgaste (``GameEngine._aplicar_desgaste_metabolico``), así que
                 la Estasis se reactiva sola cada día.

        Notas de diseño (las cuatro decisiones que sostienen esta acción):

        · **Por qué existe.** La Acción B sella el Dado de Inóculo con la Vitalidad
          del día (``accion_B_iniciar_receta``) y nada en el juego BAJA la Vitalidad
          a propósito — el Descarte solo mueve la Acidez. Quien tiene Criopreservación
          y alimenta a diario sube 2→6 y se queda clavado en 6, de modo que sus masas
          avanzan 9-11 casillas por noche y sobrepasan de un salto la zona óptima
          (2-3 casillas) de las recetas Avanzadas. La mejora que se pagó en Datos
          inhabilitaba el tramo alto del catálogo justo para su dueño.
        · **Es un interruptor de dos sentidos, no un consumo.** Puede accionarse
          cuantas veces se quiera durante cualquier visita que el jugador ya tenga;
          por eso NO llama a ``ocupar_espacio_accion`` ni marca ninguna bandera de
          "ya usada", y por eso NO aparece en ``GameEngine._jugador_elegible``: no
          otorga visitas. Un ajuste no es un recurso.
        · **Por defecto la Estasis está ACTIVA.** El estado de partida es el de
          siempre, así que quien ignore la acción no pierde nada, y la suspensión
          dura una sola noche: un ajuste olvidado no puede contaminar a nadie.
        · **No emite ``GameEvent``.** Es una acción de 0 PA, es decir que ocurre
          dentro de la ventana de deshacer, y ``GameSession.restaurar_checkpoint``
          hace ``pickle.loads`` del motor entero: un evento aquí encogería
          ``engine.eventos`` al deshacer y dejaría colgados los punteros ``since``
          de los clientes — el invariante que existe para proteger ``AvisoAccion``.
          El rastro permanente lo deja el evento DESGASTE de la Fase III, que
          informa de ``estasis_suspendida``.

        Args:
            player: Jugador que ajusta su Estasis Biológica.
            suspender: True para sufrir el desgaste de esta noche, False para
                volver a ignorarlo.

        Raises:
            InvalidActionError: ``suspender`` no es un booleano.
            RuleViolationError: El jugador no tiene la Criopreservación instalada.
        """
        if not isinstance(suspender, bool):
            raise InvalidActionError(
                f"suspender debe ser un booleano. Recibido: {suspender!r}"
            )

        if not player.tecnologias.criopreservacion:
            raise RuleViolationError(
                f"'{player.nombre}' no puede ajustar la Estasis Biológica sin la "
                "tecnología Criopreservación instalada."
            )

        player.estasis_suspendida = suspender

    def accion_auxiliar_incubadora(
        self,
        player: Player,
        slot_index: int,
        modificador: int,
    ) -> None:
        """
        Acción Auxiliar: Incubadora (ACTIONS_REGISTRY.md §3 «Incubadora»).

        Tipo:    Acción gratuita (0 PA). No ocupa espacio de acción.
        Costo:   Ninguno.
        Requiere: Tecnología Incubadora instalada y una masa en ``slot_index``.
        Efecto:  Fija ``FermentationSlot.modificador_incubadora`` de ESA masa
                 para la Fase III de esta noche: -1 frena una casilla, +1
                 acelera una, 0 deja la cinética limpia.
        Límite:  Ninguno — la Fase III devuelve el dial a 0 tras aplicarlo
                 (``GameEngine._avanzar_masas_jugador``), así que el ajuste
                 dura una sola noche y se decide masa por masa.

        Notas de diseño (las cuatro decisiones que sostienen esta acción):

        · **Por qué existe.** El modificador se elegía en la Acción B y quedaba
          sellado en la masa para siempre. Instalar la Incubadora con una masa ya
          fermentando no servía absolutamente de nada: su dial era un 0 que
          ninguna acción del juego podía tocar, así que la mejora que se acababa
          de pagar en Datos veía colapsar esa masa sin poder frenarla. El
          reglamento ya prometía un ajuste «masa por masa» en la Fase III; esto
          es lo que lo cumple.
        · **Es un dial de dos sentidos, no un consumo.** Puede accionarse cuantas
          veces se quiera durante cualquier visita que el jugador ya tenga; por
          eso NO llama a ``ocupar_espacio_accion`` ni marca ninguna bandera de "ya
          usada", y por eso NO aparece en ``GameEngine._jugador_elegible``: no
          otorga visitas. Un ajuste no es un recurso. Mismo criterio que la
          Estasis Biológica.
        · **Por defecto el dial está en 0.** Una masa nace sin ajuste y la Fase III
          lo devuelve a 0 cada noche, así que quien ignore la acción juega
          exactamente como antes y un ajuste olvidado no puede arrastrar a nadie a
          un colapso la noche siguiente.
        · **No emite ``GameEvent``.** Es una acción de 0 PA, es decir que ocurre
          dentro de la ventana de deshacer, y ``GameSession.restaurar_checkpoint``
          hace ``pickle.loads`` del motor entero: un evento aquí encogería
          ``engine.eventos`` al deshacer y dejaría colgados los punteros ``since``
          de los clientes — el invariante que existe para proteger ``AvisoAccion``.
          El rastro permanente lo deja el evento ``MASA_AVANZO`` de la Fase III,
          que informa del modificador aplicado.

        Args:
            player: Jugador que ajusta el dial.
            slot_index: Estación (0, 1 o 2) cuya masa se ajusta.
            modificador: -1, 0 o +1 casillas de avance para esta noche.

        Raises:
            InvalidActionError: ``modificador`` fuera de (-1, 0, 1).
            RuleViolationError: El jugador no tiene la Incubadora instalada,
                ``slot_index`` está fuera de [0, 2], o la estación está vacía.
        """
        if modificador not in (-1, 0, 1):
            raise InvalidActionError(
                f"modificador debe ser -1, 0 o 1. Recibido: {modificador}"
            )

        if not player.tecnologias.incubadora:
            raise RuleViolationError(
                f"'{player.nombre}' no puede ajustar el avance de una masa sin la "
                "tecnología Incubadora instalada."
            )

        if not (0 <= slot_index <= 2):
            raise RuleViolationError(
                f"slot_index debe estar en [0, 2]. Recibido: {slot_index}"
            )

        slot: Optional[FermentationSlot] = player.estaciones_fermentacion[slot_index]
        if slot is None:
            raise RuleViolationError(
                f"La estación {slot_index} de '{player.nombre}' está vacía. "
                "No hay ninguna masa cuyo avance ajustar."
            )

        slot.modificador_incubadora = modificador

    def accion_auxiliar_pedido_urgencia(
        self,
        player: Player,
        recurso: str,
        harina: Optional[TipoHarina] = None,
    ) -> None:
        """
        Acción Auxiliar: Pedido de Urgencia (GDD v0.0.2, Módulo V §2 «Logística»).

        Tipo:    Acción gratuita (0 PA) — no consume un Punto de Acción y no
                 termina el turno del jugador.
        Costo:   1 Dato de Investigación.
        Efecto:  Ignora el mercado y el precio vigente por completo: entrega
                 directamente de la reserva general UNA de estas dos parcelas
                 FIJAS, a elección del jugador:
                   · ``recurso="harina"`` → ``HARINA_PEDIDO_URGENCIA`` (50%,
                     media bolsa) del tipo indicado en ``harina``.
                   · ``recurso="agua"``   → ``AGUA_PEDIDO_URGENCIA`` tokens
                     de agua (6, o sea un 30%).
        Límite:  Ninguno (a diferencia de Horas Extras, el GDD no impone un
                 tope por ronda; se autolimita por Datos de Investigación
                 disponibles).

        Las dos cantidades son fijas y el jugador no elige ninguna: lo único
        que decide es CUÁL de los dos recursos quiere. El agua tuvo durante un
        tiempo una cantidad libre y era un agujero — ver la docstring de
        ``AGUA_PEDIDO_URGENCIA``.

        Args:
            player: Jugador que activa el Pedido de Urgencia.
            recurso: ``"harina"`` o ``"agua"``.
            harina: Tipo de harina, obligatorio si ``recurso == "harina"`` y
                prohibido en caso contrario.

        Raises:
            InvalidActionError: ``recurso`` desconocido, harina sin tipo, o un
                tipo de harina en un pedido de agua.
            MissingResourceError: Datos de Investigación insuficientes.
        """
        if recurso not in ("harina", "agua"):
            raise InvalidActionError(
                f"Pedido de Urgencia: recurso {recurso!r} inválido. "
                "Debe ser 'harina' o 'agua'."
            )
        if recurso == "harina" and harina is None:
            raise InvalidActionError(
                "Pedido de Urgencia: un pedido de harina necesita el tipo "
                f"('harina'). Debe ser uno de {[t.value for t in TipoHarina]}."
            )
        if recurso == "agua" and harina is not None:
            raise InvalidActionError(
                "Pedido de Urgencia: elige UN solo tipo de recurso. "
                "Un pedido de agua no lleva tipo de harina."
            )

        self._require_datos(player, 1)

        # Aplicar (0 PA — no se consume punto de acción)
        player.datos_investigacion -= 1

        if recurso == "harina":
            assert harina is not None  # garantizado por la validación de arriba
            player.reserva_harina[harina.value] += HARINA_PEDIDO_URGENCIA
        else:
            player.reserva_agua += AGUA_PEDIDO_URGENCIA

    # ==================================================================
    # PROTOCOLOS DE EMERGENCIA (solo cuando Vitalidad == 0)
    # ==================================================================

    def accion_H_recultivo_manual(self, player: Player) -> None:
        """
        Protocolo de Emergencia H: Re-cultivo Manual (ACTIONS_REGISTRY.md §3).

        Precondición: ``player.en_estado_contaminacion == True``
            (Vitalidad llegó a 0 en algún punto del juego).

        Costo:   1 PA + 30% Harina (cualquier tipo). Sin costo de agua
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
        self._require_cualquier_harina(player, HARINA_RECULTIVO_MANUAL)

        # Aplicar
        player.consumir_punto_accion("H")

        # Consumir la harina del re-cultivo (de los tipos con mayor reserva primero)
        harina_a_consumir = HARINA_RECULTIVO_MANUAL
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
