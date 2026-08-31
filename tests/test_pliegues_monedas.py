"""
tests/test_pliegues_monedas.py -- la Accion E (Tecnica / Pliegues) despues de
salir de la economia de PA: 0 PA, precio en Monedas segun una escalera
creciente (1/3/6 Monedas por 1/2/3 espacios), encadenable dentro de la visita,
pero conservando la regla "un espacio, una visita por dia".

Cuatro invariantes que este archivo existe para fijar, porque cada una es un
sitio donde el rediseno se puede deshacer en silencio:

  1. El precio sale de PRECIO_PLIEGUES y depende del TOTAL comprado, no del
     numero de masas -- repartir 2 espacios entre dos masas cuesta lo mismo
     que ponerlos en una.
  2. El tope diario sobrevive a la perdida del coste en PA: sin el, un jugador
     con dinero podria plegar indefinidamente y `_jugador_elegible` le seguiria
     dando visitas.
  3. Atomicidad: una E rechazada no cobra Monedas NI ocupa el espacio.
  4. El sobrepliegue hacia la zona sobrefermentada es legal y no se recorta --
     es el riesgo que equilibra el escalon de 6 Monedas.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from engine import (
    Fase,
    GameEngine,
    Market,
    PRECIO_PLIEGUES,
    PRECIO_PLIEGUES_VITALIDAD,
)
from exceptions import (
    EspacioAccionYaUsadoError,
    InvalidActionError,
    MissingResourceError,
    RuleViolationError,
)
from models import Environment, FermentationSlot, Player, RECIPE_CATALOG


def _partida() -> tuple[GameEngine, ActionManager, Player]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    engine = GameEngine([p1, p2], Environment.crear_inicial(), Market.crear_inicial())
    # Se llama a la accion directamente, sin pasar por la Fase I que reparte PA.
    p1.puntos_accion = 2
    p1.monedas = 30
    return engine, ActionManager(engine), p1


def _con_masas(player: Player, cuantas: int = 2) -> list[FermentationSlot]:
    recetas = list(RECIPE_CATALOG.values())
    slots = [
        FermentationSlot(recipe=recetas[i], posicion_track=5, dado_inoculo=1)
        for i in range(cuantas)
    ]
    player.estaciones_fermentacion = slots + [None] * (3 - cuantas)
    return slots


# ---------------------------------------------------------------------------
# 1. La escalera de precios
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("espacios,precio", sorted(PRECIO_PLIEGUES.items()))
def test_cada_escalon_cobra_su_precio_y_avanza_sus_espacios(
    espacios: int, precio: int
) -> None:
    _, manager, p1 = _partida()
    slot = _con_masas(p1, 1)[0]
    pos0, monedas0 = slot.posicion_track, p1.monedas

    manager.accion_E_tecnica_pliegues(p1, reparto={0: espacios})

    assert slot.posicion_track == pos0 + espacios
    assert p1.monedas == monedas0 - precio


def test_la_escalera_es_creciente_al_margen() -> None:
    """
    Cada espacio adicional cuesta mas que el anterior. Es lo que impide que
    comprar 3 sea un descuento por volumen -- si esto se invierte, el escalon
    caro deja de ser una decision.
    """
    marginales = [
        PRECIO_PLIEGUES[n] - PRECIO_PLIEGUES.get(n - 1, 0)
        for n in sorted(PRECIO_PLIEGUES)
    ]
    assert marginales == sorted(marginales)
    assert len(set(marginales)) == len(marginales)


def test_el_precio_depende_del_total_no_del_numero_de_masas() -> None:
    _, manager, p1 = _partida()
    slots = _con_masas(p1, 2)
    p1.tecnologias.camara_b = True
    monedas0 = p1.monedas

    manager.accion_E_tecnica_pliegues(p1, reparto={0: 1, 1: 1})

    assert p1.monedas == monedas0 - PRECIO_PLIEGUES[2]
    assert slots[0].posicion_track == 6
    assert slots[1].posicion_track == 6


def test_total_fuera_de_la_escalera_se_rechaza() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)
    with pytest.raises(InvalidActionError):
        manager.accion_E_tecnica_pliegues(p1, reparto={0: max(PRECIO_PLIEGUES) + 1})


def test_reparto_ausente_o_vacio_se_rechaza() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)
    with pytest.raises(InvalidActionError):
        manager.accion_E_tecnica_pliegues(p1)
    with pytest.raises(InvalidActionError):
        manager.accion_E_tecnica_pliegues(p1, reparto={})


# ---------------------------------------------------------------------------
# 2. Camara B reparte, no aumenta
# ---------------------------------------------------------------------------


def test_repartir_entre_dos_masas_requiere_camara_b() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 2)
    assert not p1.tecnologias.camara_b

    with pytest.raises(RuleViolationError):
        manager.accion_E_tecnica_pliegues(p1, reparto={0: 1, 1: 1})


def test_camara_b_no_aumenta_el_maximo_de_espacios() -> None:
    """La mejora cambia la distribucion, nunca la cantidad comprable."""
    _, manager, p1 = _partida()
    _con_masas(p1, 2)
    p1.tecnologias.camara_b = True

    with pytest.raises(InvalidActionError):
        manager.accion_E_tecnica_pliegues(p1, reparto={0: 2, 1: 2})


def test_recuperar_vitalidad_requiere_camara_b_y_cuesta_su_precio_fijo() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)

    with pytest.raises(RuleViolationError):
        manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad")

    p1.tecnologias.camara_b = True
    p1.vitalidad = 3
    monedas0 = p1.monedas

    manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad")

    assert p1.vitalidad == 4
    assert p1.monedas == monedas0 - PRECIO_PLIEGUES_VITALIDAD


def test_recuperar_vitalidad_es_legal_sin_masas_activas() -> None:
    """
    No usa `reparto`, asi que no necesita estaciones. `disponibilidad.py`
    deshabilitaba E en este caso por error antes de este cambio.
    """
    _, manager, p1 = _partida()
    p1.estaciones_fermentacion = [None, None, None]
    p1.tecnologias.camara_b = True
    p1.vitalidad = 2

    manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad")

    assert p1.vitalidad == 3


# ---------------------------------------------------------------------------
# 3. El tope diario sobrevive a la perdida del coste en PA
# ---------------------------------------------------------------------------


def test_sin_pa_pero_con_monedas_la_accion_sigue_siendo_legal() -> None:
    _, manager, p1 = _partida()
    slot = _con_masas(p1, 1)[0]
    p1.puntos_accion = 0

    manager.accion_E_tecnica_pliegues(p1, reparto={0: 1})

    assert slot.posicion_track == 6
    assert p1.puntos_accion == 0


def test_solo_una_vez_por_dia_aunque_sobren_monedas() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)
    p1.tecnologias.camara_b = True

    manager.accion_E_tecnica_pliegues(p1, reparto={0: 1})
    assert "E" in p1.acciones_pa_usadas_hoy
    assert p1.monedas > PRECIO_PLIEGUES_VITALIDAD

    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_E_tecnica_pliegues(p1, reparto={0: 1})
    # Todas las variantes comparten el mismo espacio.
    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad")


def test_el_espacio_e_se_libera_al_preparar_el_dia_siguiente() -> None:
    engine, manager, p1 = _partida()
    _con_masas(p1, 1)
    manager.accion_E_tecnica_pliegues(p1, reparto={0: 1})

    engine.iniciar_dia()

    assert "E" not in p1.acciones_pa_usadas_hoy


def test_pliegues_no_termina_la_visita_y_encadena_con_una_accion_de_pa() -> None:
    """
    La propiedad que define al grupo de acciones gratuitas: E se resuelve sin
    ceder el turno, asi que el jugador sigue siendo el activo y puede gastar
    sus PA despues.
    """
    from server.commands import ACCIONES_QUE_TERMINAN_TURNO, resolver_comando

    assert ACCIONES_QUE_TERMINAN_TURNO["E"] is False

    engine, manager, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None
    _con_masas(activo, 1)
    activo.monedas = 30
    nonce0 = engine.turno_nonce

    resolver_comando(engine, manager, activo, "E", {"reparto": {"0": 1}})

    assert engine.jugador_activo is activo
    assert engine.turno_nonce == nonce0
    assert activo.puntos_accion == 2


def test_un_jugador_sin_pa_sigue_elegible_por_el_espacio_de_pliegues() -> None:
    """
    Sin esta clausula en `_jugador_elegible`, quien gastara sus 2 PA nunca
    alcanzaria su E del dia.
    """
    engine, _, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None

    activo.puntos_accion = 0
    activo.accion_alimentar_usada = True
    activo.horas_extras_usadas = True
    activo.datos_investigacion = 0
    activo.monedas = min(PRECIO_PLIEGUES.values())
    # El espacio de «Descarte» tambien mantiene elegible a un jugador sin PA
    # (y su escalon mas barato tambien cuesta 1 Moneda), asi que hay que
    # apagarlo para que este test aisle de verdad la clausula de Pliegues.
    activo.acciones_pa_usadas_hoy = ["descarte"]
    activo.reserva_agua = 0

    assert engine._jugador_elegible(engine._players.index(activo))

    activo.monedas = 0
    assert not engine._jugador_elegible(engine._players.index(activo))

    activo.monedas = 30
    activo.acciones_pa_usadas_hoy = ["E", "descarte"]
    assert not engine._jugador_elegible(engine._players.index(activo))


# ---------------------------------------------------------------------------
# 4. Atomicidad y sobrepliegue
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reparto": {1: 1}},  # estacion vacia
        {"reparto": {5: 1}},  # indice fuera de rango
        {"reparto": {0: 9}},  # total fuera de la escalera
        {"opcion": "volar", "reparto": {0: 1}},  # opcion inexistente
        {"opcion": "recuperar_vitalidad"},  # sin Camara B
    ],
)
def test_una_e_rechazada_no_cobra_ni_ocupa_el_espacio(kwargs: dict) -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)
    monedas0, pos0 = p1.monedas, p1.estaciones_fermentacion[0].posicion_track

    with pytest.raises(Exception):
        manager.accion_E_tecnica_pliegues(p1, **kwargs)

    assert p1.monedas == monedas0
    assert p1.acciones_pa_usadas_hoy == []
    assert p1.estaciones_fermentacion[0].posicion_track == pos0


def test_monedas_insuficientes_no_ocupan_el_espacio() -> None:
    _, manager, p1 = _partida()
    _con_masas(p1, 1)
    p1.monedas = PRECIO_PLIEGUES[max(PRECIO_PLIEGUES)] - 1

    with pytest.raises(MissingResourceError):
        manager.accion_E_tecnica_pliegues(p1, reparto={0: max(PRECIO_PLIEGUES)})

    assert p1.acciones_pa_usadas_hoy == []


def test_el_sobrepliegue_hacia_sobrefermentada_es_legal_y_no_se_recorta() -> None:
    """
    Comprar 3 espacios puede empujar la masa mas alla de su zona optima; la
    accion no lo impide ni lo recorta -- ese riesgo es el freno del escalon
    caro, y la Fase III lo cobra horneando en colapso.
    """
    _, manager, p1 = _partida()
    slot = _con_masas(p1, 1)[0]
    receta = slot.recipe
    # Colocar la masa justo debajo del techo de la zona optima.
    slot.posicion_track = receta.zona_optima[1]
    tope_optima = receta.zona_optima[1]

    manager.accion_E_tecnica_pliegues(p1, reparto={0: 3})

    assert slot.posicion_track == tope_optima + 3
    assert slot.posicion_track > tope_optima


def test_fase_iii_hornea_en_colapso_la_masa_sobreplegada() -> None:
    engine, manager, p1 = _partida()
    slot = _con_masas(p1, 1)[0]
    slot.posicion_track = slot.recipe.zona_colapso[0] - 1
    horneados0 = len(p1.archivo_horneado_exitoso)

    engine.iniciar_dia()
    p1.acciones_pa_usadas_hoy = []
    p1.monedas = 30
    manager.accion_E_tecnica_pliegues(p1, reparto={0: 3})
    assert engine.fase_actual == Fase.FASE_II

    for jugador in engine._players:
        if engine.jugador_activo is not None:
            engine.pasar_turno(engine.jugador_activo)
    engine.resolver_fase_III()

    # La masa salio de la estacion: se horneo (en colapso, sin sumar al archivo).
    assert p1.estaciones_fermentacion[0] is None
    assert len(p1.archivo_horneado_exitoso) == horneados0


# ---------------------------------------------------------------------------
# 5. Sobre HTTP: `reparto` viaja como objeto JSON, con claves de tipo string
# ---------------------------------------------------------------------------


def _sala_iniciada():
    """Sala de 2 jugadores ya empezada, con la GameSession viva a mano para
    montar el escenario (llegar a tener una masa fermentando solo con acciones
    llevaria varios dias de juego)."""
    import random

    from starlette.testclient import TestClient

    from server.app import crear_app

    random.seed(21)
    cliente = TestClient(crear_app())
    d = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"}).json()
    room_id, host = d["room_id"], d["host_token"]
    tokens = [d["player_token"]]
    tokens.append(
        cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
        .json()["player_token"]
    )
    cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host})
    sesion = cliente.app.state.salas.obtener(room_id)  # type: ignore[attr-defined]
    return cliente, room_id, tokens, sesion


def test_reparto_con_claves_string_llega_bien_por_http() -> None:
    """
    JSON no admite claves numericas, asi que el cliente manda {"0": 2} y
    `_reparto_pliegues` tiene que convertirlo a {0: 2}. Si esa coercion se
    rompe, la accion falla solo por HTTP y no en las pruebas directas.
    """
    cliente, room_id, tokens, sesion = _sala_iniciada()
    engine = sesion.engine
    idx = engine.players.index(engine.jugador_activo)
    activo = engine.players[idx]
    slot = _con_masas(activo, 1)[0]
    activo.monedas = 20
    pos0, monedas0, nonce0 = slot.posicion_track, activo.monedas, engine.turno_nonce

    r = cliente.post(
        f"/games/{room_id}/actions",
        json={"accion": "E", "params": {"opcion": "avanzar", "reparto": {"0": 2}}},
        headers={"X-Player-Token": tokens[idx]},
    )

    assert r.status_code == 200, r.json()
    assert slot.posicion_track == pos0 + 2
    assert activo.monedas == monedas0 - PRECIO_PLIEGUES[2]
    # No cierra la visita: mismo jugador activo, mismo nonce, PA intactos.
    assert engine.jugador_activo is activo
    assert engine.turno_nonce == nonce0
    assert r.json()["jugador_en_turno_idx"] == idx
    assert r.json()["players"][idx]["puntos_accion"] == activo.puntos_accion


def test_clave_de_reparto_no_numerica_se_rechaza_por_http() -> None:
    cliente, room_id, tokens, sesion = _sala_iniciada()
    engine = sesion.engine
    idx = engine.players.index(engine.jugador_activo)
    _con_masas(engine.players[idx], 1)
    engine.players[idx].monedas = 20

    r = cliente.post(
        f"/games/{room_id}/actions",
        json={"accion": "E", "params": {"opcion": "avanzar", "reparto": {"cero": 1}}},
        headers={"X-Player-Token": tokens[idx]},
    )

    assert r.status_code == 400
    assert r.json()["error"] == "accion_invalida"


def test_deshacer_devuelve_monedas_y_libera_el_espacio_por_http() -> None:
    cliente, room_id, tokens, sesion = _sala_iniciada()
    engine = sesion.engine
    idx = engine.players.index(engine.jugador_activo)
    activo = engine.players[idx]
    slot = _con_masas(activo, 1)[0]
    activo.monedas = 20
    pos0, monedas0 = slot.posicion_track, activo.monedas
    eventos0 = len(engine.eventos)

    cliente.post(
        f"/games/{room_id}/actions",
        json={"accion": "E", "params": {"opcion": "avanzar", "reparto": {"0": 3}}},
        headers={"X-Player-Token": tokens[idx]},
    )
    assert activo.monedas == monedas0 - PRECIO_PLIEGUES[3]

    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": tokens[idx]})
    assert r.status_code == 200

    activo = sesion.engine.players[idx]
    assert activo.monedas == monedas0
    assert activo.estaciones_fermentacion[0].posicion_track == pos0
    assert "E" not in activo.acciones_pa_usadas_hoy
    # La invariante que obligo a que los avisos de accion fueran un canal
    # aparte: E no emite eventos, asi que el log no encoge al deshacer.
    assert len(sesion.engine.eventos) == eventos0
