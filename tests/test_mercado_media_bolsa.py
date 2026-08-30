"""
tests/test_mercado_media_bolsa.py -- la media bolsa de la Accion C (5 tokens,
50%): compra a la MITAD REDONDEADA HACIA ARRIBA del precio visible, venta a la
mitad redondeada hacia ABAJO.

El redondeo es la pieza de diseno que hace que media bolsa no sea un arbitraje:
con precios impares sale peor por token que la bolsa entera. Por eso se
comprueba celda a celda (3 harinas x 5 posiciones x 2 direcciones) en vez de
por muestreo -- un off-by-one en una sola casilla convertiria esa casilla en
dinero gratis, y es exactamente el tipo de fallo que un par de asserts sueltos
no ven.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from engine import (
    CANTIDAD_MEDIA_BOLSA_PCT,
    GameEngine,
    Market,
    PRECIOS_HARINA,
    POSICION_HARINA_MAX,
    POSICION_HARINA_MIN,
)
from exceptions import InvalidActionError, MissingResourceError
from models import Environment, Player, RECIPE_CATALOG, TipoHarina

CELDAS = [
    (tipo, posicion)
    for tipo in TipoHarina
    for posicion in range(POSICION_HARINA_MIN, POSICION_HARINA_MAX + 1)
]


def _partida() -> tuple[GameEngine, ActionManager, Player, Market]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    market = Market.crear_inicial()
    engine = GameEngine([p1, p2], Environment.crear_inicial(), market)
    # Los PA se reparten al iniciar el dia (Fase I); aqui se llama a la accion
    # directamente, asi que hay que darselos a mano.
    p1.puntos_accion = 2
    return engine, ActionManager(engine), p1, market


# ---------------------------------------------------------------------------
# Precio derivado: las 30 celdas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tipo,posicion", CELDAS)
def test_compra_media_redondea_hacia_arriba(tipo: TipoHarina, posicion: int) -> None:
    _, _, _, market = _partida()
    market.posiciones_harina[tipo] = posicion
    entero = PRECIOS_HARINA[tipo]["compra"][posicion - 1]

    media = market.precio_compra_harina(tipo, CANTIDAD_MEDIA_BOLSA_PCT)

    assert media == -(-entero // 2)
    # Nunca un descuento: media bolsa cuesta al menos la mitad exacta.
    assert media * 2 >= entero


@pytest.mark.parametrize("tipo,posicion", CELDAS)
def test_venta_media_redondea_hacia_abajo(tipo: TipoHarina, posicion: int) -> None:
    _, _, _, market = _partida()
    market.posiciones_harina[tipo] = posicion
    entero = PRECIOS_HARINA[tipo]["venta"][posicion - 1]

    media = market.precio_venta_harina(tipo, CANTIDAD_MEDIA_BOLSA_PCT)

    assert media == entero // 2
    # Nunca una prima: dos medias ventas jamas superan una entera.
    assert media * 2 <= entero


def test_venta_media_de_blanca_en_posicion_1_paga_cero() -> None:
    """La unica celda degenerada de la tabla, y es legal a proposito."""
    engine, manager, p1, market = _partida()
    market.posiciones_harina[TipoHarina.BLANCA] = POSICION_HARINA_MIN
    p1.reserva_harina["Blanca"] = 100
    p1.monedas = 7

    manager.accion_C_visitar_mercado(
        p1, transacciones=[{"tipo_recurso": "Blanca", "operacion": "vender_media"}]
    )

    assert p1.monedas == 7
    assert p1.reserva_harina["Blanca"] == 50


def test_cantidad_invalida_es_rechazada() -> None:
    _, _, _, market = _partida()
    with pytest.raises(InvalidActionError):
        market.precio_compra_harina(TipoHarina.BLANCA, 25)


# ---------------------------------------------------------------------------
# El visor reacciona igual a media bolsa que a una entera
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operacion,delta", [("comprar_media", 1), ("vender_media", -1)]
)
def test_media_bolsa_mueve_el_visor_una_casilla(operacion: str, delta: int) -> None:
    engine, manager, p1, market = _partida()
    market.posiciones_harina[TipoHarina.CENTENO] = 3
    p1.monedas = 20
    p1.reserva_harina["Centeno"] = 100

    manager.accion_C_visitar_mercado(
        p1, transacciones=[{"tipo_recurso": "Centeno", "operacion": operacion}]
    )

    assert market.posiciones_harina[TipoHarina.CENTENO] == 3 + delta


# ---------------------------------------------------------------------------
# La media bolsa se integra con el resto de reglas de la visita
# ---------------------------------------------------------------------------


def test_exclusividad_sigue_siendo_por_tipo_de_recurso() -> None:
    """Dos medias NO se apilan en una bolsa entera dentro de la misma visita."""
    engine, manager, p1, _ = _partida()
    p1.monedas = 20

    with pytest.raises(InvalidActionError):
        manager.accion_C_visitar_mercado(
            p1,
            transacciones=[
                {"tipo_recurso": "Blanca", "operacion": "comprar_media"},
                {"tipo_recurso": "Blanca", "operacion": "comprar_media"},
            ],
        )


def test_media_venta_puede_financiar_una_media_compra() -> None:
    """Fail-fast sobre saldos simulados: el orden dado importa, no el signo."""
    engine, manager, p1, market = _partida()
    market.posiciones_harina[TipoHarina.CENTENO] = 5  # venta 7 -> media 3
    market.posiciones_harina[TipoHarina.BLANCA] = 1  # compra 2 -> media 1
    p1.monedas = 0
    p1.reserva_harina["Centeno"] = 100
    p1.reserva_harina["Blanca"] = 0

    manager.accion_C_visitar_mercado(
        p1,
        transacciones=[
            {"tipo_recurso": "Centeno", "operacion": "vender_media"},
            {"tipo_recurso": "Blanca", "operacion": "comprar_media"},
        ],
    )

    assert p1.monedas == 2  # +3 de la venta, -1 de la compra
    assert p1.reserva_harina["Centeno"] == 50
    assert p1.reserva_harina["Blanca"] == 50


def test_vender_media_sin_media_bolsa_falla_sin_tocar_estado() -> None:
    engine, manager, p1, _ = _partida()
    p1.reserva_harina["Integral"] = 40  # 4 tokens: no llega a media bolsa
    monedas_antes = p1.monedas
    pa_antes = p1.puntos_accion

    with pytest.raises(MissingResourceError):
        manager.accion_C_visitar_mercado(
            p1, transacciones=[{"tipo_recurso": "Integral", "operacion": "vender_media"}]
        )

    assert p1.reserva_harina["Integral"] == 40
    assert p1.monedas == monedas_antes
    assert p1.puntos_accion == pa_antes
