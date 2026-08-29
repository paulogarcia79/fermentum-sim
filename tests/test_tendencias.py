"""
tests/test_tendencias.py -- el Mercado de Tendencias se REVELA al inicio del
dia (Fase I) y se APLICA al final del mismo (Fase III), de modo que rige los
precios del dia SIGUIENTE.

Antes este mazo no tenia ninguna cobertura directa (solo aparecia de refilon en
el snapshot dorado), asi que estas pruebas fijan tanto el reparto de fases como
el tope [1, 5] de los visores.
"""
from __future__ import annotations

import random
from typing import List

from engine import (
    GameEngine,
    POSICION_HARINA_INICIAL,
    POSICION_HARINA_MAX,
    POSICION_HARINA_MIN,
)
from events import EventoTipo
from main import setup_game


def _engine_con_tendencias(modificadores: List[int]) -> GameEngine:
    """Motor de 2 jugadores con el mazo de tendencias forzado a `modificadores`
    (en orden de robo), para que la prueba no dependa del azar."""
    random.seed(31337)
    engine = setup_game(["Alba", "Bruno"])
    engine.market.mazo_tendencias = list(modificadores)
    engine.market.descarte_tendencias = []
    engine.market.tendencia_pendiente = None
    return engine


def _pasar_todos(engine: GameEngine) -> None:
    for jugador in engine.players:
        engine.pasar_turno(jugador)


def _posiciones(engine: GameEngine) -> List[int]:
    return sorted(engine.market.posiciones_harina.values())


def test_fase_I_revela_pero_no_mueve_los_visores() -> None:
    engine = _engine_con_tendencias([2])
    engine.iniciar_dia()

    assert engine.market.tendencia_pendiente == 2
    # El Dia 1 se juega con los precios iniciales: la carta revelada hoy
    # todavia no toco nada.
    assert _posiciones(engine) == [POSICION_HARINA_INICIAL] * 3
    assert engine.market.descarte_tendencias == []


def test_fase_III_aplica_la_pendiente_y_la_manda_al_descarte() -> None:
    engine = _engine_con_tendencias([2])
    engine.iniciar_dia()
    _pasar_todos(engine)
    engine.resolver_fase_III()

    assert _posiciones(engine) == [POSICION_HARINA_INICIAL + 2] * 3
    assert engine.market.tendencia_pendiente is None
    # El descarte solo recibe cartas YA APLICADAS.
    assert engine.market.descarte_tendencias == [2]


def test_la_tendencia_de_hoy_rige_los_precios_de_manana() -> None:
    """El nucleo del cambio: lo revelado el Dia N se cobra el Dia N+1."""
    engine = _engine_con_tendencias([2, -1])

    engine.iniciar_dia()
    precios_dia_1 = _posiciones(engine)
    _pasar_todos(engine)
    engine.resolver_fase_III()

    engine.iniciar_dia()
    precios_dia_2 = _posiciones(engine)

    assert precios_dia_1 == [POSICION_HARINA_INICIAL] * 3
    # El Dia 2 se juega con lo que anuncio el Dia 1 (+2), no con lo que
    # anuncia hoy (-1), que sigue pendiente.
    assert precios_dia_2 == [POSICION_HARINA_INICIAL + 2] * 3
    assert engine.market.tendencia_pendiente == -1


def test_tope_superior_e_inferior_de_los_visores() -> None:
    engine = _engine_con_tendencias([2, 2, -2, -2])

    # 3 -> 5 -> 5 (topa arriba)
    for esperado in (POSICION_HARINA_INICIAL + 2, POSICION_HARINA_MAX):
        engine.iniciar_dia()
        _pasar_todos(engine)
        engine.resolver_fase_III()
        assert _posiciones(engine) == [esperado] * 3

    # 5 -> 3 -> 1 (topa abajo)
    for esperado in (3, POSICION_HARINA_MIN):
        engine.iniciar_dia()
        _pasar_todos(engine)
        engine.resolver_fase_III()
        assert _posiciones(engine) == [esperado] * 3


def test_eventos_anuncio_en_fase_I_y_aplicacion_en_fase_III() -> None:
    engine = _engine_con_tendencias([1])

    engine.iniciar_dia()
    tipos_tras_fase_I = [ev.tipo for ev in engine.eventos]
    assert tipos_tras_fase_I.count(EventoTipo.TENDENCIA_ANUNCIADA) == 1
    assert EventoTipo.TENDENCIA_MERCADO not in tipos_tras_fase_I

    _pasar_todos(engine)
    engine.resolver_fase_III()

    anuncio = next(ev for ev in engine.eventos if ev.tipo == EventoTipo.TENDENCIA_ANUNCIADA)
    aplicacion = next(ev for ev in engine.eventos if ev.tipo == EventoTipo.TENDENCIA_MERCADO)

    # Se aplica exactamente lo que se anuncio.
    assert anuncio.datos["modificador"] == aplicacion.datos["modificador"] == 1
    assert aplicacion.datos["posiciones_antes"] == {
        "Blanca": POSICION_HARINA_INICIAL,
        "Integral": POSICION_HARINA_INICIAL,
        "Centeno": POSICION_HARINA_INICIAL,
    }
    assert aplicacion.datos["posiciones_despues"] == {
        "Blanca": POSICION_HARINA_INICIAL + 1,
        "Integral": POSICION_HARINA_INICIAL + 1,
        "Centeno": POSICION_HARINA_INICIAL + 1,
    }


def test_aplicar_sin_pendiente_es_inocuo() -> None:
    """Llamarlo dos veces no debe volver a mover los visores."""
    engine = _engine_con_tendencias([2])
    engine.iniciar_dia()
    _pasar_todos(engine)
    engine.resolver_fase_III()

    posiciones_tras_aplicar = _posiciones(engine)
    assert engine.market.aplicar_tendencia_pendiente() is None
    assert _posiciones(engine) == posiciones_tras_aplicar
