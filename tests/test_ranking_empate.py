"""
tests/test_ranking_empate.py -- el quinto criterio de desempate
(CORE_MECHANICS.md §Desempate): cuando dos investigadores empatan en los cuatro
criterios comparables, COMPARTEN el puesto en vez de que el orden de
inscripcion lo rompa en silencio.

Por que existe este test. `sorted` es estable, asi que antes el jugador con el
asiento mas bajo se llevaba la posicion 1 de un empate perfecto sin que nada en
la partida lo justificara, y sin que el cliente pudiera enterarse: la vista solo
manda `{posicion, player_idx}`, no los criterios, asi que ni siquiera podia
re-derivar el desempate para detectar que hubo uno. Compartir el puesto es lo
que hace visible el empate -- de ahi que el confeti del ganador (RankingView.vue)
pueda limitarse a mirar `posicion === 1` y salga correcto para dos ganadores sin
logica extra.

El ranking es «de competicion», no «denso»: dos primeros y el siguiente en la
3, no en la 2.
"""
from __future__ import annotations

import random

from bootstrap import create_game
from models import HorneadoRecord, Player, RECIPE_CATALOG
from server.sessions import RoomManager
from server.views import game_state_view


def _registro(receta_id: str, puntos_base: int) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=RECIPE_CATALOG[receta_id],
        posicion_final=12,
        puntos_base=puntos_base,
        bono_sabor_aplicado=False,
        fue_colapso=False,
        datos_obtenidos=0,
        monedas_obtenidos=0,
    )


def _igualar(jugador: Player, *, puntos_base: int, receta: str = "pan_de_campo") -> None:
    """
    Deja al jugador en un estado conocido en los CUATRO criterios: un unico
    horneado de `receta` con `puntos_base`, y vitalidad / datos / reservas
    fijados a mano. Las reservas se vacian porque «Desperdicio» las convierte
    en Puntos de Maestria y arruinaria el empate exacto.
    """
    jugador.archivo_horneado_exitoso.clear()
    jugador.archivo_colapsos.clear()
    jugador.archivo_horneado_exitoso.append(_registro(receta, puntos_base))
    jugador.vitalidad = 3
    jugador.datos_investigacion = 1
    jugador.monedas = 0
    jugador.reserva_agua = 0
    for tipo in jugador.reserva_harina:
        jugador.reserva_harina[tipo] = 0
    jugador.episodios_contaminacion = 0


def _partida(nombres: list[str]):
    random.seed(4242)
    return create_game(nombres)


# ---------------------------------------------------------------------------
# Puestos compartidos
# ---------------------------------------------------------------------------

def test_dos_empatados_comparten_la_victoria_y_el_tercero_es_tercero() -> None:
    engine = _partida(["Alba", "Bruno", "Carla"])
    alba, bruno, carla = engine.players
    _igualar(alba, puntos_base=12)
    _igualar(bruno, puntos_base=12)
    _igualar(carla, puntos_base=4)

    assert alba.puntos_maestria_final == bruno.puntos_maestria_final
    assert carla.puntos_maestria_final < alba.puntos_maestria_final

    ranking = engine.calcular_ranking_final()

    assert [posicion for posicion, _ in ranking] == [1, 1, 3]
    ganadores = {jugador.nombre for posicion, jugador in ranking if posicion == 1}
    assert ganadores == {"Alba", "Bruno"}
    assert ranking[2][1].nombre == "Carla"


def test_sin_empate_las_posiciones_son_correlativas() -> None:
    engine = _partida(["Alba", "Bruno", "Carla"])
    alba, bruno, carla = engine.players
    _igualar(alba, puntos_base=12)
    _igualar(bruno, puntos_base=8)
    _igualar(carla, puntos_base=4)

    ranking = engine.calcular_ranking_final()

    assert [posicion for posicion, _ in ranking] == [1, 2, 3]
    assert [jugador.nombre for _, jugador in ranking] == ["Alba", "Bruno", "Carla"]


def test_un_empate_por_debajo_del_primero_tambien_comparte_puesto() -> None:
    engine = _partida(["Alba", "Bruno", "Carla"])
    alba, bruno, carla = engine.players
    _igualar(alba, puntos_base=16)
    _igualar(bruno, puntos_base=8)
    _igualar(carla, puntos_base=8)

    ranking = engine.calcular_ranking_final()

    # De competicion, no denso: los dos segundos no dejan un tercer puesto.
    assert [posicion for posicion, _ in ranking] == [1, 2, 2]
    assert ranking[0][1].nombre == "Alba"


def test_los_desempates_previos_siguen_rompiendo_el_empate() -> None:
    """
    Compartir puesto es el ULTIMO recurso: si los criterios 2-4 distinguen a los
    jugadores, siguen decidiendo y las posiciones son correlativas.
    """
    engine = _partida(["Alba", "Bruno"])
    alba, bruno = engine.players
    _igualar(alba, puntos_base=12)
    _igualar(bruno, puntos_base=12)
    # Mismo PM, pero Bruno tiene mas Vitalidad (criterio 3). Subir la Vitalidad
    # tambien sube «Madurez», asi que se compensa por puntos base -- el hueco se
    # calcula en vez de escribirse a mano para que el test no se rompa si cambia
    # la formula (mismo truco que tests/test_variedad_recetas.py).
    bruno.vitalidad = 5
    hueco = bruno.puntos_maestria_final - alba.puntos_maestria_final
    bruno.archivo_horneado_exitoso[0] = _registro("pan_de_campo", 12 - hueco)
    assert alba.puntos_maestria_final == bruno.puntos_maestria_final
    assert bruno.vitalidad > alba.vitalidad

    ranking = engine.calcular_ranking_final()

    assert [posicion for posicion, _ in ranking] == [1, 2]
    assert ranking[0][1].nombre == "Bruno"


# ---------------------------------------------------------------------------
# Viaje al cliente
# ---------------------------------------------------------------------------

def test_la_vista_envia_el_puesto_compartido() -> None:
    random.seed(777)
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo", 2)
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)

    alba, bruno = sesion.engine.players
    _igualar(alba, puntos_base=12)
    _igualar(bruno, puntos_base=12)

    ranking = game_state_view(sesion)["ranking"]

    assert [fila["posicion"] for fila in ranking] == [1, 1]
    assert {fila["player_idx"] for fila in ranking} == {0, 1}
