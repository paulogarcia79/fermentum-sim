"""
tests/test_investigacion_a_ciegas.py -- la Accion G puede robar del mazo.

La Accion G solo sabia comprar de las 4 cartas expuestas, asi que un jugador con
PA, dinero y un mercado sin nada que le sirviera no tenia forma de usar el espacio.
La «Investigacion a ciegas» abre el segundo origen: la carta SUPERIOR del mazo -- la
misma que se revelaria en el refresco de manana -- por PRECIO_RECETA_MAZO Monedas
planas, sin verla antes de pagar.

Lo que este fichero fija, porque cada pieza se rompe en silencio:

  1. El precio es plano y NO se deriva de PRECIO_RECETA[INTERMEDIA] aunque valga
     lo mismo: reajustar la tabla visible no debe reajustar la apuesta.
  2. Fail-fast REAL, y aqui hay dos cosas destructivas y no una: `pop(0)` retira
     la carta de arriba para todos, y el rebaraje del descarte consume el RNG
     global. Un intento rechazado no puede hacer ninguna de las dos.
  3. El rebaraje bajo demanda: mazo vacio + descarte lleno sigue siendo jugable,
     porque robar rebaraja primero. Solo con AMBOS vacios desaparece la opcion.
  4. La forma de la llamada: `origen` discrimina, y las combinaciones cruzadas
     (mazo con indice, mercado sin indice) son ilegales, no interpretadas.
  5. El modo mercado no cambia -- incluida la llamada posicional antigua, que es
     lo que mantiene intacto el juego dorado.
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from starlette.testclient import TestClient

import actions as actions_modulo
from actions import ActionManager
from bootstrap import create_game
from disponibilidad import acciones_disponibles
from engine import PRECIO_RECETA, PRECIO_RECETA_MAZO, GameEngine, Market
from exceptions import (
    CarpetaFullError,
    EspacioAccionYaUsadoError,
    InvalidActionError,
    MissingResourceError,
    NotEnoughActionPointsError,
    RecipeDeckEmptyError,
)
from models import Environment, Grado, Player, RECIPE_CATALOG, get_recetas_basicas
from server.app import crear_app
from server.commands import describir_accion, resolver_comando


def _partida_en_fase_ii() -> Tuple[GameEngine, ActionManager, Player]:
    """
    Partida real con la Fase II en curso: `resolver_comando` cierra la visita del
    jugador, asi que necesita un dia iniciado y al jugador activo de verdad.
    """
    random.seed(1234)
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    player = engine.jugador_activo
    assert player is not None
    player.carpeta_proyectos = []
    player.monedas = 10
    return engine, ActionManager(engine), player


def _motor() -> Tuple[GameEngine, ActionManager, Player]:
    random.seed(1234)
    engine = GameEngine(
        players=[
            Player.crear_dia_1("Alba", get_recetas_basicas()[0]),
            Player.crear_dia_1("Bruno", get_recetas_basicas()[1]),
        ],
        environment=Environment.crear_inicial(),
        market=Market.crear_inicial(),
    )
    player = engine.players[0]
    player.puntos_accion = 2
    player.carpeta_proyectos = []
    player.monedas = 10
    return engine, ActionManager(engine), player


def _disponibilidad_g(engine: GameEngine, player: Player) -> Dict[str, Any]:
    return next(a for a in acciones_disponibles(engine, player) if a["id"] == "G")


def _todas_las_cartas(engine: GameEngine, player: Player) -> Counter:
    """Todas las cartas del sistema: mesa + mazo + descarte + carpeta."""
    return Counter(
        [r for r in engine.market.recetas_visibles if r is not None]
        + engine.market.mazo_recetas
        + engine.market.descarte_recetas
        + player.carpeta_proyectos
    )


# ===========================================================================
# 1. El precio
# ===========================================================================


def test_el_precio_de_la_ciega_es_plano() -> None:
    assert PRECIO_RECETA_MAZO == 2


def test_la_ciega_cuesta_lo_mismo_salga_el_grado_que_salga() -> None:
    """
    Plano de verdad: la misma cifra con una Basica arriba y con una Avanzada.
    Si alguien derivara el precio del grado robado, esto lo caza.
    """
    for receta_id in ("pan_de_campo", "pumpernickel"):
        engine, manager, player = _motor()
        engine.market.mazo_recetas.insert(0, RECIPE_CATALOG[receta_id])
        monedas_antes = player.monedas

        manager.accion_G_investigar_protocolo(player, origen="mazo")

        assert player.carpeta_proyectos[-1] == RECIPE_CATALOG[receta_id]
        assert monedas_antes - player.monedas == PRECIO_RECETA_MAZO


# ===========================================================================
# 2. El robo: la carta de arriba, y solo ella
# ===========================================================================


def test_roba_la_carta_superior_del_mazo() -> None:
    engine, manager, player = _motor()
    mazo_antes = list(engine.market.mazo_recetas)
    visibles_antes = list(engine.market.recetas_visibles)
    descarte_antes = list(engine.market.descarte_recetas)

    manager.accion_G_investigar_protocolo(player, origen="mazo")

    # Las copias son la misma instancia congelada repetida, asi que se compara
    # por igualdad de listas y no por identidad de la carta.
    assert player.carpeta_proyectos == [mazo_antes[0]]
    assert engine.market.mazo_recetas == mazo_antes[1:]
    assert engine.market.recetas_visibles == visibles_antes
    assert engine.market.descarte_recetas == descarte_antes


def test_la_ciega_cobra_pa_y_ocupa_el_espacio() -> None:
    engine, manager, player = _motor()
    pa_antes = player.puntos_accion

    manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert player.puntos_accion == pa_antes - 1
    assert "G" in player.acciones_pa_usadas_hoy


def test_la_ciega_respeta_el_descarte_de_carpeta_llena() -> None:
    engine, manager, player = _motor()
    player.carpeta_proyectos = [
        RECIPE_CATALOG["pan_de_campo"],
        RECIPE_CATALOG["pan_de_molde"],
        RECIPE_CATALOG["pumpernickel"],
    ]
    fuera = player.carpeta_proyectos[1]

    manager.accion_G_investigar_protocolo(player, indice_descartar=1, origen="mazo")

    assert len(player.carpeta_proyectos) == 3
    assert fuera in engine.market.descarte_recetas


def test_ninguna_carta_se_pierde_ni_se_duplica() -> None:
    engine, manager, player = _motor()
    antes = _todas_las_cartas(engine, player)

    manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert _todas_las_cartas(engine, player) == antes


# ===========================================================================
# 3. Fail-fast: un intento rechazado no toca el mazo
# ===========================================================================


@pytest.mark.parametrize(
    "preparar, esperado",
    [
        (lambda p: setattr(p, "monedas", PRECIO_RECETA_MAZO - 1), MissingResourceError),
        (lambda p: setattr(p, "puntos_accion", 0), NotEnoughActionPointsError),
        (lambda p: p.acciones_pa_usadas_hoy.append("G"), EspacioAccionYaUsadoError),
        (
            lambda p: setattr(
                p,
                "carpeta_proyectos",
                [RECIPE_CATALOG["pan_de_campo"]] * 3,
            ),
            CarpetaFullError,
        ),
    ],
)
def test_un_rechazo_deja_el_mazo_intacto(preparar, esperado) -> None:
    engine, manager, player = _motor()
    preparar(player)
    mazo_antes = list(engine.market.mazo_recetas)
    descarte_antes = list(engine.market.descarte_recetas)
    monedas_antes = player.monedas

    with pytest.raises(esperado):
        manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert engine.market.mazo_recetas == mazo_antes
    assert engine.market.descarte_recetas == descarte_antes
    assert player.monedas == monedas_antes


def test_sin_monedas_no_se_rebaraja_el_descarte() -> None:
    """
    El caso que ordena las comprobaciones: con el mazo vacio, comprobar el mazo
    ANTES que las Monedas barajaria el descarte de todos por un intento que iba
    a fallar igual. El rebaraje es tan destructivo como el `pop`.
    """
    engine, manager, player = _motor()
    engine.market.descarte_recetas = list(engine.market.mazo_recetas)
    engine.market.mazo_recetas = []
    descarte_antes = list(engine.market.descarte_recetas)
    player.monedas = PRECIO_RECETA_MAZO - 1

    with pytest.raises(MissingResourceError):
        manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert engine.market.mazo_recetas == []
    assert engine.market.descarte_recetas == descarte_antes


def test_actions_no_importa_random() -> None:
    """
    El rebaraje vive en `engine.Market`, no en la accion: `actions.py` sigue sin
    conocer el RNG, que es lo que mantiene auditable donde se baraja.
    """
    fuente = Path(actions_modulo.__file__).read_text(encoding="utf-8")
    assert "import random" not in fuente


def test_la_ciega_no_emite_eventos() -> None:
    engine, manager, player = _motor()
    eventos_antes = len(engine.eventos)

    manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert len(engine.eventos) == eventos_antes


# ===========================================================================
# 4. Mazo agotado: rebarajar, y el limite real
# ===========================================================================


def test_mazo_vacio_con_descarte_rebaraja_y_roba() -> None:
    engine, manager, player = _motor()
    descarte_antes = [
        RECIPE_CATALOG["pan_de_campo"],
        RECIPE_CATALOG["pan_de_molde"],
        RECIPE_CATALOG["pumpernickel"],
    ]
    engine.market.mazo_recetas = []
    engine.market.descarte_recetas = list(descarte_antes)

    manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert engine.market.descarte_recetas == []
    assert len(engine.market.mazo_recetas) == 2
    assert Counter(engine.market.mazo_recetas + player.carpeta_proyectos) == Counter(
        descarte_antes
    )


def test_mazo_y_descarte_vacios_lo_impiden() -> None:
    engine, manager, player = _motor()
    engine.market.mazo_recetas = []
    engine.market.descarte_recetas = []
    monedas_antes = player.monedas

    with pytest.raises(RecipeDeckEmptyError):
        manager.accion_G_investigar_protocolo(player, origen="mazo")

    assert player.monedas == monedas_antes
    assert player.puntos_accion == 2
    assert "G" not in player.acciones_pa_usadas_hoy


def test_mazo_recetas_agotado_mira_tambien_el_descarte() -> None:
    engine, _, _ = _motor()
    engine.market.mazo_recetas = []
    engine.market.descarte_recetas = [RECIPE_CATALOG["pan_de_campo"]]

    assert engine.market.mazo_recetas_agotado is False

    engine.market.descarte_recetas = []
    assert engine.market.mazo_recetas_agotado is True


# ===========================================================================
# 5. La forma de la llamada
# ===========================================================================


def test_el_modo_mercado_sigue_funcionando_posicionalmente() -> None:
    """
    La llamada antigua `(player, idx)` es la que usa el bot del juego dorado:
    si cambiara de significado, el snapshot cambiaria sin que nadie lo pidiera.
    """
    engine, manager, player = _motor()
    visible = engine.market.recetas_visibles[0]
    monedas_antes = player.monedas

    manager.accion_G_investigar_protocolo(player, 0)

    assert player.carpeta_proyectos == [visible]
    assert engine.market.recetas_visibles[0] is None
    assert monedas_antes - player.monedas == PRECIO_RECETA[visible.grado]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"origen": "ciegas"},
        {"origen": ""},
        {"indice_mercado": 0, "origen": "mazo"},
        {},
    ],
    ids=["origen-desconocido", "origen-vacio", "mazo-con-indice", "mercado-sin-indice"],
)
def test_formas_ilegales_se_rechazan(kwargs) -> None:
    engine, manager, player = _motor()
    mazo_antes = list(engine.market.mazo_recetas)

    with pytest.raises(InvalidActionError):
        manager.accion_G_investigar_protocolo(player, **kwargs)

    assert engine.market.mazo_recetas == mazo_antes
    assert player.puntos_accion == 2


# ===========================================================================
# 6. disponibilidad: el mazo es el segundo suelo del espacio
# ===========================================================================


def test_G_encendida_sin_cartas_visibles_pero_con_mazo() -> None:
    engine, _, player = _motor()
    engine.market.recetas_visibles = [None] * 4
    player.monedas = PRECIO_RECETA_MAZO

    assert _disponibilidad_g(engine, player)["habilitada"] is True


def test_G_apagada_sin_cartas_visibles_y_sin_monedas_para_la_ciega() -> None:
    engine, _, player = _motor()
    engine.market.recetas_visibles = [None] * 4
    player.monedas = PRECIO_RECETA_MAZO - 1

    entrada = _disponibilidad_g(engine, player)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == f"Sin Monedas para investigar a ciegas ({PRECIO_RECETA_MAZO})"


def test_G_apagada_sin_mesa_y_sin_mazo() -> None:
    engine, _, player = _motor()
    engine.market.recetas_visibles = [None] * 4
    engine.market.mazo_recetas = []
    engine.market.descarte_recetas = []

    entrada = _disponibilidad_g(engine, player)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "No hay recetas visibles ni cartas en el mazo"


# ===========================================================================
# 7. El cable: origen por defecto, origen explicito, y el registro
# ===========================================================================


def test_el_comando_sin_origen_sigue_siendo_el_mercado() -> None:
    engine, manager, player = _partida_en_fase_ii()
    visible = engine.market.recetas_visibles[0]

    resolver_comando(engine, manager, player, "G", {"indice_mercado": 0})

    assert player.carpeta_proyectos == [visible]


def test_el_comando_con_origen_mazo_roba_del_mazo() -> None:
    engine, manager, player = _partida_en_fase_ii()
    cima = engine.market.mazo_recetas[0]

    resolver_comando(engine, manager, player, "G", {"origen": "mazo"})

    assert player.carpeta_proyectos == [cima]


def test_el_comando_rechaza_un_origen_que_no_es_texto() -> None:
    engine, manager, player = _partida_en_fase_ii()

    with pytest.raises(InvalidActionError):
        resolver_comando(engine, manager, player, "G", {"origen": 3})


def test_el_registro_distingue_la_ciega() -> None:
    engine, manager, player = _partida_en_fase_ii()
    cima = engine.market.mazo_recetas[0]

    resolver_comando(engine, manager, player, "G", {"origen": "mazo"})
    mensaje = describir_accion(engine, player, "G", {"origen": "mazo"}, None)

    assert mensaje == f"Investigó a ciegas el protocolo {cima.nombre} (robado del mazo)"


# ===========================================================================
# 8. Extremo a extremo por HTTP
# ===========================================================================


def test_la_ciega_por_http() -> None:
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

    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    idx = r.json()["jugador_en_turno_idx"]
    token = tokens["Alba"] if idx == 0 else tokens["Bruno"]
    jugador = sesion.engine.players[idx]
    jugador.monedas = 10
    jugador.carpeta_proyectos = []
    cima = sesion.engine.market.mazo_recetas[0]
    mazo_antes = len(sesion.engine.market.mazo_recetas)

    r = cliente.post(
        f"/games/{room_id}/actions",
        json={"accion": "G", "params": {"origen": "mazo"}},
        headers={"X-Player-Token": token},
    )
    assert r.status_code == 200, r.text
    estado = r.json()

    assert estado["market"]["mazo_recetas_restantes"] == mazo_antes - 1
    assert "mazo_recetas" not in estado["market"]
    assert estado["players"][idx]["carpeta_proyectos"][-1]["nombre"] == cima.nombre
    # Es una accion de PA: cierra la visita, asi que nunca hay nada que deshacer.
    assert estado["puede_deshacer"] is False
    assert estado["registro_acciones"][-1]["mensaje"] == (
        f"Investigó a ciegas el protocolo {cima.nombre} (robado del mazo)"
    )


def test_la_ciega_agotada_responde_409() -> None:
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

    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    idx = r.json()["jugador_en_turno_idx"]
    token = tokens["Alba"] if idx == 0 else tokens["Bruno"]
    sesion.engine.players[idx].monedas = 10
    sesion.engine.market.mazo_recetas = []
    sesion.engine.market.descarte_recetas = []

    r = cliente.post(
        f"/games/{room_id}/actions",
        json={"accion": "G", "params": {"origen": "mazo"}},
        headers={"X-Player-Token": token},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "mazo_recetas_agotado"
