"""
tests/_bot.py -- jugador heuristico determinista para pruebas de caracterizacion.

No es una IA competitiva: solo produce una partida reproducible y variada
(hornea, inicia masas, alimenta, investiga, compra) para tener un estado de
juego no trivial que serializar y comparar contra un snapshot dorado en
tests/test_golden_game.py. Reutilizable por futuras pruebas del bucle de
turnos (p.ej. el driver headless de la Milestone 1).

Aloja ademas `jugar_dia`, el driver de un Dia de Laboratorio completo sobre la
maquina de estados del motor. Vive aqui, y en un solo sitio, desde que se retiro
la CLI: `GameEngine.ejecutar_dia_laboratorio` existia para darle a la terminal
su punto de pausa entre dias, y al desaparecer quedo una sola forma de conducir
el motor -- la misma que usa `server/`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List

from exceptions import FermentumError

if TYPE_CHECKING:
    from actions import ActionManager
    from engine import GameEngine
    from models import Player


def jugar_dia(
    engine: "GameEngine",
    turno: Callable[["GameEngine", "Player"], None],
) -> bool:
    """
    Juega un Dia de Laboratorio completo conduciendo la maquina de estados.

    Reemplaza al desaparecido `GameEngine.ejecutar_dia_laboratorio(callback)`, y
    es su equivalente exacto: `iniciar_dia()` es `fase_I_ambiente()` seguido de
    `_preparar_fase_II()`, y el resto es el mismo round-robin sobre
    `jugador_activo`, que ambas rutas ya compartian via
    `_avanzar_a_siguiente_elegible`.

    **El chequeo del nonce es load-bearing, no defensivo.** Un callback puede
    cerrar su propia visita (llamando a `pasar_turno`) o no cerrarla: las
    acciones gratuitas -- Alimentar, Descarte, Horas Extras, Pedido de Urgencia
    -- no terminan el turno, y `heuristic_turn` hace `return` en cuanto una de
    ellas tiene exito. Si el driver cerrara siempre, robaria la visita a un
    callback que aun tenia PA; si no cerrara nunca, el bucle giraria para
    siempre sobre el mismo jugador. Comparar `turno_nonce` antes y despues es lo
    que distingue los dos casos, y es exactamente lo que hacia la ruta
    bloqueante. Sin el, `tests/test_golden_game.py` cuelga mientras los otros
    dos consumidores (cuyos callbacks siempre pasan turno) seguirian en verde.

    Args:
        engine: Motor de la partida, con el dia anterior ya resuelto.
        turno: Callback `(engine, player) -> None`, invocado UNA vez por visita.

    Returns:
        True si la partida termina con este dia, False si continua -- lo mismo
        que devolvia `ejecutar_dia_laboratorio`.

    Raises:
        GameAlreadyOverError: Si la partida ya habia terminado (lo levanta
            `iniciar_dia`, que conserva el guardia de la ruta retirada).
    """
    engine.iniciar_dia()

    while (player := engine.jugador_activo) is not None:
        nonce_antes = engine.turno_nonce
        turno(engine, player)
        if engine.turno_nonce == nonce_antes:
            engine.terminar_turno_actual()

    return engine.resolver_fase_III()


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
        lambda: _intentar_mostrador(player, manager),
    ]
    for intento in intentos:
        try:
            if intento():
                return
        except FermentumError:
            continue

    # Sin PA y sin acciones legales: pasar_turno() (no una asignacion directa
    # a puntos_accion) es obligatorio aqui -- marca al jugador como renunciado
    # por el resto del dia (engine.py:_jugador_elegible). Sin esto, un jugador
    # sin PA ni recursos pero con accion_alimentar_usada o horas_extras_usadas
    # aun en False seguiria siendo "elegible" para una proxima vuelta
    # indefinidamente.
    #
    # Desde el Turno de Mostrador, llegar hasta aqui implica 0 PA: con PA, el
    # ultimo intento siempre tiene exito. Es justo el hueco que esa accion vino
    # a tapar, y el bot lo ejerce por la misma razon que un jugador -- pasar
    # renuncia tambien a las gratuitas del resto del dia.
    engine.pasar_turno(player)


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
    if tipo is None:
        return False
    manager.accion_A_alimentar(player, harina={tipo: 10})
    return True


def _intentar_investigar(engine: "GameEngine", player: "Player", manager: "ActionManager") -> bool:
    if len(player.carpeta_proyectos) >= 3:
        return False
    for idx, receta in enumerate(engine.market.recetas_visibles):
        if receta is not None:
            manager.accion_G_investigar_protocolo(player, idx)
            return True
    return False


def _intentar_mostrador(player: "Player", manager: "ActionManager") -> bool:
    """Ultimo recurso ANTES de pasar: 1 PA por 1 Moneda.

    No ocupa espacio, asi que sirve para cada PA que quede suelto. Va el ultimo
    de la lista a proposito: es el suelo del tablero y cualquier otra jugada lo
    domina (engine.MONEDAS_MOSTRADOR).
    """
    if player.puntos_accion < 1:
        return False
    manager.accion_turno_mostrador(player)
    return True


def _intentar_adquirir(engine: "GameEngine", player: "Player", manager: "ActionManager") -> bool:
    from models import TipoHarina  # import local para evitar ciclo en TYPE_CHECKING

    for tipo in TipoHarina:
        try:
            manager.accion_C_visitar_mercado(
                player, transacciones=[{"tipo_recurso": tipo.value, "operacion": "comprar"}]
            )
            return True
        except FermentumError:
            continue
    return False
