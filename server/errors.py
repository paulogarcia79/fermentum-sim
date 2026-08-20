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
