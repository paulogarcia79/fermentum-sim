"""
server/errors.py — Errores de la Capa de Salas/Sesiones
===========================================================
Errores propios de gestionar salas y jugadores por HTTP: no representan
violaciones de las reglas del juego (eso ya lo cubre ``exceptions.py`` con
``FermentumError`` y su jerarquía) sino problemas de la capa de transporte
— sala inexistente, sala llena, token desconocido. Mantenidos separados
para que ``exceptions.py`` siga siendo estrictamente el vocabulario de
reglas del juego que ``ActionManager``/``GameEngine`` usan, independiente
de que exista o no un servidor.
"""
from __future__ import annotations


class RoomError(Exception):
    """Base de los errores de la capa de salas. Permite ``except RoomError``."""


class RoomNotFoundError(RoomError):
    """Se lanza cuando el código de sala no corresponde a ninguna partida."""


class RoomFullError(RoomError):
    """Se lanza al intentar unirse a una sala que ya tiene 4 jugadores."""


class RoomNotJoinableError(RoomError):
    """
    Se lanza al intentar unirse a o iniciar una sala que no está en estado
    LOBBY (ya empezó, o ya terminó).
    """


class NotHostError(RoomError):
    """Se lanza cuando una operación solo permitida al host (p. ej. iniciar
    la partida) se solicita con un token que no es el del host."""


class UnknownPlayerTokenError(RoomError):
    """Se lanza cuando un token de jugador no corresponde a ningún asiento
    de la sala solicitada."""


class NoActiveTurnError(RoomError):
    """Se lanza al intentar forzar un pase cuando no hay ningún turno
    activo que forzar (p. ej. la Fase II ya terminó)."""


class PlayerNotInactiveError(RoomError):
    """Se lanza al intentar forzar el pase de un jugador que todavía no
    lleva suficiente tiempo inactivo (ver ``server/sessions.py``:
    ``UMBRAL_INACTIVIDAD_SEGUNDOS``)."""


class ColorInvalidoError(RoomError):
    """Se lanza cuando el color elegido al crear/unirse a una sala no está
    en ``server/sessions.py``: ``COLORES_DISPONIBLES``."""


class ColorYaTomadoError(RoomError):
    """Se lanza cuando el color elegido ya está en uso por otro asiento de
    la misma sala."""


class CapacidadInvalidaError(RoomError):
    """Se lanza cuando ``max_jugadores`` al crear una sala está fuera del
    rango ``1..MAX_JUGADORES`` (ver ``server/sessions.py``)."""


class PartidaNoEnCursoError(RoomError):
    """Se lanza al intentar votar para terminar antes de tiempo una sala
    que no tiene una partida en curso (``RoomStatus.EN_CURSO``)."""


class PartidaNoTerminadaError(RoomError):
    """Se lanza al intentar volver una sala al lobby (``reiniciar_a_lobby``)
    antes de que su partida haya terminado."""


class NadaQueDeshacerError(RoomError):
    """Se lanza al pedir un undo (``POST /games/{id}/undo``) cuando no hay
    ningún checkpoint restaurable para la visita actual del jugador: todavía
    no hizo ninguna acción esta visita, o su visita ya terminó (una acción
    con costo de PA o un pase cierran la visita y descartan el checkpoint)."""
