"""
tests/test_events.py -- prueba el registro de eventos de GameEngine
(Milestone 2), que reemplaza el diffing de snapshots que usaba
main.py:_reporte_fermentacion para reconstruir lo ocurrido en Fase III.
"""
from __future__ import annotations

import random

from actions import ActionManager
from engine import GameEngine
from events import EventoTipo
from main import setup_game
from models import Environment, Player, RECIPE_CATALOG


def test_dia_1_emite_eventos_globales_y_desgaste_por_jugador() -> None:
    random.seed(555)
    engine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)

    def turno(engine, player) -> None:
        engine.pasar_turno(player)  # Pasa de inmediato: solo interesan los eventos automaticos.

    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)

    tipos = [ev.tipo for ev in engine.eventos]
    assert tipos.count(EventoTipo.JEFE_ASIGNADO) == 1
    assert tipos.count(EventoTipo.CLIMA_REVELADO) == 1
    assert tipos.count(EventoTipo.MERCADO_REFRESCADO) == 1
    assert tipos.count(EventoTipo.DESGASTE) == 2  # uno por jugador

    desgastes = [ev for ev in engine.eventos if ev.tipo == EventoTipo.DESGASTE]
    assert {ev.jugador_idx for ev in desgastes} == {0, 1}
    for ev in desgastes:
        assert ev.datos["vitalidad_despues"] <= ev.datos["vitalidad_antes"]


def test_horneado_manual_emite_evento_no_colapso() -> None:
    engine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)
    p1 = engine.players[0]
    receta = p1.carpeta_proyectos[0]

    p1.reserva_harina[receta.harina_base.value] = 100
    p1.reserva_agua = receta.tokens_agua
    p1.puntos_accion = 2
    slot = manager.accion_B_iniciar_receta(p1, receta)
    slot.posicion_track = receta.zona_optima[0]  # forzar zona optima para el horneado

    idx_antes = len(engine.eventos)
    manager.accion_F_hornear(p1, slot_index=0)

    nuevos = engine.eventos[idx_antes:]
    horneados = [ev for ev in nuevos if ev.tipo == EventoTipo.HORNEADO]
    assert len(horneados) == 1
    assert horneados[0].jugador_idx == 0
    assert horneados[0].datos["fue_colapso"] is False
    assert horneados[0].datos["receta_nombre"] == receta.nombre


def test_colapso_estructural_emite_horneado_colapso_y_masa_avanzo() -> None:
    engine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)
    p1 = engine.players[0]
    receta = p1.carpeta_proyectos[0]

    p1.reserva_harina[receta.harina_base.value] = 100
    p1.reserva_agua = receta.tokens_agua
    p1.puntos_accion = 2
    slot = manager.accion_B_iniciar_receta(p1, receta)
    # Colocar la masa justo debajo del limite de sobrefermentacion para que
    # cualquier avance positivo la colapse en la proxima Fase III.
    slot.posicion_track = receta.zona_sobrefermentada[0] - 1
    slot.dado_inoculo = 6  # avance maximo garantizado

    idx_antes = len(engine.eventos)
    engine._avanzar_masas_jugador(p1)

    nuevos = engine.eventos[idx_antes:]
    avances = [ev for ev in nuevos if ev.tipo == EventoTipo.MASA_AVANZO]
    horneados = [ev for ev in nuevos if ev.tipo == EventoTipo.HORNEADO]
    assert len(avances) == 1
    assert len(horneados) == 1
    assert horneados[0].datos["fue_colapso"] is True
    assert p1.estaciones_fermentacion[0] is None  # la estacion quedo liberada


def test_contaminacion_solo_se_emite_en_la_transicion() -> None:
    engine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)
    p1, p2 = engine.players
    p1.vitalidad = 1  # un solo punto de desgaste estandar lo lleva a 0
    p2.vitalidad = 6  # Bruno no debe contaminarse en esta prueba

    def turno(engine, player) -> None:
        engine.pasar_turno(player)

    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)
    assert p1.en_estado_contaminacion is True
    primeras_contaminaciones = [
        ev for ev in engine.eventos if ev.tipo == EventoTipo.CONTAMINACION
    ]
    assert len(primeras_contaminaciones) == 1
    assert primeras_contaminaciones[0].jugador_idx == 0

    idx_antes = len(engine.eventos)
    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)
    # Ya estaba contaminado: el desgaste no vuelve a emitir el evento de
    # transicion (la vitalidad se mantiene en el piso 0).
    nuevas_contaminaciones = [
        ev for ev in engine.eventos[idx_antes:] if ev.tipo == EventoTipo.CONTAMINACION
    ]
    assert nuevas_contaminaciones == []


def test_event_sink_recibe_los_mismos_eventos_que_engine_eventos() -> None:
    recibidos = []
    receta = next(r for r in RECIPE_CATALOG.values())
    players = [
        Player.crear_dia_1("Alba", receta),
        Player.crear_dia_1("Bruno", receta),
    ]
    engine = GameEngine(players, Environment.crear_inicial(), event_sink=recibidos.append)

    def turno(engine, player) -> None:
        engine.pasar_turno(player)

    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)

    assert recibidos == engine.eventos
