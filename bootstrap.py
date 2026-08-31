"""
bootstrap.py — Construcción de una Partida Nueva
===================================================
``create_game`` es el único constructor de partidas: reparte las recetas
básicas iniciales, las Cartas de Patrocinio y el orden del Día 1, y devuelve un
``GameEngine`` listo. Lo usan ``server/sessions.py`` al iniciar una sala y los
tests; nadie más construye un ``GameEngine`` a mano salvo las pruebas que
quieren un tablero degenerado a propósito.

Nació como extracción de la inicialización que vivía dentro de la CLI, para que
el servidor no tuviera que importar un módulo lleno de ``input()`` y helpers de
renderizado. La CLI ya no existe y este módulo se quedó, que era el punto: la
construcción de la partida nunca dependió de quién la mostrara.
"""
from __future__ import annotations

import random
from typing import List, Optional

from engine import GameEngine, Market
from events import EventSink
from exceptions import InsufficientPlayersError
from models import (
    PATROCINIO_CATALOG,
    Environment,
    Grado,
    PatrocinioCard,
    Player,
    RECIPE_CATALOG,
    Recipe,
)


def create_game(nombres: List[str], event_sink: Optional[EventSink] = None) -> GameEngine:
    """
    Inicializa todos los componentes de una partida nueva y devuelve un
    ``GameEngine`` listo para el Día 1.

    Proceso:
      1. Crear el entorno (mazo de clima barajado, temp 20°C).
      2. Asignar una receta básica aleatoria distinta a cada jugador (si hay
         stock suficiente; se repiten cíclicamente si hay más jugadores que
         recetas básicas).
      3. Crear el mercado central con esas Básicas ya retiradas del mazo, que
         solo entonces se baraja y revela sus 4 cartas visibles. El orden
         importa: repartir antes de barajar es lo que impide que una carta ya
         entregada siga contada en el mazo (ver ``Market.crear_inicial``).
      4. Barajar el mazo de 8 Cartas de Patrocinio y repartir 1 por jugador
         sentado (GDD v0.0.2, Módulo I §6.4 / Anexo B) — determina el orden
         de turno del Día 1 (por Iniciativa ascendente) y los recursos
         iniciales (harina, agua, monedas y Datos de Investigación) de cada
         jugador.
      5. Crear los jugadores con ``Player.crear_dia_1()``, ya con sus
         recursos de Patrocinio.
      6. Instanciar ``GameEngine`` con inyección de dependencias, pasando el
         orden de turno del Día 1 calculado en el paso 4.

    Args:
        nombres: Nombres de los jugadores, en el orden de inscripción/asiento
            a la partida (índice 0 = primer inscrito). No puede estar vacío.
            Este orden se preserva íntegramente en ``GameEngine.players`` —
            el reparto de Patrocinios baraja qué carta le toca a cada quién,
            no el orden de la lista en sí (ver ``orden_inicial`` en
            ``GameEngine.__init__``, que expresa la prioridad de turno del
            Día 1 sin reordenar la lista de jugadores).
        event_sink: Reenviado directamente a ``GameEngine`` (ver
            ``events.py``) — p. ej. ``server/sessions.py`` pasa aquí
            ``GameSession.difundir_evento`` para que los eventos emitidos
            lleguen en vivo a los suscriptores SSE de esa sala (Milestone 5).

    Returns:
        ``GameEngine`` configurado para el Día 1 (aún no iniciado — el
        llamador decide cuándo llamar a ``iniciar_dia()``).

    Raises:
        InsufficientPlayersError: Si ``nombres`` está vacío.
    """
    if not nombres:
        raise InsufficientPlayersError(
            "Se requiere al menos un jugador para iniciar la partida de Fermentum."
        )

    env = Environment.crear_inicial()

    # Jugadores — cada uno recibe una receta básica distinta si hay stock.
    # Se barajan los PROTOCOLOS Básicos, no sus copias físicas: RULEBOOK.md §3.5
    # promete que cada jugador abre con un protocolo distinto, y con 4 Básicas
    # una partida a 4 los reparte todos.
    basicas_disponibles: List[Recipe] = list({
        r.id: r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA
    }.values())
    random.shuffle(basicas_disponibles)
    repartidas: List[Recipe] = [
        basicas_disponibles[i % len(basicas_disponibles)] for i in range(len(nombres))
    ]

    # El mercado se construye DESPUÉS del reparto y recibe las Básicas ya
    # entregadas, para retirarlas del mazo antes de barajarlo y revelar.
    market = Market.crear_inicial(basicas_repartidas=repartidas)

    # Cartas de Patrocinio — 1 por jugador sentado, de un mazo de 8 barajado.
    cartas_patrocinio: List[PatrocinioCard] = list(PATROCINIO_CATALOG)
    random.shuffle(cartas_patrocinio)
    dealt: List[PatrocinioCard] = cartas_patrocinio[: len(nombres)]

    players: List[Player] = []
    for i, nombre in enumerate(nombres):
        receta = repartidas[i]
        carta = dealt[i]
        players.append(
            Player.crear_dia_1(
                nombre,
                receta,
                harina_inicial={carta.tipo_harina.value: carta.harina_pct},
                agua_inicial=carta.agua_tokens,
                monedas_iniciales=carta.monedas,
                datos_iniciales=carta.datos,
            )
        )

    # Orden de turno del Día 1: índices en `players`, ascendente por Iniciativa.
    orden_inicial: List[int] = sorted(
        range(len(dealt)), key=lambda i: dealt[i].iniciativa
    )

    return GameEngine(
        players=players,
        environment=env,
        market=market,
        event_sink=event_sink,
        orden_inicial=orden_inicial,
    )
