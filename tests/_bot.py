"""
tests/_bot.py -- jugador heuristico determinista para pruebas de caracterizacion.

No es una IA competitiva: solo produce una partida reproducible y variada
(hornea, inicia masas, alimenta, investiga, compra) para tener un estado de
juego no trivial que serializar y comparar contra un snapshot dorado en
tests/test_golden_game.py. Reutilizable por futuras pruebas del bucle de
turnos (p.ej. el driver headless de la Milestone 1).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List

from exceptions import FermentumError

if TYPE_CHECKING:
    from actions import ActionManager
    from engine import GameEngine
    from models import Player


def heuristic_turn(engine: "GameEngine", player: "Player", manager: "ActionManager") -> None:
    """Ejecuta la primera accion legal de una lista de prioridad fija; si
    ninguna aplica, cede los PA restantes (equivalente a 'Pasar' en la CLI).
    """
    intentos: List[Callable[[], bool]] = [
        lambda: _intentar_hornear(player, manager),
        lambda: _intentar_iniciar_receta(player, manager),
        lambda: _intentar_alimentar(player, manager),
        lambda: _intentar_investigar(engine, player, manager),
        lambda: _intentar_adquirir(engine, player, manager),
    ]
    for intento in intentos:
        try:
            if intento():
                return
        except FermentumError:
            continue

    player.puntos_accion = 0


def _intentar_hornear(player: "Player", manager: "ActionManager") -> bool:
    for idx, slot in enumerate(player.estaciones_fermentacion):
        if slot is not None and slot.recipe.esta_en_zona_optima(slot.posicion_track):
            manager.accion_F_hornear(player, slot_index=idx)
            return True
    return False


def _intentar_iniciar_receta(player: "Player", manager: "ActionManager") -> bool:
    if player.indice_estacion_disponible is None:
        return False
    for receta in list(player.carpeta_proyectos):
        try:
            manager.accion_B_iniciar_receta(player, receta)
            return True
        except FermentumError:
            continue
    return False


def _intentar_alimentar(player: "Player", manager: "ActionManager") -> bool:
    if player.accion_alimentar_usada:
        return False
    tipo = next((t for t, cant in player.reserva_harina.items() if cant >= 10), None)
    usar_agua = player.reserva_agua >= 2
    if tipo is None and not usar_agua:
        return False
    manager.accion_A_alimentar(
        player, usar_harina=tipo is not None, tipo_harina=tipo, usar_agua=usar_agua
    )
    return True


def _intentar_investigar(engine: "GameEngine", player: "Player", manager: "ActionManager") -> bool:
    if len(player.carpeta_proyectos) >= 3:
        return False
    for idx, receta in enumerate(engine.market.recetas_visibles):
        if receta is not None:
            manager.accion_G_investigar_protocolo(player, idx)
            return True
    return False


def _intentar_adquirir(engine: "GameEngine", player: "Player", manager: "ActionManager") -> bool:
    for idx, lote in enumerate(engine.market.suministros):
        if lote is not None:
            manager.accion_C_adquirir_insumos(player, indice_slot=idx)
            return True
    return False
