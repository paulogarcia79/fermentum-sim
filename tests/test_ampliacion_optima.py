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
from exceptions import RuleViolationError
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
    crecimiento, pre_fermento, optima, colapso = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
    for nombre, (inicio, fin) in (
        ("crecimiento", crecimiento), ("pre_fermento", pre_fermento),
        ("optima", optima), ("colapso", colapso),
    ):
        assert inicio <= fin, f"{receta.id}: zona {nombre} vacia"
        assert 1 <= inicio <= TRACK_MAX, f"{receta.id}: zona {nombre} fuera de track"
    assert crecimiento[1] + 1 == pre_fermento[0], f"{receta.id}: hueco crecimiento/pre-fermento"
    assert pre_fermento[1] + 1 == optima[0], f"{receta.id}: hueco pre-fermento/optima"
    assert optima[1] + 1 == colapso[0], f"{receta.id}: hueco optima/colapso"


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_ampliacion_cero_devuelve_las_zonas_impresas(receta: Recipe) -> None:
    assert receta.zonas_efectivas(0) == (
        receta.zona_crecimiento,
        receta.zona_pre_fermento,
        receta.zona_optima,
        receta.zona_colapso,
    )


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_ampliar_no_mueve_el_centro_exacto(receta: Recipe) -> None:
    """(a - n + b + n) // 2 == (a + b) // 2, para cualquier n. Es un teorema."""
    _, _, optima, _ = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
    centro_impreso = (receta.zona_optima[0] + receta.zona_optima[1]) // 2
    assert (optima[0] + optima[1]) // 2 == centro_impreso
    assert receta.es_centro_exacto(centro_impreso)


def test_la_ampliacion_come_por_los_dos_lados() -> None:
    focaccia = RECIPE_CATALOG["focaccia"]
    assert focaccia.zonas_efectivas(0) == ((1, 4), (5, 9), (10, 14), (15, 20))
    # El crecimiento NO se toca: la frontera de "ya se puede hornear" sigue en 5.
    assert focaccia.zonas_efectivas(1) == ((1, 4), (5, 8), (9, 15), (16, 20))
    # Una posicion que sin la mejora era zona baja, con ella es optima.
    assert not focaccia.esta_en_zona_optima(9)
    assert focaccia.esta_en_zona_optima(9, 1)
    # Y una que colapsaba, ya no.
    assert focaccia.esta_en_colapso(15)
    assert not focaccia.esta_en_colapso(15, 1)


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


def test_sin_el_modulo_esa_misma_posicion_es_pre_fermento() -> None:
    engine, _, player = _motor()
    focaccia = RECIPE_CATALOG["focaccia"]
    _masa(player, "focaccia", 9)

    registro = engine.resolver_horneado(player, 0)

    assert registro.puntos_base == focaccia.puntos_pre_fermento
    assert registro.monedas_obtenidos == focaccia.monedas_pre_fermento


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
    assert registro.zona_resultado == "pre_fermento"


# ===========================================================================
# 5. La zona de crecimiento: donde la masa todavia no es pan
# ===========================================================================


def test_la_posicion_0_no_pertenece_a_ninguna_zona_impresa() -> None:
    """
    Toda masa nace en la casilla 0 y ninguna carta imprime una zona que la incluya.
    Ese hueco es el que hacia falta cerrar.
    """
    for receta in RECIPE_CATALOG.values():
        assert receta.zona_crecimiento[0] == 1, f"{receta.id}: el crecimiento empieza en 1"


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_la_posicion_0_es_crecimiento_y_no_paga(receta: Recipe) -> None:
    """
    REGRESION del agujero que este cambio cierra. Antes, la casilla 0 no caia en
    ninguna zona y el `return` por defecto de _calcular_puntos_zona la pagaba como
    zona baja: Panettone daba 8 Puntos de Maestria y 13 Monedas por empezar una
    receta y hornearla el mismo dia, sin fermentar nada.
    """
    engine, _, _ = _motor()
    assert receta.esta_en_crecimiento(0)
    assert engine._calcular_puntos_zona(receta, 0, False) == 0
    assert engine._calcular_monedas_zona(receta, 0, False) == 0
    assert engine._calcular_datos_horneado(engine.players[0], receta, 0) == 0


def test_panettone_ya_no_paga_8_puntos_por_no_fermentar() -> None:
    """El caso concreto, escrito con sus numeros para que la regresion se lea."""
    engine, _, _ = _motor()
    panettone = RECIPE_CATALOG["panettone"]
    assert panettone.puntos_pre_fermento == 8, "si esto cambia, actualiza el numero"
    assert engine._calcular_puntos_zona(panettone, 0, False) == 0


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
@pytest.mark.parametrize("ampliacion", [0, AMPLIACION_OPTIMA_MODULO])
def test_cada_posicion_cae_en_exactamente_una_zona(receta: Recipe, ampliacion: int) -> None:
    """Exhaustividad y exclusividad sobre todo el track, incluida la casilla 0."""
    for posicion in range(0, TRACK_MAX + 1):
        pertenencias = [
            receta.esta_en_crecimiento(posicion, ampliacion),
            receta.esta_en_pre_fermento(posicion, ampliacion),
            receta.esta_en_zona_optima(posicion, ampliacion),
            receta.esta_en_colapso(posicion, ampliacion),
        ]
        assert sum(pertenencias) == 1, f"{receta.id} pos {posicion}: {pertenencias}"


def test_accion_F_rechaza_una_masa_en_crecimiento() -> None:
    engine, manager, player = _motor()
    receta = RECIPE_CATALOG["focaccia"]
    _masa(player, "focaccia", receta.zona_crecimiento[1])
    player.puntos_accion = 2

    with pytest.raises(RuleViolationError, match="Crecimiento"):
        manager.accion_F_hornear(player, 0)

    # Fail-fast: ni PA ni espacio ni la masa se tocan.
    assert player.puntos_accion == 2
    assert "F" not in player.acciones_pa_usadas_hoy
    assert player.estaciones_fermentacion[0] is not None


def test_accion_F_acepta_la_casilla_siguiente() -> None:
    engine, manager, player = _motor()
    receta = RECIPE_CATALOG["focaccia"]
    _masa(player, "focaccia", receta.zona_pre_fermento[0])
    player.puntos_accion = 2

    registro = manager.accion_F_hornear(player, 0)
    assert registro.zona_resultado == "pre_fermento"


def test_el_crecimiento_nunca_se_amplia() -> None:
    """
    La frontera de "ya se puede hornear" no puede moverse bajo los pies del jugador
    al instalar el Modulo Analitico a media fermentacion.
    """
    for receta in RECIPE_CATALOG.values():
        sin_modulo, *_ = receta.zonas_efectivas(0)
        con_modulo, *_ = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
        assert sin_modulo == con_modulo == receta.zona_crecimiento


def test_un_pre_fermento_demasiado_estrecho_no_se_construye() -> None:
    """
    Se vaciaria al ampliarse la zona optima. La validacion vive en __post_init__,
    asi que una carta asi aborta `import models` en vez de romper a mitad de partida.
    """
    from tests.test_recetas_grado import _receta_de_prueba

    with pytest.raises(ValueError, match="pre-fermento"):
        _receta_de_prueba(
            zona_crecimiento=(1, 9),
            zona_pre_fermento=(10, 10),  # una sola casilla
            zona_optima=(11, 15),
            zona_colapso=(16, 20),
        )


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_el_pre_fermento_sobrevive_al_modulo(receta: Recipe) -> None:
    _, pre_fermento, _, _ = receta.zonas_efectivas(AMPLIACION_OPTIMA_MODULO)
    assert pre_fermento[0] <= pre_fermento[1]
