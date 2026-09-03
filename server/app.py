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

Transporte: POST + ``GET /games/{id}/events/stream`` (Server-Sent Events,
Milestone 5) con ``GET /games/{id}/events?since=N`` (polling) como ruta de
reconexión/respaldo permanente — no WebSockets: los comandos ya obtienen
códigos de estado HTTP reales sobre POST normal, y SSE reconecta solo con
``Last-Event-ID`` sin necesidad de ningún esquema de correlación de
request-id como haría falta con WS. Cada ``GameSession`` reenvía sus
eventos en vivo a los clientes SSE conectados vía
``GameSession.difundir_evento``, pasada como ``event_sink`` al
``GameEngine`` de esa sala (ver ``server/sessions.py``).

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

import asyncio
import contextlib
import json
from typing import Any, AsyncIterator, Dict, List, Tuple, Type, Union

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from actions import ActionManager
from engine import GameEngine
from events import GameEvent
from exceptions import (
    FermentumError,
    GameAlreadyOverError,
    InsufficientPlayersError,
    InvalidActionError,
    MarketSlotEmptyError,
    RecipeDeckEmptyError,
    NotYourTurnError,
    PhaseViolationError,
    ResourceDeficitError,
    RuleViolationError,
)
from server import persistence
from server.commands import (
    ACCIONES_QUE_REVELAN,
    ACCIONES_QUE_TERMINAN_TURNO,
    MENSAJES_MOVIMIENTO,
    describir_accion,
    resolver_comando,
)
from server.errors import (
    CapacidadInvalidaError,
    ColorInvalidoError,
    ColorYaTomadoError,
    NadaQueDeshacerError,
    NoActiveTurnError,
    NotHostError,
    PartidaNoEnCursoError,
    PartidaNoTerminadaError,
    PlayerNotInactiveError,
    RoomError,
    RoomFullError,
    RoomNotFoundError,
    RoomNotJoinableError,
    UnknownPlayerTokenError,
)
from server.sessions import (
    MAX_JUGADORES,
    AvisoAccion,
    GameSession,
    RoomManager,
    RoomStatus,
    Seat,
)
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
    (RecipeDeckEmptyError, 409, "mazo_recetas_agotado"),
    (FermentumError, 400, "error_de_reglas"),  # respaldo genérico
    (RoomNotFoundError, 404, "sala_no_encontrada"),
    (RoomFullError, 409, "sala_llena"),
    (RoomNotJoinableError, 409, "sala_no_disponible"),
    (NotHostError, 403, "no_es_host"),
    (UnknownPlayerTokenError, 401, "token_desconocido"),
    (NoActiveTurnError, 409, "sin_turno_activo"),
    (PlayerNotInactiveError, 409, "jugador_no_inactivo"),
    (ColorInvalidoError, 400, "color_invalido"),
    (ColorYaTomadoError, 409, "color_ya_tomado"),
    (CapacidadInvalidaError, 400, "capacidad_invalida"),
    (PartidaNoEnCursoError, 409, "partida_no_en_curso"),
    (PartidaNoTerminadaError, 409, "partida_no_terminada"),
    (NadaQueDeshacerError, 409, "nada_que_deshacer"),
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


def _requerir_token_sse(request: Request) -> str:
    """
    Como ``_requerir_token``, pero también acepta ``?player_token=`` —
    ``EventSource``, la API nativa del navegador para SSE, no puede enviar
    cabeceras personalizadas, así que es la única forma en que el cliente
    web puede autenticar esta ruta en particular. El resto de rutas siguen
    siendo estrictamente de cabecera, para no exponer el token en URLs
    (logs de acceso, historial) donde no hace falta.
    """
    token = request.headers.get("X-Player-Token") or request.query_params.get("player_token")
    if not token:
        raise UnknownPlayerTokenError(
            "Falta el token de jugador (cabecera X-Player-Token o parámetro player_token)."
        )
    return token


async def _cuerpo_json(request: Request) -> Dict[str, Any]:
    try:
        cuerpo = await request.json()
    except json.JSONDecodeError:
        raise InvalidActionError("El cuerpo de la petición no es JSON válido.")
    if not isinstance(cuerpo, dict):
        raise InvalidActionError("El cuerpo de la petición debe ser un objeto JSON.")
    return cuerpo


NOMBRE_LONGITUD_MINIMA = 3


def _requerir_nombre(cuerpo: Dict[str, Any]) -> str:
    nombre = str(cuerpo.get("nombre") or "").strip()
    if not nombre:
        raise InvalidActionError("Se requiere 'nombre' (no vacío) en el cuerpo.")
    if len(nombre) < NOMBRE_LONGITUD_MINIMA:
        raise InvalidActionError(
            f"'nombre' debe tener al menos {NOMBRE_LONGITUD_MINIMA} caracteres."
        )
    return nombre


def _requerir_color(cuerpo: Dict[str, Any]) -> str:
    color = str(cuerpo.get("color") or "").strip()
    if not color:
        raise InvalidActionError("Se requiere 'color' (no vacío) en el cuerpo.")
    return color


def _requerir_max_jugadores(cuerpo: Dict[str, Any]) -> int:
    """
    Chequeo de forma (si viene, ¿es un entero?) -- el rango real
    (``1..MAX_JUGADORES``) lo valida ``RoomManager.crear_sala`` (regla de
    dominio, igual que ``_validar_color``). Opcional: por defecto
    ``MAX_JUGADORES`` (4), el techo histórico antes de que este campo
    existiera -- LobbyView.vue siempre manda un valor explícito desde su
    selector nuevo, pero cualquier otro llamador de la API (tests
    incluidos) no tiene por qué que preocuparse por la capacidad.
    """
    crudo = cuerpo.get("max_jugadores", MAX_JUGADORES)
    if isinstance(crudo, bool) or not isinstance(crudo, int):
        raise InvalidActionError("'max_jugadores' debe ser un entero.")
    return crudo


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


def _evento_a_dict(ev: GameEvent) -> Dict[str, Any]:
    return {
        "tipo": ev.tipo.value,
        "dia": ev.dia,
        "jugador_idx": ev.jugador_idx,
        "datos": ev.datos,
        "mensaje": ev.mensaje,
    }


def _formatear_sse(seq: int, evento: GameEvent) -> str:
    payload = json.dumps(_evento_a_dict(evento), ensure_ascii=False)
    return f"id: {seq}\ndata: {payload}\n\n"


def _formatear_sse_aviso(aviso: AvisoAccion) -> str:
    """
    Frame efímero de acción de jugador (ver ``AvisoAccion``), en un canal
    paralelo sobre la misma conexión: lleva nombre (``event: accion``, así
    que llega a un ``addEventListener('accion', ...)`` y no al ``onmessage``
    del log de eventos) y **deliberadamente NINGUNA línea ``id:``**.

    Lo segundo es lo que sostiene todo el diseño: el navegador solo mueve su
    ``Last-Event-ID`` cuando el frame trae ``id:``, así que un aviso no puede
    descolocar el puntero de resume del log de eventos -- que es un índice
    dentro de ``engine.eventos``, donde un aviso nunca entra.
    """
    payload = json.dumps(
        {"accion": aviso.accion, "jugador_idx": aviso.jugador_idx}, ensure_ascii=False
    )
    return f"event: accion\ndata: {payload}\n\n"


INTERVALO_LIMPIEZA_SEGUNDOS = 10 * 60
"""Cada cuánto corre RoomManager.limpiar_inactivas() en segundo plano (Milestone 6)."""


def _crear_lifespan(salas: RoomManager):
    """
    Construye el context manager de ciclo de vida de la app (Milestone 6):
    al arrancar, recarga las salas persistidas en disco
    (``server/persistence.py``); mientras corre, limpia periódicamente las
    salas sin actividad reciente (``RoomManager.limpiar_inactivas``); al
    apagar, cancela esa tarea de limpieza en segundo plano con limpieza.
    """

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        for sesion in persistence.cargar_todas():
            salas.restaurar(sesion)

        async def limpiar_periodicamente() -> None:
            while True:
                await asyncio.sleep(INTERVALO_LIMPIEZA_SEGUNDOS)
                salas.limpiar_inactivas()

        tarea = asyncio.create_task(limpiar_periodicamente())
        try:
            yield
        finally:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea

    return lifespan


def crear_app() -> Starlette:
    """Construye la aplicación Starlette con un ``RoomManager`` propio."""
    salas = RoomManager()

    async def crear_sala(request: Request) -> JSONResponse:
        try:
            cuerpo = await _cuerpo_json(request)
            nombre = _requerir_nombre(cuerpo)
            color = _requerir_color(cuerpo)
            max_jugadores = _requerir_max_jugadores(cuerpo)
            sesion, asiento = salas.crear_sala(nombre, color, max_jugadores)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {
                "room_id": sesion.id,
                "host_token": sesion.host_token,
                "player_token": asiento.token,
                "player_index": asiento.player_index,
                "max_jugadores": sesion.max_jugadores,
            },
            status_code=201,
        )

    async def unirse_sala(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            cuerpo = await _cuerpo_json(request)
            nombre = _requerir_nombre(cuerpo)
            color = _requerir_color(cuerpo)
            _sesion, asiento = salas.unirse(room_id, nombre, color)
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
                vista = game_state_view(sesion)
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
                "max_jugadores": sesion.max_jugadores,
                "seats": [
                    {"player_index": a.player_index, "nombre": a.nombre, "color": a.color}
                    for a in sesion.seats
                ],
            }
        )

    async def obtener_estado(request: Request) -> JSONResponse:
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            sesion.asiento_por_token(token)  # valida identidad
            _requerir_partida_iniciada(sesion)
            async with sesion.lock:
                vista = game_state_view(sesion)
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
            {"seq": seq_actual, "eventos": [_evento_a_dict(ev) for ev in eventos_nuevos]}
        )

    async def flujo_eventos(request: Request) -> Response:
        """
        SSE (Server-Sent Events): empuja cada evento nuevo de la sala en
        cuanto se emite, en vez de que el cliente tenga que sondear
        ``GET /games/{id}/events``. El polling sigue existiendo como ruta
        de reconexión/respaldo permanente (Milestone 5 solo lo complementa,
        no lo reemplaza).

        Resume desde ``Last-Event-ID`` (enviado automáticamente por
        ``EventSource`` al reconectar) o, si no está presente, desde
        ``?since=N`` (para un primer connect, o un cliente sin soporte
        nativo de ``EventSource``, p. ej. ``curl``).
        """
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token_sse(request)
            sesion = salas.obtener(room_id)
            sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)

        id_resumen = request.headers.get("Last-Event-ID") or request.query_params.get("since")
        try:
            desde = int(id_resumen) if id_resumen else 0
        except ValueError:
            desde = 0

        cola: "asyncio.Queue[Union[GameEvent, AvisoAccion]]" = asyncio.Queue()
        # Suscribirse y leer el backlog bajo el mismo lock que protege toda
        # mutación del motor: ninguna emisión concurrente puede colarse
        # entre "ya me suscribí" y "ya leí lo que había hasta ahora" (ver
        # GameSession.difundir_evento).
        async with sesion.lock:
            sesion.suscriptores.append(cola)
            backlog = list(engine.eventos[desde:])

        async def generador() -> AsyncIterator[str]:
            seq = desde
            try:
                for evento in backlog:
                    seq += 1
                    yield _formatear_sse(seq, evento)
                while True:
                    try:
                        evento = await asyncio.wait_for(cola.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"  # evita que un proxy cierre la conexión inactiva
                        continue
                    if isinstance(evento, AvisoAccion):
                        # No incrementa `seq`: un aviso no es parte del log.
                        yield _formatear_sse_aviso(evento)
                        continue
                    seq += 1
                    yield _formatear_sse(seq, evento)
            finally:
                if cola in sesion.suscriptores:
                    sesion.suscriptores.remove(cola)

        return StreamingResponse(
            generador(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # nginx: no bufferear el stream
            },
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
                # Antes de mutar: la Acción F emite su HORNEADO durante el
                # propio despacho, y la línea "Horneó X" del registro debe
                # leerse por delante de ese evento, no detrás.
                pos_eventos = len(engine.eventos)
                # Checkpoint de deshacer. Una acción gratuita deja la visita
                # abierta, así que el estado PRE-acción se fotografía la
                # primera vez (las siguientes gratuitas de la misma visita
                # comparten ese punto de restauración). El orden importa:
                # ActionManager valida todo y revienta ANTES de mutar
                # (fail-fast), así que si la acción se rechaza hay que
                # devolver el checkpoint a como estaba -- ni descartar el de
                # una visita que no terminó, ni conservar uno recién creado
                # para una acción que nunca ocurrió.
                es_gratuita = accion in ACCIONES_QUE_TERMINAN_TURNO and not ACCIONES_QUE_TERMINAN_TURNO[accion]
                checkpoint_nuevo = es_gratuita and not sesion.puede_deshacer()
                if checkpoint_nuevo:
                    sesion.tomar_checkpoint()
                try:
                    resultado = resolver_comando(engine, manager, jugador, accion, params)
                except FermentumError:
                    if checkpoint_nuevo:
                        sesion.limpiar_checkpoint()
                    raise
                if not es_gratuita:
                    sesion.limpiar_checkpoint()  # la visita terminó: nada deshacible
                # Antes de re-tomar el checkpoint de una acción reveladora:
                # así su entrada queda DENTRO de la longitud congelada y un
                # deshacer posterior no la tacha (lo revelado no se
                # des-revela).
                sesion.registrar_accion(
                    accion,
                    asiento.player_index,
                    describir_accion(engine, jugador, accion, params, resultado),
                    pos_eventos,
                )
                # Contrato de ACCIONES_QUE_REVELAN (hoy todas False): lo
                # revelado no se des-revela -- el checkpoint se re-toma
                # DESPUÉS de resolver, y ese es el nuevo piso del deshacer.
                if ACCIONES_QUE_REVELAN.get(accion):
                    sesion.tomar_checkpoint()
                # Aquí y no antes: la acción ya se aplicó, así que una
                # rechazada por fail-fast no suena en ninguna pestaña. Y
                # antes de avanzar de fase, para que el aviso de la acción
                # llegue por delante de los eventos de Fase III que ella misma
                # disparó.
                sesion.difundir_accion(accion, asiento.player_index)
                _avanzar_fase_si_corresponde(sesion)
                salas.guardar(sesion)
                vista = game_state_view(sesion)
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
                sesion.limpiar_checkpoint()  # el pase cierra la visita
                pos_eventos = len(engine.eventos)
                engine.pasar_turno(jugador)
                sesion.registrar_accion(
                    "pasar",
                    asiento.player_index,
                    MENSAJES_MOVIMIENTO["pasar"],
                    pos_eventos,
                )
                sesion.difundir_accion("pasar", asiento.player_index)
                _avanzar_fase_si_corresponde(sesion)
                salas.guardar(sesion)
                vista = game_state_view(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def deshacer(request: Request) -> JSONResponse:
        """
        Deshace la visita en curso del jugador activo: restaura el motor al
        checkpoint tomado antes de su primera acción de esta visita. Solo
        el propio jugador activo, solo mientras su visita siga abierta
        (una acción con costo de PA o un pase la cierran), ilimitado dentro
        de esa ventana -- siempre vuelve al mismo punto. No emite eventos:
        dentro de la ventana solo caben acciones gratuitas, que tampoco los
        emiten, así que el log queda intacto y los punteros `since` de los
        clientes siguen siendo válidos.
        """
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            asiento = sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)

            async with sesion.lock:
                _requerir_turno_del_jugador(engine, asiento)
                if not sesion.puede_deshacer():
                    raise NadaQueDeshacerError(
                        "No hay nada que deshacer: todavía no hiciste ninguna "
                        "acción en esta visita."
                    )
                sesion.restaurar_checkpoint()
                # `sesion.engine` y no `engine`: el local apunta al motor
                # recién descartado. (Las longitudes coinciden por el
                # invariante, pero leer el objeto muerto es una trampa.)
                sesion.registrar_accion(
                    "deshacer",
                    asiento.player_index,
                    MENSAJES_MOVIMIENTO["deshacer"],
                    len(sesion.engine.eventos),
                )
                sesion.difundir_accion("deshacer", asiento.player_index)
                salas.guardar(sesion)
                vista = game_state_view(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def forzar_pase(request: Request) -> JSONResponse:
        """
        Cualquier jugador sentado en la sala (no hace falta ser el host, ni
        el jugador inactivo) puede pedir que se pase el turno del jugador
        activo si lleva ``UMBRAL_INACTIVIDAD_SEGUNDOS`` sin ninguna
        petición autenticada — destraba una partida cuando alguien se
        desconectó a mitad de su turno, en vez de dejarla congelada.
        """
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            # Valida que quien pide sea un jugador de la sala, y se conserva:
            # el registro nombra a quién forzó el pase.
            solicitante = sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)

            async with sesion.lock:
                pos_eventos = len(engine.eventos)
                idx_pasado = sesion.forzar_pase_por_inactividad()
                # Después (no antes): si el pase forzado se rechaza (jugador
                # aún activo), su checkpoint de visita debe sobrevivir.
                sesion.limpiar_checkpoint()
                sesion.registrar_accion(
                    "pase_forzado",
                    idx_pasado,
                    MENSAJES_MOVIMIENTO["pase_forzado"].format(nombre=solicitante.nombre),
                    pos_eventos,
                )
                # El aviso sigue siendo "pasar": es el canal de sonido, y un
                # pase forzado suena igual. Solo el registro los distingue.
                sesion.difundir_accion("pasar", idx_pasado)
                _avanzar_fase_si_corresponde(sesion)
                salas.guardar(sesion)
                vista = game_state_view(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def confirmar_fin(request: Request) -> JSONResponse:
        """
        Cualquier jugador sentado puede confirmar que quiere terminar la
        partida antes de tiempo (no hay forma de retirar un voto ya
        emitido). Una vez que confirmaron todos los asientos, la partida
        se fuerza a terminar de inmediato -- mismo estado terminal que un
        fin natural (deck agotado / 5º horneado), así que la vista de
        ranking del cliente no necesita ningún caso especial.
        """
        room_id = request.path_params["room_id"]
        try:
            token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            asiento = sesion.asiento_por_token(token)
            engine = _requerir_partida_iniciada(sesion)

            async with sesion.lock:
                todos_confirmaron = sesion.confirmar_fin_anticipado(asiento.player_index)
                if todos_confirmaron:
                    engine.forzar_fin_de_partida()
                    sesion.status = RoomStatus.TERMINADA
                salas.guardar(sesion)
                vista = game_state_view(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(vista)

    async def volver_a_lobby(request: Request) -> JSONResponse:
        """
        Solo el host puede volver la sala a LOBBY tras una partida
        terminada (natural o por voto) -- conserva los asientos (nombres,
        tokens, colores) para que el mismo grupo empiece otra partida sin
        recrear la sala. Devuelve la misma forma que ``GET /games/{id}``,
        ya que no queda ningún ``engine`` que serializar.
        """
        room_id = request.path_params["room_id"]
        try:
            host_token = _requerir_token(request)
            sesion = salas.obtener(room_id)
            async with sesion.lock:
                sesion.reiniciar_a_lobby(host_token)
                salas.guardar(sesion)
        except (FermentumError, RoomError) as exc:
            return _respuesta_error(exc)
        return JSONResponse(
            {
                "room_id": sesion.id,
                "status": sesion.status.value,
                "max_jugadores": sesion.max_jugadores,
                "seats": [
                    {"player_index": a.player_index, "nombre": a.nombre, "color": a.color}
                    for a in sesion.seats
                ],
            }
        )

    aplicacion = Starlette(
        routes=[
            Route("/games", crear_sala, methods=["POST"]),
            Route("/games/{room_id}", ver_sala, methods=["GET"]),
            Route("/games/{room_id}/join", unirse_sala, methods=["POST"]),
            Route("/games/{room_id}/start", iniciar_sala, methods=["POST"]),
            Route("/games/{room_id}/state", obtener_estado, methods=["GET"]),
            Route("/games/{room_id}/events", obtener_eventos, methods=["GET"]),
            Route("/games/{room_id}/events/stream", flujo_eventos, methods=["GET"]),
            Route("/games/{room_id}/actions", enviar_accion, methods=["POST"]),
            Route("/games/{room_id}/pass", pasar, methods=["POST"]),
            Route("/games/{room_id}/undo", deshacer, methods=["POST"]),
            Route("/games/{room_id}/force-pass", forzar_pase, methods=["POST"]),
            Route("/games/{room_id}/confirm-end", confirmar_fin, methods=["POST"]),
            Route("/games/{room_id}/return-to-lobby", volver_a_lobby, methods=["POST"]),
        ],
        lifespan=_crear_lifespan(salas),
    )
    # El RoomManager es privado del closure de arriba; exponerlo en
    # `app.state` no cambia ninguna ruta y le da a las pruebas la unica cosa
    # que HTTP no puede devolver: la GameSession viva, para poder engancharle
    # un suscriptor falso y observar lo que se difunde (ver
    # tests/test_avisos_accion.py).
    aplicacion.state.salas = salas
    return aplicacion


app = crear_app()


if __name__ == "__main__":
    import uvicorn

    # workers=1: ver la nota de concurrencia al inicio de este módulo.
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
