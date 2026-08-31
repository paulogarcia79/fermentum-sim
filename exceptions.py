"""
exceptions.py — Excepciones Semánticas de Fermentum
=====================================================
Define la jerarquía de errores del motor de juego.

Estándar aplicado (ARCHITECTURE.md §3):
  · No se usan excepciones genéricas (Exception / ValueError) para violaciones
    de reglas de negocio; cada tipo de error tiene una clase semántica propia.
  · El engine y las acciones deben levantar estas excepciones en lugar de
    retornar False o códigos de error implícitos.
  · Principio Fail-Fast: todo método de acción valida precondiciones y lanza
    la excepción apropiada ANTES de modificar cualquier estado interno.
"""


class FermentumError(Exception):
    """
    Excepción base de Fermentum.
    Todas las excepciones del motor heredan de esta clase para permitir
    captura genérica del dominio: ``except FermentumError``.
    """


# ---------------------------------------------------------------------------
# Excepciones de Acciones del Jugador (Fase II)
# ---------------------------------------------------------------------------


class InvalidActionError(FermentumError):
    """
    Se lanza cuando un jugador intenta ejecutar una acción que viola las
    reglas del juego (ej. usar Horas Extras dos veces en el mismo turno,
    intentar hornear una masa que no existe, instalar dos mejoras).
    """


class ResourceDeficitError(FermentumError):
    """
    Se lanza cuando el jugador carece de los recursos necesarios para
    ejecutar una acción (ej. PA insuficientes, tokens de harina/agua
    faltantes, Datos de Investigación insuficientes para una mejora).
    """


class NotEnoughActionPointsError(ResourceDeficitError):
    """
    Subclase semántica de ResourceDeficitError.
    Se lanza específicamente cuando el jugador no tiene suficientes Puntos
    de Acción (PA) para ejecutar una acción de costo >= 1 PA.
    """


class MissingResourceError(ResourceDeficitError):
    """
    Subclase semántica de ResourceDeficitError.
    Se lanza cuando faltan tokens de harina, agua o Datos de Investigación
    para satisfacer el costo de una acción.
    """


class RuleViolationError(FermentumError):
    """
    Se lanza cuando una operación violaría una invariante de reglas del juego
    (ej. intentar colocar una masa en la Estación 03 sin Cámara B activa,
    superar el límite de 3 cartas en la carpeta de proyectos).
    """


class StationBlockedError(RuleViolationError):
    """
    Subclase semántica de RuleViolationError.
    Se lanza cuando todas las estaciones de fermentación disponibles están
    ocupadas, o se intenta usar la Estación 03 sin tener Cámara B activa
    (PLAYER_STATE.md §3: Bloqueo de Estación).
    """


class CarpetaFullError(RuleViolationError):
    """
    Subclase semántica de RuleViolationError.
    Se lanza cuando se intenta añadir una receta a la Carpeta de Proyectos
    ya llena (límite: 3 cartas) sin especificar cuál descartar
    (PLAYER_STATE.md §1: carpeta_proyectos límite = 3).
    """


class EspacioAccionYaUsadoError(RuleViolationError):
    """
    Subclase semántica de RuleViolationError.
    Se lanza cuando un jugador intenta usar un espacio de acción con costo
    de PA (Acciones B a I, Simposio Técnico) que ya usó en el día actual —
    cada espacio de acción solo puede visitarse una vez por Día de
    Laboratorio (PLAYER_STATE.md, `acciones_pa_usadas_hoy`).
    """


# ---------------------------------------------------------------------------
# Excepciones de Flujo del Motor (engine.py)
# ---------------------------------------------------------------------------


class PhaseViolationError(FermentumError):
    """
    Se lanza cuando se intenta ejecutar una operación fuera de la fase
    de juego en la que está permitida (ej. intentar ejecutar una acción
    de jugador durante la Fase I o la Fase III).
    """


class GameAlreadyOverError(FermentumError):
    """
    Se lanza cuando se intenta continuar una partida que ya ha terminado
    (ej. llamar a iniciar_dia() después de que el mazo de clima se agotó o
    un jugador horneó su quinta receta exitosa).
    """


class InsufficientPlayersError(FermentumError):
    """
    Se lanza al intentar inicializar un GameEngine sin jugadores.
    El juego requiere mínimo 1 investigador para comenzar.
    """


class MarketSlotEmptyError(FermentumError):
    """
    Se lanza cuando un jugador intenta tomar un recurso de un slot de
    mercado que ya fue reclamado por otro jugador en este mismo día.
    """


class NotYourTurnError(FermentumError):
    """
    Se lanza cuando se intenta resolver una acción o pase de turno para un
    jugador que no es el ``jugador_activo`` actual de ``GameEngine``.

    Pensada para la capa de servidor (``server/commands.py``), que debe
    verificar la identidad del jugador que envía cada comando antes de
    despacharlo a ``ActionManager`` — la CLI no la usa porque su callback
    de turno solo se invoca para el jugador correcto.
    """
