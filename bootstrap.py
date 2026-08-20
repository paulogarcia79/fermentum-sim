"""
bootstrap.py — Construcción de una Partida Nueva
===================================================
Extrae la lógica de inicialización que antes vivía solo en
``main.py:setup_game`` a un módulo sin ninguna dependencia de CLI, para que
un servidor (``server/``) pueda construir partidas sin importar ``main.py``
(que trae consigo helpers de renderizado y prompts basados en ``input()``).

``main.py:setup_game`` delega en ``create_game`` de este módulo; su única
responsabilidad adicional es rellenar nombres por defecto cuando el llamador
de la CLI no proporciona ninguno, una conveniencia que no tiene sentido para
un servidor (donde los nombres siempre vienen del flujo de unión a la sala).
"""
from __future__ import annotations

import random
from typing import List

from engine import GameEngine, Market
from exceptions import InsufficientPlayersError
from models import Environment, Grado, Player, RECIPE_CATALOG, Recipe


def create_game(nombres: List[str]) -> GameEngine:
    """
    Inicializa todos los componentes de una partida nueva y devuelve un
    ``GameEngine`` listo para el Día 1.

    Proceso:
      1. Crear el entorno (mazo de clima barajado, temp 20°C).
      2. Crear el mercado central (mazo de recetas, 4 slots visibles, 3 lotes).
      3. Asignar una receta básica aleatoria distinta a cada jugador (si hay
         stock suficiente; se repiten cíclicamente si hay más jugadores que
         recetas básicas).
      4. Crear los jugadores con ``Player.crear_dia_1()``.
      5. Instanciar ``GameEngine`` con inyección de dependencias.

    Args:
        nombres: Nombres de los jugadores, en el orden de inscripción a la
            partida (índice 0 = primer inscrito). No puede estar vacío.

    Returns:
        ``GameEngine`` configurado para el Día 1 (aún no iniciado — el
        llamador decide cuándo llamar a ``iniciar_dia()`` o
        ``ejecutar_dia_laboratorio()``).

    Raises:
        InsufficientPlayersError: Si ``nombres`` está vacío.
    """
    if not nombres:
        raise InsufficientPlayersError(
            "Se requiere al menos un jugador para iniciar la partida de Fermentum."
        )

    env = Environment.crear_inicial()
    market = Market.crear_inicial()

    # Jugadores — cada uno recibe una receta básica distinta si hay stock.
    basicas_disponibles: List[Recipe] = list({
        r.id: r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA
    }.values())
    random.shuffle(basicas_disponibles)

    players: List[Player] = []
    for i, nombre in enumerate(nombres):
        receta = basicas_disponibles[i % len(basicas_disponibles)]
        players.append(Player.crear_dia_1(nombre, receta, player_index=i))

    return GameEngine(players=players, environment=env, market=market)
