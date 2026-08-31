"""
tests/test_turn_state_machine.py -- prueba la maquina de estado de turno no
bloqueante de GameEngine (Milestone 1: iniciar_dia / jugador_activo /
terminar_turno_actual / pasar_turno / resolver_fase_III), sin usar el
callback bloqueante que usa la CLI.

Cubre:
  · Un driver headless completo (sin callback) juega varios dias.
  · El bug que motivo el redefinicion de la economia de turno: un jugador
    sin PA pero con una accion gratuita sin usar (Accion A / Horas Extras)
    debe seguir recibiendo visitas -- antes de este cambio, quedaba
    bloqueado del resto del dia en cuanto su PA llegaba a 0.
  · pasar_turno() renuncia al resto del dia por completo, incluidas las
    acciones gratuitas pendientes -- no solo a los PA.
"""
from __future__ import annotations

import random

from actions import ActionManager
from engine import Fase, GameEngine
from bootstrap import create_game
from models import Player

from tests._bot import heuristic_turn


def _resolver_visita(engine: GameEngine, player: Player, manager: ActionManager) -> None:
    """Ejecuta una visita con el bot heuristico y cierra el turno si el bot
    no lo hizo ya el mismo (p. ej. via pasar_turno en su rama de fallback)."""
    nonce_antes = engine.turno_nonce
    heuristic_turn(engine, player, manager)
    if engine.turno_nonce == nonce_antes:
        engine.terminar_turno_actual()


def test_headless_driver_plays_multiple_dias_sin_callback() -> None:
    random.seed(777)
    engine = create_game(["Ada", "Chen"])
    manager = ActionManager(engine)

    for _ in range(3):
        if engine.partida_terminada:
            break
        engine.iniciar_dia()
        assert engine.fase_actual == Fase.FASE_II

        while (player := engine.jugador_activo) is not None:
            _resolver_visita(engine, player, manager)

        assert engine.jugador_activo is None
        assert engine.fase_actual == Fase.FASE_III
        engine.resolver_fase_III()

    assert engine.environment.dia_actual == 4


def test_jugador_sin_pa_conserva_elegibilidad_para_accion_gratuita() -> None:
    """Antes de la Milestone 1, un jugador con puntos_accion == 0 nunca
    volvia a ser visitado, aunque no hubiera usado Accion A ni Horas
    Extras -- quedaba bloqueado de alimentar su cultivo el resto del dia."""
    engine = create_game(["Ada", "Chen"])
    engine.iniciar_dia()

    jugador = engine.jugador_activo
    assert jugador is not None
    jugador.puntos_accion = 0  # Simula PA agotado por otras vias.
    assert jugador.accion_alimentar_usada is False
    assert jugador.horas_extras_usadas is False

    assert engine.jugador_activo is jugador
    engine.terminar_turno_actual()

    # Debe volver a ser elegible en una vuelta posterior pese a PA == 0,
    # porque aun no uso ninguna de sus dos acciones gratuitas.
    visto_de_nuevo = False
    for _ in range(4):
        candidato = engine.jugador_activo
        if candidato is jugador:
            visto_de_nuevo = True
            break
        if candidato is None:
            break
        engine.terminar_turno_actual()
    assert visto_de_nuevo, "un jugador sin PA pero sin acciones gratuitas usadas debe seguir elegible"


def test_pasar_turno_renuncia_tambien_a_acciones_gratuitas() -> None:
    """pasar_turno() debe ser una renuncia total al resto del dia, no solo
    a los PA -- a diferencia de simplemente quedarse sin PA por gastarlos
    en otras acciones."""
    engine = create_game(["Ada", "Chen"])
    engine.iniciar_dia()

    jugador = engine.jugador_activo
    assert jugador is not None
    assert jugador.accion_alimentar_usada is False
    assert jugador.horas_extras_usadas is False

    engine.pasar_turno(jugador)

    for _ in range(4):
        candidato = engine.jugador_activo
        assert candidato is not jugador, "pasar_turno() no debe conceder mas visitas este dia"
        if candidato is None:
            break
        engine.terminar_turno_actual()


def test_turno_orden_expone_la_secuencia_del_dia_como_copia() -> None:
    """engine.turno_orden: indices en players, orden de juego, [0] = Jefe.
    Debe ser una copia defensiva (mutarla no afecta al motor)."""
    engine = create_game(["Ada", "Chen", "Bo"])
    engine.iniciar_dia()

    orden = engine.turno_orden
    assert sorted(orden) == [0, 1, 2]
    assert orden[0] == engine.players.index(engine.jefe_investigador)
    assert engine.players[orden[0]] is engine.jugador_activo  # el Jefe abre la Fase II

    activo_antes = engine.jugador_activo
    orden.reverse()  # mutar la lista devuelta
    assert engine.turno_orden[0] == engine.players.index(engine.jefe_investigador)
    assert engine.jugador_activo is activo_antes
