"""
tests/test_fin_de_partida.py -- «todos juegan el mismo numero de dias»: el fin
de partida se DISPARA de inmediato pero la partida termina al concluir el Dia
de Laboratorio en curso (CORE_MECHANICS.md §3, RULEBOOK.md §11.1).

Esto ya funcionaba, pero funcionaba por omision: `_partida_terminada` es un
pestillo y ningun camino de la Fase II lo lee, asi que el dia sigue solo porque
nadie lo corta. Estos tests fijan esa omision como regla -- una "optimizacion"
futura que anadiera un chequeo de fin en `terminar_turno_actual` romperia el
reparto de dias sin que nada mas se quejara.

Cubre los dos gatillos naturales (5º horneado a media Fase II, mazo de clima
agotado en la Fase I) y la excepcion deliberada: el voto unanime de fin
anticipado SI corta la ultima jornada, porque nadie pierde equidad cuando todos
piden parar.
"""
from __future__ import annotations

import random

from actions import ActionManager
from bootstrap import create_game
from engine import Fase, GameEngine
from events import EventoTipo
from exceptions import GameAlreadyOverError
from models import FermentationSlot, HorneadoRecord, Player, Recipe

from tests._bot import heuristic_turn


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _hornear_quinta(engine: GameEngine, jugador: Player) -> None:
    """Deja al jugador en 4/5 y hornea con exito el quinto, en zona optima."""
    receta = jugador.carpeta_proyectos[0]
    jugador.archivo_horneado_exitoso = [_registro_optimo(receta) for _ in range(4)]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta,
        dado_inoculo=1,
        posicion_track=receta.zona_optima[0],
        bono_sabor=False,
        modificador_incubadora=0,
    )
    engine.resolver_horneado(jugador, 0)


def _registro_optimo(receta: Recipe) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=receta,
        posicion_final=receta.zona_optima[0],
        puntos_base=receta.puntos_optimos,
        bono_sabor_aplicado=False,
        fue_colapso=False,
        datos_obtenidos=0,
        monedas_obtenidos=0,
        ampliacion_aplicada=0,
    )


def _resolver_visita(engine: GameEngine, player: Player, manager: ActionManager) -> None:
    nonce_antes = engine.turno_nonce
    heuristic_turn(engine, player, manager)
    if engine.turno_nonce == nonce_antes:
        engine.terminar_turno_actual()


# ---------------------------------------------------------------------------
# Gatillo 1: el 5º horneado exitoso, a media Fase II
# ---------------------------------------------------------------------------


def test_el_dia_se_completa_tras_el_quinto_horneado() -> None:
    """El gatillo salta a media Fase II y NO corta el dia: los demas jugadores
    siguen recibiendo visitas y la Fase III se resuelve entera (renta, desgaste,
    colapsos, tendencia). Solo entonces la fase pasa a TERMINADA."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()

    # Aseguramos que el gatillo salta con el otro jugador aun por jugar.
    disparador = engine.jugador_activo
    assert disparador is not None
    otro = next(j for j in engine.players if j is not disparador)

    _hornear_quinta(engine, disparador)
    assert engine.partida_terminada

    # El pestillo no toca la maquina de turnos: seguimos en Fase II.
    assert engine.fase_actual == Fase.FASE_II
    assert engine.jugador_activo is not None

    # Y el otro jugador llega a jugar su jornada completa.
    otro_fue_visitado = False
    while (player := engine.jugador_activo) is not None:
        if player is otro:
            otro_fue_visitado = True
        _resolver_visita(engine, player, manager)
    assert otro_fue_visitado, "el jugador que no disparo el final se quedo sin jugar"

    assert engine.fase_actual == Fase.FASE_III
    assert engine.resolver_fase_III() is True
    assert engine.fase_actual == Fase.TERMINADA


def test_el_quinto_horneado_emite_el_evento_con_su_motivo() -> None:
    engine = _motor()
    engine.iniciar_dia()
    jugador = engine.players[0]

    _hornear_quinta(engine, jugador)

    fines = [e for e in engine.eventos if e.tipo == EventoTipo.FIN_DE_PARTIDA]
    assert len(fines) == 1
    assert fines[0].datos["motivo"] == "quinta_receta"
    assert fines[0].jugador_idx == engine.players.index(jugador)


def test_no_se_puede_iniciar_otro_dia_tras_la_ultima_jornada() -> None:
    """El reparto de dias es exacto por los dos lados: la ultima jornada se
    juega entera, y no hay una jornada de mas."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    _hornear_quinta(engine, engine.players[0])

    while (player := engine.jugador_activo) is not None:
        _resolver_visita(engine, player, manager)
    engine.resolver_fase_III()

    try:
        engine.iniciar_dia()
        raise AssertionError("deberia haber lanzado GameAlreadyOverError")
    except GameAlreadyOverError:
        pass


# ---------------------------------------------------------------------------
# Gatillo 2: el mazo de clima agotado, en la Fase I
# ---------------------------------------------------------------------------


def test_el_dia_se_completa_tras_agotarse_el_mazo_de_clima() -> None:
    """El mazo se detecta al revelar la carta de la Fase I, antes de que nadie
    actue: ese dia se juega igualmente completo y es el ultimo."""
    engine = _motor()
    manager = ActionManager(engine)

    # Dejamos una sola carta: la Fase I de hoy la roba y agota el mazo.
    del engine.environment.mazo_clima[1:]
    engine.iniciar_dia()

    assert engine.partida_terminada
    assert engine.environment.ultima_carta_clima is not None, "el dia si tuvo clima"
    assert engine.fase_actual == Fase.FASE_II

    fines = [e for e in engine.eventos if e.tipo == EventoTipo.FIN_DE_PARTIDA]
    assert len(fines) == 1
    assert fines[0].datos["motivo"] == "mazo_agotado"
    assert fines[0].jugador_idx is None

    visitados = set()
    while (player := engine.jugador_activo) is not None:
        visitados.add(player.nombre)
        _resolver_visita(engine, player, manager)
    assert visitados == {j.nombre for j in engine.players}

    assert engine.resolver_fase_III() is True
    assert engine.fase_actual == Fase.TERMINADA


# ---------------------------------------------------------------------------
# La excepcion: el voto unanime SI corta la ultima jornada
# ---------------------------------------------------------------------------


def test_el_fin_anticipado_funciona_durante_la_ultima_jornada() -> None:
    """Con el gatillo ya disparado la partida NO ha terminado todavia, asi que
    el acuerdo unanime sigue pudiendo saltarse lo que queda de dia. Antes este
    camino miraba el pestillo y devolvia GameAlreadyOverError (HTTP 410)."""
    engine = _motor()
    engine.iniciar_dia()
    _hornear_quinta(engine, engine.players[0])
    assert engine.partida_terminada
    assert engine.fase_actual == Fase.FASE_II

    engine.forzar_fin_de_partida()
    assert engine.fase_actual == Fase.TERMINADA


def test_el_fin_anticipado_se_rechaza_con_la_partida_ya_puntuada() -> None:
    engine = _motor()
    engine.iniciar_dia()
    engine.forzar_fin_de_partida()

    try:
        engine.forzar_fin_de_partida()
        raise AssertionError("deberia haber lanzado GameAlreadyOverError")
    except GameAlreadyOverError:
        pass
