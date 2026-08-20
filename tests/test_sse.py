"""
tests/test_sse.py -- prueba el mecanismo de empuje SSE (Milestone 5).

Starlette's TestClient no maneja bien un generador verdaderamente
indefinido (como el de flujo_eventos, que espera en un bucle hasta que el
cliente se desconecta): probarlo intentando leer el stream de extremo a
extremo se cuelga de forma poco fiable, sin importar si hay concurrencia de
por medio o no -- se confirmó experimentalmente antes de escribir esta
suite. En vez de eso:

  · Las rutas de error (token faltante, sala inexistente, partida no
    iniciada) se prueban con un GET normal, sin streaming -- esas rutas
    retornan un JSONResponse antes de entrar siquiera al generador, asi que
    no tienen ese problema.
  · El mecanismo real que le da su valor a esta milestone --
    GameSession.difundir_evento actuando como event_sink de GameEngine, y
    reenviando a cada suscriptor -- se prueba directamente, sin pasar por
    HTTP/ASGI en absoluto. Es la pieza nueva y no trivial; el streaming en
    sí (formato SSE, backlog, keepalive) es codigo simple ya cubierto por
    la verificacion manual contra un servidor uvicorn real (ver CLAUDE.md).
"""
from __future__ import annotations

from typing import List

from starlette.testclient import TestClient

from events import EventoTipo, GameEvent
from server.app import crear_app
from server.sessions import RoomManager


class _ColaFalsa:
    """Sustituto de asyncio.Queue para probar difundir_evento sin
    necesitar un loop de eventos activo -- solo se usa put_nowait()."""

    def __init__(self) -> None:
        self.recibidos: List[GameEvent] = []

    def put_nowait(self, evento: GameEvent) -> None:
        self.recibidos.append(evento)


def _cliente() -> TestClient:
    return TestClient(crear_app())


def test_difundir_evento_reenvia_a_todos_los_suscriptores() -> None:
    salas = RoomManager()
    sesion, _anfitrion = salas.crear_sala("Alba")
    cola_1, cola_2 = _ColaFalsa(), _ColaFalsa()
    sesion.suscriptores.extend([cola_1, cola_2])

    evento = GameEvent(tipo=EventoTipo.CLIMA_REVELADO, dia=1, jugador_idx=None, mensaje="test")
    sesion.difundir_evento(evento)

    assert cola_1.recibidos == [evento]
    assert cola_2.recibidos == [evento]


def test_iniciar_sala_conecta_el_event_sink_a_los_suscriptores() -> None:
    """La pieza central de esta milestone: iniciar una sala debe dejar el
    GameEngine emitiendo hacia GameSession.difundir_evento, para que
    cualquier suscriptor SSE ya conectado reciba los eventos de Fase I del
    Día 1 (jefe_asignado, clima_revelado, mercado_refrescado) sin sondear."""
    salas = RoomManager()
    sesion, anfitrion = salas.crear_sala("Alba")
    salas.unirse(sesion.id, "Bruno")

    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    salas.iniciar(sesion.id, sesion.host_token)

    tipos = [ev.tipo for ev in cola.recibidos]
    assert EventoTipo.JEFE_ASIGNADO in tipos
    assert EventoTipo.CLIMA_REVELADO in tipos
    assert EventoTipo.MERCADO_REFRESCADO in tipos


def test_flujo_eventos_requiere_token() -> None:
    cliente = _cliente()
    r = cliente.post("/games", json={"nombre": "Alba"})
    room_id = r.json()["room_id"]

    r = cliente.get(f"/games/{room_id}/events/stream")
    assert r.status_code == 401
    assert r.json()["error"] == "token_desconocido"


def test_flujo_eventos_sala_inexistente() -> None:
    cliente = _cliente()
    r = cliente.get("/games/ZZZZZZ/events/stream", headers={"X-Player-Token": "x"})
    assert r.status_code == 404
    assert r.json()["error"] == "sala_no_encontrada"


def test_flujo_eventos_partida_no_iniciada() -> None:
    cliente = _cliente()
    r = cliente.post("/games", json={"nombre": "Alba"})
    d = r.json()

    r = cliente.get(
        f"/games/{d['room_id']}/events/stream", headers={"X-Player-Token": d["player_token"]}
    )
    assert r.status_code == 409
    assert r.json()["error"] == "sala_no_disponible"
