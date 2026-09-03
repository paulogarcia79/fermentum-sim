"""
tests/test_pedido_urgencia.py -- el Pedido de Urgencia entrega parcelas FIJAS.

El jugador elige QUE recurso quiere, nunca CUANTO. La mitad de harina ya era
fija (HARINA_PEDIDO_URGENCIA); la de agua no lo era: la accion aceptaba un
`agua_tokens_urgencia: int` sin tope que el cliente enviaba desde un
`<input type="number">` sin maximo. Como una receta pide entre 10 y 17 tokens
y un lote del 100% cuesta de 7 a 14 Monedas, 1 Dato compraba toda el agua de
la partida entera, y el unico freno era la penalizacion por desperdicio del
recuento final (-1 PM por cada 3 tokens sin usar).

Cuatro invariantes que este archivo existe para fijar:

  1. Las dos cantidades salen de sus constantes y no de un parametro. Si
     vuelve a colarse una cantidad en la firma o en el wire, estos tests
     dejan de tener sentido y hay que releer la regla, no ajustarlos.
  2. El discriminador `recurso` es exhaustivo y excluyente: nada fuera de
     {"harina", "agua"}, harina obligada a declarar tipo, agua obligada a NO
     declararlo.
  3. Fail-fast: un pedido rechazado no cobra el Dato ni entrega nada.
  4. El Pedido no emite ningun GameEvent. Es una accion de 0 PA, o sea que
     ocurre DENTRO de la ventana de deshacer, y `restaurar_checkpoint` repone
     el motor desde un pickle: un evento suyo haria encoger `engine.eventos`
     al deshacer y dejaria los punteros `since` / `Last-Event-ID` de los
     clientes por delante del servidor. Es el mismo invariante que protege
     `tests/test_avisos_accion.py`, visto desde el otro lado.
"""
from __future__ import annotations

import pytest

from actions import (
    ActionManager,
    AGUA_PEDIDO_URGENCIA,
    HARINA_PEDIDO_URGENCIA,
)
from engine import GameEngine, Market
from exceptions import InvalidActionError, MissingResourceError
from models import Environment, Player, RECIPE_CATALOG, TipoHarina
from server.commands import resolver_comando


def _partida() -> tuple[GameEngine, ActionManager, Player]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    engine = GameEngine([p1, p2], Environment.crear_inicial(), Market.crear_inicial())
    # Se llama a la accion directamente, sin pasar por la Fase I que reparte PA.
    p1.puntos_accion = 2
    p1.datos_investigacion = 5
    return engine, ActionManager(engine), p1


# ===========================================================================
# Las dos parcelas fijas
# ===========================================================================

def test_agua_entrega_la_cantidad_fija() -> None:
    _, manager, p1 = _partida()
    antes = p1.reserva_agua

    manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")

    assert p1.reserva_agua == antes + AGUA_PEDIDO_URGENCIA
    assert p1.datos_investigacion == 4, "el Pedido cuesta exactamente 1 Dato"
    assert p1.puntos_accion == 2, "el Pedido es de 0 PA"


def test_dos_pedidos_de_agua_suman_dos_parcelas() -> None:
    """No hay tope de usos: el limite es el Dato, no la accion (ACTIONS_REGISTRY
    §Pedido de Urgencia). Lo que ya no se puede es pedir una parcela mayor."""
    _, manager, p1 = _partida()
    antes = p1.reserva_agua

    manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")
    manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")

    assert p1.reserva_agua == antes + 2 * AGUA_PEDIDO_URGENCIA
    assert p1.datos_investigacion == 3


@pytest.mark.parametrize("tipo", list(TipoHarina))
def test_harina_entrega_media_bolsa_del_tipo_pedido(tipo: TipoHarina) -> None:
    _, manager, p1 = _partida()
    antes = dict(p1.reserva_harina)

    manager.accion_auxiliar_pedido_urgencia(p1, recurso="harina", harina=tipo)

    for clave, valor in p1.reserva_harina.items():
        esperado = antes[clave] + (HARINA_PEDIDO_URGENCIA if clave == tipo.value else 0)
        assert valor == esperado, f"la reserva de {clave} no cuadra"
    assert p1.reserva_agua == 0, "un pedido de harina no toca el agua"
    assert p1.datos_investigacion == 4


# ===========================================================================
# El discriminador
# ===========================================================================

@pytest.mark.parametrize(
    "kwargs",
    [
        {"recurso": "datos"},           # recurso inexistente
        {"recurso": "Agua"},            # sensible a mayusculas, a proposito
        {"recurso": ""},
        {"recurso": "harina"},          # harina sin declarar el tipo
        {"recurso": "agua", "harina": TipoHarina.BLANCA},  # agua con tipo
    ],
)
def test_pedidos_malformados_no_cobran_ni_entregan(kwargs) -> None:
    """Fail-fast: la validacion va ENTERA antes de la primera mutacion."""
    _, manager, p1 = _partida()
    harina_antes = dict(p1.reserva_harina)

    with pytest.raises(InvalidActionError):
        manager.accion_auxiliar_pedido_urgencia(p1, **kwargs)

    assert p1.datos_investigacion == 5, "un pedido rechazado no cobra el Dato"
    assert p1.reserva_agua == 0
    assert p1.reserva_harina == harina_antes


def test_sin_datos_no_hay_pedido() -> None:
    _, manager, p1 = _partida()
    p1.datos_investigacion = 0

    with pytest.raises(MissingResourceError):
        manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")

    assert p1.reserva_agua == 0


# ===========================================================================
# El camino por el wire (server/commands.py)
# ===========================================================================

def test_wire_agua_no_lleva_cantidad() -> None:
    engine, manager, p1 = _partida()

    resolver_comando(engine, manager, p1, "pedido_urgencia", {"recurso": "agua"})

    assert p1.reserva_agua == AGUA_PEDIDO_URGENCIA


def test_wire_harina_resuelve_el_enum() -> None:
    engine, manager, p1 = _partida()
    antes = p1.reserva_harina["Centeno"]

    resolver_comando(
        engine, manager, p1, "pedido_urgencia", {"recurso": "harina", "harina": "Centeno"}
    )

    assert p1.reserva_harina["Centeno"] == antes + HARINA_PEDIDO_URGENCIA


@pytest.mark.parametrize(
    "params",
    [
        {},                                        # sin recurso
        {"recurso": None},
        {"recurso": 6},                            # el viejo entero, por si vuelve
        {"recurso": "harina", "harina": "Espelta"},  # harina inexistente
    ],
)
def test_wire_rechaza_parametros_invalidos(params) -> None:
    engine, manager, p1 = _partida()

    with pytest.raises(InvalidActionError):
        resolver_comando(engine, manager, p1, "pedido_urgencia", params)

    assert p1.datos_investigacion == 5


# ===========================================================================
# El invariante de la ventana de deshacer
# ===========================================================================

def test_el_pedido_no_emite_eventos() -> None:
    """Ver la docstring del modulo: un GameEvent aqui romperia el deshacer."""
    engine, manager, p1 = _partida()
    antes = len(engine.eventos)

    manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")
    manager.accion_auxiliar_pedido_urgencia(p1, recurso="harina", harina=TipoHarina.BLANCA)

    assert len(engine.eventos) == antes
