"""
tests/test_variedad_recetas.py -- el termino de puntuacion final «Variedad de
Recetas» (CORE_MECHANICS.md §3): la curva triangular sobre las recetas
DISTINTAS horneadas con exito, el desglose de los 7 terminos que sustituyo a la
aritmetica que estuvo duplicada a mano en la CLI, su papel como primer criterio de desempate y su
viaje al cliente via server/views.py.
"""
from __future__ import annotations

import random

from models import HorneadoRecord, Player, RECIPE_CATALOG
from server.sessions import RoomManager
from server.views import game_state_view

# Los 7 terminos de CORE_MECHANICS.md §3, en el orden en que se presentan.
TERMINOS_ESPERADOS = [
    "Base",
    "Sabor",
    "Madurez",
    "Variedad de Recetas",
    "Desperdicio",
    "Contaminación",
    "Conversión de Riqueza",
]

# n recetas distintas -> n*(n+1)//2 PM. El tope real es 5: la partida termina
# al quinto horneado exitoso.
TRIANGULARES = {0: 0, 1: 1, 2: 3, 3: 6, 4: 10, 5: 15}


def _registro(receta_id: str, puntos_base: int = 8, *, colapso: bool = False) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=RECIPE_CATALOG[receta_id],
        posicion_final=12,
        puntos_base=puntos_base,
        bono_sabor_aplicado=False,
        fue_colapso=colapso,
        datos_obtenidos=0,
        monedas_obtenidos=0,
    )


def _jugador(nombre: str = "Alba") -> Player:
    return Player(nombre=nombre)


def _sesion_iniciada():
    random.seed(777)
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo", 2)
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)
    return sesion


# ---------------------------------------------------------------------------
# La curva
# ---------------------------------------------------------------------------

def test_curva_triangular_de_cero_a_cinco_recetas_distintas() -> None:
    recetas = ["pan_de_campo", "focaccia", "miche", "brioche", "pumpernickel"]
    jugador = _jugador()

    assert jugador.recetas_distintas_horneadas == 0
    assert jugador.puntos_variedad == TRIANGULARES[0]

    for n, receta_id in enumerate(recetas, start=1):
        jugador.archivo_horneado_exitoso.append(_registro(receta_id))
        assert jugador.recetas_distintas_horneadas == n
        assert jugador.puntos_variedad == TRIANGULARES[n]

    # La escalada es el punto del termino: cada clase nueva vale mas que la
    # anterior (incrementos 1, 2, 3, 4, 5).
    incrementos = [TRIANGULARES[n] - TRIANGULARES[n - 1] for n in range(1, 6)]
    assert incrementos == [1, 2, 3, 4, 5]


def test_las_copias_de_la_misma_carta_cuentan_como_una_sola_clase() -> None:
    """El mazo reparte copias (COPIAS_POR_GRADO), asi que repetir no da variedad."""
    jugador = _jugador()
    for _ in range(3):
        jugador.archivo_horneado_exitoso.append(_registro("pan_graham"))

    assert len(jugador.archivo_horneado_exitoso) == 3
    assert jugador.recetas_distintas_horneadas == 1
    assert jugador.puntos_variedad == 1  # no 6


def test_un_colapso_nunca_aporta_variedad() -> None:
    """
    Ni siquiera de una carta que no aparezca en el archivo de exitos: provocar
    un colapso es gratis (iniciar una masa y dejar que la Fase III la hornee al
    sobrefermentar), asi que contarlo permitiria cosechar el bono sin hornear
    bien nada.
    """
    jugador = _jugador()
    jugador.archivo_horneado_exitoso.append(_registro("pan_de_campo"))
    jugador.archivo_colapsos.append(_registro("pumpernickel", -4, colapso=True))

    assert jugador.recetas_distintas_horneadas == 1
    assert jugador.puntos_variedad == 1


# ---------------------------------------------------------------------------
# El desglose
# ---------------------------------------------------------------------------

def test_el_desglose_suma_exactamente_los_puntos_finales() -> None:
    jugador = _jugador()
    jugador.archivo_horneado_exitoso.append(_registro("pan_de_campo", 9))
    jugador.archivo_horneado_exitoso.append(_registro("focaccia", 11))
    jugador.archivo_colapsos.append(_registro("miche", -4, colapso=True))
    jugador.monedas = 12
    jugador.contador_contaminaciones = 1
    jugador.reserva_agua = 4

    desglose = jugador.desglose_maestria
    assert sum(desglose.values()) == jugador.puntos_maestria_final
    assert desglose["Variedad de Recetas"] == 3  # dos exitos distintos


def test_el_desglose_lleva_los_siete_terminos_en_orden() -> None:
    """
    Guardarrail del refactor: RankingView.vue recorre este mapa en
    vez de recalcular la formula, y el orden de insercion es el de
    presentacion. Mientras estuvo duplicada, la version del CLI se quedo sin
    «Conversión de Riqueza» y no sumaba su propio TOTAL.
    """
    assert list(_jugador().desglose_maestria) == TERMINOS_ESPERADOS


def test_la_variedad_entra_en_los_puntos_finales() -> None:
    """Un jugador que reparte sus horneados puntua mas que uno que repite."""
    variado = _jugador("Variado")
    repetidor = _jugador("Repetidor")
    for receta_id in ("pan_de_campo", "focaccia", "miche"):
        variado.archivo_horneado_exitoso.append(_registro(receta_id, 9))
    for _ in range(3):
        repetidor.archivo_horneado_exitoso.append(_registro("pan_de_campo", 9))

    # Misma puntuacion base (3 x 9) y mismo estado en todo lo demas.
    assert variado.desglose_maestria["Base"] == repetidor.desglose_maestria["Base"]
    assert variado.puntos_maestria_final - repetidor.puntos_maestria_final == 6 - 1


# ---------------------------------------------------------------------------
# Desempate
# ---------------------------------------------------------------------------

def test_la_variedad_desempata_por_delante_de_la_vitalidad() -> None:
    sesion = _sesion_iniciada()
    engine = sesion.engine
    variado, vital = engine.players[0], engine.players[1]

    # Estado limpio y equivalente en ambos, salvo lo que se prueba.
    for jugador in (variado, vital):
        jugador.reserva_harina = {k: 0 for k in jugador.reserva_harina}
        jugador.reserva_agua = 0
        jugador.monedas = 0
        jugador.acidez = 0
        jugador.vitalidad = 3

    variado.archivo_horneado_exitoso.append(_registro("pan_de_campo", 9))
    variado.archivo_horneado_exitoso.append(_registro("focaccia", 9))
    vital.archivo_horneado_exitoso.append(_registro("miche", 9))
    vital.archivo_horneado_exitoso.append(_registro("miche", 9))
    # `vital` recibe MAS vitalidad -- el antiguo primer desempate -- y se le
    # compensa con puntos base la ventaja de variedad de `variado` (y el punto
    # de Madurez que trae esa vitalidad extra) hasta dejar un empate exacto en
    # Puntos de Maestria. La diferencia se calcula en vez de escribirse a mano
    # para que el test no se rompa si cambia la curva triangular.
    vital.vitalidad = 6
    hueco = variado.puntos_maestria_final - vital.puntos_maestria_final
    vital.archivo_horneado_exitoso.append(_registro("miche", hueco))

    assert variado.puntos_maestria_final == vital.puntos_maestria_final
    assert vital.vitalidad > variado.vitalidad
    assert variado.recetas_distintas_horneadas > vital.recetas_distintas_horneadas

    ranking = engine.calcular_ranking_final()
    assert [jugador.nombre for _, jugador in ranking][0] == variado.nombre


# ---------------------------------------------------------------------------
# Viaje al cliente
# ---------------------------------------------------------------------------

def test_la_vista_envia_el_desglose_y_el_recuento() -> None:
    sesion = _sesion_iniciada()
    jugador = sesion.engine.players[0]
    jugador.archivo_horneado_exitoso.append(_registro("pan_de_campo"))
    jugador.archivo_horneado_exitoso.append(_registro("focaccia"))

    datos_jugador = game_state_view(sesion)["players"][0]

    assert datos_jugador["recetas_distintas_horneadas"] == 2
    assert list(datos_jugador["desglose_maestria"]) == TERMINOS_ESPERADOS
    assert datos_jugador["desglose_maestria"]["Variedad de Recetas"] == 3
    assert sum(datos_jugador["desglose_maestria"].values()) == datos_jugador["puntos_maestria_final"]
