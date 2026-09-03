"""
tests/test_recetas_grado.py -- los tres grados de receta (Basica / Intermedia /
Avanzada) definidos por las harinas que la carta imprime.

El grado dejo de ser una etiqueta escrita a mano: lo deriva
`_grado_desde_harinas` del reparto de harinas, y `Recipe.__post_init__` verifica
que el campo `grado` coincida. Cuatro cosas que este archivo existe para fijar,
porque cada una es un sitio donde el diseno se puede deshacer en silencio:

  1. La derivacion misma: Blanca 100 -> Basica, especial 100 -> Avanzada,
     dos tipos distintos 50/50 -> Intermedia. Las dos formas legales (100 y
     50+50) son exactamente las dos que la Bolsa de Harinas sabe vender.
  2. Una carta mal etiquetada revienta al CONSTRUIRSE. Como RECIPE_CATALOG es
     una constante de nivel de modulo, eso significa que revienta en
     `import models` -- nunca a mitad de partida ni al renderizar.
  3. Las bandas de puntos por grado no se solapan (9-12 / 13-16 / 17-20). Sin
     este test, "Intermedia" vuelve a ser decoracion en cuanto alguien anada
     una carta.
  4. La Accion B cobra TODAS las harinas impresas. Ninguna receta esta
     restringida por tecnologia: `Recipe` ya no tiene donde escribirlo.
"""
from __future__ import annotations

from collections import Counter
from typing import Tuple

import pytest

from actions import ActionManager
from bootstrap import create_game
from engine import GameEngine, Market
from exceptions import MissingResourceError, RuleViolationError
from models import (
    COPIAS_POR_GRADO,
    Environment,
    Grado,
    Player,
    HARINAS_ESPECIALES,
    RECIPE_CATALOG,
    Recipe,
    TOTAL_MAZO_RECETAS,
    TecnologiaID,
    Technologies,
    TipoHarina,
    _grado_desde_harinas,
    build_recipe_deck,
    get_recetas_avanzadas,
    get_recetas_basicas,
    get_recetas_intermedias,
    seleccionar_receta_inicial,
)

BANDAS_PUNTOS = {
    Grado.BASICA: (9, 12),
    Grado.INTERMEDIA: (13, 16),
    Grado.AVANZADA: (17, 20),
}


# ===========================================================================
# 1. La derivacion del grado a partir de las harinas
# ===========================================================================


def test_una_bolsa_de_blanca_es_basica() -> None:
    assert _grado_desde_harinas(((TipoHarina.BLANCA, 100),)) is Grado.BASICA


@pytest.mark.parametrize("especial", HARINAS_ESPECIALES)
def test_una_bolsa_de_harina_especial_es_avanzada(especial: TipoHarina) -> None:
    assert _grado_desde_harinas(((especial, 100),)) is Grado.AVANZADA


def test_dos_medias_bolsas_distintas_son_intermedia() -> None:
    harinas = ((TipoHarina.BLANCA, 50), (TipoHarina.CENTENO, 50))
    assert _grado_desde_harinas(harinas) is Grado.INTERMEDIA


def test_la_blanca_nunca_es_especial() -> None:
    """La Blanca es el producto comun: es lo que impide que una Basica sea Avanzada."""
    assert TipoHarina.BLANCA not in HARINAS_ESPECIALES
    assert set(HARINAS_ESPECIALES) == {TipoHarina.CENTENO, TipoHarina.INTEGRAL}


@pytest.mark.parametrize(
    "harinas",
    [
        pytest.param(((TipoHarina.BLANCA, 90), (TipoHarina.CENTENO, 10)), id="reparto_90_10"),
        pytest.param(((TipoHarina.BLANCA, 50),), id="una_sola_media_bolsa"),
        pytest.param(((TipoHarina.CENTENO, 50), (TipoHarina.CENTENO, 50)), id="tipo_repetido"),
        pytest.param(
            ((TipoHarina.BLANCA, 34), (TipoHarina.CENTENO, 33), (TipoHarina.INTEGRAL, 33)),
            id="tres_harinas",
        ),
        pytest.param((), id="sin_harinas"),
    ],
)
def test_repartos_ilegales_no_tienen_grado(harinas) -> None:
    """
    Un reparto que la Bolsa no sabe vender no es "otro grado": es un error.
    La Bolsa solo vende bolsa entera (10 tokens) y media bolsa (5); no existe
    un primitivo de compra por token suelto que haga pagable un 90/10.
    """
    with pytest.raises(ValueError):
        _grado_desde_harinas(harinas)


# ===========================================================================
# 2. El grado impreso no puede mentir
# ===========================================================================


def _receta_de_prueba(**overrides) -> Recipe:
    """Construye una Recipe valida, con los campos indicados sobrescritos."""
    campos = dict(
        id="carta_de_prueba",
        nombre="Carta de Prueba",
        grado=Grado.BASICA,
        harinas=((TipoHarina.BLANCA, 100),),
        hidratacion_pct=60,
        tokens_agua=12,
        acidez_diana=(3,),
        bono_sabor_pts=3,
        zona_crecimiento=(1, 5),
        zona_pre_fermento=(6, 10),
        zona_optima=(11, 15),
        zona_colapso=(16, 20),
        puntos_pre_fermento=4,
        puntos_optimos=10,
        penalizacion_colapso=-2,
        monedas_pre_fermento=13,
        monedas_optima=17,
        monedas_colapso=11,
    )
    campos.update(overrides)
    return Recipe(**campos)


def test_una_receta_bien_etiquetada_se_construye() -> None:
    receta = _receta_de_prueba(
        grado=Grado.INTERMEDIA,
        harinas=((TipoHarina.BLANCA, 50), (TipoHarina.INTEGRAL, 50)),
    )
    assert receta.grado is Grado.INTERMEDIA


def test_grado_que_no_coincide_con_las_harinas_revienta_al_construir() -> None:
    """
    El caso concreto que motivo la regla: una carta de Blanca 100 etiquetada
    'Avanzada' (asi estaban Pizza, Brioche y Panettone antes del cambio).
    """
    with pytest.raises(ValueError, match="Avanzada"):
        _receta_de_prueba(grado=Grado.AVANZADA)


def test_el_error_de_etiquetado_nombra_la_carta_y_las_harinas() -> None:
    with pytest.raises(ValueError) as excinfo:
        _receta_de_prueba(id="pan_mentiroso", grado=Grado.INTERMEDIA)
    mensaje = str(excinfo.value)
    assert "pan_mentiroso" in mensaje
    assert "Blanca 100%" in mensaje


def test_reparto_que_no_suma_100_revienta_al_construir() -> None:
    with pytest.raises(ValueError):
        _receta_de_prueba(harinas=((TipoHarina.BLANCA, 60),))


# ===========================================================================
# 3. El catalogo maestro cumple sus propias reglas
# ===========================================================================


def test_el_catalogo_tiene_cuatro_cartas_por_grado() -> None:
    """
    Cuatro Basicas y no tres: `bootstrap.create_game` reparte una Basica distinta
    por jugador y ciclaba `i % len` con solo tres, dando al jugador 4 una copia
    de la del jugador 1.
    """
    assert len(RECIPE_CATALOG) == 12
    assert len(get_recetas_basicas()) == 4
    assert len(get_recetas_intermedias()) == 4
    assert len(get_recetas_avanzadas()) == 4


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_cada_carta_puntua_dentro_de_la_banda_de_su_grado(receta: Recipe) -> None:
    minimo, maximo = BANDAS_PUNTOS[receta.grado]
    assert minimo <= receta.puntos_optimos <= maximo


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_cada_carta_pide_exactamente_una_bolsa_de_harina(receta: Recipe) -> None:
    assert sum(receta.requisito_harina.values()) == 100


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_tokens_agua_es_la_hidratacion_redondeada_hacia_arriba(receta: Recipe) -> None:
    """RECIPE_DATABASE.md: tokens_agua = ceil(hidratacion_pct / 5)."""
    assert receta.tokens_agua == -(-receta.hidratacion_pct // 5)


def test_requisito_harina_usa_las_mismas_claves_que_la_reserva_del_jugador() -> None:
    """
    La simetria de forma es lo que permite que validar y cobrar sean un unico
    bucle en la Accion B, en vez de dos ramas segun el numero de harinas.
    """
    claves_reserva = {t.value for t in TipoHarina}
    for receta in RECIPE_CATALOG.values():
        assert set(receta.requisito_harina) <= claves_reserva


def test_ninguna_receta_esta_restringida_por_tecnologia() -> None:
    """
    La regla es estructural, no una convencion: `Recipe` ya no tiene donde
    escribir una puerta tecnologica, asi que ninguna carta puede tenerla.
    """
    assert not hasattr(Recipe, "__annotations__") or (
        "req_tecnologico" not in Recipe.__annotations__
    )
    for receta in RECIPE_CATALOG.values():
        assert not hasattr(receta, "req_tecnologico")


def test_el_mercado_puede_repartir_los_tres_grados() -> None:
    """
    Guardarrail: el mazo del mercado se construia como `avanzadas + basicas`, asi
    que al pasar Pizza/Brioche/Panettone a Intermedias el escalon medio entero
    quedo fuera del mazo -- invisible, sin que ningun test fallara. Cada carta
    del catalogo tiene que poder llegar a la mesa.
    """
    market = Market.crear_inicial()
    en_juego = [r for r in market.recetas_visibles if r is not None] + market.mazo_recetas

    assert {r.id for r in en_juego} == set(RECIPE_CATALOG)
    assert {r.grado for r in en_juego} == set(Grado)


def test_el_mazo_del_mercado_son_las_36_cartas_fisicas() -> None:
    """
    El mazo no es un ejemplar por protocolo: son las copias que imprime
    RULEBOOK.md §12 (4 por Basica, 3 por Intermedia, 2 por Avanzada). La escasez
    de las Avanzadas es una barrera independiente de su precio.
    """
    market = Market.crear_inicial()
    en_juego = [r for r in market.recetas_visibles if r is not None] + market.mazo_recetas

    assert len(en_juego) == TOTAL_MAZO_RECETAS == 36
    conteo = Counter(r.grado for r in en_juego)
    assert conteo[Grado.BASICA] == 16
    assert conteo[Grado.INTERMEDIA] == 12
    assert conteo[Grado.AVANZADA] == 8


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_cada_protocolo_aporta_las_copias_de_su_grado(receta: Recipe) -> None:
    assert build_recipe_deck().count(receta) == COPIAS_POR_GRADO[receta.grado]


def test_build_recipe_deck_vigila_la_integridad_del_catalogo() -> None:
    """El assert de las 36 cartas es lo que rompe si alguien anade un 13o protocolo."""
    assert len(build_recipe_deck()) == TOTAL_MAZO_RECETAS


def test_la_basica_repartida_sale_del_mazo_del_mercado() -> None:
    """
    RULEBOOK.md §3.5: la Basica que va a la Carpeta inicial se retira del mazo
    ANTES de barajarlo y revelar la exposicion, no despues. Se retira UNA copia
    por jugador, no el protocolo entero -- con 4 copias por Basica, quitar las
    cuatro dejaria ese protocolo fuera del mercado en una partida a 4 jugadores.

    El orden es lo que hace la retirada segura: con el mazo barajado en una sola
    baraja, una Basica puede salir en las 4 cartas visibles, asi que retirarla
    del mazo despues de revelar podria no encontrar ninguna copia que quitar.
    """
    engine = create_game(["Alba", "Bruno", "Cora", "Dani"])
    market = engine.market
    en_juego = [r for r in market.recetas_visibles if r is not None] + market.mazo_recetas

    assert len(en_juego) == TOTAL_MAZO_RECETAS - 4
    for player in engine.players:
        repartida = player.carpeta_proyectos[0]
        assert repartida.grado is Grado.BASICA
        assert en_juego.count(repartida) == COPIAS_POR_GRADO[Grado.BASICA] - 1


def test_la_receta_inicial_siempre_es_basica() -> None:
    for _ in range(20):
        assert seleccionar_receta_inicial().grado is Grado.BASICA


# ===========================================================================
# 4. La Accion B cobra las harinas impresas
# ===========================================================================


def _preparar(receta: Recipe) -> Tuple[GameEngine, ActionManager, Player]:
    """Motor de dos jugadores con el jugador activo surtido para iniciar `receta`."""
    engine = GameEngine(
        players=[
            Player.crear_dia_1("Alba", get_recetas_basicas()[0]),
            Player.crear_dia_1("Bruno", get_recetas_basicas()[1]),
        ],
        environment=Environment.crear_inicial(),
        market=Market.crear_inicial(),
    )
    manager = ActionManager(engine)
    player = engine.players[0]
    player.puntos_accion = 2
    player.vitalidad = 3
    player.dados_inoculo = 3
    player.carpeta_proyectos = [receta]
    player.reserva_agua = receta.tokens_agua + 5
    for tipo, pct in receta.requisito_harina.items():
        player.reserva_harina[tipo] = pct
    return engine, manager, player


def test_accion_B_cobra_media_bolsa_de_cada_tipo_en_una_intermedia() -> None:
    receta = get_recetas_intermedias()[0]
    _, manager, player = _preparar(receta)

    manager.accion_B_iniciar_receta(player, receta)

    assert len(receta.requisito_harina) == 2
    for tipo in receta.requisito_harina:
        assert player.reserva_harina[tipo] == 0


def test_accion_B_rechaza_una_intermedia_con_una_sola_de_las_dos_mitades() -> None:
    receta = get_recetas_intermedias()[0]
    _, manager, player = _preparar(receta)
    faltante = list(receta.requisito_harina)[1]
    player.reserva_harina[faltante] = 0

    with pytest.raises(MissingResourceError, match=faltante):
        manager.accion_B_iniciar_receta(player, receta)

    # Fail-fast: la mitad que si tenia sigue intacta y no se gasto PA.
    presente = list(receta.requisito_harina)[0]
    assert player.reserva_harina[presente] == receta.requisito_harina[presente]
    assert player.puntos_accion == 2


def test_accion_B_nombra_las_dos_harinas_que_faltan_no_solo_la_primera() -> None:
    """Con una Intermedia, saber que falta 'una' harina no dice cual comprar."""
    receta = get_recetas_intermedias()[0]
    _, manager, player = _preparar(receta)
    for tipo in receta.requisito_harina:
        player.reserva_harina[tipo] = 0

    with pytest.raises(MissingResourceError) as excinfo:
        manager.accion_B_iniciar_receta(player, receta)

    for tipo in receta.requisito_harina:
        assert tipo in str(excinfo.value)




