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
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from bootstrap import create_game
from engine import GameEngine
from events import GameEvent
from server import persistence
from server.errors import (
    CapacidadInvalidaError,
    ColorInvalidoError,
    ColorYaTomadoError,
    NoActiveTurnError,
    NotHostError,
    PartidaNoEnCursoError,
    PartidaNoTerminadaError,
    PlayerNotInactiveError,
    RoomFullError,
    RoomNotFoundError,
    RoomNotJoinableError,
    UnknownPlayerTokenError,
)

MAX_JUGADORES = 4
"""
Techo absoluto de jugadores por sala -- el juego está documentado en todas
partes como 1-4 jugadores, y ``COLORES_DISPONIBLES`` (abajo) solo tiene 6
tonos con margen justo para este techo, no más. El creador de la sala elige
la capacidad real (``GameSession.max_jugadores``, ``1..MAX_JUGADORES``) al
crearla -- ver ``RoomManager.crear_sala``.
"""

COLORES_DISPONIBLES: List[Tuple[str, str]] = [
    ("rojo", "#e0574f"),
    ("azul", "#5b8dd9"),
    ("verde", "#4caf6e"),
    ("amarillo", "#e0c04f"),
    ("morado", "#a374d9"),
    ("cian", "#4fb8b0"),
]
"""
Paleta fija de colores de jugador, elegidos en el lobby (ver `LobbyView.vue`).
Tonos deliberadamente distintos de los colores semánticos ya usados en la UI
(`--color-acento`/`--color-bien`/`--color-mal` en `App.vue`) para que un
color de jugador nunca se confunda con un estado de "bien"/"mal"/"activo".
6 opciones para hasta `MAX_JUGADORES` = 4 asientos, dejando margen real de
elección en vez de agotar la paleta exactamente al llenar la sala.
"""

_IDS_COLORES_DISPONIBLES = frozenset(id_ for id_, _ in COLORES_DISPONIBLES)

# Alfabeto sin 0/O/1/I/L (se confunden fácilmente al compartir un código de
# sala de viva voz o por chat).
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LONGITUD_CODIGO = 6

UMBRAL_INACTIVIDAD_SEGUNDOS = 90
"""
Tiempo sin interacción (ver ``Seat.last_seen``) tras el cual cualquier
jugador sentado puede forzar el pase del turno activo
(``GameSession.forzar_pase_por_inactividad``). Más generoso que el "60s"
de referencia del plan original porque el polling de respaldo del cliente
va cada 4s y ``EventSource`` reconecta solo — 90s de silencio total es una
señal mucho más fuerte de desconexión real que de un simple parpadeo de red.
"""

# Umbrales de limpieza de salas inactivas (RoomManager.limpiar_inactivas):
# una sala en LOBBY que nadie inicia se limpia rápido; una partida EN_CURSO
# se conserva mucho más tiempo (una sesión real puede durar horas); una
# partida TERMINADA se conserva solo lo justo para ver el resultado final.
UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS = 30 * 60
UMBRAL_LIMPIEZA_EN_CURSO_SEGUNDOS = 4 * 60 * 60
UMBRAL_LIMPIEZA_TERMINADA_SEGUNDOS = 60 * 60


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
    color: str
    last_seen: float = field(default_factory=time.time)
    """Marca de tiempo de la última petición autenticada de este jugador
    (actualizada en ``GameSession.asiento_por_token``, el punto de paso
    obligado de toda ruta autenticada). Usada por ``forzar_pase_por_inactividad``
    y por ``RoomManager.limpiar_inactivas``."""


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
    max_jugadores: int = MAX_JUGADORES
    """Capacidad de esta sala en particular, elegida por el host al
    crearla (``RoomManager.crear_sala``) -- entre 1 y ``MAX_JUGADORES``.
    Cubre el chequeo de sala llena en ``RoomManager.unirse``; no gatilla
    ``iniciar`` (el host puede empezar con menos jugadores que el
    objetivo, igual que hoy) y sobrevive sin cambios a
    ``reiniciar_a_lobby`` (misma sala, mismo objetivo)."""
    status: RoomStatus = RoomStatus.LOBBY
    seats: List[Seat] = field(default_factory=list)
    engine: Optional[GameEngine] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    suscriptores: List["asyncio.Queue[GameEvent]"] = field(default_factory=list)
    creado_en: float = field(default_factory=time.time)
    votos_fin_anticipado: Set[int] = field(default_factory=set)
    """Índices de jugador que confirmaron terminar la partida antes de
    tiempo (ver ``confirmar_fin_anticipado``) -- se vacía en
    ``reiniciar_a_lobby``, nunca se retira un voto individual."""

    def __getstate__(self) -> Dict[str, Any]:
        """
        Excluye ``lock`` y ``suscriptores`` de la persistencia
        (``server/persistence.py``, Milestone 6): un ``asyncio.Lock`` o una
        cola de suscriptor SSE activos no tienen ningún sentido fuera del
        proceso/event loop que los creó — una conexión SSE de un cliente
        no sobrevive a un reinicio del servidor de todas formas.
        """
        estado = self.__dict__.copy()
        estado.pop("lock", None)
        estado.pop("suscriptores", None)
        return estado

    def __setstate__(self, estado: Dict[str, Any]) -> None:
        """Contraparte de ``__getstate__``: reconstruye un lock y una lista
        de suscriptores nuevos y vacíos al restaurar desde disco."""
        self.__dict__.update(estado)
        self.lock = asyncio.Lock()
        self.suscriptores = []

    def asiento_por_token(self, token: str) -> Seat:
        """
        Resuelve un token de jugador a su asiento, y marca el momento de
        esta interacción (``Seat.last_seen``) — todo llamador autenticado
        pasa por aquí, así que es el único punto donde hace falta
        actualizarlo.

        Raises:
            UnknownPlayerTokenError: Si ningún asiento de esta sala tiene
                ese token.
        """
        for asiento in self.seats:
            if secrets.compare_digest(asiento.token, token):
                asiento.last_seen = time.time()
                return asiento
        raise UnknownPlayerTokenError(
            f"Token de jugador desconocido para la sala {self.id!r}."
        )

    def difundir_evento(self, evento: GameEvent) -> None:
        """``EventSink`` de ``GameEngine``: reenvía el evento a cada cliente
        SSE conectado a esta sala ahora mismo."""
        for cola in self.suscriptores:
            cola.put_nowait(evento)

    def forzar_pase_por_inactividad(self) -> None:
        """
        Pasa el turno del jugador activo si lleva al menos
        ``UMBRAL_INACTIVIDAD_SEGUNDOS`` sin ninguna petición autenticada —
        pensado para que cualquier jugador sentado (no solo el host) pueda
        destrabar una partida cuando otro se desconectó a mitad de su turno,
        en vez de dejar la sala congelada indefinidamente.

        El llamador (``server/app.py``) es responsable de sostener
        ``self.lock`` mientras invoca este método, igual que para
        cualquier otra mutación del motor.

        Raises:
            NoActiveTurnError: No hay ningún turno activo que forzar.
            PlayerNotInactiveError: El jugador activo todavía no lleva
                suficiente tiempo inactivo.
        """
        if self.engine is None or self.engine.jugador_activo is None:
            raise NoActiveTurnError("No hay ningún turno activo que forzar.")

        jugador = self.engine.jugador_activo
        asiento = self.seats[self.engine.players.index(jugador)]
        inactividad = time.time() - asiento.last_seen
        if inactividad < UMBRAL_INACTIVIDAD_SEGUNDOS:
            raise PlayerNotInactiveError(
                f"'{asiento.nombre}' lleva {inactividad:.0f}s inactivo; "
                f"se requieren {UMBRAL_INACTIVIDAD_SEGUNDOS}s para forzar el pase."
            )
        self.engine.pasar_turno(jugador)

    def confirmar_fin_anticipado(self, player_index: int) -> bool:
        """
        Registra que ``player_index`` confirmó terminar la partida antes de
        tiempo (no hay forma de retirar un voto). Devuelve ``True`` si con
        este voto ya confirmaron todos los asientos -- el llamador
        (``server/app.py``) es quien entonces invoca
        ``engine.forzar_fin_de_partida()`` y ajusta ``status``, ya que
        forzar el fin de la partida es una mutación del motor, no de la
        sala en sí.

        Raises:
            PartidaNoEnCursoError: La sala no tiene una partida en curso.
        """
        if self.status != RoomStatus.EN_CURSO:
            raise PartidaNoEnCursoError(f"La sala {self.id!r} no tiene una partida en curso.")
        self.votos_fin_anticipado.add(player_index)
        return len(self.votos_fin_anticipado) >= len(self.seats)

    def reiniciar_a_lobby(self, host_token: str) -> None:
        """
        Vuelve la sala a ``LOBBY`` tras una partida terminada (natural o
        forzada), conservando ``seats``/``host_token`` -- mismos nombres,
        tokens y colores -- para que el mismo grupo pueda empezar otra
        partida sin recrear la sala. Solo el host puede hacerlo (mismo
        control que ``RoomManager.iniciar``).

        Raises:
            NotHostError: ``host_token`` no coincide con el de la sala.
            PartidaNoTerminadaError: La partida todavía no terminó.
        """
        if not secrets.compare_digest(self.host_token, host_token):
            raise NotHostError(f"Solo el host puede reiniciar la sala {self.id!r}.")
        if self.status != RoomStatus.TERMINADA:
            raise PartidaNoTerminadaError(f"La sala {self.id!r} todavía no terminó.")
        self.status = RoomStatus.LOBBY
        self.engine = None
        self.votos_fin_anticipado = set()


def _validar_color(color: str, tomados: List[str]) -> None:
    if color not in _IDS_COLORES_DISPONIBLES:
        raise ColorInvalidoError(f"Color {color!r} no es una opción válida.")
    if color in tomados:
        raise ColorYaTomadoError(f"El color {color!r} ya está en uso en esta sala.")


class RoomManager:
    """Registro en memoria de todas las salas activas del proceso."""

    def __init__(self) -> None:
        self._salas: Dict[str, GameSession] = {}

    def crear_sala(
        self, nombre_host: str, color: str, max_jugadores: int = MAX_JUGADORES
    ) -> Tuple[GameSession, Seat]:
        """
        Crea una sala nueva en estado LOBBY con el host como primer asiento.

        Raises:
            CapacidadInvalidaError: ``max_jugadores`` fuera de ``1..MAX_JUGADORES``.
            ColorInvalidoError: ``color`` no está en ``COLORES_DISPONIBLES``.
        """
        if not (1 <= max_jugadores <= MAX_JUGADORES):
            raise CapacidadInvalidaError(
                f"max_jugadores debe estar entre 1 y {MAX_JUGADORES}. Recibido: {max_jugadores}"
            )
        _validar_color(color, tomados=[])
        room_id = self._generar_codigo_unico()
        sesion = GameSession(
            id=room_id, host_token=secrets.token_urlsafe(32), max_jugadores=max_jugadores
        )
        asiento = Seat(
            player_index=0, nombre=nombre_host, token=secrets.token_urlsafe(32), color=color
        )
        sesion.seats.append(asiento)
        self._salas[room_id] = sesion
        self.guardar(sesion)
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

    def unirse(self, room_id: str, nombre: str, color: str) -> Tuple[GameSession, Seat]:
        """
        Raises:
            RoomNotFoundError: Ver ``obtener``.
            RoomNotJoinableError: La sala ya no está en LOBBY.
            RoomFullError: La sala ya tiene ``max_jugadores`` asientos.
            ColorInvalidoError: ``color`` no está en ``COLORES_DISPONIBLES``.
            ColorYaTomadoError: Otro asiento de esta sala ya tiene ese color.
        """
        sesion = self.obtener(room_id)
        if sesion.status != RoomStatus.LOBBY:
            raise RoomNotJoinableError(f"La sala {room_id!r} ya no admite nuevos jugadores.")
        if len(sesion.seats) >= sesion.max_jugadores:
            raise RoomFullError(f"La sala {room_id!r} ya tiene {sesion.max_jugadores} jugadores.")
        _validar_color(color, tomados=[a.color for a in sesion.seats])

        asiento = Seat(
            player_index=len(sesion.seats),
            nombre=nombre,
            token=secrets.token_urlsafe(32),
            color=color,
        )
        sesion.seats.append(asiento)
        self.guardar(sesion)
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
        self.guardar(sesion)
        return sesion

    def guardar(self, sesion: GameSession) -> None:
        """Persiste el estado actual de una sala en disco (ver
        ``server/persistence.py``). No lanza excepciones — un fallo de
        persistencia no debe tumbar la petición que ya mutó el estado en
        memoria correctamente."""
        persistence.guardar(sesion)

    def restaurar(self, sesion: GameSession) -> None:
        """Reinserta una sala recuperada de disco al arrancar el proceso
        (ver ``server/app.py:crear_app``)."""
        self._salas[sesion.id] = sesion

    def limpiar_inactivas(self) -> List[str]:
        """
        Elimina (de memoria y de disco) las salas sin actividad reciente.
        Pensado para correr periódicamente en segundo plano (ver
        ``server/app.py``'s lifespan) — no se llama desde ninguna ruta HTTP.

        Returns:
            Los códigos de las salas eliminadas.
        """
        ahora = time.time()
        umbrales = {
            RoomStatus.LOBBY: UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS,
            RoomStatus.EN_CURSO: UMBRAL_LIMPIEZA_EN_CURSO_SEGUNDOS,
            RoomStatus.TERMINADA: UMBRAL_LIMPIEZA_TERMINADA_SEGUNDOS,
        }
        eliminadas: List[str] = []
        for room_id, sesion in list(self._salas.items()):
            ultima_actividad = max(
                (asiento.last_seen for asiento in sesion.seats), default=sesion.creado_en
            )
            if ahora - ultima_actividad > umbrales[sesion.status]:
                eliminadas.append(room_id)
        for room_id in eliminadas:
            del self._salas[room_id]
            persistence.borrar(room_id)
        return eliminadas

    def _generar_codigo_unico(self) -> str:
        while True:
            codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LONGITUD_CODIGO))
            if codigo not in self._salas:
                return codigo
