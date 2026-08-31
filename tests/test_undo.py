"""
tests/test_undo.py -- deshacer la visita en curso (POST /games/{id}/undo).

La ventana de deshacer es SOLO la propia visita: el checkpoint se toma antes
de la primera accion gratuita de la visita y se descarta cuando la visita
termina (accion con costo de PA, pase, pase forzado). La restauracion es por
pickle del motor -- ver GameSession.tomar_checkpoint/restaurar_checkpoint --
y no toca el log de eventos (las acciones gratuitas no emiten ninguno).
"""
from __future__ import annotations

import random

from starlette.testclient import TestClient

from server.app import crear_app
from server.sessions import RoomManager
from server import persistence


def _partida_2p(seed: int = 21):
    """Sala de 2 jugadores iniciada por HTTP. Devuelve (cliente, room_id,
    token del jugador activo, token del otro, estado inicial)."""
    random.seed(seed)
    cliente = TestClient(crear_app())
    d = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"}).json()
    room_id, host_token, token_alba = d["room_id"], d["host_token"], d["player_token"]
    token_bruno = cliente.post(
        f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"}
    ).json()["player_token"]
    estado = cliente.post(
        f"/games/{room_id}/start", headers={"X-Player-Token": host_token}
    ).json()
    tokens = [token_alba, token_bruno]
    activo = estado["jugador_en_turno_idx"]
    return cliente, room_id, tokens[activo], tokens[1 - activo], estado


def _estado(cliente, room_id, token):
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text
    return r.json()


def _alimentar(cliente, room_id, token):
    """Accion A (gratuita): +1 vitalidad por 10% de harina Blanca."""
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"tipo_harina": "Blanca"}},
    )
    return r


def test_deshacer_restaura_el_estado_previo_a_la_visita() -> None:
    cliente, room_id, token, _, antes = _partida_2p()
    assert antes["puede_deshacer"] is False

    r = _alimentar(cliente, room_id, token)
    assert r.status_code == 200, r.text
    despues = r.json()
    idx = despues["jugador_en_turno_idx"]
    assert despues["puede_deshacer"] is True
    assert despues["players"][idx]["accion_alimentar_usada"] is True
    assert despues["players"][idx]["vitalidad"] == antes["players"][idx]["vitalidad"] + 1

    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text
    restaurado = r.json()
    # Restauracion completa: la vista entera vuelve a ser la de antes de la
    # accion (mismo dia, mismo nonce, mismos recursos, marcador de A limpio).
    assert restaurado == antes


def test_deshacer_sin_nada_hecho_es_409() -> None:
    cliente, room_id, token, _, _ = _partida_2p()
    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert r.status_code == 409
    assert r.json()["error"] == "nada_que_deshacer"


def test_deshacer_por_jugador_no_activo_es_409() -> None:
    cliente, room_id, token, token_otro, _ = _partida_2p()
    assert _alimentar(cliente, room_id, token).status_code == 200
    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token_otro})
    assert r.status_code == 409
    assert r.json()["error"] == "no_es_tu_turno"


def test_deshacer_es_ilimitado_al_mismo_punto() -> None:
    cliente, room_id, token, _, antes = _partida_2p()
    for _ in range(2):
        assert _alimentar(cliente, room_id, token).status_code == 200
        r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
        assert r.status_code == 200, r.text
        assert r.json() == antes


def test_accion_que_termina_turno_cierra_la_ventana() -> None:
    cliente, room_id, token, _, _ = _partida_2p()
    assert _alimentar(cliente, room_id, token).status_code == 200

    # Investigar Protocolo (G, 1 PA) termina la visita.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "G", "params": {"indice_mercado": 0}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["puede_deshacer"] is False

    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert r.status_code == 409  # ya no es su turno, o no hay checkpoint


def test_accion_gratuita_rechazada_no_toca_el_checkpoint() -> None:
    """Fail-fast: una A invalida (tipo de harina inexistente) no debe ni crear
    ni destruir el punto de restauracion."""
    cliente, room_id, token, _, _ = _partida_2p()

    # Rechazada de entrada por parametro invalido: NO crea checkpoint.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"tipo_harina": "Trigo"}},
    )
    assert r.status_code != 200, r.text
    assert _estado(cliente, room_id, token)["puede_deshacer"] is False


def test_restaurar_recablea_el_event_sink_y_no_toca_el_log() -> None:
    """Unitario (sin HTTP): tras restaurar, el motor clonado debe volver a
    emitir hacia GameSession.difundir_evento, y el log queda identico."""
    random.seed(99)
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo", 2)
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)

    eventos_antes = len(sesion.engine.eventos)
    sesion.tomar_checkpoint()
    # El pickle no debe dejar el sink desprendido en el motor vivo.
    assert sesion.engine._event_sink == sesion.difundir_evento

    sesion.restaurar_checkpoint()
    assert sesion.engine._event_sink == sesion.difundir_evento
    assert len(sesion.engine.eventos) == eventos_antes
    assert sesion.puede_deshacer() is False


def test_checkpoint_sobrevive_a_un_reinicio_del_proceso() -> None:
    """El checkpoint viaja en el pickle de persistencia: guardar con un
    checkpoint vivo, recargar desde disco, y deshacer sigue funcionando."""
    cliente, room_id, token, _, antes = _partida_2p(seed=55)
    assert _alimentar(cliente, room_id, token).status_code == 200

    recargadas = {s.id: s for s in persistence.cargar_todas()}
    sesion = recargadas[room_id]
    assert sesion.puede_deshacer() is True
    sesion.restaurar_checkpoint()
    jugador = sesion.engine.jugador_activo
    assert jugador is not None and jugador.accion_alimentar_usada is False
