"""
tests/test_desarrollo_tecnologico.py -- el termino de puntuacion final
«Desarrollo Tecnologico» (CORE_MECHANICS.md §3): la curva triangular sobre las
mejoras de laboratorio INSTALADAS, su indiferencia al coste en Datos, su
posicion en el desglose y su viaje al cliente.

Es la MISMA curva que «Variedad de Recetas» -- las dos salen de
`models.puntos_triangulares`, que existe precisamente para que los dos
reglamentos impriman dos tablas derivadas de una sola funcion (ver
tests/test_reglamento_al_dia.py). Lo que este fichero fija es lo que NO comparte
con Variedad: que cuenta mejoras y no cartas, que no pondera por precio, y que
nunca baja.
"""
from __future__ import annotations

import random

from actions import COSTOS_TECNOLOGIA
from models import Player, TecnologiaID, puntos_triangulares
from server.sessions import RoomManager
from server.views import game_state_view

# n mejoras instaladas -> n*(n+1)//2 PM. El tope es 4: solo hay cuatro mejoras,
# y a diferencia del tope de Variedad (5, por el gatillo del quinto horneado)
# este lo impone la propia clase `Technologies`.
TRIANGULARES = {0: 0, 1: 1, 2: 3, 3: 6, 4: 10}

CLAVE = "Desarrollo Tecnológico"


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

def test_curva_triangular_de_cero_a_cuatro_mejoras() -> None:
    jugador = _jugador()

    assert jugador.tecnologias.cantidad_instaladas == 0
    assert jugador.puntos_desarrollo_tecnologico == TRIANGULARES[0]

    for n, tecnologia in enumerate(TecnologiaID, start=1):
        jugador.tecnologias.activar(tecnologia)
        assert jugador.tecnologias.cantidad_instaladas == n
        assert jugador.puntos_desarrollo_tecnologico == TRIANGULARES[n]

    # La escalada es el punto del termino, igual que en Variedad: cada mejora
    # nueva vale mas que la anterior, asi que quedarse en tres renuncia al
    # incremento mas grande del tablero (4 PM) y no a un promedio.
    incrementos = [TRIANGULARES[n] - TRIANGULARES[n - 1] for n in range(1, 5)]
    assert incrementos == [1, 2, 3, 4]


def test_es_literalmente_la_misma_curva_que_variedad() -> None:
    """
    Una sola derivacion, dos tablas: es lo que permite al reglamento decir «la
    misma curva que Variedad» en vez de imprimir una segunda formula, y lo que
    tests/test_reglamento_al_dia.py contrasta contra los dos documentos.
    """
    equipado = _jugador()
    for n, tecnologia in enumerate(TecnologiaID, start=1):
        equipado.tecnologias.activar(tecnologia)
        assert equipado.puntos_desarrollo_tecnologico == puntos_triangulares(n)

    # El mismo n produce el mismo numero en los dos terminos: lo unico que los
    # distingue es donde se corta la curva (4 mejoras frente a 5 horneados).
    variado = _jugador()
    assert variado.puntos_variedad == 0
    assert [puntos_triangulares(n) for n in range(5)] == list(TRIANGULARES.values())


# ---------------------------------------------------------------------------
# Que cuenta, y que no
# ---------------------------------------------------------------------------

def test_solo_cuentan_las_mejoras_INSTALADAS_no_los_datos_ahorrados() -> None:
    """Tener con que comprarlas no es tenerlas: el termino premia el
    laboratorio construido, no la caja de Datos."""
    jugador = _jugador()
    jugador.datos_investigacion = sum(COSTOS_TECNOLOGIA.values())  # 13, para las cuatro

    assert jugador.tecnologias.cantidad_instaladas == 0
    assert jugador.puntos_desarrollo_tecnologico == 0
    assert jugador.desglose_maestria[CLAVE] == 0


def test_el_coste_en_datos_es_irrelevante() -> None:
    """
    Sin ponderar, igual que una Basica y una Avanzada cuentan una clase cada una
    en Variedad pese a costar 1 y 3 Monedas. La consecuencia -- comprar primero
    lo barato es estrictamente correcto -- esta aceptada por diseno.
    """
    barata, cara = _jugador("Barata"), _jugador("Cara")
    barata.tecnologias.activar(TecnologiaID.CRIOPRESERVACION)  # 2 Datos
    cara.tecnologias.activar(TecnologiaID.CAMARA_B)            # 4 Datos

    assert COSTOS_TECNOLOGIA[TecnologiaID.CRIOPRESERVACION] < COSTOS_TECNOLOGIA[TecnologiaID.CAMARA_B]
    assert barata.puntos_desarrollo_tecnologico == cara.puntos_desarrollo_tecnologico == 1


def test_el_termino_nunca_baja() -> None:
    """
    A diferencia de Variedad -- que pierde un escalon cuando el Simposio Tecnico
    saca un horneado del archivo -- nada desinstala una mejora: `Technologies`
    no tiene inversa de `activar`. La asimetria es deliberada, no un descuido.
    """
    jugador = _jugador()
    anteriores = []
    for tecnologia in TecnologiaID:
        jugador.tecnologias.activar(tecnologia)
        anteriores.append(jugador.puntos_desarrollo_tecnologico)
    assert anteriores == sorted(anteriores)
    assert not hasattr(jugador.tecnologias, "desactivar")


# ---------------------------------------------------------------------------
# El desglose
# ---------------------------------------------------------------------------

def test_ocupa_el_hueco_5_justo_detras_de_variedad() -> None:
    """El orden de insercion es el orden de presentacion en todos los
    consumidores (RankingView.vue, RULEBOOK 11.2): los dos terminos de AMPLITUD
    van juntos."""
    claves = list(_jugador().desglose_maestria)
    assert claves.index(CLAVE) == 4
    assert claves[claves.index(CLAVE) - 1] == "Variedad de Recetas"


def test_el_desglose_sigue_sumando_los_puntos_finales() -> None:
    jugador = _jugador()
    jugador.tecnologias.activar(TecnologiaID.INCUBADORA)
    jugador.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    jugador.monedas = 12
    jugador.reserva_agua = 4

    desglose = jugador.desglose_maestria
    assert desglose[CLAVE] == 3
    assert sum(desglose.values()) == jugador.puntos_maestria_final


def test_equiparse_puntua_frente_a_no_equiparse() -> None:
    equipado, pelado = _jugador("Equipado"), _jugador("Pelado")
    for tecnologia in TecnologiaID:
        equipado.tecnologias.activar(tecnologia)

    assert equipado.puntos_maestria_final - pelado.puntos_maestria_final == 10


# ---------------------------------------------------------------------------
# Viaje al cliente
# ---------------------------------------------------------------------------

def test_la_vista_envia_el_termino_y_el_recuento_es_derivable() -> None:
    """
    El termino viaja dentro del desglose; el RECUENTO no necesita campo propio,
    a diferencia de `recetas_distintas_horneadas`, porque `tecnologias` ya viaja
    como cuatro booleanos y MiTablero.vue los cuenta.
    """
    sesion = _sesion_iniciada()
    jugador = sesion.engine.players[0]
    jugador.tecnologias.activar(TecnologiaID.CAMARA_B)
    jugador.tecnologias.activar(TecnologiaID.CRIOPRESERVACION)

    datos_jugador = game_state_view(sesion)["players"][0]

    assert datos_jugador["desglose_maestria"][CLAVE] == 3
    assert sum(datos_jugador["tecnologias"].values()) == 2
    assert sum(datos_jugador["desglose_maestria"].values()) == datos_jugador["puntos_maestria_final"]
