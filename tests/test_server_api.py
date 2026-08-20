"""
tests/test_server_api.py -- prueba de extremo a extremo del backend headless
(Milestone 3) puramente por HTTP, usando el TestClient de Starlette (que
recorre la pila ASGI real: routing, parseo de JSON, handlers) en vez de
llamar directamente a server/sessions.py o server/commands.py.

Esta es la prueba de "de-riesgo" que la Milestone 3 pedía como criterio de
listo -- una partida de 2 jugadores jugada enteramente por HTTP, sin ningun
frontend -- convertida en una prueba pytest permanente en vez de un script
descartable, para que quede como red de regresion del backend igual que el
resto de la suite.
"""
from __future__ import annotations

from typing import Any, Dict

from starlette.testclient import TestClient

from server.app import crear_app


def _cliente() -> TestClient:
    return TestClient(crear_app())


def test_partida_completa_de_2_jugadores_por_http() -> None:
    cliente = _cliente()

    # -- Crear sala (Alba, host) --
    r = cliente.post("/games", json={"nombre": "Alba"})
    assert r.status_code == 201, r.text
    datos = r.json()
    room_id = datos["room_id"]
    host_token = datos["host_token"]
    token_alba = datos["player_token"]
    assert datos["player_index"] == 0

    # -- Unirse (Bruno) --
    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno"})
    assert r.status_code == 201, r.text
    token_bruno = r.json()["player_token"]
    assert r.json()["player_index"] == 1

    # -- Metadata de sala antes de empezar --
    r = cliente.get(f"/games/{room_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "lobby"
    assert len(r.json()["seats"]) == 2

    # -- Iniciar (solo el host) --
    r = cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["fase_actual"] == "fase_ii"
    # Ambos jugadores parten con la misma vitalidad/datos el Día 1 (ver
    # PLAYER_STATE.md §2): el desempate de _determinar_investigador_jefe
    # recae en el primero inscrito.
    assert estado["jugador_en_turno_idx"] == 0
    assert "mazo_clima" not in estado["environment"]  # redaccion: solo el conteo
    assert estado["environment"]["cartas_clima_restantes"] > 0
    assert "mazo_recetas" not in estado["market"]

    # -- Bruno intenta actuar fuera de su turno --
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token_bruno},
        json={"accion": "G", "params": {"indice_mercado": 0}},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "no_es_tu_turno"

    # -- Alba investiga un protocolo (Accion G, termina el turno) --
    slot_receta = next(
        i for i, r in enumerate(estado["market"]["recetas_visibles"]) if r is not None
    )
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token_alba},
        json={"accion": "G", "params": {"indice_mercado": slot_receta}},
    )
    assert r.status_code == 200, r.text
    estado = r.json()
    assert len(estado["players"][0]["carpeta_proyectos"]) == 2  # la inicial + la nueva
    assert estado["jugador_en_turno_idx"] == 1  # le toca a Bruno

    # -- Bruno pasa (renuncia al resto del dia) --
    r = cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": token_bruno})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["jugador_en_turno_idx"] == 0  # Alba aun tiene PA

    # -- Alba pasa tambien: Fase II se agota, el motor avanza Fase III y el Dia 2 --
    r = cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": token_alba})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["environment"]["dia_actual"] == 2
    assert estado["fase_actual"] == "fase_ii"
    assert estado["jugador_en_turno_idx"] is not None

    # -- El registro de eventos cubre ambos dias --
    r = cliente.get(f"/games/{room_id}/events?since=0", headers={"X-Player-Token": token_alba})
    assert r.status_code == 200, r.text
    eventos: Dict[str, Any] = r.json()
    tipos = [ev["tipo"] for ev in eventos["eventos"]]
    # jefe_asignado se emite en Fase I: una vez por dia iniciado (Dia 1 y
    # Dia 2). desgaste se emite en Fase III: solo el Dia 1 completo su
    # Fase II y por lo tanto su Fase III dentro de esta prueba -- el Dia 2
    # recien empezo (nadie actuo ni paso todavia), asi que solo hay 2
    # eventos de desgaste (uno por jugador), no 4.
    assert tipos.count("jefe_asignado") == 2
    assert tipos.count("desgaste") == 2
    assert eventos["seq"] == len(eventos["eventos"])


def test_token_desconocido_es_401() -> None:
    cliente = _cliente()
    r = cliente.post("/games", json={"nombre": "Alba"})
    room_id = r.json()["room_id"]

    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": "no-existe"})
    assert r.status_code == 401
    assert r.json()["error"] == "token_desconocido"


def test_sala_inexistente_es_404() -> None:
    cliente = _cliente()
    r = cliente.get("/games/ZZZZZZ")
    assert r.status_code == 404
    assert r.json()["error"] == "sala_no_encontrada"


def test_no_host_no_puede_iniciar_la_sala() -> None:
    cliente = _cliente()
    r = cliente.post("/games", json={"nombre": "Alba"})
    room_id = r.json()["room_id"]

    r = cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": "token-falso"})
    assert r.status_code == 403
    assert r.json()["error"] == "no_es_host"
