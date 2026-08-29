"""
tests/test_events.py -- prueba el registro de eventos de GameEngine
(Milestone 2), que reemplaza el diffing de snapshots que usaba
main.py:_reporte_fermentacion para reconstruir lo ocurrido en Fase III.
"""
from __future__ import annotations

import random

from actions import ActionManager
from engine import GameEngine, Market, NUM_RECIPE_SLOTS
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
    assert tipos.count(EventoTipo.MERCADO_REFRESCADO) == 1  # reabastecimiento (inicio del dia)
    assert tipos.count(EventoTipo.RECETA_DESCARTADA) == 1  # rotacion (fin del dia)
    assert tipos.count(EventoTipo.DESGASTE) == 2  # uno por jugador
    # La tendencia se anuncia al inicio del dia y se aplica al final, una vez cada uno.
    assert tipos.count(EventoTipo.TENDENCIA_ANUNCIADA) == 1
    assert tipos.count(EventoTipo.TENDENCIA_MERCADO) == 1
    assert tipos.index(EventoTipo.TENDENCIA_ANUNCIADA) < tipos.index(EventoTipo.TENDENCIA_MERCADO)

    anuncio = next(ev for ev in engine.eventos if ev.tipo == EventoTipo.TENDENCIA_ANUNCIADA)
    aplicacion = next(ev for ev in engine.eventos if ev.tipo == EventoTipo.TENDENCIA_MERCADO)
    assert anuncio.datos["modificador"] == aplicacion.datos["modificador"]

    descartada = next(ev for ev in engine.eventos if ev.tipo == EventoTipo.RECETA_DESCARTADA)
    assert descartada.jugador_idx is None  # evento global
    assert "receta_id" in descartada.datos and "receta_nombre" in descartada.datos

    desgastes = [ev for ev in engine.eventos if ev.tipo == EventoTipo.DESGASTE]
    assert {ev.jugador_idx for ev in desgastes} == {0, 1}
    for ev in desgastes:
        assert ev.datos["vitalidad_despues"] <= ev.datos["vitalidad_antes"]


def test_mercado_rotacion_descarta_al_final_y_reabastece_al_inicio() -> None:
    """Fin del dia: descarta la receta mas antigua (extremo derecho). Inicio del
    dia: protocolo_refresco rellena todos los huecos hasta NUM_RECIPE_SLOTS."""
    random.seed(99)
    market = Market.crear_inicial()
    assert len(market.recetas_visibles) == NUM_RECIPE_SLOTS
    assert all(r is not None for r in market.recetas_visibles)

    # Un jugador toma dos recetas del mercado durante la Fase II.
    market.tomar_receta(0)
    market.tomar_receta(2)
    assert market.recetas_visibles.count(None) == 2

    # Fin del dia: se descarta la mas antigua real (la de mas a la derecha).
    mas_antigua = next(r for r in reversed(market.recetas_visibles) if r is not None)
    descartada = market.descartar_receta_mas_antigua()
    assert descartada is mas_antigua
    assert descartada in market.descarte_recetas
    assert descartada not in [r for r in market.recetas_visibles if r is not None]

    # Inicio del dia siguiente: reabastecimiento completo.
    reveladas = market.protocolo_refresco()
    assert len(market.recetas_visibles) == NUM_RECIPE_SLOTS
    assert all(r is not None for r in market.recetas_visibles)  # mazo tiene de sobra
    assert reveladas == 3  # se rellenaron los 3 huecos (2 tomadas + 1 descartada)


def test_mercado_reabastece_no_descarta() -> None:
    """protocolo_refresco por si solo nunca manda cartas al descarte."""
    random.seed(7)
    market = Market.crear_inicial()
    market.tomar_receta(1)
    assert market.descarte_recetas == []
    market.protocolo_refresco()
    assert market.descarte_recetas == []
    assert all(r is not None for r in market.recetas_visibles)


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

    datos_antes = p1.datos_investigacion
    idx_antes = len(engine.eventos)
    manager.accion_F_hornear(p1, slot_index=0)

    nuevos = engine.eventos[idx_antes:]
    horneados = [ev for ev in nuevos if ev.tipo == EventoTipo.HORNEADO]
    assert len(horneados) == 1
    assert horneados[0].jugador_idx == 0
    assert horneados[0].datos["fue_colapso"] is False
    assert horneados[0].datos["receta_nombre"] == receta.nombre
    # Zona optima -> +1 Dato de Investigacion, acreditado al jugador.
    assert horneados[0].datos["datos_generados"] == 1
    assert p1.datos_investigacion == datos_antes + 1


def test_horneado_una_celda_bajo_optima_no_da_datos() -> None:
    """Frontera exacta que el track del frontend dibujaba mal: una masa en
    ``zona_optima[0] - 1`` es zona baja para el motor (0 Datos, puntos_baja)."""
    engine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)
    p1 = engine.players[0]
    receta = p1.carpeta_proyectos[0]

    p1.reserva_harina[receta.harina_base.value] = 100
    p1.reserva_agua = receta.tokens_agua
    p1.puntos_accion = 2
    slot = manager.accion_B_iniciar_receta(p1, receta)
    slot.posicion_track = receta.zona_optima[0] - 1

    datos_antes = p1.datos_investigacion
    record = manager.accion_F_hornear(p1, slot_index=0)

    assert record.fue_colapso is False
    assert record.datos_obtenidos == 0
    assert record.puntos_base == receta.puntos_baja
    assert p1.datos_investigacion == datos_antes


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
