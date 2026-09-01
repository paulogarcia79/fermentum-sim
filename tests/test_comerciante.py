"""
tests/test_comerciante.py -- la quinta tecnologia de laboratorio: mejores
condiciones de COMPRA en la Accion C (actions.DESCUENTO_COMERCIANTE,
RULEBOOK §10).

Las cuatro mejoras anteriores apuntan todas a la mitad biologica del juego (la
fermentacion y lo que puntua); Comerciante es la primera que apunta a la
economica. Lo que este fichero fija son las tres reglas que la hacen sana en vez
de meramente generosa, y que son justo las que un reajuste futuro podria romper
sin que nada mas se queje:

  · **Solo compras.** Un beneficio en los dos sentidos convertiria el ciclo
    comprar->vender en una bomba de Monedas: en Blanca la horquilla entre Compra
    y Venta es de UNA sola Moneda, asi que descontar la compra ya la iguala. El
    test de arbitraje de abajo es el guardarrail de esa cuenta.
  · **Suelo de 1**, nunca 0. Una compra gratis moveria el visor sin coste.
  · **El visor se mueve igual.** Una transaccion es una senal de mercado con
    independencia de lo que se pago por ella -- lo mismo que ya vale para media
    bolsa frente a una entera.

Y una cuarta cosa, que no es una regla sino una propiedad estructural: la
puntuacion (`puntos_desarrollo_tecnologico`) llego a cinco escalones sin tocar
la formula, porque la curva nunca estuvo topada a mano. Eso vive en
tests/test_desarrollo_tecnologico.py; aqui solo se comprueba que el recuento la
alcanza.
"""
from __future__ import annotations

import random

import pytest

from actions import (
    ActionManager,
    COSTOS_TECNOLOGIA,
    DESCUENTO_COMERCIANTE,
    RECURSO_MOLINO,
)
from bootstrap import create_game
from engine import (
    GameEngine,
    PRECIO_AGUA,
    PRECIO_CONTRATO_MOLINO,
    PRECIO_RECETA,
    PRECIOS_HARINA,
    POSICION_HARINA_MIN,
)
from exceptions import RuleViolationError
from models import Player, TecnologiaID, TipoHarina


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _dia_iniciado():
    """Motor + manager + los dos jugadores, con el dia ya abierto."""
    engine = _motor()
    engine.iniciar_dia()
    return engine, ActionManager(engine), engine.players[0], engine.players[1]


def _con_comerciante(jugador: Player) -> Player:
    jugador.tecnologias.activar(TecnologiaID.COMERCIANTE)
    return jugador


# ---------------------------------------------------------------------------
# El descuento, compra a compra
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tipo", list(TipoHarina))
@pytest.mark.parametrize("operacion", ["comprar", "comprar_media"])
def test_toda_compra_de_harina_cuesta_una_moneda_menos(tipo, operacion) -> None:
    engine, manager, con, sin = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = sin.monedas = 40

    transaccion = [{"tipo_recurso": tipo.value, "operacion": operacion}]
    manager.accion_C_visitar_mercado(sin, transaccion)
    pagado_sin = 40 - sin.monedas

    # El visor se movio con la compra del primero, asi que el segundo compra
    # desde la posicion nueva: se compara contra SU propio precio impreso.
    posicion = engine.market.posiciones_harina[tipo.value]
    entero = PRECIOS_HARINA[tipo]["compra"][posicion - 1]
    impreso = entero if operacion == "comprar" else -(-entero // 2)

    manager.accion_C_visitar_mercado(con, transaccion)
    pagado_con = 40 - con.monedas

    assert pagado_sin > 0
    assert pagado_con == max(1, impreso - DESCUENTO_COMERCIANTE)


@pytest.mark.parametrize("lote", [10, 30, 60, 100])
def test_todo_lote_de_agua_cuesta_una_moneda_menos(lote) -> None:
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = 40
    impreso = PRECIO_AGUA[engine.environment.temperatura_actual][lote]

    manager.accion_C_visitar_mercado(
        con, [{"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": lote}]
    )

    assert 40 - con.monedas == max(1, impreso - DESCUENTO_COMERCIANTE)


@pytest.mark.parametrize("tipo", list(TipoHarina))
def test_firmar_el_molino_cuesta_una_moneda_menos(tipo) -> None:
    _, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = 40

    manager.accion_C_visitar_mercado(
        con,
        [
            {
                "tipo_recurso": RECURSO_MOLINO,
                "operacion": "contratar",
                "tipo_harina": tipo.value,
            }
        ],
    )

    assert con.contrato_molino == tipo.value
    assert 40 - con.monedas == max(1, PRECIO_CONTRATO_MOLINO[tipo] - DESCUENTO_COMERCIANTE)


def test_el_descuento_se_aplica_a_cada_transaccion_de_la_visita() -> None:
    """No es «1 Moneda por visita»: una visita con tres compras ahorra tres."""
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = 60
    temp = engine.environment.temperatura_actual
    posicion = engine.market.posiciones_harina["Blanca"]

    impreso = (
        PRECIOS_HARINA[TipoHarina.BLANCA]["compra"][posicion - 1]
        + PRECIO_AGUA[temp][30]
        + PRECIO_CONTRATO_MOLINO[TipoHarina.CENTENO]
    )

    manager.accion_C_visitar_mercado(
        con,
        [
            {"tipo_recurso": "Blanca", "operacion": "comprar"},
            {"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": 30},
            {
                "tipo_recurso": RECURSO_MOLINO,
                "operacion": "contratar",
                "tipo_harina": "Centeno",
            },
        ],
    )

    assert 60 - con.monedas == impreso - 3 * DESCUENTO_COMERCIANTE


# ---------------------------------------------------------------------------
# El suelo de 1 Moneda
# ---------------------------------------------------------------------------

def test_una_compra_nunca_baja_de_una_moneda() -> None:
    """
    Media bolsa de Blanca en la posicion 1 cuesta 1 Moneda impresa (⌈2/2⌉), asi
    que sin suelo el Comerciante la tendria gratis -- y con ella moveria el visor
    sin gastar nada, que es un empujon ilimitado del mercado ajeno.
    """
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    engine.market.posiciones_harina["Blanca"] = POSICION_HARINA_MIN
    con.monedas = 10

    impreso = -(-PRECIOS_HARINA[TipoHarina.BLANCA]["compra"][0] // 2)
    assert impreso - DESCUENTO_COMERCIANTE == 0, "el caso deja de ser el limite"

    manager.accion_C_visitar_mercado(
        con, [{"tipo_recurso": "Blanca", "operacion": "comprar_media"}]
    )

    assert 10 - con.monedas == 1


def test_el_agua_mas_barata_sigue_costando_una_moneda() -> None:
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    engine.environment.temperatura_actual = 10  # lote de 10% -> 1 Moneda impresa
    con.monedas = 10

    assert PRECIO_AGUA[10][10] == 1

    manager.accion_C_visitar_mercado(
        con, [{"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": 10}]
    )

    assert 10 - con.monedas == 1


# ---------------------------------------------------------------------------
# Lo que NO toca
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tipo", list(TipoHarina))
@pytest.mark.parametrize("operacion", ["vender", "vender_media"])
def test_las_ventas_cobran_exactamente_lo_mismo(tipo, operacion) -> None:
    engine, manager, con, sin = _dia_iniciado()
    _con_comerciante(con)
    for jugador in (con, sin):
        jugador.monedas = 0
        jugador.reserva_harina[tipo.value] = 100

    manager.accion_C_visitar_mercado(con, [{"tipo_recurso": tipo.value, "operacion": operacion}])
    # Vender movio el visor hacia el extremo barato, asi que se devuelve a su
    # sitio antes de la venta de control: lo que se compara es el descuento, no
    # el efecto de mercado de la primera venta.
    engine.market.posiciones_harina[tipo.value] += 1
    manager.accion_C_visitar_mercado(sin, [{"tipo_recurso": tipo.value, "operacion": operacion}])

    assert con.monedas == sin.monedas


@pytest.mark.parametrize("tipo", list(TipoHarina))
@pytest.mark.parametrize("posicion", [1, 2, 3, 4, 5])
def test_el_ciclo_comprar_vender_gana_como_mucho_una_moneda(tipo, posicion) -> None:
    """
    Las 15 celdas del ciclo comprar->vender, que es la cuenta que el disenno
    acepta a ojos abiertos (ver actions.DESCUENTO_COMERCIANTE).

    Lo contraintuitivo: comprar SUBE el visor una casilla, asi que la venta
    posterior cobra el precio de la casilla siguiente. En Blanca la horquilla
    Compra-Venta es de 1 Moneda y el visor se mueve 1, de modo que los dos se
    cancelan EXACTAMENTE y la ida y vuelta ya era de saldo cero sin ninguna
    tecnologia. Con el descuento pasa a +1 en Blanca (0 en Integral, -1 en
    Centeno). No lo cierra el precio sino el espacio de accion: la Regla de
    Exclusividad impide hacerlo en una visita y el espacio C se agota una vez al
    dia, asi que ese +1 cuesta DOS dias de mercado.

    Si algun dia la Bolsa deja de moverse una casilla por transaccion, este test
    es el que lo dira.
    """
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    engine.market.posiciones_harina[tipo.value] = posicion
    con.monedas = 40
    con.reserva_harina[tipo.value] = 0
    monedas_antes = con.monedas

    # Dos visitas, porque comprar y vender la misma harina no cabe en una (Regla
    # de Exclusividad). En partida real serian dos DIAS: el espacio C es unico
    # por dia, y eso es justamente lo que acota la ganancia.
    manager.accion_C_visitar_mercado(con, [{"tipo_recurso": tipo.value, "operacion": "comprar"}])
    con.puntos_accion = 2
    con.acciones_pa_usadas_hoy.clear()
    manager.accion_C_visitar_mercado(con, [{"tipo_recurso": tipo.value, "operacion": "vender"}])

    ganancia = con.monedas - monedas_antes

    assert con.reserva_harina[tipo.value] == 0
    assert ganancia <= 1, "el ciclo nunca puede dar mas de 1 Moneda"
    if tipo is not TipoHarina.BLANCA or posicion == 5:
        assert ganancia <= 0, "solo Blanca por debajo del tope llega a +1"


@pytest.mark.parametrize("tipo", list(TipoHarina))
def test_el_visor_se_mueve_igual_con_descuento(tipo) -> None:
    """Una transaccion es una senal de mercado con independencia de su precio --
    el mismo argumento que ya vale para media bolsa frente a una entera."""
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = 40
    antes = engine.market.posiciones_harina[tipo.value]

    manager.accion_C_visitar_mercado(con, [{"tipo_recurso": tipo.value, "operacion": "comprar"}])

    assert engine.market.posiciones_harina[tipo.value] == min(5, antes + 1)


def test_no_toca_los_precios_de_las_otras_acciones() -> None:
    """
    El descuento vive DENTRO de la Accion C. Las recetas (G) y los Pliegues (E)
    tambien se pagan en Monedas y siguen costando lo impreso: Comerciante mejora
    tus condiciones en el mercado, no la economia entera. Si algun dia se decide
    lo contrario sera una decision, no un descuido.
    """
    engine, manager, con, _ = _dia_iniciado()
    _con_comerciante(con)
    con.monedas = 20
    con.carpeta_proyectos.clear()

    receta = engine.market.recetas_visibles[0]
    antes = con.monedas
    manager.accion_G_investigar_protocolo(con, 0)

    assert antes - con.monedas == PRECIO_RECETA[receta.grado]


# ---------------------------------------------------------------------------
# Instalarla (Accion D)
# ---------------------------------------------------------------------------

def test_se_instala_por_su_precio_en_datos() -> None:
    _, manager, jugador, _ = _dia_iniciado()
    jugador.datos_investigacion = 10

    manager.accion_D_implementar_mejora(jugador, TecnologiaID.COMERCIANTE)

    assert jugador.tecnologias.comerciante
    assert jugador.datos_investigacion == 10 - COSTOS_TECNOLOGIA[TecnologiaID.COMERCIANTE]


def test_no_se_instala_dos_veces() -> None:
    _, manager, jugador, _ = _dia_iniciado()
    jugador.datos_investigacion = 10
    manager.accion_D_implementar_mejora(jugador, TecnologiaID.COMERCIANTE)
    jugador.puntos_accion = 2
    jugador.acciones_pa_usadas_hoy.clear()

    with pytest.raises(RuleViolationError):
        manager.accion_D_implementar_mejora(jugador, TecnologiaID.COMERCIANTE)


def test_cuenta_como_la_quinta_mejora_del_desarrollo_tecnologico() -> None:
    """El recuento llega a 5 sin tocar la curva, que nunca estuvo topada."""
    jugador = Player(nombre="Alba")
    for tecnologia in TecnologiaID:
        jugador.tecnologias.activar(tecnologia)

    assert jugador.tecnologias.cantidad_instaladas == 5
    assert jugador.puntos_desarrollo_tecnologico == 15
