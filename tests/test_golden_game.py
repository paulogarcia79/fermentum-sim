"""
tests/test_golden_game.py -- caracterizacion del bucle Fase I/II/III completo.

Juega una partida determinista (RNG global sembrado) con dos jugadores
"bot" (tests/_bot.py) durante varios Dias de Laboratorio usando la API
publica actual de GameEngine (ejecutar_dia_laboratorio con callback
bloqueante), serializa el estado final con dataclasses.asdict, y lo compara
contra un snapshot dorado en tests/golden/.

Proposito: dar a los refactors de Milestone 1 en adelante (turn-state
machine, event stream) una linea base de comportamiento verificada, en un
proyecto que hasta ahora no tenia ninguna red de regresion confiable.
"""
from __future__ import annotations

import dataclasses
import json
import random
from pathlib import Path
from typing import Any, Dict

from actions import ActionManager
from engine import GameEngine
from main import setup_game
from models import Player

from tests._bot import heuristic_turn

SEED = 1234
NUM_DIAS = 4
GOLDEN_PATH = Path(__file__).parent / "golden" / "day4_2p_seed1234.json"


def _jugar_partida_determinista() -> Dict[str, Any]:
    random.seed(SEED)
    engine: GameEngine = setup_game(["Alba", "Bruno"])
    manager = ActionManager(engine)

    def turno(engine: GameEngine, player: Player) -> None:
        heuristic_turn(engine, player, manager)

    for _ in range(NUM_DIAS):
        if engine.partida_terminada:
            break
        engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)

    estado = {
        "players": [dataclasses.asdict(p) for p in engine.players],
        "environment": dataclasses.asdict(engine.environment),
        "market": dataclasses.asdict(engine.market),
        "partida_terminada": engine.partida_terminada,
    }
    # Normalizado a traves de JSON (p.ej. tuplas -> listas) para que la
    # comparacion contra el snapshot dorado -- tambien cargado desde JSON --
    # no reporte falsos positivos por diferencias de tipo sin importancia.
    return json.loads(json.dumps(estado))


def test_golden_game_state_matches_snapshot() -> None:
    resultado = _jugar_partida_determinista()
    esperado = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert resultado == esperado


def test_golden_game_is_reproducible() -> None:
    """La misma semilla debe producir exactamente el mismo estado dos veces,
    confirmando que no hay fuentes de no-determinismo ocultas (orden de
    dict, iteracion de sets, etc.) mas alla del RNG global sembrado."""
    primera = _jugar_partida_determinista()
    segunda = _jugar_partida_determinista()
    assert primera == segunda
