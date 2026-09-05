"""
tests/test_alimentar_escalones.py -- la Accion A tiene dos escalones y se paga
SOLO en harina de un mismo tipo (o mezclada, en el escalon caro).

Dos cosas que este archivo existe para fijar:

  1. `models.HARINA_ALIMENTAR = {1: 10, 2: 30}`: una sola accion al dia, y en
     ella el jugador elige +1 (10%, de UN tipo) o +2 (30%, de un tipo o
     mezclados). Los puntos se DERIVAN de la suma del reparto -- no hay un
     `pasos` aparte -- asi que una suma que no es escalon (20) se rechaza.
     Elegir +1 renuncia al +2 por ese dia: la bandera `accion_alimentar_usada`
     sigue siendo un bool, sin cambio de forma persistida.
  2. La casilla no miente. `disponibilidad.py` encendia la Accion A con
     `harina_total >= 10 or reserva_agua >= 2`: la mitad de agua era un resto
     de cuando la accion tambien refrescaba con agua, y la suma entre tipos
     dejaba pasar 5% + 5%, que `accion_A_alimentar` rechaza. Ahora
     `Player.puede_alimentar` (>= 10% de un mismo tipo) es lo que consultan la
     disponibilidad, `engine._jugador_elegible` y la propia accion.

La accion sigue sin emitir ningun GameEvent: es de 0 PA, o sea que ocurre
DENTRO de la ventana de deshacer, y un evento suyo haria encoger
`engine.eventos` al restaurar (el invariante de tests/test_avisos_accion.py).
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from disponibilidad import acciones_disponibles
from engine import GameEngine, Market
from exceptions import InvalidActionError, MissingResourceError
from models import Environment, HARINA_ALIMENTAR, Player, RECIPE_CATALOG
from server.commands import describir_accion, resolver_comando


def _partida() -> tuple[GameEngine, ActionManager, Player]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    engine = GameEngine([p1, p2], Environment.crear_inicial(), Market.crear_inicial())
    p1.reserva_harina = {"Blanca": 40, "Centeno": 20, "Integral": 0}
    p1.reserva_agua = 5
    p1.vitalidad = 2
    p1.accion_alimentar_usada = False
    return engine, ActionManager(engine), p1


def _disponible(engine: GameEngine, player: Player) -> dict:
    return next(a for a in acciones_disponibles(engine, player) if a["id"] == "A")


# ===========================================================================
# La escalera
# ===========================================================================

def test_la_escalera_es_la_documentada() -> None:
    assert HARINA_ALIMENTAR == {1: 10, 2: 30}


def test_un_token_de_un_tipo_da_mas_uno() -> None:
    _, manager, p1 = _partida()
    puntos = manager.accion_A_alimentar(p1, harina={"Blanca": 10})
    assert puntos == 1
    assert p1.vitalidad == 3
    assert p1.reserva_harina == {"Blanca": 30, "Centeno": 20, "Integral": 0}
    assert p1.accion_alimentar_usada is True


def test_tres_tokens_de_un_tipo_dan_mas_dos() -> None:
    _, manager, p1 = _partida()
    puntos = manager.accion_A_alimentar(p1, harina={"Blanca": 30})
    assert puntos == 2
    assert p1.vitalidad == 4
    assert p1.reserva_harina["Blanca"] == 10


def test_tres_tokens_mezclados_dan_mas_dos_y_cobran_cada_tipo() -> None:
    _, manager, p1 = _partida()
    puntos = manager.accion_A_alimentar(p1, harina={"Blanca": 20, "Centeno": 10})
    assert puntos == 2
    assert p1.vitalidad == 4
    assert p1.reserva_harina == {"Blanca": 20, "Centeno": 10, "Integral": 0}


def test_el_tope_de_vitalidad_sigue_siendo_seis() -> None:
    _, manager, p1 = _partida()
    p1.vitalidad = 5
    manager.accion_A_alimentar(p1, harina={"Blanca": 30})
    assert p1.vitalidad == 6


def test_elegir_mas_uno_renuncia_al_mas_dos_ese_dia() -> None:
    _, manager, p1 = _partida()
    manager.accion_A_alimentar(p1, harina={"Blanca": 10})
    with pytest.raises(InvalidActionError):
        manager.accion_A_alimentar(p1, harina={"Blanca": 10})
    assert p1.vitalidad == 3


# ===========================================================================
# Fail-fast: nada se cobra si algo falla
# ===========================================================================

@pytest.mark.parametrize(
    "harina",
    [
        {"Blanca": 20},                     # suma que no es escalon
        {"Blanca": 40},                     # por encima del escalon mas caro
        {"Blanca": 5, "Centeno": 5},        # no son tokens enteros
        {"Blanca": 0, "Centeno": 10},       # cero no es un reparto
        {"Blanca": -10, "Centeno": 20},     # negativo
        {"Trigo": 10},                      # tipo inexistente
        {"Blanca": True},                   # un bool no es una cantidad
        {},                                 # vacio
        None,                               # ausente
        ["Blanca"],                         # no es un reparto
    ],
)
def test_un_reparto_mal_formado_se_rechaza_sin_tocar_nada(harina) -> None:
    _, manager, p1 = _partida()
    antes = dict(p1.reserva_harina)
    with pytest.raises(InvalidActionError):
        manager.accion_A_alimentar(p1, harina=harina)
    assert p1.reserva_harina == antes
    assert p1.vitalidad == 2
    assert p1.accion_alimentar_usada is False


def test_la_suma_que_no_es_escalon_nombra_la_escalera() -> None:
    _, manager, p1 = _partida()
    with pytest.raises(InvalidActionError, match=r"20%.*10% = \+1, 30% = \+2"):
        manager.accion_A_alimentar(p1, harina={"Blanca": 20})


def test_un_faltante_nombra_todos_los_tipos_que_faltan() -> None:
    _, manager, p1 = _partida()
    p1.reserva_harina = {"Blanca": 10, "Centeno": 0, "Integral": 0}
    with pytest.raises(MissingResourceError) as exc:
        manager.accion_A_alimentar(p1, harina={"Blanca": 20, "Centeno": 10})
    assert "Blanca" in str(exc.value) and "Centeno" in str(exc.value)
    assert p1.reserva_harina == {"Blanca": 10, "Centeno": 0, "Integral": 0}
    assert p1.vitalidad == 2
    assert p1.accion_alimentar_usada is False


def test_cinco_mas_cinco_no_paga_el_escalon_barato() -> None:
    """La accion exige 10% de UN tipo; sumar entre tipos no vale."""
    _, manager, p1 = _partida()
    p1.reserva_harina = {"Blanca": 5, "Centeno": 5, "Integral": 0}
    with pytest.raises(MissingResourceError):
        manager.accion_A_alimentar(p1, harina={"Blanca": 10})
    assert p1.puede_alimentar is False


def test_no_emite_eventos() -> None:
    engine, manager, p1 = _partida()
    antes = len(engine.eventos)
    manager.accion_A_alimentar(p1, harina={"Blanca": 20, "Centeno": 10})
    assert len(engine.eventos) == antes


# ===========================================================================
# La casilla no miente
# ===========================================================================

def test_sin_harina_pero_con_agua_la_casilla_esta_apagada() -> None:
    engine, _, p1 = _partida()
    p1.reserva_harina = {"Blanca": 0, "Centeno": 0, "Integral": 0}
    p1.reserva_agua = 5
    a = _disponible(engine, p1)
    assert a["habilitada"] is False
    assert a["motivo"] == "Sin harina: necesitas 10% de un mismo tipo"


def test_cinco_mas_cinco_apaga_la_casilla() -> None:
    engine, _, p1 = _partida()
    p1.reserva_harina = {"Blanca": 5, "Centeno": 5, "Integral": 0}
    assert _disponible(engine, p1)["habilitada"] is False


def test_diez_de_un_tipo_enciende_la_casilla() -> None:
    engine, _, p1 = _partida()
    p1.reserva_harina = {"Blanca": 0, "Centeno": 10, "Integral": 0}
    p1.reserva_agua = 0
    assert _disponible(engine, p1)["habilitada"] is True


def test_ya_usada_gana_al_motivo_de_harina() -> None:
    engine, _, p1 = _partida()
    p1.reserva_harina = {"Blanca": 0, "Centeno": 0, "Integral": 0}
    p1.accion_alimentar_usada = True
    assert _disponible(engine, p1)["motivo"] == "Ya se usó hoy"


def test_sin_harina_no_conserva_la_visita_por_la_accion_a() -> None:
    """`_jugador_elegible` media solo la bandera: un jugador sin harina volvia
    a la rotacion toda la ronda por una accion que no podia permitirse."""
    engine, _, p1 = _partida()
    p1.puntos_accion = 0
    p1.datos_investigacion = 0
    p1.monedas = 0
    p1.reserva_agua = 0
    p1.horas_extras_usadas = True
    p1.acciones_pa_usadas_hoy = ["E", "descarte"]
    p1.accion_alimentar_usada = False

    p1.reserva_harina = {"Blanca": 10, "Centeno": 0, "Integral": 0}
    assert engine._jugador_elegible(0) is True

    p1.reserva_harina = {"Blanca": 5, "Centeno": 5, "Integral": 0}
    assert engine._jugador_elegible(0) is False


# ===========================================================================
# El wire
# ===========================================================================

def test_el_wire_lleva_solo_el_reparto() -> None:
    engine, manager, p1 = _partida()
    resultado = resolver_comando(
        engine, manager, p1, "A", {"harina": {"Blanca": 20, "Centeno": 10}}
    )
    assert resultado == 2
    assert p1.vitalidad == 4


def test_el_wire_viejo_ya_no_significa_nada() -> None:
    engine, manager, p1 = _partida()
    with pytest.raises(InvalidActionError):
        resolver_comando(engine, manager, p1, "A", {"tipo_harina": "Blanca"})
    assert p1.vitalidad == 2


def test_la_frase_del_registro_distingue_los_escalones() -> None:
    engine, manager, p1 = _partida()
    params = {"harina": {"Blanca": 10}}
    r = resolver_comando(engine, manager, p1, "A", params)
    assert describir_accion(engine, p1, "A", params, r) == "Alimentó el cultivo con Blanca"

    p1.accion_alimentar_usada = False
    params = {"harina": {"Blanca": 20, "Centeno": 10}}
    r = resolver_comando(engine, manager, p1, "A", params)
    assert (
        describir_accion(engine, p1, "A", params, r)
        == "Alimentó el cultivo con 20% Blanca y 10% Centeno (+2 Vitalidad)"
    )
