"""
engine.py — Motor de Juego de Fermentum
=========================================
Orquesta el bucle principal del simulador: el «Día de Laboratorio».

Contenido:
  · Constantes de configuración del mercado y puntuación.
  · Market — modelo auxiliar del mercado central (idealmente pertenecería a
    models.py; se ubica aquí porque models.py está cerrado y es exclusivo de
    la capa de lógica del motor).
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
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

from events import EventoTipo, EventSink, GameEvent
from exceptions import (
    GameAlreadyOverError,
    InsufficientPlayersError,
    InvalidActionError,
    MarketSlotEmptyError,
    PhaseViolationError,
)
from models import (
    ClimateCard,
    EfectoBiologico,
    EfectoClimatico,
    Environment,
    AMPLIACION_OPTIMA_MODULO,
    FermentationSlot,
    Grado,
    HorneadoRecord,
    Player,
    Recipe,
    TipoHarina,
    build_tendencias_deck,
    TOTAL_MAZO_RECETAS,
    expandir_copias,
    get_recetas_avanzadas,
    get_recetas_basicas,
    get_recetas_intermedias,
)

# ===========================================================================
# SECCIÓN 1: CONSTANTES DE CONFIGURACIÓN
# ===========================================================================

# --- Mercado Central ---
NUM_RECIPE_SLOTS: int = 4
"""Número de ranuras de recetas visibles en el mercado. Convención de eurogames."""

# --- Datos de Investigación por Horneado ---
DATOS_BAKE_ZONA_OPTIMA: int = 1
"""Datos otorgados al hornear dentro de la zona óptima (ACTIONS_REGISTRY.md §2F)."""

DATOS_BAKE_CENTRO_EXACTO_BONUS: int = 1
"""
Datos extra al hornear en el CENTRO EXACTO de la zona óptima con Módulo Analítico
activo. Se suma encima de ``DATOS_BAKE_MODULO_BONUS``, de modo que con el Módulo un
horneado paga 2 Datos en la zona óptima y 3 en el centro exacto (ACTIONS_REGISTRY.md §2D).
"""

DATOS_BAKE_MODULO_BONUS: int = 1
"""
Datos extra al hornear en CUALQUIER punto de la zona óptima con Módulo Analítico.

El Módulo era una compra trampa cuando su único efecto era el bono de centro exacto:
había que clavar el centro unas tres veces sólo para amortizar su precio. Ahora paga
en toda la zona, que es lo que convierte al Módulo en el motor de investigación de la
partida (y lo que justifica su precio de 4 Datos en ``actions.COSTOS_TECNOLOGIA``).
"""

PRECIO_RECETA: Mapping[Grado, int] = MappingProxyType({
    Grado.BASICA: 1,
    Grado.INTERMEDIA: 2,
    Grado.AVANZADA: 3,
})
"""
Coste en Monedas de adquirir una receta del mercado (Acción G), por grado.

Las recetas eran lo único gratis del juego: el mercado era una cola, no una economía.
El precio se indexa por GRADO y no por carta, igual que ``COPIAS_POR_GRADO`` y
``PRECIO_PLIEGUES``: el grado ya lo derivan las harinas impresas, así que el precio no
puede contradecir a la carta ni hace falta un campo nuevo en ``Recipe``.

Es aditivo sobre el 1 PA de la Acción G, que sigue siendo la escasez real.
"""

PRECIO_RENTA: Mapping[Grado, int] = MappingProxyType({
    Grado.BASICA: 1,
    Grado.INTERMEDIA: 2,
    Grado.AVANZADA: 3,
})
"""
Monedas que paga CADA horneado exitoso del archivo en CADA Fase III.

Una receta horneada con éxito deja de ser historial y pasa a ser una fuente de
ingresos: la panadería acumula clientela. Eso convierte el momento de hornear en una
decisión de inversión — hornear pronto rinde más que hornear tarde — en vez de un acto
puramente de puntuación.

**No es dinero nuevo.** Los pagos por zona de las 12 cartas se recortaron en
``PRECIO_RENTA[grado] * 3`` (Básica -3, Intermedia -6, Avanzada -9) sobre las tres
zonas, de modo que el total se conserva y lo que cambia es CUÁNDO se cobra. El 3 es un
**horizonte de amortización común a todos los grados**: cualquier horneado recupera su
pago antiguo al tercer día, así que la presión temporal es idéntica sea cual sea la
carta y elegir receta sigue siendo una cuestión de puntos y harina, no de velocidad de
retorno. Ese 3 no es una constante de runtime: es la derivación con la que se autoraron
los números de ``RECIPE_CATALOG``, y vive aquí documentado y no en el código.

Se indexa por GRADO, como ``PRECIO_RECETA`` / ``COPIAS_POR_GRADO`` / ``PRECIO_PLIEGUES``:
el grado lo derivan las harinas impresas, así que la renta no puede contradecir a la
carta ni hace falta un campo nuevo en ``Recipe``.

Sólo paga ``archivo_horneado_exitoso``. Un colapso va a ``archivo_colapsos`` y no cobra
nada: provocar un colapso es gratis (iniciar una masa y dejar que la Fase III la hornee
sola), así que pagarlo sería regalar la renta sin hornear bien nada — el mismo argumento
de incentivos que ya rige «Variedad de Recetas».
"""

DATOS_SIMPOSIO: Mapping[Grado, int] = MappingProxyType({
    Grado.BASICA: 1,
    Grado.INTERMEDIA: 2,
    Grado.AVANZADA: 3,
})
"""
Datos de Investigación que entrega el Simposio Técnico por el horneado sacrificado.

Es **deliberadamente una constante distinta de ``PRECIO_RENTA``** aunque hoy tengan los
mismos valores: compartir una sola tabla acoplaría dos reglas sin relación entre sí, y
reequilibrar la renta movería en silencio lo que paga el Simposio.

Es tacaña a propósito. Sacrificar un horneado cuesta sus puntos base (9-20 PM), su renta
para el resto de la partida y puede bajar un escalón de «Variedad de Recetas», así que
ningún rendimiento en Datos lo hace *eficiente*. Su papel es ser una **palanca de
emergencia** — quemar un éxito pasado para salvar el presente — y no una jugada de
motor. En la práctica se sacrifica siempre la carta más barata que se tenga.
"""

# --- Bono de Sabor en Monedas (Hornear y Vender) ---
MONEDAS_BONO_SABOR: int = 2
"""
Monedas adicionales al hornear y vender si el Cubo de Acidez estaba sellado
(GDD v0.0.2, Módulo III §F). Se excluye en un colapso, igual que el bono de
Puntos de Maestría — ambos comparten la condición `bono_sabor_aplicado`.
"""

# --- Bolsa de Harinas (Visitar el Mercado) ---
POSICION_HARINA_INICIAL: int = 3
"""Posición inicial (1-5) de los 3 visores de harina, antes de la primera Tendencia."""

POSICION_HARINA_MIN: int = 1
POSICION_HARINA_MAX: int = 5

PRECIOS_HARINA: Dict[TipoHarina, Dict[str, Tuple[int, int, int, int, int]]] = {
    TipoHarina.BLANCA: {
        "compra": (2, 3, 4, 5, 6),
        "venta": (1, 2, 3, 4, 5),
    },
    TipoHarina.INTEGRAL: {
        "compra": (4, 5, 6, 7, 8),
        "venta": (2, 3, 4, 5, 6),
    },
    TipoHarina.CENTENO: {
        "compra": (6, 7, 8, 9, 10),
        "venta": (3, 4, 5, 6, 7),
    },
}
"""
Tabla de precios (en Monedas) de la Bolsa de Harinas, indexada por posición del
visor (1-5, GDD v0.0.2 Módulo III §C). ``precios["compra"][posicion - 1]``.
"""

CANTIDAD_BOLSA_PCT: int = 100
"""Bolsa entera de harina: 10 tokens del 10% (la unidad en la que opera el mercado)."""

CANTIDAD_MEDIA_BOLSA_PCT: int = 50
"""Media bolsa: 5 tokens. Compra redondeando hacia arriba, venta hacia abajo."""

PRECIO_AGUA: Dict[int, Dict[int, int]] = {
    30: {10: 3, 30: 6, 60: 10, 100: 14},
    25: {10: 2, 30: 5, 60: 8, 100: 12},
    20: {10: 2, 30: 4, 60: 7, 100: 10},
    15: {10: 1, 30: 3, 60: 6, 100: 9},
    10: {10: 1, 30: 2, 60: 4, 100: 7},
}
"""
Matriz de precios (en Monedas) del Suministro Hídrico Global, indexada por
[temperatura_actual][lote_pct] (GDD v0.0.2 Módulo III §C). Las 5 filas cubren
toda temperatura alcanzable desde la base de 20°C con los modificadores del
mazo de clima (0, ±5, ±10).
"""

AGUA_TOKENS_POR_LOTE: Dict[int, int] = {10: 2, 30: 6, 60: 12, 100: 20}
"""Tokens de agua (5% c/u) recibidos por cada tamaño de lote comprado."""

# --- Técnica de Pliegues (Acción E) ---
PRECIO_PLIEGUES: Dict[int, int] = {1: 1, 2: 3, 3: 6}
"""
Escalera de precios (en Monedas) de la Acción E: espacios totales comprados ->
coste. Es deliberadamente creciente al margen (1, 2 y 3 Monedas por el 1º, 2º y
3er espacio) para que la versión fuerte sea una inversión real al cambio de
5 Monedas = 1 Punto de Maestría del recuento final (CORE_MECHANICS.md §3.5).
"""

PRECIO_PLIEGUES_VITALIDAD: int = 6
"""
Coste (en Monedas) de la variante 'recuperar_vitalidad' de la Acción E, que
requiere Cámara B. Se fija al nivel del escalón más caro de PRECIO_PLIEGUES
porque el desgaste metabólico es de -1 Vitalidad por día: a un precio bajo,
comprarla a diario equivaldría a inmunidad permanente a la Contaminación.
"""

# --- Descarte y Refresco del cultivo (control de Acidez) ---
PRECIO_DESCARTE: Dict[int, int] = {1: 1, 2: 3, 3: 6}
"""
Escalera de precios (en Monedas) del sentido *descendente* del Descarte:
niveles de Acidez retirados -> coste. Descartar parte del cultivo y refrescarlo
con harina nueva es la operación que en panadería real baja la acidez, y es
tirar producto: por eso se paga y por eso el sentido contrario (subir, que es
sólo añadir agua) no cuesta Monedas.

Marginal creciente (1, 2 y 3 Monedas por el 1º, 2º y 3er nivel) por la misma
razón que ``PRECIO_PLIEGUES``: el volumen nunca es un descuento.
"""

COSTE_REFRESCO_AGUA: Dict[int, int] = {1: 2, 2: 5, 3: 9}
"""
Escalera de costes (en tokens de Agua) del sentido *ascendente* del Descarte:
niveles de Acidez ganados -> tokens. El primer escalón son los mismos 2 tokens
que costaba la mitad de agua de la Acción A antes de que el control de Acidez
se consolidara aquí, así que subir un nivel cuesta hoy exactamente lo que
costaba entonces.

Marginal creciente (2, 3 y 4 tokens) en espejo de ``PRECIO_DESCARTE``.
"""

# ===========================================================================
# SECCIÓN 2: MODELOS AUXILIARES DEL MERCADO CENTRAL
# ===========================================================================


def _texto_modificador(modificador: int) -> str:
    """Modificador de tendencia para mensajes al jugador: ``+2`` / ``-1`` /
    ``sin cambio`` (en vez del poco natural ``+0``)."""
    return f"{modificador:+d}" if modificador else "sin cambio"


@dataclass
class Market:
    """
    Estado del mercado central compartido entre todos los jugadores.

    El mercado de recetas funciona como una cola con antigüedad visible:
      · Posición 0 (izquierda) = carta más nueva (recién incorporada).
      · Posición N-1 (derecha) = carta más antigua (próxima a descartarse).

    Rotación del mercado de recetas (CORE_MECHANICS.md §2), en dos mitades:
      · **Fin del día (Fase III)**: ``descartar_receta_mas_antigua()`` retira la
        carta real más a la derecha y la manda al descarte.
      · **Inicio del día (Fase I)**: ``protocolo_refresco()`` compacta las cartas
        supervivientes y rellena todos los huecos hasta ``NUM_RECIPE_SLOTS``,
        revelando cartas nuevas a la izquierda. Si el mazo se agota, baraja el
        descarte como mazo nuevo.

    Bolsa de Harinas y Mercado de Tendencias (GDD v0.0.2, Módulo III §C / Módulo II §6):
      · ``posiciones_harina``: 3 visores compartidos (Blanca/Integral/Centeno), cada uno
        una posición 1-5 que indexa ``PRECIOS_HARINA`` para el costo de Comprar/Vender
        Harina en la Acción C (Visitar el Mercado).
      · ``mazo_tendencias``/``descarte_tendencias``: mazo de 21 cartas que desplaza
        los 3 visores simultáneamente, también en dos mitades (CORE_MECHANICS.md §2):
        se **revela** al inicio del día (Fase I, ``robar_tendencia``) como pronóstico,
        y se **aplica** al final del día (Fase III, ``aplicar_tendencia_pendiente``),
        de modo que rige los precios del día SIGUIENTE. Entre ambos momentos la carta
        vive en ``tendencia_pendiente``, a la vista de todos.

    Attributes:
        recetas_visibles: Lista de NUM_RECIPE_SLOTS slots de recetas activas.
            ``None`` indica que el slot fue tomado por un jugador este día.
        mazo_recetas: Mazo oculto de recetas pendientes de aparecer en el mercado.
        descarte_recetas: Recetas descartadas del mercado (se remezclan si el mazo se agota).
        posiciones_harina: Posición actual (1-5) de cada visor de la Bolsa de Harinas.
        mazo_tendencias: Mazo de Tendencias de Mercado sin robar todavía.
        descarte_tendencias: Cartas de Tendencia ya APLICADAS (se remezclan si el mazo
            se agota). La carta revelada hoy todavía no está aquí: ver
            ``tendencia_pendiente``.
        tendencia_pendiente: Carta revelada al inicio del día y pendiente de aplicarse
            al final de este mismo día. ``None`` fuera de esa ventana (incluido el
            Día 1 antes de su Fase I, que por eso se juega con los precios iniciales).
    """

    recetas_visibles: List[Optional[Recipe]]
    mazo_recetas: List[Recipe]
    descarte_recetas: List[Recipe] = field(default_factory=list)
    posiciones_harina: Dict[TipoHarina, int] = field(
        default_factory=lambda: {
            TipoHarina.BLANCA: POSICION_HARINA_INICIAL,
            TipoHarina.INTEGRAL: POSICION_HARINA_INICIAL,
            TipoHarina.CENTENO: POSICION_HARINA_INICIAL,
        }
    )
    mazo_tendencias: List[int] = field(default_factory=list)
    descarte_tendencias: List[int] = field(default_factory=list)
    tendencia_pendiente: Optional[int] = None

    # ------------------------------------------------------------------
    # Factory Method
    # ------------------------------------------------------------------

    @classmethod
    def crear_inicial(cls) -> "Market":
        """
        Construye el mercado en su estado inicial de partida.

        El mazo de recetas son las 36 cartas físicas (cada protocolo con sus
        copias, ver ``COPIAS_POR_GRADO``): las "de compra" -- Avanzadas e
        Intermedias mezcladas entre sí -- con las Básicas barajadas al fondo
        como reserva.
        Se revelan las primeras NUM_RECIPE_SLOTS cartas. Los 3 visores de la Bolsa
        de Harinas inician en ``POSICION_HARINA_INICIAL`` y el mazo de Tendencias
        de Mercado (21 cartas) se baraja.

        Las Intermedias van MEZCLADAS con las Avanzadas, no en un tercer estrato
        por debajo: el escalón medio existe para escalarse durante la partida, y
        un mazo en escalera estricta lo haría aparecer justo cuando ya sobra.
        Las Básicas siguen al fondo por la razón de siempre: cada jugador ya
        empieza con una, así que en el mercado son la red de seguridad para
        cuando el mazo principal se agota.

        Returns:
            Instancia de Market lista para el inicio de la partida.
        """
        # Cartas de compra: lo que un jugador va al mercado a buscar. Cada
        # protocolo entra con sus copias físicas (COPIAS_POR_GRADO): las Básicas
        # son comunes y las Avanzadas escasas, así que la rareza es una barrera
        # independiente del precio.
        principales: List[Recipe] = expandir_copias(
            get_recetas_avanzadas() + get_recetas_intermedias()
        )
        basicas: List[Recipe] = expandir_copias(get_recetas_basicas())
        random.shuffle(principales)
        random.shuffle(basicas)
        mazo: List[Recipe] = principales + basicas
        assert len(mazo) == TOTAL_MAZO_RECETAS, (
            f"El mazo de recetas debe tener exactamente {TOTAL_MAZO_RECETAS} "
            f"cartas, los dos estratos suman {len(mazo)}."
        )

        visibles: List[Optional[Recipe]] = [
            (mazo.pop(0) if mazo else None) for _ in range(NUM_RECIPE_SLOTS)
        ]

        mercado = cls(recetas_visibles=visibles, mazo_recetas=mazo)
        mercado.mazo_tendencias = build_tendencias_deck()
        random.shuffle(mercado.mazo_tendencias)
        return mercado

    # ------------------------------------------------------------------
    # Protocolo de Refresco
    # ------------------------------------------------------------------

    def protocolo_refresco(self) -> int:
        """
        Reabastece el mercado de recetas al inicio del día (Fase I).

        Reglas (CORE_MECHANICS.md §2, Fase I) — solo rellena, no descarta (el
        descarte de la carta más antigua ocurre al final del día anterior, ver
        ``descartar_receta_mas_antigua``):
          - Compacta las cartas supervivientes conservando su orden
            (más nueva → más antigua).
          - Revela cartas nuevas del mazo, a la izquierda, hasta volver a tener
            ``NUM_RECIPE_SLOTS`` recetas visibles. Si el mazo se agota, baraja el
            descarte como nuevo mazo. Si mazo y descarte quedan vacíos, el mercado
            puede quedar por debajo del máximo (huecos ``None`` al extremo derecho).

        Returns:
            Número de cartas nuevas reveladas en esta llamada.
        """
        supervivientes: List[Recipe] = [
            r for r in self.recetas_visibles if r is not None
        ]

        nuevas: List[Recipe] = []
        for _ in range(NUM_RECIPE_SLOTS - len(supervivientes)):
            if not self.mazo_recetas and self.descarte_recetas:
                self.mazo_recetas = self.descarte_recetas[:]
                self.descarte_recetas = []
                random.shuffle(self.mazo_recetas)
            if not self.mazo_recetas:
                break
            nuevas.append(self.mazo_recetas.pop(0))

        # Nuevas a la izquierda (más nuevas); supervivientes a su derecha; los
        # huecos que no se pudieron rellenar quedan al extremo derecho (más
        # antiguo), que es justo lo próximo a descartarse.
        combinadas: List[Optional[Recipe]] = [*nuevas, *supervivientes]
        combinadas += [None] * (NUM_RECIPE_SLOTS - len(combinadas))
        self.recetas_visibles = combinadas

        return len(nuevas)

    def descartar_receta_mas_antigua(self) -> Optional[Recipe]:
        """
        Descarta la receta visible más antigua del mercado (fin del día, Fase III).

        Recorre ``recetas_visibles`` desde la derecha (más antigua) hasta la
        primera carta real, la retira (el slot queda ``None``) y la manda a
        ``descarte_recetas``. La compactación de los huecos la hace el
        ``protocolo_refresco`` del día siguiente.

        Returns:
            La receta descartada, o ``None`` si el mercado no tiene ninguna carta.
        """
        for i in range(len(self.recetas_visibles) - 1, -1, -1):
            receta: Optional[Recipe] = self.recetas_visibles[i]
            if receta is not None:
                self.recetas_visibles[i] = None
                self.descarte_recetas.append(receta)
                return receta
        return None

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

    # ------------------------------------------------------------------
    # Bolsa de Harinas (Acción C: Visitar el Mercado)
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_cantidad(cantidad_pct: int) -> None:
        if cantidad_pct not in (CANTIDAD_BOLSA_PCT, CANTIDAD_MEDIA_BOLSA_PCT):
            raise InvalidActionError(
                f"cantidad_pct inválida: {cantidad_pct!r}. El mercado opera en "
                f"bolsa entera ({CANTIDAD_BOLSA_PCT}%) o media "
                f"({CANTIDAD_MEDIA_BOLSA_PCT}%)."
            )

    def precio_compra_harina(
        self, tipo: TipoHarina, cantidad_pct: int = CANTIDAD_BOLSA_PCT
    ) -> int:
        """
        Costo en Monedas de comprar una bolsa de ``tipo`` en su posición actual.

        Media bolsa cuesta la MITAD REDONDEADA HACIA ARRIBA del precio visible
        (GDD v0.0.2 Módulo III §C). El redondeo no es un detalle: es lo que
        impide que media bolsa sea un arbitraje — con precios impares sale peor
        por token que la bolsa entera, así que es liquidez, no descuento.
        """
        self._validar_cantidad(cantidad_pct)
        posicion = self.posiciones_harina[tipo]
        entero = PRECIOS_HARINA[tipo]["compra"][posicion - 1]
        if cantidad_pct == CANTIDAD_BOLSA_PCT:
            return entero
        return (entero + 1) // 2

    def precio_venta_harina(
        self, tipo: TipoHarina, cantidad_pct: int = CANTIDAD_BOLSA_PCT
    ) -> int:
        """
        Monedas recibidas al vender una bolsa de ``tipo`` en su posición actual.

        Media bolsa cobra la mitad REDONDEADA HACIA ABAJO (misma razón que en
        la compra, en el otro sentido). Puede dar 0 Monedas —Blanca en posición
        1— y eso es legal: el jugador entrega media bolsa a cambio de mover el
        visor hacia abajo, y lo ve antes de confirmar.
        """
        self._validar_cantidad(cantidad_pct)
        posicion = self.posiciones_harina[tipo]
        entero = PRECIOS_HARINA[tipo]["venta"][posicion - 1]
        if cantidad_pct == CANTIDAD_BOLSA_PCT:
            return entero
        return entero // 2

    def mover_visor_harina(self, tipo: TipoHarina, hacia_caro: bool) -> None:
        """
        Desplaza 1 casilla el visor de ``tipo`` (comprar → más caro, vender → más
        barato), respetando los topes [``POSICION_HARINA_MIN``, ``POSICION_HARINA_MAX``].

        Args:
            tipo: Tipo de harina cuyo visor se desplaza.
            hacia_caro: True al comprar (+1), False al vender (-1).
        """
        delta = 1 if hacia_caro else -1
        nueva = self.posiciones_harina[tipo] + delta
        self.posiciones_harina[tipo] = max(
            POSICION_HARINA_MIN, min(POSICION_HARINA_MAX, nueva)
        )

    # ------------------------------------------------------------------
    # Mazo de Tendencias de Mercado (se revela en Fase I, se aplica en Fase III)
    # ------------------------------------------------------------------

    def robar_tendencia(self) -> int:
        """
        Revela la carta superior del mazo de Tendencias de Mercado (Fase I),
        remezclando el descarte como nuevo mazo si estaba agotado (mismo patrón
        que el mazo de recetas en ``protocolo_refresco``).

        **Solo revela: NO mueve los visores.** La carta queda en
        ``tendencia_pendiente`` a la vista de todos durante el día y se aplica al
        final del mismo (``aplicar_tendencia_pendiente``), por lo que rige los
        precios del día siguiente y no los de hoy.

        Returns:
            El modificador entero de la carta revelada (-2, -1, 0, +1 o +2).
        """
        if not self.mazo_tendencias and self.descarte_tendencias:
            self.mazo_tendencias = self.descarte_tendencias[:]
            self.descarte_tendencias = []
            random.shuffle(self.mazo_tendencias)

        modificador: int = self.mazo_tendencias.pop(0)
        self.tendencia_pendiente = modificador
        return modificador

    def aplicar_tendencia_pendiente(self) -> Optional[int]:
        """
        Aplica al final del día (Fase III) la tendencia revelada esta mañana:
        desplaza los 3 visores y manda la carta al descarte.

        Returns:
            El modificador aplicado, o ``None`` si no había ninguno pendiente
            (p.ej. si se llama dos veces, o antes de la primera Fase I).
        """
        modificador: Optional[int] = self.tendencia_pendiente
        if modificador is None:
            return None

        self.aplicar_tendencia(modificador)
        self.descarte_tendencias.append(modificador)
        self.tendencia_pendiente = None
        return modificador

    def aplicar_tendencia(self, modificador: int) -> None:
        """
        Desplaza los 3 visores de la Bolsa de Harinas por ``modificador``
        simultáneamente, cada uno con su propio tope [1, 5] (sin arrastre ni
        efecto acumulado más allá del límite — GDD v0.0.2 Módulo II §6).
        """
        for tipo in self.posiciones_harina:
            nueva = self.posiciones_harina[tipo] + modificador
            self.posiciones_harina[tipo] = max(
                POSICION_HARINA_MIN, min(POSICION_HARINA_MAX, nueva)
            )

    def __repr__(self) -> str:
        recetas_str = [r.nombre if r else "—" for r in self.recetas_visibles]
        posiciones_str = {t.value: p for t, p in self.posiciones_harina.items()}
        return (
            f"Market(recetas={recetas_str}, "
            f"mazo_restante={len(self.mazo_recetas)}, "
            f"posiciones_harina={posiciones_str})"
        )


# ===========================================================================
# SECCIÓN 3: MOTOR PRINCIPAL DEL JUEGO
# ===========================================================================

# Alias de tipo para el callback de turno de jugador (Fase II).
TurnCallback = Callable[["GameEngine", Player], None]


class Fase(str, Enum):
    """
    Fase actual del Día de Laboratorio, expuesta por ``GameEngine.fase_actual``.

    Sostiene la máquina de estado de turno no bloqueante (``iniciar_dia``,
    ``jugador_activo``, ``terminar_turno_actual``, ``pasar_turno``,
    ``resolver_fase_III``) que coexiste con la ruta bloqueante original
    (``ejecutar_dia_laboratorio`` con callback síncrono, usada por la CLI).
    Ambas rutas comparten la misma implementación de ronda de turnos
    (``_preparar_fase_II`` / ``_avanzar_a_siguiente_elegible``) para que no
    puedan divergir en su comportamiento.
    """

    PREPARACION = "preparacion"
    FASE_I = "fase_i"
    FASE_II = "fase_ii"
    FASE_III = "fase_iii"
    TERMINADA = "terminada"


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
        event_sink: Optional[EventSink] = None,
        orden_inicial: Optional[List[int]] = None,
    ) -> None:
        """
        Inicializa el motor de juego con inyección de dependencias.

        Args:
            players: Lista de investigadores participantes (1-4).
            environment: Estado del entorno global (temperatura, mazo de clima, día).
            market: Estado del mercado central. Si ``None``, se crea automáticamente
                con ``Market.crear_inicial()``.
            event_sink: Invocable opcional ``(GameEvent) -> None`` al que se
                reenvía cada evento en el momento en que se emite (p. ej.
                para transmitirlo a clientes conectados). El motor conserva
                el registro completo en ``self.eventos`` independientemente
                de si se proporciona un sink.
            orden_inicial: Índices en ``players``, ordenados ascendentemente por
                Iniciativa de la Carta de Patrocinio repartida en el setup (GDD
                v0.0.2, Módulo I §6.4). Cuando se proporciona, determina el
                Investigador Jefe y el orden de turno del Día 1 únicamente —
                ``self._players`` NUNCA se reordena, así que esto no afecta a
                ``Seat.player_index`` en ``server/sessions.py``. A partir del
                Día 2, el criterio habitual (mayor Vitalidad, desempate por
                Datos) vuelve a aplicarse sin cambios. ``None`` (por defecto)
                preserva el comportamiento anterior a esta funcionalidad —
                usado por cualquier construcción directa de ``GameEngine`` que
                no pase por ``bootstrap.create_game()`` (p. ej. tests).

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
        self._orden_inicial_iniciativa: Optional[List[int]] = orden_inicial

        # Estado interno del turno actual
        self._jefe_investigador: Optional[Player] = None
        self._partida_terminada: bool = False

        # Registro de eventos (ver events.py).
        self._eventos: List[GameEvent] = []
        self._event_sink: Optional[EventSink] = event_sink

        # Máquina de estado de turno no bloqueante (ver clase Fase).
        self._fase: Fase = Fase.PREPARACION
        self._turno_orden: List[int] = []  # Índices en self._players.
        self._turno_cursor: int = 0
        self._turno_nonce: int = 0
        self._turno_pasado: Set[int] = set()  # Índices que ya ejecutaron pasar_turno() hoy.

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

    @property
    def fase_actual(self) -> Fase:
        """Fase actual del Día de Laboratorio (ver clase ``Fase``)."""
        return self._fase

    def forzar_fin_de_partida(self) -> None:
        """
        Termina la partida de inmediato, fuera de los dos gatillos naturales
        (mazo de clima agotado, 5º horneado exitoso) -- usado cuando todos
        los jugadores acuerdan terminar antes de tiempo (ver ``server/``).

        Deja el motor en el mismo estado terminal que produce un fin
        natural (``_partida_terminada`` y ``_fase`` en ``Fase.TERMINADA``),
        en vez de esperar al próximo ``resolver_fase_III()`` -- así
        ``calcular_ranking_final()`` (que ya es válido "en cualquier
        momento", ver su docstring) y todo el resto de la vista de estado
        siguen funcionando sin cambios para un fin anticipado.

        Raises:
            GameAlreadyOverError: Si la partida ya había terminado.
        """
        if self._partida_terminada:
            raise GameAlreadyOverError("La partida ya había terminado.")
        self._partida_terminada = True
        self._fase = Fase.TERMINADA

    @property
    def jugador_activo(self) -> Optional[Player]:
        """
        Jugador cuyo turno está activo en la Fase II actual, o ``None`` si
        la Fase II no está en curso o su ronda de turnos ya se agotó (todos
        los jugadores sin PA y sin acciones gratuitas pendientes).

        Un jugador sigue siendo elegible para una visita mientras tenga
        ``puntos_accion > 0`` **o** aún no haya usado su Acción A (Alimentar)
        u Horas Extras este día — ambas acciones gratuitas no terminan el
        turno de quien las usa, así que un jugador sin PA conserva su vuelta
        exclusivamente para poder usarlas (salvo que ya haya pasado
        explícitamente con ``pasar_turno``, lo que cede el resto del día).
        """
        if self._fase != Fase.FASE_II:
            return None
        return self._players[self._turno_orden[self._turno_cursor]]

    @property
    def turno_orden(self) -> List[int]:
        """
        Índices en ``self.players`` en el orden de juego del día actual
        (``[0]`` = Investigador Jefe en todas las ramas: Día 1 por Iniciativa
        de Patrocinio, Día 2+ como ``[jefe] + resto`` en orden de inscripción).

        Lo llena ``_preparar_fase_II``; entre ``resolver_fase_III`` y el
        siguiente ``iniciar_dia`` conserva el orden del día anterior. Copia
        defensiva, igual que ``eventos``.
        """
        return list(self._turno_orden)

    @property
    def turno_nonce(self) -> int:
        """
        Contador que se incrementa cada vez que se cierra una visita de
        turno (``terminar_turno_actual`` / ``pasar_turno``). Sirve como
        guarda de "sumisión obsoleta" para llamadores externos (p. ej. un
        servidor) que necesitan detectar una acción enviada contra un
        estado de turno que ya cambió.
        """
        return self._turno_nonce

    @property
    def eventos(self) -> List[GameEvent]:
        """
        Registro completo de eventos emitidos durante la partida hasta el
        momento (ver ``events.py``), en orden de emisión. Un llamador que
        solo quiera los eventos nuevos desde su última lectura puede
        recordar ``len(engine.eventos)`` y volver a leer desde ese índice.
        """
        return list(self._eventos)

    def _emit(
        self,
        tipo: EventoTipo,
        jugador_idx: Optional[int] = None,
        datos: Optional[Dict[str, object]] = None,
        mensaje: str = "",
    ) -> None:
        """Registra un ``GameEvent`` y lo reenvía a ``self._event_sink`` si hay uno."""
        evento = GameEvent(
            tipo=tipo,
            dia=self._environment.dia_actual,
            jugador_idx=jugador_idx,
            datos=datos or {},
            mensaje=mensaje,
        )
        self._eventos.append(evento)
        if self._event_sink is not None:
            self._event_sink(evento)

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
          3. :meth:`resolver_fase_III` — cinética biológica, desgaste y evaluación de fin.

        Este método SIEMPRE se detiene al final del día actual (no encadena
        automáticamente al Día siguiente) para preservar el punto de pausa
        que la CLI usa entre días (main.py: reporte + "Pulsa Enter…").

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
        return self.resolver_fase_III()

    def iniciar_dia(self) -> None:
        """
        Inicia el Día de Laboratorio actual sin bloquear a la espera de
        turnos: ejecuta la Fase I (automática) y deja el motor listo con el
        cursor de turno de Fase II posicionado en el primer jugador elegible.

        Alternativa no bloqueante a ``ejecutar_dia_laboratorio`` para
        llamadores externos (p. ej. un servidor) que necesitan resolver el
        turno de cada jugador en una llamada independiente en vez de un
        callback síncrono. Tras llamar a este método, se consulta
        ``jugador_activo`` y se resuelven acciones hasta que sea ``None``,
        y luego se llama a ``resolver_fase_III()``.

        Comparte ``_preparar_fase_II()`` con ``fase_II_accion()`` (la ruta
        bloqueante) para que ambas rutas no puedan divergir en el reset de
        PA/orden de turno ni en la condición de elegibilidad.

        Raises:
            GameAlreadyOverError: Si la partida ya terminó.
        """
        if self._partida_terminada:
            raise GameAlreadyOverError(
                f"La partida ya terminó en el Día {self._environment.dia_actual - 1}. "
                "No se pueden ejecutar más Días de Laboratorio."
            )

        self.fase_I_ambiente()
        self._preparar_fase_II()

    # ==================================================================
    # FASE I: AMBIENTE
    # ==================================================================

    def fase_I_ambiente(self) -> None:
        """
        Fase I: Ambiente — prepara el entorno global para el día (CORE_MECHANICS.md §2).

        Pasos (en orden):
          1. **Actualización de Jerarquía**: asigna el Investigador Jefe al jugador
             con mayor Vitalidad (desempate: Datos de Investigación) — salvo el
             Día 1, donde la Carta de Patrocinio de menor Iniciativa decide
             (ver ``orden_inicial`` en el constructor).
          2. **Reset de Entorno**: la temperatura vuelve a 20°C y el efecto pasivo
             se neutraliza antes de aplicar la carta del día.
          3. **Resolución del Clima**: roba la carta superior del mazo de clima,
             aplica su modificador térmico y registra el efecto pasivo vigente.
             Los efectos biológicos inmediatos (+Vitalidad / +Acidez) se aplican
             a todos los jugadores instantáneamente.
             Si el mazo se agota, se activa el gatillo de fin de partida.
          4. **Mercado de Tendencias**: revela una carta como pronóstico y la deja
             en ``Market.tendencia_pendiente``. **No mueve los visores todavía**:
             se aplica al final de este mismo día (``resolver_fase_III``), así que
             rige los precios de mañana. Los de hoy son los que dejó la tendencia
             de ayer, ya visibles durante toda la jornada.
          5. **Protocolo de Refresco**: reabastece el mercado de recetas hasta
             ``NUM_RECIPE_SLOTS``, rellenando los huecos dejados por Acción G y
             por el descarte de fin del día anterior. Ya no descarta aquí.
        """
        # Paso 1: Determinar Investigador Jefe
        if self._environment.dia_actual == 1 and self._orden_inicial_iniciativa is not None:
            self._jefe_investigador = self._players[self._orden_inicial_iniciativa[0]]
        else:
            self._jefe_investigador = self._determinar_investigador_jefe()
        self._emit(
            EventoTipo.JEFE_ASIGNADO,
            jugador_idx=self._players.index(self._jefe_investigador),
            datos={"nombre": self._jefe_investigador.nombre},
            mensaje=f"{self._jefe_investigador.nombre} es el Investigador Jefe hoy.",
        )

        # Paso 2: Reset del entorno al inicio del día
        self._environment.resetear_temperatura_base()
        self._environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
        temp_antes: int = self._environment.temperatura_actual

        # Paso 3: Resolver carta de clima
        carta: Optional[ClimateCard] = self._robar_carta_clima()
        if carta is not None:
            self._resolver_carta_clima(carta)
            self._emit(
                EventoTipo.CLIMA_REVELADO,
                datos={
                    "carta_id": carta.id,
                    "carta_nombre": carta.nombre,
                    "modificador_termico": carta.modificador_termico,
                    "temp_antes": temp_antes,
                    "temp_despues": self._environment.temperatura_actual,
                    "efecto_pasivo": carta.efecto_pasivo.value,
                    "efecto_biologico": carta.efecto_biologico.value,
                },
                mensaje=f"Carta de clima revelada: {carta.nombre} "
                        f"({carta.modificador_termico:+d}°C).",
            )

        # Paso 4: Mercado de Tendencias — SOLO se anuncia. La Bolsa de Harinas no
        # se mueve hoy: la carta se aplica al final de este día (Fase III) y por
        # tanto rige los precios de mañana. Los precios de hoy son los que dejó
        # la tendencia de ayer, ya visibles cuando los jugadores decidieron.
        modificador_tendencia: int = self._market.robar_tendencia()
        self._emit(
            EventoTipo.TENDENCIA_ANUNCIADA,
            datos={"modificador": modificador_tendencia},
            mensaje=(
                f"Tendencia anunciada ({_texto_modificador(modificador_tendencia)}): "
                "se aplicará al final del día y regirá los precios de mañana."
            ),
        )

        # Paso 5: Protocolo de Refresco del mercado (reabastece a NUM_RECIPE_SLOTS;
        # el descarte de la carta más antigua ocurrió al final del día anterior).
        reveladas: int = self._market.protocolo_refresco()
        self._emit(
            EventoTipo.MERCADO_REFRESCADO,
            datos={"reveladas": reveladas},
            mensaje=(
                f"El mercado se reabasteció con {reveladas} receta(s)."
                if reveladas
                else "El mercado central se refrescó."
            ),
        )

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
            self._emit(
                EventoTipo.FIN_DE_PARTIDA,
                datos={"motivo": "mazo_agotado"},
                mensaje="El mazo de clima se agotó. La partida termina al "
                        "concluir este día.",
            )

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
        Fase II: Acción — turnos intercalados (round-robin) hasta que ningún
        jugador tenga PA ni acciones gratuitas pendientes (CORE_MECHANICS.md §2).

        Flujo:
          1. ``_preparar_fase_II()`` reinicia PA/flags y calcula el orden de
             turno (delegado, compartido con la ruta no bloqueante).
          2. Mientras exista un ``jugador_activo``, se invoca el callback UNA
             SOLA VEZ; si el callback no cerró la visita él mismo (p. ej.
             llamando a ``pasar_turno``), se cierra aquí con
             ``terminar_turno_actual()`` — una invocación de callback por
             vuelta como máximo, igual que el comportamiento original.
          3. El bucle termina cuando ``jugador_activo`` es ``None``.

        Un jugador con 0 PA conserva su elegibilidad mientras aún no haya
        usado su Acción A u Horas Extras este día (ver ``jugador_activo``);
        el callback puede usar esa visita para ejecutar la acción gratuita
        pendiente. Este es el único cambio de comportamiento observable
        frente a la implementación original: antes, un jugador sin PA nunca
        volvía a ser visitado, y por lo tanto no podía alimentar su cultivo
        ni usar Horas Extras una vez agotados sus PA por otras vías.

        Args:
            ejecutar_turno_jugador: Callback ``(engine, player) -> None`` invocado
                una vez por jugador por vuelta del round-robin. ``None`` durante
                pruebas de integración del bucle de fases (equivalente a una
                Fase II sin jugadores: la ronda se da por agotada de inmediato).
        """
        self._preparar_fase_II()

        if ejecutar_turno_jugador is None:
            self._fase = Fase.FASE_III
            return

        while (player := self.jugador_activo) is not None:
            nonce_antes = self._turno_nonce
            ejecutar_turno_jugador(self, player)
            # Si el callback ya cerró la visita él mismo (llamando a
            # terminar_turno_actual()/pasar_turno() directamente -- p. ej.
            # la Acción P de la CLI, ver main.py), el nonce ya cambió y no
            # se debe cerrar una segunda vez.
            if self._turno_nonce == nonce_antes:
                self.terminar_turno_actual()

    # ==================================================================
    # MÁQUINA DE ESTADO DE TURNO (API no bloqueante, Fase II)
    # ==================================================================

    def _preparar_fase_II(self) -> None:
        """
        Prepara el estado de turno para la Fase II del día actual: resetea
        los indicadores de acciones gratuitas usadas, los espacios de acción
        con costo de PA ya visitados hoy, y los PA de todos los jugadores,
        calcula el orden de turno del día (Investigador Jefe primero), y
        posiciona el cursor en el primer jugador elegible.

        Compartido por ``fase_II_accion()`` (ruta bloqueante, usada por la
        CLI) e ``iniciar_dia()`` (ruta de estado explícito) para que ambas
        no puedan divergir en esta lógica.
        """
        orden: List[Player] = self._orden_de_turno()

        for player in orden:
            player.accion_alimentar_usada = False
            player.acciones_pa_usadas_hoy = []
        for player in orden:
            player.resetear_puntos_accion()

        self._turno_orden = [self._players.index(p) for p in orden]
        self._turno_cursor = 0
        self._turno_pasado = set()
        self._avanzar_a_siguiente_elegible(desde=0, incluir_actual=True)

    def _jugador_elegible(self, indice: int) -> bool:
        """
        True si el jugador en ``self._players[indice]`` conserva una visita
        pendiente en la ronda de Fase II actual.

        Un jugador que ejecutó ``pasar_turno`` este día nunca vuelve a ser
        elegible (cede el resto del día, incluidas sus acciones gratuitas
        pendientes). En caso contrario, es elegible si tiene PA disponibles,
        si aún no ha usado Acción A u Horas Extras hoy, si aún puede pagar
        un Pedido de Urgencia (0 PA, sin límite por ronda, sin flag de "ya
        usado" — se autolimita por Datos de Investigación disponibles), si
        aún le queda el espacio de Pliegues sin usar y puede pagar al menos su
        escalón más barato (0 PA, se paga en Monedas — ver PRECIO_PLIEGUES), o
        si le queda el espacio de Descarte sin usar y puede pagar el escalón
        más barato de *alguno* de sus dos sentidos: bajar cuesta Monedas
        (PRECIO_DESCARTE), subir cuesta Agua (COSTE_REFRESCO_AGUA), así que un
        jugador sin Monedas pero con agua sigue teniendo una visita pendiente.
        """
        if indice in self._turno_pasado:
            return False
        player = self._players[indice]
        return (
            player.puntos_accion > 0
            or not player.accion_alimentar_usada
            or not player.horas_extras_usadas
            or player.datos_investigacion >= 1
            or (
                "E" not in player.acciones_pa_usadas_hoy
                and player.monedas >= min(PRECIO_PLIEGUES.values())
            )
            or (
                "descarte" not in player.acciones_pa_usadas_hoy
                and (
                    player.monedas >= min(PRECIO_DESCARTE.values())
                    or player.reserva_agua >= min(COSTE_REFRESCO_AGUA.values())
                )
            )
        )

    def _avanzar_a_siguiente_elegible(self, desde: int, incluir_actual: bool) -> None:
        """
        Busca, a partir de la posición ``desde`` en ``self._turno_orden``, el
        siguiente jugador elegible, dando como máximo una vuelta completa.

        Si ``incluir_actual`` es True, la posición ``desde`` misma se
        considera candidata (usado al preparar la Fase II); si es False, la
        búsqueda arranca en ``desde + 1`` (usado al cerrar la visita de un
        jugador, para no re-seleccionarlo salvo que dé la vuelta completa y
        siga siendo el único elegible).

        Actualiza ``self._turno_cursor`` a la posición encontrada y deja
        ``self._fase`` en ``FASE_II``; si nadie es elegible, la ronda de
        Fase II quedó agotada y ``self._fase`` pasa a ``FASE_III``.
        """
        n = len(self._turno_orden)
        inicio = desde if incluir_actual else desde + 1
        for offset in range(n):
            candidato = (inicio + offset) % n
            if self._jugador_elegible(self._turno_orden[candidato]):
                self._turno_cursor = candidato
                self._fase = Fase.FASE_II
                return
        self._fase = Fase.FASE_III

    def terminar_turno_actual(self) -> None:
        """
        Cierra la visita del jugador activo y avanza el cursor de turno al
        siguiente jugador elegible (ver ``_avanzar_a_siguiente_elegible``).
        Si ya no queda ningún jugador elegible, la Fase II termina y la fase
        pasa a ``FASE_III``.

        Debe llamarse exactamente una vez por cada visita completada — tras
        una acción (gratuita o no) o tras un pase explícito
        (``pasar_turno``, que ya delega en este método).

        Raises:
            PhaseViolationError: Si la Fase II del día actual no está en
                curso (p. ej. se llama sin haber preparado la Fase II, o
                después de que ya terminó).
        """
        if self._fase != Fase.FASE_II:
            raise PhaseViolationError(
                "terminar_turno_actual() solo puede llamarse durante la Fase II "
                f"en curso. Fase actual: {self._fase.value!r}."
            )
        self._turno_nonce += 1
        self._avanzar_a_siguiente_elegible(desde=self._turno_cursor, incluir_actual=False)

    def pasar_turno(self, player: Player) -> None:
        """
        Pasa el turno del jugador activo: cede todos los PA restantes y
        renuncia también a cualquier acción gratuita (Acción A, Horas
        Extras) que aún no haya usado este día — a diferencia de agotar los
        PA por otras vías, un pase explícito es una renuncia total al resto
        del día, no solo a las acciones de costo en PA (ver
        ``_jugador_elegible``). Equivalente a la opción "P" de la CLI
        (``main.py:_ejecutar_turno_jugador``).

        Args:
            player: Debe ser el jugador actualmente activo
                (``self.jugador_activo``); ver esa propiedad.
        """
        player.puntos_accion = 0
        self._turno_pasado.add(self._turno_orden[self._turno_cursor])
        self.terminar_turno_actual()

    def resolver_fase_III(self) -> bool:
        """
        Resuelve la Fase III (Fermentación): avance de masas, colapsos
        automáticos y desgaste metabólico (``fase_III_fermentacion``),
        descarta la receta más antigua del Mercado Central (rotación de fin del
        día — el reabastecimiento ocurre en la Fase I del día siguiente),
        evalúa el fin de partida e incrementa el contador de días.

        Deja el motor en ``Fase.TERMINADA`` si la partida concluyó, o de
        vuelta en ``Fase.PREPARACION`` — listo para que un llamador externo
        invoque ``iniciar_dia()`` (o ``ejecutar_dia_laboratorio``) para el
        siguiente Día de Laboratorio. A propósito NO encadena
        automáticamente la Fase I del día siguiente, para no romper la
        pausa/reporte por día que usa la CLI entre días.

        Returns:
            True si la partida terminó con este día, False si el motor
            quedó listo para iniciar un nuevo día.

        Raises:
            PhaseViolationError: Si la Fase II del día actual aún no ha
                concluido (``jugador_activo`` no es ``None``).
        """
        if self._fase != Fase.FASE_III:
            raise PhaseViolationError(
                "resolver_fase_III() solo puede llamarse cuando la Fase II del "
                f"día actual concluyó. Fase actual: {self._fase.value!r}."
            )

        self.fase_III_fermentacion()

        # Rotación del Mercado: al final del día se descarta la receta más antigua
        # (la Fase I del día siguiente reabastece hasta NUM_RECIPE_SLOTS).
        descartada: Optional[Recipe] = self._market.descartar_receta_mas_antigua()
        if descartada is not None:
            self._emit(
                EventoTipo.RECETA_DESCARTADA,
                datos={
                    "receta_id": descartada.id,
                    "receta_nombre": descartada.nombre,
                },
                mensaje=f"El mercado descartó la receta más antigua: "
                        f"'{descartada.nombre}'.",
            )

        # Bolsa de Harinas: se aplica ahora la tendencia anunciada esta mañana,
        # así que los precios que quedan son los que regirán mañana. Mismo
        # reparto fin-de-día/inicio-de-día que la rotación de recetas de arriba.
        posiciones_antes = dict(self._market.posiciones_harina)
        modificador_tendencia: Optional[int] = self._market.aplicar_tendencia_pendiente()
        if modificador_tendencia is not None:
            self._emit(
                EventoTipo.TENDENCIA_MERCADO,
                datos={
                    "modificador": modificador_tendencia,
                    "posiciones_antes": {t.value: p for t, p in posiciones_antes.items()},
                    "posiciones_despues": {
                        t.value: p for t, p in self._market.posiciones_harina.items()
                    },
                },
                mensaje=(
                    f"Tendencia aplicada ({_texto_modificador(modificador_tendencia)}): "
                    "así quedan los precios de la Bolsa de Harinas para mañana."
                ),
            )

        fin: bool = self._evaluar_fin_de_juego()
        self._environment.dia_actual += 1

        self._fase = Fase.TERMINADA if fin else Fase.PREPARACION
        return fin

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
             ``zona_colapso``, se hornea automáticamente con 0 PA y la
             penalización correspondiente.
          3. **Desgaste Metabólico**: reduce la Vitalidad del cultivo base de cada
             jugador en -1 (o -2 con «Aletargamiento Invernal» activo).
             La Vitalidad nunca cae por debajo de 0; si llega a 0, el jugador entra
             en estado de Contaminación (gestionado por ``Player.ajustar_vitalidad``).
          4. **Ingresos de Panadería**: cada horneado exitoso del archivo paga
             ``PRECIO_RENTA[grado]`` Monedas a su dueño (ver ``_cobrar_renta_panaderia``).

        El orden de 3 y 4 no es indiferente aunque hoy sean independientes: la renta se
        cobra DESPUÉS del desgaste para que el informe nocturno cuente la noche en el
        mismo orden en que ocurre, y para que cualquier regla futura que ligue ingresos
        a la salud del cultivo lea una Vitalidad ya actualizada.
        """
        # Paso 1 + 2: Avance de masas y detección/resolución de colapsos.
        #             Se itera sobre todos los jugadores de forma secuencial.
        #             La simultaneidad física del juego de mesa se simula procesando
        #             todos los jugadores en la misma pasada del bucle.
        for player in self._players:
            self._avanzar_masas_jugador(player)

        # Paso 3: Desgaste metabólico al final de la Fase III (CLIMATE_LOGIC.md §4).
        self._aplicar_desgaste_metabolico()

        # Paso 4: Ingresos de Panadería — el archivo de horneados rinde Monedas.
        for player in self._players:
            self._cobrar_renta_panaderia(player)

    def _cobrar_renta_panaderia(self, player: Player) -> int:
        """
        Paga a ``player`` la renta de su archivo de horneados (CORE_MECHANICS.md §2).

        Cada registro de ``archivo_horneado_exitoso`` rinde ``PRECIO_RENTA[grado]``
        Monedas, todas las noches, mientras siga en el archivo.

        **Se deriva del archivo vivo, nunca se cachea.** No hay ``Player.renta_diaria``
        ni un campo de renta sellado en ``HorneadoRecord``, y por eso la regla «si el
        registro sale del archivo, su ingreso desaparece» se cumple sola: el Simposio
        Técnico saca un horneado con un ``pop()`` y la noche siguiente ya cobra de menos,
        sin ningún código que lo coordine. Cachear la renta sería exactamente el bug que
        esta forma evita.

        Un horneado hecho en la Fase II de HOY ya está en el archivo cuando corre esta
        Fase III, así que cobra esa misma noche — por eso tampoco hace falta saber en qué
        día se horneó cada registro.

        Args:
            player: Jugador que cobra.

        Returns:
            Monedas acreditadas (0 si el archivo está vacío).
        """
        if not player.archivo_horneado_exitoso:
            return 0

        desglose: List[Dict[str, Any]] = []
        total: int = 0
        for record in player.archivo_horneado_exitoso:
            monedas: int = PRECIO_RENTA[record.recipe.grado]
            total += monedas
            desglose.append({
                "receta_id": record.recipe.id,
                "receta_nombre": record.recipe.nombre,
                "grado": record.recipe.grado.value,
                "monedas": monedas,
            })

        player.monedas += total
        self._emit(
            EventoTipo.RENTA_PANADERIA,
            jugador_idx=self._players.index(player),
            datos={"monedas_recibidas": total, "desglose": desglose},
            mensaje=(
                f"Ingresos de panadería: {player.nombre} cobra {total} Monedas de "
                f"{len(desglose)} horneado(s) en su archivo."
            ),
        )
        return total

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

        Si tras el avance la posición ≥ ``zona_colapso[0]``, se activa
        el Colapso Estructural (horneado automático de emergencia, 0 PA).

        Args:
            player: Jugador cuyas masas activas deben avanzar.
        """
        jugador_idx: int = self._players.index(player)

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
            posicion_antes: int = slot.posicion_track
            avance: int = slot.calcular_avance(self._environment.temperatura_actual)
            slot.posicion_track += avance
            self._emit(
                EventoTipo.MASA_AVANZO,
                jugador_idx=jugador_idx,
                datos={
                    "estacion_idx": idx,
                    "receta_nombre": slot.recipe.nombre,
                    "posicion_antes": posicion_antes,
                    "posicion_despues": slot.posicion_track,
                    "avance": avance,
                },
                mensaje=f"'{slot.recipe.nombre}' avanzó {posicion_antes} → "
                        f"{slot.posicion_track} (+{avance}).",
            )

            # Evaluar gatillo de Colapso Estructural (CLIMATE_LOGIC.md §3 regla 2).
            # Contra la zona AMPLIADA del propietario: con Módulo Analítico el umbral
            # de colapso está una casilla más arriba, así que una masa que colapsaría
            # sin la mejora sobrevive con ella.
            if slot.recipe.esta_en_colapso(
                slot.posicion_track, self.ampliacion_zona_optima(player)
            ):
                self.resolver_horneado(player, idx, fue_colapso=True)

    def ampliacion_zona_optima(self, player: Player) -> int:
        """
        Casillas de ampliación de la zona óptima vigentes AHORA para ``player``.

        Fuente única: todo cálculo por zona (puntos, monedas, datos y el gatillo de
        colapso de la Fase III) pasa por aquí, de modo que la ampliación no pueda
        aplicarse en unos sitios y en otros no — que es exactamente cómo se colaría
        una masa que colapsa pese a tener el Módulo instalado.
        """
        return AMPLIACION_OPTIMA_MODULO if player.tecnologias.modulo_analitico else 0

    def _delta_desgaste(self, player: Player) -> int:
        """
        Desgaste de Vitalidad que ``player`` sufrirá en la Fase III de HOY.

        Fuente única de verdad del cálculo, compartida por
        ``_aplicar_desgaste_metabolico`` (que lo aplica de verdad) y por
        ``vitalidad_prevista``/``riesgo_colapso`` (que lo predicen para la UI),
        de modo que el aviso al jugador no pueda divergir del efecto real.

        Returns:
            0 si el jugador tiene Criopreservación (Estasis Biológica);
            si no, ``environment.desgaste_vitalidad_fase_3`` (-1, o -2 con
            Aletargamiento Invernal activo).
        """
        if player.tecnologias.criopreservacion:
            return 0
        return self._environment.desgaste_vitalidad_fase_3

    def vitalidad_prevista(self, player: Player) -> int:
        """
        Vitalidad que tendrá ``player`` tras el desgaste de esta noche.

        La carta de clima del día ya se resolvió en la Fase I y nada más en la
        Fase III toca la Vitalidad antes del desgaste, así que durante la Fase II
        esta predicción es exacta, no una estimación.
        """
        return max(0, min(6, player.vitalidad + self._delta_desgaste(player)))

    def riesgo_colapso(self, player: Player) -> bool:
        """
        True si el desgaste de esta noche llevará a ``player`` a Vitalidad 0
        por primera vez, es decir, un episodio de contaminación NUEVO
        (-3 Puntos de Maestría y bloqueo de la Acción B).

        Un jugador ya contaminado devuelve False: seguir en 0 no es un episodio
        nuevo, misma regla que aplica ``Player.ajustar_vitalidad`` y que hace
        que ``EventoTipo.CONTAMINACION`` solo se emita en la transición.
        """
        if player.en_estado_contaminacion:
            return False
        return self.vitalidad_prevista(player) == 0

    def _aplicar_desgaste_metabolico(self) -> None:
        """
        Aplica el Desgaste Metabólico al cultivo base de todos los jugadores.

        Ejecutado tras procesar el avance de todas las masas (CLIMATE_LOGIC.md §4):
          · Estándar: ``-1`` Vitalidad.
          · Aletargamiento Invernal activo: ``-2`` Vitalidad.
          · Criopreservación activa ("Estasis Biológica", GDD v0.0.2 Módulo III §5):
            el jugador ignora el desgaste por completo este día (``delta = 0``).
          · Límite suelo: la Vitalidad nunca cae por debajo de 0.
          · Consecuencia de llegar a 0: estado de Contaminación + penalización
            de -3 PM (gestionado automáticamente por ``Player.ajustar_vitalidad``).
        """
        for jugador_idx, player in enumerate(self._players):
            delta: int = self._delta_desgaste(player)
            vit_antes: int = player.vitalidad
            contaminado_antes: bool = player.en_estado_contaminacion

            player.ajustar_vitalidad(delta)

            self._emit(
                EventoTipo.DESGASTE,
                jugador_idx=jugador_idx,
                datos={"delta": delta, "vitalidad_antes": vit_antes, "vitalidad_despues": player.vitalidad},
                mensaje=f"{player.nombre} sufre desgaste metabólico: "
                        f"Vitalidad {vit_antes} → {player.vitalidad}.",
            )
            if player.en_estado_contaminacion and not contaminado_antes:
                self._emit(
                    EventoTipo.CONTAMINACION,
                    jugador_idx=jugador_idx,
                    mensaje=f"¡{player.nombre} entró en estado de Contaminación!",
                )

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

        Lógica de puntuación y venta (GDD v0.0.2 Módulo III §F — "Hornear y Vender"):
          · **Colapso**: ``puntos_base = recipe.penalizacion_colapso`` (negativo),
            ``monedas = recipe.monedas_colapso``. El bono de sabor NO se aplica
            (ni en Puntos de Maestría ni en Monedas) — la fermentación fue un fracaso.
          · **Zona óptima**: ``puntos_base = recipe.puntos_optimos``,
            ``monedas = recipe.monedas_optima``. Se acreditan Datos de Investigación
            (+ extra si centro exacto + Módulo Analítico). El bono de sabor SE aplica
            si el Cubo de Laboratorio estaba sellado: +``bono_sabor_pts`` de la receta
            y +``MONEDAS_BONO_SABOR`` (2) Monedas.
          · **Pre-fermento** (masa cruda): ``puntos_base = recipe.puntos_pre_fermento``,
            ``monedas = recipe.monedas_pre_fermento``. Sin Datos de Investigación.
            El bono de sabor SE aplica igual que en zona óptima.

        Efectos sobre el estado del jugador:
          1. El slot en ``estaciones_fermentacion`` se libera (``None``).
          2. Se recupera 1 dado de inóculo (máx 3).
          3. Los Datos de Investigación ganados se acreditan inmediatamente.
          4. Las Monedas ganadas se acreditan inmediatamente.
          5. El ``HorneadoRecord`` se añade al archivo correspondiente
             (``archivo_horneado_exitoso`` o ``archivo_colapsos``).
          6. Si el jugador alcanza 5 horneados exitosos, se activa el fin de partida.

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

        # --- Cálculo de puntos, datos y monedas ---
        ampliacion: int = self.ampliacion_zona_optima(player)
        puntos_base: int = self._calcular_puntos_zona(
            recipe, posicion, fue_colapso, ampliacion
        )
        datos_obtenidos: int = (
            0
            if fue_colapso
            else self._calcular_datos_horneado(player, recipe, posicion)
        )

        # El bono de sabor no aplica en un colapso (fermentación fallida).
        bono_sabor_aplicado: bool = slot.bono_sabor and not fue_colapso

        monedas_base: int = self._calcular_monedas_zona(
            recipe, posicion, fue_colapso, ampliacion
        )
        monedas_obtenidos: int = monedas_base + (
            MONEDAS_BONO_SABOR if bono_sabor_aplicado else 0
        )

        # --- Crear registro inmutable del horneado ---
        record = HorneadoRecord(
            recipe=recipe,
            posicion_final=posicion,
            puntos_base=puntos_base,
            bono_sabor_aplicado=bono_sabor_aplicado,
            fue_colapso=fue_colapso,
            datos_obtenidos=datos_obtenidos,
            monedas_obtenidos=monedas_obtenidos,
            ampliacion_aplicada=ampliacion,
        )

        # --- Actualizar estado del jugador ---
        player.estaciones_fermentacion[slot_index] = None  # Liberar slot
        player.dados_inoculo = min(3, player.dados_inoculo + 1)  # Recuperar dado
        player.datos_investigacion += datos_obtenidos  # Acreditar datos
        player.monedas += monedas_obtenidos  # Acreditar monedas (Hornear y Vender)

        jugador_idx: int = self._players.index(player)
        if fue_colapso:
            player.archivo_colapsos.append(record)
            self._emit(
                EventoTipo.HORNEADO,
                jugador_idx=jugador_idx,
                datos={
                    "receta_nombre": recipe.nombre,
                    "puntos_totales": record.puntos_totales,
                    "fue_colapso": True,
                    "datos_generados": datos_obtenidos,
                    "monedas_obtenidas": monedas_obtenidos,
                },
                mensaje=f"Colapso estructural: '{recipe.nombre}' se horneó de "
                        f"emergencia por {record.puntos_totales} pts y "
                        f"{monedas_obtenidos} Monedas.",
            )
        else:
            player.archivo_horneado_exitoso.append(record)
            self._emit(
                EventoTipo.HORNEADO,
                jugador_idx=jugador_idx,
                datos={
                    "receta_nombre": recipe.nombre,
                    "puntos_totales": record.puntos_totales,
                    "fue_colapso": False,
                    "datos_generados": datos_obtenidos,
                    "monedas_obtenidas": monedas_obtenidos,
                },
                mensaje=f"Horneado exitoso: '{recipe.nombre}' por "
                        f"{record.puntos_totales} pts y {monedas_obtenidos} Monedas"
                        + (f" (+{datos_obtenidos} Datos)." if datos_obtenidos else "."),
            )
            # Evaluar gatillo de fin de partida por quinta receta exitosa.
            # (PLAYER_STATE.md §3: len(archivo_horneado_exitoso) >= 5)
            if len(player.archivo_horneado_exitoso) >= 5:
                self._partida_terminada = True
                self._emit(
                    EventoTipo.FIN_DE_PARTIDA,
                    jugador_idx=jugador_idx,
                    datos={"motivo": "quinta_receta"},
                    mensaje=f"¡{player.nombre} horneó su quinta receta exitosa! "
                            "La partida termina al concluir este día.",
                )

        return record

    # ==================================================================
    # CÁLCULOS INTERNOS DE HORNEADO
    # ==================================================================

    def _calcular_puntos_zona(
        self,
        recipe: Recipe,
        posicion: int,
        fue_colapso: bool,
        ampliacion: int = 0,
    ) -> int:
        """
        Calcula los Puntos de Maestría según la zona del track de fermentación.

        Tabla de resolución:

        +-----------------------+--------------------------------------------+
        | Condición             | Puntos retornados                          |
        +=======================+============================================+
        | Colapso (forzado)     | ``recipe.penalizacion_colapso`` (negativo) |
        +-----------------------+--------------------------------------------+
        | Zona de colapso       | ``recipe.penalizacion_colapso``            |
        | (manual desde esa pos)| (hornear desde allí sigue siendo colapso)  |
        +-----------------------+--------------------------------------------+
        | Zona óptima           | ``recipe.puntos_optimos``                  |
        +-----------------------+--------------------------------------------+
        | Pre-fermento          | ``recipe.puntos_pre_fermento``             |
        +-----------------------+--------------------------------------------+

        Args:
            recipe: Receta de la masa que se está horneando.
            posicion: Posición actual en el track de fermentación.
            fue_colapso: True si es un horneado forzado por sobrefermentación.
            ampliacion: Casillas de ampliación de la zona óptima del propietario
                (``ampliacion_zona_optima``). Las zonas se leen ya ampliadas.

        Returns:
            Puntos de Maestría (entero, puede ser negativo).
        """
        if fue_colapso or recipe.esta_en_colapso(posicion, ampliacion):
            return recipe.penalizacion_colapso

        if recipe.esta_en_zona_optima(posicion, ampliacion):
            return recipe.puntos_optimos

        if recipe.esta_en_pre_fermento(posicion, ampliacion):
            return recipe.puntos_pre_fermento

        # Crecimiento: la masa todavia no es pan. La Accion F rechaza hornear aqui,
        # asi que este retorno solo se alcanza por un colapso automatico imposible
        # o por un llamador nuevo; que el caso por defecto pague CERO es deliberado.
        return 0

    def _calcular_monedas_zona(
        self,
        recipe: Recipe,
        posicion: int,
        fue_colapso: bool,
        ampliacion: int = 0,
    ) -> int:
        """
        Calcula las Monedas obtenidas al hornear y vender, según la zona del
        track de fermentación (GDD v0.0.2, Módulo III §F). Misma estructura de
        3 ramas que ``_calcular_puntos_zona``.

        Args:
            recipe: Receta de la masa que se está horneando.
            posicion: Posición actual en el track de fermentación.
            fue_colapso: True si es un horneado forzado por sobrefermentación.

        Returns:
            Monedas base (antes del Bono de Sabor).
        """
        if fue_colapso or recipe.esta_en_colapso(posicion, ampliacion):
            return recipe.monedas_colapso

        if recipe.esta_en_zona_optima(posicion, ampliacion):
            return recipe.monedas_optima

        if recipe.esta_en_pre_fermento(posicion, ampliacion):
            return recipe.monedas_pre_fermento

        # Crecimiento: la masa no es pan, no hay venta. Ver _calcular_puntos_zona.
        return 0

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
          · Zona baja o sobrefermentada: 0 datos.
          · Zona óptima: ``DATOS_BAKE_ZONA_OPTIMA`` (1 dato).
          · Con Módulo Analítico: +``DATOS_BAKE_MODULO_BONUS`` en CUALQUIER punto de
            la zona óptima, y +``DATOS_BAKE_CENTRO_EXACTO_BONUS`` más si además es el
            centro exacto. Es decir 1 / 2 / 3 datos.

        Las zonas se leen ya ampliadas por el Módulo, así que una posición que sin la
        mejora sería zona baja puede pagar datos con ella instalada.

        Args:
            player: Jugador que hornea (se verifica si tiene Módulo Analítico).
            recipe: Receta de la masa.
            posicion: Posición actual en el track.

        Returns:
            Datos de Investigación otorgados (0, 1, 2 o 3).
        """
        ampliacion: int = self.ampliacion_zona_optima(player)
        if not recipe.esta_en_zona_optima(posicion, ampliacion):
            return 0

        datos: int = DATOS_BAKE_ZONA_OPTIMA

        if player.tecnologias.modulo_analitico:
            datos += DATOS_BAKE_MODULO_BONUS
            # El centro exacto no se mueve al ampliar la zona (ver es_centro_exacto),
            # así que sigue siendo la misma casilla que imprime la carta.
            if recipe.es_centro_exacto(posicion):
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
          2. Desempate 1: mayor variedad de recetas distintas horneadas con
             éxito (``Player.recetas_distintas_horneadas``). Va por delante de
             la Vitalidad: la variedad es el objetivo que el término
             «Variedad de Recetas» pide perseguir, así que también decide
             quién gana un empate.
          3. Desempate 2: mayor Vitalidad actual del cultivo base.
          4. Desempate 3: mayor cantidad de Datos de Investigación.
          5. Si persiste empate: orden de inscripción (posición en la lista).

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
                p.recetas_distintas_horneadas,
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

        El Día 1, si se proporcionó ``orden_inicial`` al constructor (Iniciativa
        de la Carta de Patrocinio), ese orden es el que manda. A partir del Día
        2, el Investigador Jefe (determinado por Vitalidad) actúa primero y el
        resto sigue en su orden original de inscripción a la partida. Si el
        Jefe no se ha determinado aún (antes del primer día), se usa el orden
        original.

        Returns:
            Lista ordenada de jugadores para la Fase II del día actual.
        """
        if self._environment.dia_actual == 1 and self._orden_inicial_iniciativa is not None:
            return [self._players[i] for i in self._orden_inicial_iniciativa]

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
