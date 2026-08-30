"""
tests/test_ampliacion_optima.py -- el Modulo Analitico ensancha la zona optima.

El Modulo perdio su unico trabajo real (abrir las recetas Avanzadas) al quitarse
las puertas tecnologicas, y lo que le quedaba -- +1 Dato solo en el centro exacto --
lo dejaba como una compra trampa: con un maximo de 5 horneados por partida habia
que clavar el centro unas tres veces solo para amortizar su precio. Ahora ensancha
la zona optima una casilla por lado y sube los Datos del horneado.

Lo que este archivo fija:

  1. Toda la aritmetica vive en `Recipe.zonas_efectivas`, y ninguna de las 12 cartas
     degenera al ampliarse (zona vacia o fuera del track 1-20).
  2. Ensanchar NO mueve el centro exacto: (a-n + b+n)//2 == (a+b)//2. La zona perdona
     mas, pero acertar el centro sigue costando lo mismo.
  3. La ampliacion se aplica en LOS CUATRO sitios que leen zonas -- puntos, monedas,
     datos y el gatillo de colapso de la Fase III. El colapso es el que carga el peso:
     si se olvida ahi, una masa colapsa pese a tener la mejora instalada.
  4. Es un efecto EN VIVO, no sellado en la masa: instalar el Modulo salva una masa
     que ya esta fermentando. Pero el HORNEADO si sella la ampliacion aplicada, o
     `zona_resultado` reetiquetaria despues como "baja" un horneado que fue optimo.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from engine import (
    AMPLIACION_OPTIMA_MODULO,
    DATOS_BAKE_CENTRO_EXACTO_BONUS,
    DATOS_BAKE_MODULO_BONUS,
    DATOS_BAKE_ZONA_OPTIMA,
    GameEngine,
    Market,
)
from models import (
    Environment,
    FermentationSlot,
    Player,
    RECIPE_CATALOG,
    Recipe,
    TecnologiaID,
    get_recetas_basicas,
)

TRACK_MAX = 20


def _motor() -> tuple[GameEngine, ActionManager, Player]:
    engine = GameEngine(
        players=[
            Player.crear_dia_1("Alba", get_recetas_basicas()[0]),
            Player.crear_dia_1("Bruno", get_recetas_basicas()[1]),
        ],
        environment=Environment.crear_inicial(),
        market=Market.crear_inicial(),
    )
    return engine, ActionManager(engine), engine.players[0]


def _masa(player: Player, receta_id: str, posicion: int) -> FermentationSlot:
    slot = FermentationSlot(
        recipe=RECIPE_CATALOG[receta_id],
        dado_inoculo=1,
        posicion_track=posicion,
        bono_sabor=False,
        acidez_inicial=1,
    )
    player.estaciones_fermentacion[0] = slot
    return slot


# ===========================================================================
# 1. La aritmetica de las zonas
# ===========================================================================


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_ninguna_carta_degenera_al_ampliarse(receta: Recipe) -> None:
    baja, optima, sobre = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
    for nombre, (inicio, fin) in (("baja", baja), ("optima", optima), ("sobre", sobre)):
        assert inicio <= fin, f"{receta.id}: zona {nombre} vacia"
        assert 1 <= inicio <= TRACK_MAX, f"{receta.id}: zona {nombre} fuera de track"
    assert baja[1] + 1 == optima[0], f"{receta.id}: hueco entre baja y optima"
    assert optima[1] + 1 == sobre[0], f"{receta.id}: hueco entre optima y sobre"


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_ampliacion_cero_devuelve_las_zonas_impresas(receta: Recipe) -> None:
    assert receta.zonas_efectivas(0) == (
        receta.zona_baja,
        receta.zona_optima,
        receta.zona_sobrefermentada,
    )


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_ampliar_no_mueve_el_centro_exacto(receta: Recipe) -> None:
    """(a - n + b + n) // 2 == (a + b) // 2, para cualquier n. Es un teorema."""
    _, optima, _ = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
    centro_impreso = (receta.zona_optima[0] + receta.zona_optima[1]) // 2
    assert (optima[0] + optima[1]) // 2 == centro_impreso
    assert receta.es_centro_exacto(centro_impreso)


def test_la_ampliacion_come_por_los_dos_lados() -> None:
    focaccia = RECIPE_CATALOG["focaccia"]
    assert focaccia.zonas_efectivas(0) == ((1, 9), (10, 14), (15, 20))
    assert focaccia.zonas_efectivas(1) == ((1, 8), (9, 15), (16, 20))
    # Una posicion que sin la mejora era zona baja, con ella es optima.
    assert not focaccia.esta_en_zona_optima(9)
    assert focaccia.esta_en_zona_optima(9, 1)
    # Y una que colapsaba, ya no.
    assert focaccia.esta_sobrefermentada(15)
    assert not focaccia.esta_sobrefermentada(15, 1)


# ===========================================================================
# 2. El engine aplica la ampliacion en los cuatro sitios
# ===========================================================================


def test_ampliacion_zona_optima_sigue_a_la_tecnologia() -> None:
    _, _, player = _motor()
    engine = _motor()[0]
    assert engine.ampliacion_zona_optima(player) == 0
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    assert engine.ampliacion_zona_optima(player) == AMPLIACION_OPTIMA_MODULO


def test_una_masa_que_colapsaria_sobrevive_con_el_modulo() -> None:
    """
    El sitio que carga el peso: el gatillo de colapso de la Fase III. Si se olvida
    de la ampliacion, la mejora no sirve de nada donde mas importa.
    """
    engine, _, player = _motor()
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    # La masa AVANZA antes de comprobarse: con temperatura 20 y dado 1 el avance
    # es 5, asi que 10 -> 15. Focaccia colapsa desde 15; con el Modulo, desde 16.
    _masa(player, "focaccia", 10)

    engine._avanzar_masas_jugador(player)

    assert player.archivo_colapsos == [], "colapso pese al Modulo instalado"
    assert player.estaciones_fermentacion[0] is not None


def test_la_misma_masa_si_colapsa_sin_el_modulo() -> None:
    engine, _, player = _motor()
    _masa(player, "focaccia", 10)  # tambien acaba en 15

    engine._avanzar_masas_jugador(player)

    assert len(player.archivo_colapsos) == 1
    assert player.estaciones_fermentacion[0] is None


def test_puntos_y_monedas_leen_la_zona_ampliada() -> None:
    engine, _, player = _motor()
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    focaccia = RECIPE_CATALOG["focaccia"]
    _masa(player, "focaccia", 9)  # zona baja impresa, optima con el Modulo

    registro = engine.resolver_horneado(player, 0)

    assert registro.puntos_base == focaccia.puntos_optimos
    assert registro.monedas_obtenidos == focaccia.monedas_optima


def test_sin_el_modulo_esa_misma_posicion_es_zona_baja() -> None:
    engine, _, player = _motor()
    focaccia = RECIPE_CATALOG["focaccia"]
    _masa(player, "focaccia", 9)

    registro = engine.resolver_horneado(player, 0)

    assert registro.puntos_base == focaccia.puntos_baja
    assert registro.monedas_obtenidos == focaccia.monedas_baja


# ===========================================================================
# 3. Los Datos del horneado: 1 / 2 / 3
# ===========================================================================


def test_datos_sin_modulo_en_zona_optima() -> None:
    engine, _, player = _motor()
    _masa(player, "focaccia", 10)
    assert engine.resolver_horneado(player, 0).datos_obtenidos == DATOS_BAKE_ZONA_OPTIMA


def test_datos_con_modulo_en_zona_optima_no_central() -> None:
    engine, _, player = _motor()
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    _masa(player, "focaccia", 10)  # optima, pero el centro es 12
    esperado = DATOS_BAKE_ZONA_OPTIMA + DATOS_BAKE_MODULO_BONUS
    assert engine.resolver_horneado(player, 0).datos_obtenidos == esperado


def test_datos_con_modulo_en_el_centro_exacto() -> None:
    engine, _, player = _motor()
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    _masa(player, "focaccia", 12)
    esperado = (
        DATOS_BAKE_ZONA_OPTIMA + DATOS_BAKE_MODULO_BONUS + DATOS_BAKE_CENTRO_EXACTO_BONUS
    )
    assert engine.resolver_horneado(player, 0).datos_obtenidos == esperado == 3


def test_el_centro_exacto_no_paga_extra_sin_el_modulo() -> None:
    engine, _, player = _motor()
    _masa(player, "focaccia", 12)
    assert engine.resolver_horneado(player, 0).datos_obtenidos == DATOS_BAKE_ZONA_OPTIMA


# ===========================================================================
# 4. En vivo al fermentar, sellada al hornear
# ===========================================================================


def test_instalar_el_modulo_afecta_a_una_masa_ya_en_marcha() -> None:
    """
    La ampliacion NO se sella en la masa como `modificador_incubadora`: se recalcula
    en cada resolucion, asi que comprar la mejora rescata lo que ya esta dentro.
    """
    engine, manager, player = _motor()
    _masa(player, "focaccia", 10)  # acaba en 15 y colapsaria esta noche
    player.datos_investigacion = 99
    player.puntos_accion = 2

    manager.accion_D_implementar_mejora(player, TecnologiaID.MODULO_ANALITICO)
    engine._avanzar_masas_jugador(player)

    assert player.archivo_colapsos == []


def test_el_horneado_sella_la_ampliacion_para_el_archivo() -> None:
    """
    Sin sellarla, `zona_resultado` se recalcularia contra las zonas IMPRESAS y
    archivaria para siempre como "baja" un horneado que puntuo como optimo.
    """
    engine, _, player = _motor()
    player.tecnologias.activar(TecnologiaID.MODULO_ANALITICO)
    _masa(player, "focaccia", 9)

    registro = engine.resolver_horneado(player, 0)

    assert registro.ampliacion_aplicada == AMPLIACION_OPTIMA_MODULO
    assert registro.zona_resultado == "optima"


def test_el_archivo_de_un_horneado_sin_modulo_no_lleva_ampliacion() -> None:
    engine, _, player = _motor()
    _masa(player, "focaccia", 9)

    registro = engine.resolver_horneado(player, 0)

    assert registro.ampliacion_aplicada == 0
    assert registro.zona_resultado == "baja"
