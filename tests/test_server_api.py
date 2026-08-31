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

import random
from typing import Any, Dict

from starlette.testclient import TestClient

from models import FermentationSlot, HorneadoRecord
from server.app import crear_app


def _cliente() -> TestClient:
    return TestClient(crear_app())


def test_partida_completa_de_2_jugadores_por_http() -> None:
    # El orden de turno del Día 1 sale del reparto aleatorio de PATROCINIO_CATALOG
    # (ver bootstrap.create_game), asi que sin sembrar el RNG global esta prueba
    # era un volado: fallaba ~la mitad de las veces en el assert de
    # `jugador_en_turno_idx` de mas abajo. La semilla la vuelve determinista.
    random.seed(21)
    cliente = _cliente()

    # -- Crear sala (Alba, host) --
    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    assert r.status_code == 201, r.text
    datos = r.json()
    room_id = datos["room_id"]
    host_token = datos["host_token"]
    token_alba = datos["player_token"]
    assert datos["player_index"] == 0

    # -- Unirse (Bruno) --
    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
    assert r.status_code == 201, r.text
    token_bruno = r.json()["player_token"]
    assert r.json()["player_index"] == 1

    # -- Metadata de sala antes de empezar --
    r = cliente.get(f"/games/{room_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "lobby"
    assert len(r.json()["seats"]) == 2
    assert {a["color"] for a in r.json()["seats"]} == {"rojo", "azul"}

    # -- Bruno intenta el color ya tomado por Alba --
    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Carla", "color": "rojo"})
    assert r.status_code == 409
    assert r.json()["error"] == "color_ya_tomado"

    # -- Color fuera de la paleta --
    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Carla", "color": "fucsia"})
    assert r.status_code == 400
    assert r.json()["error"] == "color_invalido"

    # -- Iniciar (solo el host) --
    r = cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["fase_actual"] == "fase_ii"
    # El Día 1 el orden de turno NO sale del desempate por vitalidad/datos
    # (ambos jugadores parten iguales, ver PLAYER_STATE.md §2) sino de la
    # iniciativa de las cartas de Patrocinio repartidas en bootstrap.create_game.
    # Con la semilla de arriba le toca a Alba (índice 0).
    assert estado["jugador_en_turno_idx"] == 0
    # turno_orden: secuencia completa del dia, [0] = Investigador Jefe.
    assert estado["turno_orden"][0] == estado["jefe_investigador_idx"]
    assert sorted(estado["turno_orden"]) == list(range(len(estado["players"])))
    assert "mazo_clima" not in estado["environment"]  # redaccion: solo el conteo
    assert estado["environment"]["cartas_clima_restantes"] > 0
    assert "mazo_recetas" not in estado["market"]
    assert estado["players"][0]["color"] == "rojo"
    assert estado["players"][1]["color"] == "azul"
    # Prediccion de colapso: calculada en el servidor porque la formula del
    # desgaste es una regla de CLIMATE_LOGIC.md y no debe duplicarse en el
    # cliente. El Dia 1 todos parten con Vitalidad 2 (models.VITALIDAD_INICIAL),
    # asi que el desgaste estandar (-1) los deja en 1 y NADIE esta en riesgo:
    # esa es justamente la razon de ser del 2 — que «Aletargamiento Invernal»
    # deje de ser una contaminacion inevitable jueguen como jueguen.
    for datos_jugador in estado["players"]:
        assert datos_jugador["vitalidad_prevista"] == 1
        assert datos_jugador["en_riesgo_colapso"] is False
        # Nadie ha horneado todavia, asi que no hay renta de panaderia.
        assert datos_jugador["renta_diaria"] == 0
        # Marcador en vivo de horneados: presente desde el Dia 1 (en cero).
        assert datos_jugador["puntos_horneados"] == 0

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
    assert estado["turno_orden"][0] == estado["jefe_investigador_idx"]
    assert sorted(estado["turno_orden"]) == list(range(len(estado["players"])))

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
    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
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
    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    room_id = r.json()["room_id"]

    r = cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": "token-falso"})
    assert r.status_code == 403
    assert r.json()["error"] == "no_es_host"


def _sala_en_curso_de_2(cliente: TestClient) -> Dict[str, str]:
    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    datos = r.json()
    room_id, host_token, token_alba = datos["room_id"], datos["host_token"], datos["player_token"]
    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
    token_bruno = r.json()["player_token"]
    cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    return {
        "room_id": room_id,
        "host_token": host_token,
        "token_alba": token_alba,
        "token_bruno": token_bruno,
    }


def test_ultima_jornada_sigue_jugandose_por_http() -> None:
    """El contrato que lee el cliente durante la ultima jornada (ver
    GameView.vue): tras el 5º horneado, `partida_terminada` ya es True pero
    `fase_actual` sigue en "fase_ii" -- y ahi esta la distincion, porque el
    cliente pintaba el ranking (y escondia la barra de acciones) en cuanto veia
    el pestillo, dejando al resto de la mesa sin poder jugar el dia que les
    corresponde. Aqui se comprueba por HTTP que ese dia SI se puede jugar."""
    random.seed(21)
    app = crear_app()
    cliente = TestClient(app)
    s = _sala_en_curso_de_2(cliente)
    room_id = s["room_id"]

    # Alba (indice 0, le toca con esta semilla) llega al horneado numero 5.
    engine = app.state.salas.obtener(room_id).engine
    alba = engine.players[0]
    receta = alba.carpeta_proyectos[0]
    alba.archivo_horneado_exitoso = [
        HorneadoRecord(
            recipe=receta,
            posicion_final=receta.zona_optima[0],
            puntos_base=receta.puntos_optimos,
            bono_sabor_aplicado=False,
            fue_colapso=False,
            datos_obtenidos=0,
            monedas_obtenidos=0,
            ampliacion_aplicada=0,
        )
        for _ in range(4)
    ]
    alba.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta,
        dado_inoculo=1,
        posicion_track=receta.zona_optima[0],
        bono_sabor=False,
        modificador_incubadora=0,
    )

    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": s["token_alba"]},
        json={"accion": "F", "params": {"slot_index": 0}},
    )
    assert r.status_code == 200, r.text
    estado = r.json()

    # El gatillo salto, pero la partida NO ha terminado: es la ultima jornada.
    assert estado["partida_terminada"] is True
    assert estado["fase_actual"] == "fase_ii"
    assert len(estado["ranking"]) == 2  # el ranking ya es valido, pero es parcial

    # Y Bruno, que aun no habia jugado hoy, conserva su turno y puede actuar.
    # (Alba tampoco ha acabado: hornear le cerro la visita, no el dia -- le
    # quedan 1 PA y sus acciones gratuitas, y el gatillo no se los quita.)
    assert estado["jugador_en_turno_idx"] == 1
    tokens = {0: s["token_alba"], 1: s["token_bruno"]}
    jugaron = set()
    while (idx := estado["jugador_en_turno_idx"]) is not None:
        jugaron.add(idx)
        r = cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": tokens[idx]})
        assert r.status_code == 200, r.text
        estado = r.json()
    assert jugaron == {0, 1}

    # Con la Fase II agotada, la Fase III cierra el dia y ahi si termina todo.
    assert estado["fase_actual"] == "terminada"


def test_fin_anticipado_puede_cortar_la_ultima_jornada() -> None:
    """El voto unanime es la unica forma de saltarse lo que queda de la ultima
    jornada. Antes rebotaba con 410 partida_terminada, porque el motor miraba
    el pestillo del gatillo en vez de la fase."""
    random.seed(21)
    app = crear_app()
    cliente = TestClient(app)
    s = _sala_en_curso_de_2(cliente)
    room_id = s["room_id"]

    engine = app.state.salas.obtener(room_id).engine
    engine._partida_terminada = True  # gatillo natural ya disparado hoy

    r = cliente.post(f"/games/{room_id}/confirm-end", headers={"X-Player-Token": s["token_alba"]})
    assert r.status_code == 200, r.text
    assert r.json()["fase_actual"] == "fase_ii"

    r = cliente.post(f"/games/{room_id}/confirm-end", headers={"X-Player-Token": s["token_bruno"]})
    assert r.status_code == 200, r.text
    assert r.json()["fase_actual"] == "terminada"


def test_votar_fin_anticipado_requiere_partida_en_curso() -> None:
    # Con la sala aun en LOBBY (sin engine), el guard de "partida iniciada"
    # se dispara antes: sala_no_disponible, no partida_no_en_curso.
    cliente = _cliente()
    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    datos = r.json()

    r = cliente.post(
        f"/games/{datos['room_id']}/confirm-end",
        headers={"X-Player-Token": datos["player_token"]},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "sala_no_disponible"

    # partida_no_en_curso si aparece una vez que la sala YA tiene un engine
    # pero la partida no esta EN_CURSO -- p. ej. tras terminar (TERMINADA).
    s = _sala_en_curso_de_2(cliente)
    cliente.post(f"/games/{s['room_id']}/confirm-end", headers={"X-Player-Token": s["token_alba"]})
    cliente.post(f"/games/{s['room_id']}/confirm-end", headers={"X-Player-Token": s["token_bruno"]})

    r = cliente.post(f"/games/{s['room_id']}/confirm-end", headers={"X-Player-Token": s["token_alba"]})
    assert r.status_code == 409
    assert r.json()["error"] == "partida_no_en_curso"


def test_fin_anticipado_por_votacion_y_vuelta_al_lobby() -> None:
    cliente = _cliente()
    s = _sala_en_curso_de_2(cliente)
    room_id = s["room_id"]

    # -- Volver al lobby antes de que la partida termine: rechazado --
    r = cliente.post(f"/games/{room_id}/return-to-lobby", headers={"X-Player-Token": s["host_token"]})
    assert r.status_code == 409
    assert r.json()["error"] == "partida_no_terminada"

    # -- Alba confirma sola: no alcanza, la partida sigue en curso --
    r = cliente.post(f"/games/{room_id}/confirm-end", headers={"X-Player-Token": s["token_alba"]})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["fase_actual"] != "terminada"
    assert estado["votos_fin_anticipado"] == [0]

    # -- Bruno confirma tambien: ahora es unanime, la partida se fuerza a terminar --
    r = cliente.post(f"/games/{room_id}/confirm-end", headers={"X-Player-Token": s["token_bruno"]})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["fase_actual"] == "terminada"
    assert sorted(estado["votos_fin_anticipado"]) == [0, 1]
    # calcular_ranking_final() es valido "en cualquier momento" -- confirma
    # que un fin forzado a mitad de partida sigue produciendo un ranking usable.
    assert len(estado["ranking"]) == 2
    assert {r["player_idx"] for r in estado["ranking"]} == {0, 1}

    # -- Bruno (no-host) no puede reiniciar la sala --
    r = cliente.post(f"/games/{room_id}/return-to-lobby", headers={"X-Player-Token": s["token_bruno"]})
    assert r.status_code == 403
    assert r.json()["error"] == "no_es_host"

    # -- El host si puede: la sala vuelve a LOBBY, los asientos se conservan --
    r = cliente.post(f"/games/{room_id}/return-to-lobby", headers={"X-Player-Token": s["host_token"]})
    assert r.status_code == 200, r.text
    metadata = r.json()
    assert metadata["status"] == "lobby"
    assert {a["color"] for a in metadata["seats"]} == {"rojo", "azul"}

    # -- El estado del juego ya no esta disponible: la sala esta en LOBBY --
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": s["token_alba"]})
    assert r.status_code == 409
    assert r.json()["error"] == "sala_no_disponible"

    # -- El mismo grupo puede empezar una segunda partida en la misma sala --
    r = cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": s["host_token"]})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["environment"]["dia_actual"] == 1
    assert estado["votos_fin_anticipado"] == []
