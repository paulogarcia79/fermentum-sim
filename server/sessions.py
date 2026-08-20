"""
server/sessions.py — Salas y Jugadores en Memoria
=====================================================
Modelo de sala (``GameSession``) y su registro en memoria
(``RoomManager``): quién puede unirse, cuándo empieza la partida, y cómo se
traduce un token de jugador a su asiento. Un `dict[str, GameSession]` simple
es suficiente para esta milestone — un proceso, un worker (ver
``server/app.py``); si el servidor necesitara escalar horizontalmente algún
día, este es el punto donde se introduciría un almacén compartido, no antes
(``CLAUDE.md`` documenta esta limitación de despliegue).

Sin cuentas ni contraseñas: el código de sala + el token de jugador (emitido
al crear la sala o al unirse) son la única identidad. Adecuado para partidas
privadas entre conocidos, no para autenticación robusta — se documenta así
en vez de insinuar lo contrario.
"""
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from bootstrap import create_game
from engine import GameEngine
from events import GameEvent
from server.errors import (
    NotHostError,
    RoomFullError,
    RoomNotFoundError,
    RoomNotJoinableError,
    UnknownPlayerTokenError,
)

MAX_JUGADORES = 4

# Alfabeto sin 0/O/1/I/L (se confunden fácilmente al compartir un código de
# sala de viva voz o por chat).
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LONGITUD_CODIGO = 6


class RoomStatus(str, Enum):
    """Estado de una sala/partida."""

    LOBBY = "lobby"
    EN_CURSO = "en_curso"
    TERMINADA = "terminada"


@dataclass
class Seat:
    """Un asiento de jugador dentro de una sala."""

    player_index: int
    nombre: str
    token: str


@dataclass
class GameSession:
    """
    Una sala/partida en memoria.

    ``lock`` serializa toda operación que lea o mute ``engine`` para esta
    sala específica (validar → despachar → mutar → construir la vista de
    respuesta) — necesario porque múltiples jugadores pueden enviar
    peticiones concurrentes contra la misma partida.

    ``suscriptores``: colas de los clientes SSE conectados actualmente a
    ``GET /games/{id}/events/stream`` (Milestone 5). ``difundir_evento`` se
    pasa como ``event_sink`` a ``GameEngine`` (vía ``bootstrap.create_game``
    en ``RoomManager.iniciar``), así que cada evento emitido por el motor
    llega en vivo a cada suscriptor sin que nadie tenga que sondear
    ``engine.eventos``. Como toda emisión ocurre de forma síncrona dentro
    de un handler que ya sostiene ``lock`` (fase de mutación, sin ningún
    ``await`` de por medio — ver ``server/app.py``), y una ruta SSE se
    registra en ``suscriptores`` sosteniendo ese mismo ``lock``, no hay
    ninguna ventana de carrera entre "ya me suscribí" y "ya leí el
    backlog": ambas cosas ocurren atómicamente respecto a cualquier
    mutación concurrente.
    """

    id: str
    host_token: str
    status: RoomStatus = RoomStatus.LOBBY
    seats: List[Seat] = field(default_factory=list)
    engine: Optional[GameEngine] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    suscriptores: List["asyncio.Queue[GameEvent]"] = field(default_factory=list)

    def asiento_por_token(self, token: str) -> Seat:
        """
        Resuelve un token de jugador a su asiento.

        Raises:
            UnknownPlayerTokenError: Si ningún asiento de esta sala tiene
                ese token.
        """
        for asiento in self.seats:
            if secrets.compare_digest(asiento.token, token):
                return asiento
        raise UnknownPlayerTokenError(
            f"Token de jugador desconocido para la sala {self.id!r}."
        )

    def difundir_evento(self, evento: GameEvent) -> None:
        """``EventSink`` de ``GameEngine``: reenvía el evento a cada cliente
        SSE conectado a esta sala ahora mismo."""
        for cola in self.suscriptores:
            cola.put_nowait(evento)


class RoomManager:
    """Registro en memoria de todas las salas activas del proceso."""

    def __init__(self) -> None:
        self._salas: Dict[str, GameSession] = {}

    def crear_sala(self, nombre_host: str) -> Tuple[GameSession, Seat]:
        """Crea una sala nueva en estado LOBBY con el host como primer asiento."""
        room_id = self._generar_codigo_unico()
        sesion = GameSession(id=room_id, host_token=secrets.token_urlsafe(32))
        asiento = Seat(player_index=0, nombre=nombre_host, token=secrets.token_urlsafe(32))
        sesion.seats.append(asiento)
        self._salas[room_id] = sesion
        return sesion, asiento

    def obtener(self, room_id: str) -> GameSession:
        """
        Raises:
            RoomNotFoundError: Si no existe ninguna sala con ese código.
        """
        sesion = self._salas.get(room_id)
        if sesion is None:
            raise RoomNotFoundError(f"No existe ninguna sala con código {room_id!r}.")
        return sesion

    def unirse(self, room_id: str, nombre: str) -> Tuple[GameSession, Seat]:
        """
        Raises:
            RoomNotFoundError: Ver ``obtener``.
            RoomNotJoinableError: La sala ya no está en LOBBY.
            RoomFullError: La sala ya tiene ``MAX_JUGADORES`` asientos.
        """
        sesion = self.obtener(room_id)
        if sesion.status != RoomStatus.LOBBY:
            raise RoomNotJoinableError(f"La sala {room_id!r} ya no admite nuevos jugadores.")
        if len(sesion.seats) >= MAX_JUGADORES:
            raise RoomFullError(f"La sala {room_id!r} ya tiene {MAX_JUGADORES} jugadores.")

        asiento = Seat(
            player_index=len(sesion.seats),
            nombre=nombre,
            token=secrets.token_urlsafe(32),
        )
        sesion.seats.append(asiento)
        return sesion, asiento

    def iniciar(self, room_id: str, host_token: str) -> GameSession:
        """
        Construye el ``GameEngine`` (vía ``bootstrap.create_game``) a partir
        de los asientos actuales, en orden de inscripción, e inicia el Día 1.

        Raises:
            RoomNotFoundError: Ver ``obtener``.
            NotHostError: ``host_token`` no coincide con el de la sala.
            RoomNotJoinableError: La sala ya fue iniciada.
            InsufficientPlayersError: La sala no tiene ningún asiento (no
                debería poder ocurrir: ``crear_sala`` siempre agrega uno).
        """
        sesion = self.obtener(room_id)
        if not secrets.compare_digest(sesion.host_token, host_token):
            raise NotHostError(f"Solo el host puede iniciar la sala {room_id!r}.")
        if sesion.status != RoomStatus.LOBBY:
            raise RoomNotJoinableError(f"La sala {room_id!r} ya fue iniciada.")

        nombres = [asiento.nombre for asiento in sesion.seats]
        sesion.engine = create_game(nombres, event_sink=sesion.difundir_evento)
        sesion.engine.iniciar_dia()
        sesion.status = RoomStatus.EN_CURSO
        return sesion

    def _generar_codigo_unico(self) -> str:
        while True:
            codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LONGITUD_CODIGO))
            if codigo not in self._salas:
                return codigo
