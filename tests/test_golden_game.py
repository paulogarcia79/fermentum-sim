"""
tests/test_golden_game.py -- caracterizacion del bucle Fase I/II/III completo.

Juega una partida determinista (RNG global sembrado) con dos jugadores
"bot" (tests/_bot.py) durante varios Dias de Laboratorio conduciendo la
maquina de estados de GameEngine (tests/_bot.py:jugar_dia), serializa el estado
final con dataclasses.asdict, y lo compara contra un snapshot dorado en
tests/golden/.

El snapshot ya demostro que sirve para lo que existe: la retirada de la CLI
elimino la ruta bloqueante (`ejecutar_dia_laboratorio`) con la que este test se
escribio, y la migracion a la maquina de estados paso contra este mismo fichero
SIN regenerarlo -- que es la prueba de que las dos rutas eran equivalentes, en
vez de la suposicion de que lo eran.

Proposito: dar a los refactors de Milestone 1 en adelante (turn-state
machine, event stream) una linea base de comportamiento verificada, en un
proyecto que hasta ahora no tenia ninguna red de regresion confiable.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict

from actions import ActionManager
from engine import GameEngine
from bootstrap import create_game
from models import Player
from serialization import snapshot

from tests._bot import heuristic_turn, jugar_dia

SEED = 1234
NUM_DIAS = 4
GOLDEN_PATH = Path(__file__).parent / "golden" / "day4_2p_seed1234.json"


def _jugar_partida_determinista() -> Dict[str, Any]:
    random.seed(SEED)
    engine: GameEngine = create_game(["Alba", "Bruno"])
    manager = ActionManager(engine)

    def turno(engine: GameEngine, player: Player) -> None:
        heuristic_turn(engine, player, manager)

    for _ in range(NUM_DIAS):
        if engine.partida_terminada:
            break
        jugar_dia(engine, turno)

    # Normalizado a traves de JSON (p.ej. tuplas -> listas) para que la
    # comparacion contra el snapshot dorado -- tambien cargado desde JSON --
    # no reporte falsos positivos por diferencias de tipo sin importancia.
    return json.loads(json.dumps(snapshot(engine)))


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
