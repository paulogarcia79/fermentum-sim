"""
engine.py — Motor de Juego de Fermentum
=========================================
Orquesta el bucle principal del simulador: el «Día de Laboratorio».

Contenido:
  · Constantes de configuración del mercado y puntuación.
  · SupplyLote / Market  — modelos auxiliares del mercado central
    (idealmente pertenecerían a models.py; se ubican aquí porque models.py
    está cerrado y son exclusivos de la capa de lógica del motor).
  · GameEngine — clase principal que implementa las tres fases del día y
    la evaluación de fin de partida.

Estándares aplicados (ARCHITECTURE.md):
  · Inyección de Dependencias: GameEngine recibe players, environment y market
    como parámetros → permite pruebas unitarias aisladas.
  · Separación de Responsabilidades: este módulo solo orquesta fases y resuelve
    la cinética automática. La lógica de acciones de jugador vive en actions.py.
  · Strict Type Hinting (PEP 484) en todos los atributos, parámetros y retornos.
  · Excepciones semánticas importadas desde exceptions.py (Fail-Fast).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from exceptions import (
    GameAlreadyOverError,
    InsufficientPlayersError,
    MarketSlotEmptyError,
)
from models import (
    ClimateCard,
    EfectoBiologico,
    EfectoClimatico,
    Environment,
    FermentationSlot,
    HorneadoRecord,
    Player,
    Recipe,
    get_recetas_avanzadas,
    get_recetas_basicas,
)

# ===========================================================================
# SECCIÓN 1: CONSTANTES DE CONFIGURACIÓN
# ===========================================================================

# --- Mercado Central ---
NUM_RECIPE_SLOTS: int = 4
"""Número de ranuras de recetas visibles en el mercado. Convención de eurogames."""

NUM_SUPPLY_SLOTS: int = 3
"""Número de lotes de suministros disponibles por día (CORE_MECHANICS.md §2 Fase I)."""

# --- Datos de Investigación por Horneado ---
DATOS_BAKE_ZONA_OPTIMA: int = 1
"""Datos otorgados al hornear dentro de la zona óptima (ACTIONS_REGISTRY.md §2F)."""

DATOS_BAKE_CENTRO_EXACTO_BONUS: int = 1
"""
Datos extra al hornear en el centro exacto de la zona óptima con Módulo Analítico
activo (ACTIONS_REGISTRY.md §2D: «Genera +1 Dato extra al hornear en centro exacto»).
"""

# --- Puntuación de Zona Baja ---
PUNTOS_ZONA_BAJA_DIVISOR: int = 3
"""
Divisor para calcular los puntos al hornear en zona baja (masa cruda).
Assumption: RECIPE_DATABASE.md indica «pocos puntos» sin cuantificar.
Se usa: puntos_zona_baja = max(1, puntos_optimos // PUNTOS_ZONA_BAJA_DIVISOR).
"""

# ===========================================================================
# SECCIÓN 2: MODELOS AUXILIARES DEL MERCADO CENTRAL
# ===========================================================================


def _generar_lote_150() -> Dict[str, int]:
    """
    Genera un lote aleatorio de recursos cuya suma total es exactamente 150.

    Distribuye 15 unidades de 10% entre los cuatro tipos de recurso
    (Blanca, Centeno, Integral, agua) usando el método de «cortes aleatorios»
    (stars-and-bars). Todos los valores son múltiplos de 10.

    Returns:
        Diccionario con claves ``"Blanca"``, ``"Centeno"``, ``"Integral"``, ``"agua"``
        cuyos valores suman 150.
    """
    total_units = 15  # 15 × 10% = 150%
    # Tres cortes aleatorios en [0, 15] dividen el total en 4 partes
    c1, c2, c3 = sorted(random.randint(0, total_units) for _ in range(3))
    return {
        "Blanca":   c1 * 10,
        "Centeno":  (c2 - c1) * 10,
        "Integral": (c3 - c2) * 10,
        "agua":     (total_units - c3) * 10,
    }


@dataclass
class SupplyLote:
    """
    Lote de suministros disponible en el mercado central.

    Un lote es una mezcla aleatoria de harinas y agua que el jugador puede
    adquirir gastando 1 PA (Acción C: Adquirir Insumos).

    Attributes:
        recursos: Diccionario con claves ``"Blanca"``, ``"Centeno"``,
            ``"Integral"`` (valores en % múltiplos de 10) y ``"agua"``
            (valor en % múltiplo de 10, convertible a tokens de 5%).
            La suma de todos los valores es siempre exactamente 150.
    """

    recursos: Dict[str, int]

    def __post_init__(self) -> None:
        claves_requeridas = {"Blanca", "Centeno", "Integral", "agua"}
        if set(self.recursos.keys()) != claves_requeridas:
            raise ValueError(
                f"SupplyLote.recursos debe tener las claves {claves_requeridas}. "
                f"Recibido: {set(self.recursos.keys())}"
            )
        total = sum(self.recursos.values())
        if total != 150:
            raise ValueError(
                f"La suma de los valores del lote debe ser exactamente 150. "
                f"Recibido: {total}"
            )


@dataclass
class Market:
    """
    Estado del mercado central compartido entre todos los jugadores.

    El mercado de recetas funciona como una cola con antigüedad visible:
      · Posición 0 (izquierda) = carta más nueva (recién incorporada).
      · Posición N-1 (derecha) = carta más antigua (próxima a descartarse).

    Protocolo de Refresco (Fase I — CORE_MECHANICS.md §2):
      · Recetas: elimina la más antigua (derecha), desplaza el resto a la derecha
        y revela una nueva carta a la izquierda. Si el mazo se agota, baraja el descarte.
      · Suministros: descarta todos los lotes no reclamados y genera 3 nuevos.

    Attributes:
        recetas_visibles: Lista de NUM_RECIPE_SLOTS slots de recetas activas.
            ``None`` indica que el slot fue tomado por un jugador este día.
        mazo_recetas: Mazo oculto de recetas pendientes de aparecer en el mercado.
        descarte_recetas: Recetas descartadas del mercado (se remezclan si el mazo se agota).
        suministros: Lista de NUM_SUPPLY_SLOTS lotes de suministros.
            ``None`` indica que el slot fue tomado por un jugador este día.
    """

    recetas_visibles: List[Optional[Recipe]]
    mazo_recetas: List[Recipe]
    descarte_recetas: List[Recipe] = field(default_factory=list)
    suministros: List[Optional[SupplyLote]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factory Method
    # ------------------------------------------------------------------

    @classmethod
    def crear_inicial(cls) -> "Market":
        """
        Construye el mercado en su estado inicial de partida.

        El mazo de recetas se compone de todas las avanzadas (mezcladas) seguidas
        de las básicas al fondo. Se revelan las primeras NUM_RECIPE_SLOTS cartas
        y se generan NUM_SUPPLY_SLOTS lotes de suministros aleatorios.

        Returns:
            Instancia de Market lista para el inicio de la partida.
        """
        avanzadas: List[Recipe] = get_recetas_avanzadas()
        basicas: List[Recipe] = get_recetas_basicas()
        random.shuffle(avanzadas)
        random.shuffle(basicas)
        # Las recetas avanzadas dominan el mercado; las básicas están al fondo
        # disponibles si el mazo de avanzadas se agota.
        mazo: List[Recipe] = avanzadas + basicas

        visibles: List[Optional[Recipe]] = [
            (mazo.pop(0) if mazo else None) for _ in range(NUM_RECIPE_SLOTS)
        ]

        mercado = cls(recetas_visibles=visibles, mazo_recetas=mazo)
        mercado._generar_suministros()
        return mercado

    # ------------------------------------------------------------------
    # Protocolo de Refresco
    # ------------------------------------------------------------------

    def protocolo_refresco(self) -> None:
        """
        Ejecuta el Protocolo de Refresco del mercado central (Fase I).

        Reglas (CORE_MECHANICS.md §2, Fase I):
          - Recetas: descarta la más antigua (extremo derecho), desplaza las
            restantes a la derecha y revela una nueva carta a la izquierda.
            Si el mazo se agota, baraja el descarte como nuevo mazo.
          - Suministros: descarta todos los lotes no reclamados y revela 3 nuevos.
        """
        # --- Refresco de Recetas ---

        # 1. Descartar la carta más antigua (posición derecha = índice -1).
        #    Si el slot estaba vacío (ya tomado), se elimina silenciosamente.
        if self.recetas_visibles:
            oldest: Optional[Recipe] = self.recetas_visibles.pop()  # rightmost
            if oldest is not None:
                self.descarte_recetas.append(oldest)

        # 2. Obtener nueva carta del mazo (barajando descarte si es necesario).
        if not self.mazo_recetas and self.descarte_recetas:
            self.mazo_recetas = self.descarte_recetas[:]
            self.descarte_recetas = []
            random.shuffle(self.mazo_recetas)

        nueva_carta: Optional[Recipe] = (
            self.mazo_recetas.pop(0) if self.mazo_recetas else None
        )

        # 3. Insertar la nueva carta en la posición izquierda (más nueva).
        self.recetas_visibles.insert(0, nueva_carta)

        # --- Refresco de Suministros ---
        self._generar_suministros()

    # ------------------------------------------------------------------
    # Operaciones del Mercado (consumidas por actions.py)
    # ------------------------------------------------------------------

    def tomar_receta(self, indice: int) -> Recipe:
        """
        Retira una receta del mercado (Acción G: Investigar Protocolo).
        El slot queda como ``None`` hasta el próximo Protocolo de Refresco.

        Args:
            indice: Posición en ``recetas_visibles`` (0 = más nueva, N-1 = más antigua).

        Returns:
            La receta tomada del mercado.

        Raises:
            MarketSlotEmptyError: Si el slot ya estaba vacío (tomado este día).
            ValueError: Si el índice está fuera de rango.
        """
        if not (0 <= indice < len(self.recetas_visibles)):
            raise ValueError(
                f"Índice de receta inválido: {indice}. "
                f"Rango válido: [0, {len(self.recetas_visibles) - 1}]"
            )
        receta: Optional[Recipe] = self.recetas_visibles[indice]
        if receta is None:
            raise MarketSlotEmptyError(
                f"El slot de receta {indice} ya fue tomado este día. "
                "Se repondrá en el próximo Protocolo de Refresco."
            )
        self.recetas_visibles[indice] = None
        return receta

    def tomar_suministro(self, indice: int) -> SupplyLote:
        """
        Retira un lote de suministros del mercado (Acción C: Adquirir Insumos).
        El slot queda como ``None`` hasta el próximo Protocolo de Refresco.

        Args:
            indice: Posición en ``suministros`` (0, 1 o 2).

        Returns:
            El lote de suministros tomado.

        Raises:
            MarketSlotEmptyError: Si el slot ya estaba vacío (tomado este día).
            ValueError: Si el índice está fuera de rango.
        """
        if not (0 <= indice < len(self.suministros)):
            raise ValueError(
                f"Índice de suministro inválido: {indice}. "
                f"Rango válido: [0, {len(self.suministros) - 1}]"
            )
        lote: Optional[SupplyLote] = self.suministros[indice]
        if lote is None:
            raise MarketSlotEmptyError(
                f"El lote de suministro {indice} ya fue tomado este día. "
                "Se repondrá en el próximo Protocolo de Refresco."
            )
        self.suministros[indice] = None
        return lote

    # ------------------------------------------------------------------
    # Generación Interna de Suministros
    # ------------------------------------------------------------------

    def _generar_suministros(self) -> None:
        """
        Genera NUM_SUPPLY_SLOTS lotes de suministros nuevos de forma aleatoria.

        Cada lote es un diccionario con claves ``"Blanca"``, ``"Centeno"``,
        ``"Integral"`` y ``"agua"``, donde todos los valores son múltiplos de 10
        y su suma es exactamente 150.
        """
        self.suministros = [
            SupplyLote(recursos=_generar_lote_150())
            for _ in range(NUM_SUPPLY_SLOTS)
        ]

    def __repr__(self) -> str:
        recetas_str = [r.nombre if r else "—" for r in self.recetas_visibles]
        return (
            f"Market(recetas={recetas_str}, "
            f"mazo_restante={len(self.mazo_recetas)}, "
            f"suministros={len([s for s in self.suministros if s is not None])} activos)"
        )


# ===========================================================================
# SECCIÓN 3: MOTOR PRINCIPAL DEL JUEGO
# ===========================================================================

# Alias de tipo para el callback de turno de jugador (Fase II).
TurnCallback = Callable[["GameEngine", Player], None]


class GameEngine:
    """
    Orquesta el bucle principal del juego Fermentum: el «Día de Laboratorio».

    Responsabilidades:
      · Secuenciar las tres fases de cada ronda (Ambiente → Acción → Fermentación).
      · Mantener el estado global del turno (jefe_investigador, fase activa).
      · Resolver la Cinética Biológica: avance automático de masas en Fase III.
      · Detectar Colapsos Estructurales y aplicar horneados de emergencia (0 PA).
      · Aplicar el Desgaste Metabólico al cultivo base al final de cada día.
      · Evaluar los dos gatillos de fin de partida.
      · Exponer resolver_horneado() como API pública para actions.py (Acción F).

    NO hace:
      · Ejecutar la lógica de las 9 acciones del jugador (eso es actions.py).
      · Instanciar jugadores o entorno internamente (principio de Inyección de
        Dependencias — ARCHITECTURE.md §1).

    Ejemplo de uso::

        env = Environment.crear_inicial()
        players = [
            Player.crear_dia_1("Investigador 1", receta_1),
            Player.crear_dia_1("Investigador 2", receta_2),
        ]
        market = Market.crear_inicial()
        engine = GameEngine(players=players, environment=env, market=market)

        while not engine.partida_terminada:
            fin = engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=mi_handler)
    """

    def __init__(
        self,
        players: List[Player],
        environment: Environment,
        market: Optional[Market] = None,
    ) -> None:
        """
        Inicializa el motor de juego con inyección de dependencias.

        Args:
            players: Lista de investigadores participantes (1-4).
            environment: Estado del entorno global (temperatura, mazo de clima, día).
            market: Estado del mercado central. Si ``None``, se crea automáticamente
                con ``Market.crear_inicial()``.

        Raises:
            InsufficientPlayersError: Si se proporciona una lista de jugadores vacía.
        """
        if not players:
            raise InsufficientPlayersError(
                "Se requiere al menos un jugador para iniciar la partida de Fermentum."
            )

        self._players: List[Player] = players
        self._environment: Environment = environment
        self._market: Market = market if market is not None else Market.crear_inicial()

        # Estado interno del turno actual
        self._jefe_investigador: Optional[Player] = None
        self._partida_terminada: bool = False

    # ==================================================================
    # PROPIEDADES PÚBLICAS DE ESTADO (solo lectura)
    # ==================================================================

    @property
    def players(self) -> List[Player]:
        """Lista de jugadores participantes."""
        return self._players

    @property
    def environment(self) -> Environment:
        """Estado del entorno global (temperatura, clima, día)."""
        return self._environment

    @property
    def market(self) -> Market:
        """Estado actual del mercado central."""
        return self._market

    @property
    def jefe_investigador(self) -> Optional[Player]:
        """
        Jugador con el rol de Investigador Jefe en el turno actual.
        Determinado al inicio de cada Fase I. ``None`` antes del primer día.
        """
        return self._jefe_investigador

    @property
    def partida_terminada(self) -> bool:
        """
        True si se activó algún gatillo de fin de partida:
          · El mazo de clima se agotó, o
          · Algún jugador alcanzó 5 horneados exitosos.
        El día en curso se completa antes de que el motor deje de avanzar.
        """
        return self._partida_terminada

    # ==================================================================
    # BUCLE PRINCIPAL
    # ==================================================================

    def ejecutar_dia_laboratorio(
        self,
        ejecutar_turno_jugador: Optional[TurnCallback] = None,
        on_fase_i_complete: Optional[Callable[["GameEngine"], None]] = None,
    ) -> bool:
        """
        Orquesta un Día de Laboratorio completo (ronda de juego).

        Ejecuta las tres fases de forma secuencial y estricta:
          1. :meth:`fase_I_ambiente`   — clima, jerarquía y refresco de mercado.
          2. :meth:`fase_II_accion`    — turnos intercalados de jugadores (round-robin).
          3. :meth:`fase_III_fermentacion` — cinética biológica y desgaste.

        Incluso si se activa un gatillo de fin de partida durante la Fase II o III,
        el día en curso se completa íntegramente antes de retornar ``True``
        (regla de CORE_MECHANICS.md §3: «se termina el Día de Laboratorio en curso»).

        Al final incrementa el contador de días del entorno.

        Args:
            ejecutar_turno_jugador: Callback opcional ``(engine, player) -> None``
                invocado UNA VEZ por jugador por cada vuelta del round-robin de Fase II.
                Cuando es ``None``, los turnos de los jugadores se omiten.
            on_fase_i_complete: Callback opcional ``(engine) -> None`` invocado
                justo después de que la Fase I concluye y antes de iniciar la Fase II.
                Permite a la CLI mostrar el evento climático antes de pedir acciones.

        Returns:
            True si la partida termina al concluir este día, False si continúa.

        Raises:
            GameAlreadyOverError: Si se intenta ejecutar un día después de que
                la partida ya haya terminado.
        """
        if self._partida_terminada:
            raise GameAlreadyOverError(
                f"La partida ya terminó en el Día {self._environment.dia_actual - 1}. "
                "No se pueden ejecutar más Días de Laboratorio."
            )

        self.fase_I_ambiente()
        if on_fase_i_complete is not None:
            on_fase_i_complete(self)
        self.fase_II_accion(ejecutar_turno_jugador)
        self.fase_III_fermentacion()

        fin: bool = self._evaluar_fin_de_juego()
        self._environment.dia_actual += 1
        return fin

    # ==================================================================
    # FASE I: AMBIENTE
    # ==================================================================

    def fase_I_ambiente(self) -> None:
        """
        Fase I: Ambiente — prepara el entorno global para el día (CORE_MECHANICS.md §2).

        Pasos (en orden):
          1. **Actualización de Jerarquía**: asigna el Investigador Jefe al jugador
             con mayor Vitalidad (desempate: Datos de Investigación).
          2. **Reset de Entorno**: la temperatura vuelve a 20°C y el efecto pasivo
             se neutraliza antes de aplicar la carta del día.
          3. **Resolución del Clima**: roba la carta superior del mazo de clima,
             aplica su modificador térmico y registra el efecto pasivo vigente.
             Los efectos biológicos inmediatos (+Vitalidad / +Acidez) se aplican
             a todos los jugadores instantáneamente.
             Si el mazo se agota, se activa el gatillo de fin de partida.
          4. **Protocolo de Refresco**: actualiza el mercado de recetas y suministros.
        """
        # Paso 1: Determinar Investigador Jefe
        self._jefe_investigador = self._determinar_investigador_jefe()

        # Paso 2: Reset del entorno al inicio del día
        self._environment.resetear_temperatura_base()
        self._environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO

        # Paso 3: Resolver carta de clima
        carta: Optional[ClimateCard] = self._robar_carta_clima()
        if carta is not None:
            self._resolver_carta_clima(carta)

        # Paso 4: Protocolo de Refresco del mercado
        self._market.protocolo_refresco()

    def _determinar_investigador_jefe(self) -> Player:
        """
        Selecciona el Investigador Jefe para el turno actual.

        Criterio de selección (CORE_MECHANICS.md §2, Fase I):
          1. Mayor nivel de Vitalidad del cultivo base.
          2. Desempate: mayor cantidad de Datos de Investigación.
          3. Empate persistente: posición en la lista de jugadores (el primero
             tiene prioridad — orden de inscripción a la partida).

        Returns:
            El jugador que actúa como Investigador Jefe este día.
        """
        return max(
            self._players,
            key=lambda p: (p.vitalidad, p.datos_investigacion),
        )

    def _robar_carta_clima(self) -> Optional[ClimateCard]:
        """
        Roba la carta superior (índice 0) del mazo de clima.

        La carta se mueve al montón de descarte del entorno. Si el mazo queda
        vacío tras el robo (o ya lo estaba), activa el flag de fin de partida.
        El día en curso se completará antes de que el motor se detenga.

        Returns:
            La carta de clima robada, o ``None`` si el mazo ya estaba agotado
            al inicio de este día (caso raro: fin de partida ya activado en el
            día anterior pero el día en curso se está completando).
        """
        if self._environment.mazo_agotado:
            # El mazo se agotó en el día anterior; este día no tendrá carta.
            self._partida_terminada = True
            return None

        carta: ClimateCard = self._environment.mazo_clima.pop(0)
        self._environment.descarte_clima.append(carta)

        # Si con esta carta el mazo quedó vacío, el día de hoy es el último.
        if self._environment.mazo_agotado:
            self._partida_terminada = True

        return carta

    def _resolver_carta_clima(self, carta: ClimateCard) -> None:
        """
        Aplica todos los efectos de la carta de clima al estado global.

        Orden de aplicación (CLIMATE_LOGIC.md §2):
          1. Modificador térmico: ``temperatura_actual += carta.modificador_termico``.
          2. Efecto pasivo: se registra para la resolución de Fase III.
          3. Efecto biológico inmediato: se aplica a todos los jugadores al instante.

        Nota: el reset de temperatura (20°C base) se realiza en ``fase_I_ambiente``
        antes de llamar a este método, por lo que ``aplicar_carta_clima`` solo
        aplica el delta incremental.

        Args:
            carta: Carta de clima revelada en esta Fase I.
        """
        # 1 + 2: Modificador térmico + efecto pasivo vigente para Fase III.
        #        Environment.aplicar_carta_clima() aplica ambos en un solo paso.
        #        Adicionalmente se registra la carta para consulta de la CLI.
        self._environment.ultima_carta_clima = carta
        self._environment.aplicar_carta_clima(carta)

        # 3. Efecto biológico inmediato (aplicado a todos los jugadores).
        if carta.efecto_biologico == EfectoBiologico.GANANCIA_VITALIDAD:
            for player in self._players:
                player.ajustar_vitalidad(+1)
        elif carta.efecto_biologico == EfectoBiologico.GANANCIA_ACIDEZ:
            for player in self._players:
                player.ajustar_acidez(+1)

    # ==================================================================
    # FASE II: ACCIÓN
    # ==================================================================

    def fase_II_accion(
        self,
        ejecutar_turno_jugador: Optional[TurnCallback] = None,
    ) -> None:
        """
        Fase II: Acción — turnos intercalados (round-robin) hasta agotar todos los PA
        (CORE_MECHANICS.md §2).

        Flujo:
          1. Se reinician los Puntos de Acción de **todos** los jugadores (2 PA c/u).
          2. Mientras algún jugador tenga PA > 0, se itera sobre el orden de turno.
             Por cada jugador con PA > 0 se invoca el callback UNA SOLA VEZ;
             el jugador ejecuta 1 acción (o pasa cediendo sus PA restantes).
          3. El bucle termina cuando ningún jugador tiene PA disponibles.

        Args:
            ejecutar_turno_jugador: Callback ``(engine, player) -> None`` invocado
                una vez por jugador por vuelta del round-robin. ``None`` durante
                pruebas de integración del bucle de fases.
        """
        orden: List[Player] = self._orden_de_turno()

        # Paso 0: Reiniciar flag de Acción A para todos los jugadores.
        for player in orden:
            player.accion_alimentar_usada = False

        # Paso 1: Asignar 2 PA a todos antes de iniciar el round-robin.
        for player in orden:
            player.resetear_puntos_accion()

        if ejecutar_turno_jugador is None:
            return

        # Paso 2: Round-robin hasta que todos tengan 0 PA.
        while any(p.puntos_accion > 0 for p in orden):
            for player in orden:
                if player.puntos_accion > 0:
                    ejecutar_turno_jugador(self, player)

    # ==================================================================
    # FASE III: FERMENTACIÓN
    # ==================================================================

    def fase_III_fermentacion(self) -> None:
        """
        Fase III: Fermentación — resolución automática simultánea para todos los
        jugadores (CORE_MECHANICS.md §2 + CLIMATE_LOGIC.md §3-4).

        Pasos (en orden):
          1. **Cinética Biológica**: avanza todas las masas activas de todos los
             jugadores usando la fórmula de avance del Ábaco de Fermentación.
          2. **Colapso Estructural**: si una masa supera el límite inferior de su
             ``zona_sobrefermentada``, se hornea automáticamente con 0 PA y la
             penalización correspondiente.
          3. **Desgaste Metabólico**: reduce la Vitalidad del cultivo base de cada
             jugador en -1 (o -2 con «Aletargamiento Invernal» activo).
             La Vitalidad nunca cae por debajo de 0; si llega a 0, el jugador entra
             en estado de Contaminación (gestionado por ``Player.ajustar_vitalidad``).
        """
        # Paso 1 + 2: Avance de masas y detección/resolución de colapsos.
        #             Se itera sobre todos los jugadores de forma secuencial.
        #             La simultaneidad física del juego de mesa se simula procesando
        #             todos los jugadores en la misma pasada del bucle.
        for player in self._players:
            self._avanzar_masas_jugador(player)

        # Paso 3: Desgaste metabólico al final de la Fase III (CLIMATE_LOGIC.md §4).
        self._aplicar_desgaste_metabolico()

    def _avanzar_masas_jugador(self, player: Player) -> None:
        """
        Avanza todas las masas activas de un jugador y resuelve colapsos.

        Algoritmo de Cinética Biológica (CLIMATE_LOGIC.md §3):

        .. code-block:: text

            Avance_Final = (temperatura_actual // 5)
                         + dado_inoculo
                         + modificador_incubadora

        Donde:
          · ``temperatura_actual // 5`` = Ábaco de Fermentación (inercia térmica).
          · ``dado_inoculo`` = valor sellado al iniciar la receta (≡ Vitalidad del día B).
          · ``modificador_incubadora`` = ajuste local -1/0/+1 si el jugador tiene
            la tecnología Incubadora activa.

        Si tras el avance la posición ≥ ``zona_sobrefermentada[0]``, se activa
        el Colapso Estructural (horneado automático de emergencia, 0 PA).

        Args:
            player: Jugador cuyas masas activas deben avanzar.
        """
        # Recopilar índices activos ANTES de iterar para evitar mutación concurrente.
        # Un colapso durante la iteración libera un slot, lo que invalida el iterador.
        indices_activos: List[int] = [
            i
            for i, slot in enumerate(player.estaciones_fermentacion)
            if slot is not None
        ]

        for idx in indices_activos:
            slot: Optional[FermentationSlot] = player.estaciones_fermentacion[idx]

            # El slot puede haberse liberado si un colapso anterior en este ciclo
            # fue resuelto por otra vía (defensivo: no debería ocurrir en modo normal).
            if slot is None:
                continue

            # Calcular el avance de esta masa usando la fórmula de cinética.
            avance: int = slot.calcular_avance(self._environment.temperatura_actual)
            slot.posicion_track += avance

            # Evaluar gatillo de Colapso Estructural (CLIMATE_LOGIC.md §3 regla 2).
            if slot.recipe.esta_sobrefermentada(slot.posicion_track):
                self.resolver_horneado(player, idx, fue_colapso=True)

    def _aplicar_desgaste_metabolico(self) -> None:
        """
        Aplica el Desgaste Metabólico al cultivo base de todos los jugadores.

        Ejecutado tras procesar el avance de todas las masas (CLIMATE_LOGIC.md §4):
          · Estándar: ``-1`` Vitalidad.
          · Aletargamiento Invernal activo: ``-2`` Vitalidad.
          · Límite suelo: la Vitalidad nunca cae por debajo de 0.
          · Consecuencia de llegar a 0: estado de Contaminación + penalización
            de -3 PM (gestionado automáticamente por ``Player.ajustar_vitalidad``).
        """
        delta: int = self._environment.desgaste_vitalidad_fase_3
        for player in self._players:
            player.ajustar_vitalidad(delta)

    # ==================================================================
    # RESOLUCIÓN DE HORNEADO (API pública para actions.py — Acción F)
    # ==================================================================

    def resolver_horneado(
        self,
        player: Player,
        slot_index: int,
        fue_colapso: bool = False,
    ) -> HorneadoRecord:
        """
        Resuelve el horneado de una masa: manual (Acción F) o automático por colapso.

        Es el único punto de entrada para finalizar una masa, ya sea por decisión
        del jugador (``fue_colapso=False``, costo 1 PA gestionado por actions.py)
        o por Colapso Estructural automático (``fue_colapso=True``, costo 0 PA).

        Lógica de puntuación:
          · **Colapso**: ``puntos_base = recipe.penalizacion_colapso`` (negativo).
            El bono de sabor NO se aplica (la fermentación fue un fracaso).
          · **Zona óptima**: ``puntos_base = recipe.puntos_optimos``.
            Se acreditan Datos de Investigación (+ extra si centro exacto + Módulo Analítico).
            El bono de sabor SE aplica si el Cubo de Laboratorio estaba sellado.
          · **Zona baja** (masa cruda): ``puntos_base = max(1, puntos_optimos // 3)``.
            Assumption: «pocos puntos» no cuantificados en RECIPE_DATABASE.md.
            Sin Datos de Investigación. El bono de sabor SE aplica.

        Efectos sobre el estado del jugador:
          1. El slot en ``estaciones_fermentacion`` se libera (``None``).
          2. Se recupera 1 dado de inóculo (máx 3).
          3. Los Datos de Investigación ganados se acreditan inmediatamente.
          4. El ``HorneadoRecord`` se añade al archivo correspondiente
             (``archivo_horneado_exitoso`` o ``archivo_colapsos``).
          5. Si el jugador alcanza 5 horneados exitosos, se activa el fin de partida.

        Args:
            player: Jugador propietario de la masa a hornear.
            slot_index: Índice en ``estaciones_fermentacion`` (0, 1 o 2).
            fue_colapso: ``True`` si el horneado es un Colapso Estructural automático.
                El caller (``_avanzar_masas_jugador``) lo pasa cuando corresponde.
                ``False`` por defecto para el horneado manual desde actions.py.

        Returns:
            Registro inmutable ``HorneadoRecord`` del horneado realizado.

        Raises:
            ValueError: Si el ``slot_index`` no contiene una masa activa.
        """
        slot: Optional[FermentationSlot] = player.estaciones_fermentacion[slot_index]
        if slot is None:
            raise ValueError(
                f"La estación {slot_index} del jugador '{player.nombre}' está vacía. "
                "No hay masa que hornear."
            )

        recipe: Recipe = slot.recipe
        posicion: int = slot.posicion_track

        # --- Cálculo de puntos y datos ---
        puntos_base: int = self._calcular_puntos_zona(recipe, posicion, fue_colapso)
        datos_obtenidos: int = (
            0
            if fue_colapso
            else self._calcular_datos_horneado(player, recipe, posicion)
        )

        # El bono de sabor no aplica en un colapso (fermentación fallida).
        bono_sabor_aplicado: bool = slot.bono_sabor and not fue_colapso

        # --- Crear registro inmutable del horneado ---
        record = HorneadoRecord(
            recipe=recipe,
            posicion_final=posicion,
            puntos_base=puntos_base,
            bono_sabor_aplicado=bono_sabor_aplicado,
            fue_colapso=fue_colapso,
            datos_obtenidos=datos_obtenidos,
        )

        # --- Actualizar estado del jugador ---
        player.estaciones_fermentacion[slot_index] = None  # Liberar slot
        player.dados_inoculo = min(3, player.dados_inoculo + 1)  # Recuperar dado
        player.datos_investigacion += datos_obtenidos  # Acreditar datos

        if fue_colapso:
            player.archivo_colapsos.append(record)
        else:
            player.archivo_horneado_exitoso.append(record)
            # Evaluar gatillo de fin de partida por quinta receta exitosa.
            # (PLAYER_STATE.md §3: len(archivo_horneado_exitoso) >= 5)
            if len(player.archivo_horneado_exitoso) >= 5:
                self._partida_terminada = True

        return record

    # ==================================================================
    # CÁLCULOS INTERNOS DE HORNEADO
    # ==================================================================

    def _calcular_puntos_zona(
        self,
        recipe: Recipe,
        posicion: int,
        fue_colapso: bool,
    ) -> int:
        """
        Calcula los Puntos de Maestría según la zona del track de fermentación.

        Tabla de resolución:

        +-----------------------+--------------------------------------------+
        | Condición             | Puntos retornados                          |
        +=======================+============================================+
        | Colapso (forzado)     | ``recipe.penalizacion_colapso`` (negativo) |
        +-----------------------+--------------------------------------------+
        | Zona sobrefermentada  | ``recipe.penalizacion_colapso``            |
        | (manual desde esa pos)| (hornear desde allí sigue siendo colapso)  |
        +-----------------------+--------------------------------------------+
        | Zona óptima           | ``recipe.puntos_optimos``                  |
        +-----------------------+--------------------------------------------+
        | Zona baja             | ``max(1, puntos_optimos // 3)`` ¹          |
        +-----------------------+--------------------------------------------+

        ¹ Assumption: RECIPE_DATABASE.md describe «pocos puntos» sin dar la fórmula
        exacta. Se usa 1/3 de los puntos óptimos con mínimo de 1.

        Args:
            recipe: Receta de la masa que se está horneando.
            posicion: Posición actual en el track de fermentación.
            fue_colapso: True si es un horneado forzado por sobrefermentación.

        Returns:
            Puntos de Maestría (entero, puede ser negativo).
        """
        if fue_colapso or recipe.esta_sobrefermentada(posicion):
            return recipe.penalizacion_colapso

        if recipe.esta_en_zona_optima(posicion):
            return recipe.puntos_optimos

        # Zona baja: masa cruda
        return max(1, recipe.puntos_optimos // PUNTOS_ZONA_BAJA_DIVISOR)

    def _calcular_datos_horneado(
        self,
        player: Player,
        recipe: Recipe,
        posicion: int,
    ) -> int:
        """
        Calcula los Datos de Investigación ganados al hornear una masa.

        Reglas (ACTIONS_REGISTRY.md §2F y §2D):
          · Zona baja o sobrefermentada: 0 datos.
          · Zona óptima: ``DATOS_BAKE_ZONA_OPTIMA`` (1 dato).
          · Centro exacto + Módulo Analítico activo:
            +``DATOS_BAKE_CENTRO_EXACTO_BONUS`` datos adicionales.

        Args:
            player: Jugador que hornea (se verifica si tiene Módulo Analítico).
            recipe: Receta de la masa.
            posicion: Posición actual en el track.

        Returns:
            Datos de Investigación otorgados (0, 1 o 2).
        """
        if not recipe.esta_en_zona_optima(posicion):
            return 0

        datos: int = DATOS_BAKE_ZONA_OPTIMA

        # Bono por hornear en el centro exacto con Módulo Analítico instalado.
        if recipe.es_centro_exacto(posicion) and player.tecnologias.modulo_analitico:
            datos += DATOS_BAKE_CENTRO_EXACTO_BONUS

        return datos

    # ==================================================================
    # EVALUACIÓN DE FIN DE PARTIDA
    # ==================================================================

    def _evaluar_fin_de_juego(self) -> bool:
        """
        Verifica si se activó algún gatillo de fin de partida al concluir el día.

        Los gatillos se detectan y registran de forma proactiva durante el día:
          · ``_robar_carta_clima()`` activa el flag al agotar el mazo de clima.
          · ``resolver_horneado()`` activa el flag al alcanzar 5 horneados exitosos.

        Este método solo lee el flag; no realiza modificaciones de estado.

        Returns:
            True si la partida ha terminado, False si debe continuar.
        """
        return self._partida_terminada

    def calcular_ranking_final(self) -> List[Tuple[int, Player]]:
        """
        Calcula el ranking final de los jugadores al terminar la partida.

        Criterios (CORE_MECHANICS.md §3 «Desempate»):
          1. Puntos de Maestría totales (``Player.puntos_maestria_final``).
          2. Desempate 1: mayor Vitalidad actual del cultivo base.
          3. Desempate 2: mayor cantidad de Datos de Investigación.
          4. Si persiste empate: orden de inscripción (posición en la lista).

        Se puede llamar en cualquier momento (resultados parciales si la partida
        aún no ha terminado).

        Returns:
            Lista de tuplas ``(posición_1based, player)`` ordenada de mayor
            a menor puntaje. El primero es el ganador.
        """
        ranking: List[Player] = sorted(
            self._players,
            key=lambda p: (
                p.puntos_maestria_final,
                p.vitalidad,
                p.datos_investigacion,
            ),
            reverse=True,
        )
        return [(pos + 1, player) for pos, player in enumerate(ranking)]

    # ==================================================================
    # UTILIDADES INTERNAS
    # ==================================================================

    def _orden_de_turno(self) -> List[Player]:
        """
        Retorna la lista de jugadores en orden de turno para la Fase II.

        El Investigador Jefe actúa primero (prioridad en mercados y acciones).
        Los demás siguen en su orden original de inscripción a la partida.
        Si el Jefe no se ha determinado aún (antes del primer día), se usa el
        orden original.

        Returns:
            Lista ordenada de jugadores para la Fase II del día actual.
        """
        if self._jefe_investigador is None:
            return list(self._players)

        resto: List[Player] = [
            p for p in self._players if p is not self._jefe_investigador
        ]
        return [self._jefe_investigador] + resto

    def __repr__(self) -> str:
        jefe_nombre: Optional[str] = (
            self._jefe_investigador.nombre if self._jefe_investigador else None
        )
        return (
            f"GameEngine("
            f"día={self._environment.dia_actual}, "
            f"jugadores={[p.nombre for p in self._players]}, "
            f"jefe={jefe_nombre!r}, "
            f"temp={self._environment.temperatura_actual}°C, "
            f"terminada={self._partida_terminada})"
        )
