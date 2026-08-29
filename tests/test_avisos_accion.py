"""
tests/test_avisos_accion.py -- el canal efímero de acciones de jugador
(``server/sessions.py:AvisoAccion``), que es lo que permite al cliente sonar
un efecto distinto por acción y refrescar el estado en el acto.

Es un canal aparte del log de eventos, y las dos propiedades que lo hacen
seguro son justo lo que se prueba aquí:

  · Un frame de aviso NO lleva línea ``id:``, así que el navegador no mueve
    su ``Last-Event-ID`` -- un aviso no puede descolocar el puntero de resume
    del log de eventos, que es un índice dentro de ``engine.eventos``.
  · Un aviso NO entra en ``engine.eventos``, así que un deshacer (que hace
    ``pickle.loads`` del motor entero) no puede dejar el puntero de ningún
    cliente por delante del servidor. El último test es el guardarraíl de ese
    invariante: si algún día una acción gratuita empezara a emitir un
    ``GameEvent``, ese test se pone rojo antes de que nadie lo note en vivo.

Igual que en tests/test_sse.py, el generador SSE no se consume de extremo a
extremo (el TestClient de Starlette se cuelga con un ``StreamingResponse``
genuinamente abierto): se observa la difusión enganchando una cola falsa a la
``GameSession`` viva, y el formato de frame se prueba sobre la función pura.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from starlette.testclient import TestClient

from events import EventoTipo, GameEvent
from server.app import _formatear_sse, _formatear_sse_aviso, crear_app
from server.sessions import AvisoAccion


class _ColaFalsa:
    """Sustituto de asyncio.Queue: difundir_* solo usa put_nowait()."""

    def __init__(self) -> None:
        self.recibidos: List[Any] = []

    def put_nowait(self, item: Any) -> None:
        self.recibidos.append(item)

    def acciones(self) -> List[str]:
        return [i.accion for i in self.recibidos if isinstance(i, AvisoAccion)]


def _partida_iniciada() -> Tuple[TestClient, str, Dict[str, str], Any]:
    """Sala de 2 jugadores ya empezada. Devuelve tambien la GameSession viva
    (via app.state.salas) para poder engancharle un suscriptor falso."""
    random.seed(21)
    cliente = TestClient(crear_app())

    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    d = r.json()
    room_id, host_token = d["room_id"], d["host_token"]
    tokens = {"Alba": d["player_token"]}

    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
    tokens["Bruno"] = r.json()["player_token"]

    cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    sesion = cliente.app.state.salas.obtener(room_id)  # type: ignore[attr-defined]
    return cliente, room_id, tokens, sesion


def _token_del_jugador_en_turno(cliente: TestClient, room_id: str, tokens: Dict[str, str]) -> str:
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    idx = r.json()["jugador_en_turno_idx"]
    return tokens["Alba"] if idx == 0 else tokens["Bruno"]


# ---------------------------------------------------------------------------
# Formato de frame
# ---------------------------------------------------------------------------


def test_frame_de_aviso_no_lleva_id_y_va_por_su_propio_canal() -> None:
    """La propiedad que sostiene todo el diseño: sin `id:`, el navegador no
    mueve Last-Event-ID; con `event: accion`, el frame llega a un listener
    propio y no al onmessage del log de eventos."""
    frame = _formatear_sse_aviso(AvisoAccion(accion="C", jugador_idx=1))

    assert frame.startswith("event: accion\n")
    assert "id:" not in frame
    assert '"accion": "C"' in frame
    assert '"jugador_idx": 1' in frame

    # Contraste con un evento del log, que sí numera.
    evento = GameEvent(tipo=EventoTipo.CLIMA_REVELADO, dia=1, jugador_idx=None, mensaje="x")
    assert _formatear_sse(7, evento).startswith("id: 7\n")


# ---------------------------------------------------------------------------
# Difusión
# ---------------------------------------------------------------------------


def test_difundir_accion_llega_a_todos_los_suscriptores() -> None:
    _cliente, _room_id, _tokens, sesion = _partida_iniciada()
    cola_1, cola_2 = _ColaFalsa(), _ColaFalsa()
    sesion.suscriptores.extend([cola_1, cola_2])

    sesion.difundir_accion("F", 1)

    esperado = AvisoAccion(accion="F", jugador_idx=1)
    assert cola_1.recibidos == [esperado]
    assert cola_2.recibidos == [esperado]


def test_accion_valida_difunde_un_aviso() -> None:
    cliente, room_id, tokens, sesion = _partida_iniciada()
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)

    # Simposio Técnico: descarta una receta de la carpeta por 1 Dato. Es la
    # accion con menos precondiciones de recursos del Día 1.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "simposio", "params": {"origen": "carpeta", "indice": 0}},
    )
    assert r.status_code == 200, r.text
    assert cola.acciones() == ["simposio"]


def test_accion_rechazada_no_difunde_nada() -> None:
    """Fail-fast: ActionManager valida y revienta antes de mutar, asi que una
    acción rechazada no debe sonar en ninguna pestaña."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Índice de carpeta inexistente -> InvalidActionError antes de tocar nada.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "simposio", "params": {"origen": "carpeta", "indice": 99}},
    )
    assert r.status_code >= 400
    assert cola.acciones() == []


def test_pasar_y_deshacer_tambien_difunden() -> None:
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Acción gratuita (no cierra la visita) -> deja checkpoint -> se puede deshacer.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"usar_harina": True, "tipo_harina": "Blanca"}},
    )
    assert r.status_code == 200, r.text

    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text

    r = cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text

    assert cola.acciones() == ["A", "deshacer", "pasar"]


# ---------------------------------------------------------------------------
# El invariante que obligó a que esto NO fuera un GameEvent
# ---------------------------------------------------------------------------


def test_accion_gratuita_y_deshacer_no_alteran_el_log_de_eventos() -> None:
    """Guardarraíl: los avisos no entran en engine.eventos, asi que deshacer
    (un pickle.loads del motor entero) no puede encoger el log y dejar el
    puntero `since` de un cliente por delante del servidor."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    antes = len(sesion.engine.eventos)

    cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"usar_harina": True, "tipo_harina": "Blanca"}},
    )
    assert len(sesion.engine.eventos) == antes

    cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    # `sesion.engine` es un objeto NUEVO tras restaurar el checkpoint.
    assert len(sesion.engine.eventos) == antes
