"""
server/app.py — Aplicación Starlette y Rutas HTTP
=====================================================
Backend headless de Fermentum: un proceso, un worker (ver la nota de
concurrencia más abajo), estado en memoria por sala (``server/sessions.py``).

Elegido Starlette + uvicorn sobre FastAPI/pydantic y sobre Flask:
  · La validación de reglas que importa ya vive en ``ActionManager``
    (``_require_*``, fail-fast) y el estado saliente ya serializa limpio con
    ``dataclasses.asdict`` (ver ``serialization.py``) — una capa de esquema
    pydantic sería validación paralela y redundante para lo que este
    servidor necesita.
  · Flask es WSGI: una conexión de streaming de larga duración (SSE, cuando
    llegue en la Milestone 5) ocuparía un worker completo.

Transporte: POST + polling (``GET /games/{id}/events?since=N``), no
WebSockets — el servidor empuja pocas veces por minuto, los comandos ya
obtienen códigos de estado HTTP reales, y no hace falta un esquema de
correlación de request-id como con WS. SSE llega en la Milestone 5 como
optimización de latencia pura; el polling se mantiene después como ruta de
reconexión.

**Concurrencia — restricción de despliegue**: este servidor asume un único
proceso con un único worker de uvicorn (``uvicorn.run(..., workers=1)`` o
equivalente). Con varios workers, cada uno tendría su propio
``RoomManager`` en memoria y las salas se repartirían de forma impredecible
entre procesos con estado divergente — no hay nada en este módulo que lo
impida, así que es responsabilidad de quien despliegue no usarlo así. Toda
mutación del motor ocurre de forma síncrona dentro del handler bajo el
``asyncio.Lock`` de la sala (``GameSession.lock``), sin ningún ``await``
entre validar y mutar.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Type

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from actions import ActionManager
from engine import GameEngine
from exceptions import (
    FermentumError,
    GameAlreadyOverError,
    InsufficientPlayersError,
    InvalidActionError,
    MarketSlotEmptyError,
    NotYourTurnError,
    PhaseViolationError,
    ResourceDeficitError,
    RuleViolationError,
)
from server.commands import resolver_comando
from server.errors import (
    NotHostError,
    RoomError,
    RoomFullError,
    RoomNotFoundError,
    RoomNotJoinableError,
    UnknownPlayerTokenError,
)
from server.sessions import GameSession, RoomManager, RoomStatus, Seat
from server.views import game_state_view

# ===========================================================================
# MAPEO DE ERRORES A RESPUESTAS HTTP
# ===========================================================================
# Un solo isinstance-walk cubre toda la jerarquía FermentumError/RoomError
# sin enumerar cada excepción hoja: los `_require_*` de ActionManager ya
# levantan el tipo semántico correcto (ARCHITECTURE.md §3), así que mapear
# los tipos "cubo" (ResourceDeficitError, RuleViolationError, ...) alcanza.
_MAPEO_ERRORES: List[Tuple[Type[Exception], int, str]] = [
    (NotYourTurnError, 409, "no_es_tu_turno"),
    (ResourceDeficitError, 400, "recursos_insuficientes"),
    (InvalidActionError, 400, "accion_invalida"),
    (RuleViolationError, 409, "regla_violada"),
    (PhaseViolationError, 403, "fase_invalida"),
    (GameAlreadyOverError, 410, "partida_terminada"),
    (InsufficientPlayersError, 400, "jugadores_insuficientes"),
    (MarketSlotEmptyError, 409, "slot_mercado_ocupado"),
    (FermentumError, 400, "error_de_reglas"),  # respaldo genérico
    (RoomNotFoundError, 404, "sala_no_encontrada"),
    (RoomFullError, 409, "sala_llena"),
    (RoomNotJoinableError, 409, "sala_no_disponible"),
    (NotHostError, 403, "no_es_host"),
    (UnknownPlayerTokenError, 401, "token_desconocido"),
    (RoomError, 400, "error_de_sala"),  # respaldo genérico
]


def _respuesta_error(exc: Exception) -> JSONResponse:
    for tipo, status_code, codigo in _MAPEO_ERRORES:
        if isinstance(exc, tipo):
            return JSONResponse({"error": codigo, "mensaje": str(exc)}, status_code=status_code)
    raise exc  # no reconocido: que Starlette lo trate como error 500


def _requerir_token(request: Request) -> str:
    token = request.headers.get("X-Player-Token")
    if not token:
        raise UnknownPlayerTokenError("Falta la cabecera X-Player-Token.")
    return token


async def _cuerpo_json(request: Request) -> Dict[str, Any]:
    try:
        cuerpo = await request.json()
    except json.JSONDecodeError:
        raise InvalidActionError("El cuerpo de la petición no es JSON válido.")
    if not isinstance(cuerpo, dict):
        raise InvalidActionError("El cuerpo de la petición debe ser un objeto JSON.")
    return cuerpo


def _requerir_nombre(cuerpo: Dict[str, Any]) -> str:
    nombre = str(cuerpo.get("nombre") or "").strip()
    if not nombre:
        raise InvalidActionError("Se requiere 'nombre' (no vacío) en el cuerpo.")
    return nombre


def _avanzar_fase_si_corresponde(sesion: GameSession) -> None:
    """
    Si la ronda de Fase II se agotó tras la última acción o pase, resuelve
    automáticamente la Fase III y, si la partida continúa, inicia el
    siguiente Día de Laboratorio — no hay ningún jugador al que pedirle que
    dispare estas fases automáticas explícitamente (ambas son automáticas
    también en la CLI, ver ``engine.py:resolver_fase_III``/``iniciar_dia``).

    Debe llamarse con ``sesion.lock`` ya adquirido.
    """
    engine = sesion.engine
    assert engine is not None
    if engine.jugador_activo is not None:
        return
    fin = engine.resolver_fase_III()
    if fin:
        sesion.status = RoomStatus.TERMINADA
    else:
        engine.iniciar_dia()


def _requerir_partida_iniciada(sesion: GameSession) -> GameEngine:
    if sesion.engine is None:
        raise RoomNotJoinableError(f"La sala {sesion.id!r} aún no ha comenzado.")
    return sesion.engine


def _requerir_turno_del_jugador(engine: GameEngine, asiento: Seat) -> None:
    jugador_activo = engine.jugador_activo
    if jugador_activo is None or engine.players.index(jugador_activo) != asiento.player_index:
        raise NotYourTurnError(f"No es el turno de '{asiento.nombre}'.")


def crear_app() -> Starlette:
    """Construye la aplicación Starlette con un ``RoomManager`` propio."""
    salas = RoomManager()

    async def crear_sala(request: Request) -> JSONResponse:
        try:
            cuerpo = await _cuerpo_json(request)
            nombre = _requerir_nombre(cuerpo)
            sesion, asiento = salas.crear_sala(nombre)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {
                "room_id": sesion.id,
                "host_token": sesion.host_token,
                "player_token": asiento.token,
                "player_index": asiento.player_index,
            },
            status_code=201,
        )

    async def unirse_sala(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            cuerpo = await _cuerpo_json(request)
            nombre = _requerir_nombre(cuerpo)
            _sesion, asiento = salas.unirse(room_id, nombre)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {"player_index": asiento.player_index, "player_token": asiento.token},
            status_code=201,
        )

    async def iniciar_sala(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            host_token = _requerir_token(request)
            sesion = salas.iniciar(room_id, host_token)
            async with sesion.lock:
                vista = game_state_view(sesion.engine)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def ver_sala(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            sesion = salas.obtener(room_id)
        except RoomError as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {
                "room_id": sesion.id,
                "status": sesion.status.value,
                "seats": [
                    {"player_index": a.player_index, "nombre": a.nombre} for a in sesion.seats
                ],
            }
        )

    async def obtener_estado(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            sesion.asiento_por_token(token)  # valida identidad
            engine = _requerir_partida_iniciada(sesion)
            async with sesion.lock:
                vista = game_state_view(engine)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def obtener_eventos(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)
            try:
                desde = int(request.query_params.get("since", "0"))
            except ValueError:
                raise InvalidActionError("'since' debe ser un entero.")
            async with sesion.lock:
                eventos_nuevos = engine.eventos[desde:]
                seq_actual = len(engine.eventos)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {
                "seq": seq_actual,
                "eventos": [
                    {
                        "tipo": ev.tipo.value,
                        "dia": ev.dia,
                        "jugador_idx": ev.jugador_idx,
                        "datos": ev.datos,
                        "mensaje": ev.mensaje,
                    }
                    for ev in eventos_nuevos
                ],
            }
        )

    async def enviar_accion(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            cuerpo = await _cuerpo_json(request)
            accion = cuerpo.get("accion")
            params = cuerpo.get("params") or {}
            nonce_esperado = cuerpo.get("turno_nonce")
            if not isinstance(accion, str):
                raise InvalidActionError("Se requiere 'accion' (string) en el cuerpo.")
            if not isinstance(params, dict):
                raise InvalidActionError("'params' debe ser un objeto JSON.")

            sesion = salas.obtener(room_id)
            asiento = sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)

            async with sesion.lock:
                _requerir_turno_del_jugador(engine, asiento)
                if nonce_esperado is not None and nonce_esperado != engine.turno_nonce:
                    raise NotYourTurnError(
                        "El estado de turno cambió antes de que llegara esta "
                        f"acción (turno_nonce esperado {engine.turno_nonce}, "
                        f"recibido {nonce_esperado})."
                    )
                jugador = engine.players[asiento.player_index]
                manager = ActionManager(engine)
                resolver_comando(engine, manager, jugador, accion, params)
                _avanzar_fase_si_corresponde(sesion)
                vista = game_state_view(engine)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def pasar(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            asiento = sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)

            async with sesion.lock:
                _requerir_turno_del_jugador(engine, asiento)
                jugador = engine.players[asiento.player_index]
                engine.pasar_turno(jugador)
                _avanzar_fase_si_corresponde(sesion)
                vista = game_state_view(engine)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    return Starlette(
        routes=[
            Route("/games", crear_sala, methods=["POST"]),
            Route("/games/{room_id}", ver_sala, methods=["GET"]),
            Route("/games/{room_id}/join", unirse_sala, methods=["POST"]),
            Route("/games/{room_id}/start", iniciar_sala, methods=["POST"]),
            Route("/games/{room_id}/state", obtener_estado, methods=["GET"]),
            Route("/games/{room_id}/events", obtener_eventos, methods=["GET"]),
            Route("/games/{room_id}/actions", enviar_accion, methods=["POST"]),
            Route("/games/{room_id}/pass", pasar, methods=["POST"]),
        ]
    )


app = crear_app()


if __name__ == "__main__":
    import uvicorn

    # workers=1: ver la nota de concurrencia al inicio de este módulo.
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
