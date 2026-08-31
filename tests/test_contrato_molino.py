"""
tests/test_contrato_molino.py -- «Contrato con el Molino»: la unica fuente de
harina que no pasa por la Bolsa (engine.PRECIO_CONTRATO_MOLINO /
RENDIMIENTO_MOLINO_PCT, ACTIONS_REGISTRY.md §C).

Existe porque el lado de VENTA del mercado era funcionalidad muerta: la unica
forma de tener harina era comprarla, y comprar mueve el visor hacia el extremo
caro, asi que una ida y vuelta comprar->vender pierde siempre. Con el contrato,
un jugador produce harina que nunca compro y vender por fin significa algo.

Los dos guardarrailes que importan aqui:
  · la amortizacion comun al 4º dia, que es la cuenta con la que se escribieron
    los tres precios (misma funcion que HORIZONTE_AMORTIZACION cumple para la
    renta de panaderia), y
  · que la entrega se DERIVA del contrato vivo y no de ningun campo cacheado de
    produccion diaria.
"""
from __future__ import annotations

import random

import pytest

from actions import ActionManager, RECURSO_MOLINO
from bootstrap import create_game
from engine import (
    GameEngine,
    POSICION_HARINA_INICIAL,
    PRECIOS_HARINA,
    PRECIO_CONTRATO_MOLINO,
    RENDIMIENTO_MOLINO_PCT,
)
from events import EventoTipo
from exceptions import InvalidActionError, MissingResourceError, RuleViolationError
from models import TipoHarina

# El horizonte con el que se autoraron los tres precios: la harina entregada
# vale su precio de COMPRA en la posicion inicial del visor, y a las 4 noches
# el acumulado cubre el contrato -- en las 3, ninguno de los tres llega.
HORIZONTE_AMORTIZACION = 4


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _contratar(tipo: TipoHarina) -> dict:
    return {
        "tipo_recurso": RECURSO_MOLINO,
        "operacion": "contratar",
        "tipo_harina": tipo.value,
    }


# ---------------------------------------------------------------------------
# Firmar el contrato (Accion C)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tipo", list(TipoHarina))
def test_firmar_cobra_el_precio_del_tipo_y_deja_el_contrato(tipo) -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 20

    manager.accion_C_visitar_mercado(jugador, [_contratar(tipo)])

    assert jugador.contrato_molino == tipo.value
    assert jugador.monedas == 20 - PRECIO_CONTRATO_MOLINO[tipo]


def test_firmar_no_mueve_el_visor() -> None:
    """El molino produce FUERA de la Bolsa. Que la produccion propia no sea una
    senal de mercado es lo que hace que vender esa harina despues valga la pena;
    si firmar encareciese el tipo contratado, el contrato se pagaria solo."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 20
    antes = dict(engine.market.posiciones_harina)

    manager.accion_C_visitar_mercado(jugador, [_contratar(TipoHarina.CENTENO)])

    assert engine.market.posiciones_harina == antes


def test_se_puede_firmar_y_comprar_la_misma_harina_en_una_visita() -> None:
    """El molino es su propio tipo_recurso, no el de la harina contratada, asi
    que la Regla de Exclusividad no bloquea la jugada natural del dia que firmas
    (el molino no entrega hasta la noche, y hoy sigues necesitando harina)."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 30
    harina_antes = jugador.reserva_harina["Centeno"]

    manager.accion_C_visitar_mercado(
        jugador,
        [
            _contratar(TipoHarina.CENTENO),
            {"tipo_recurso": "Centeno", "operacion": "comprar"},
        ],
    )

    assert jugador.contrato_molino == "Centeno"
    assert jugador.reserva_harina["Centeno"] == harina_antes + 100


def test_dos_contratos_en_la_misma_visita_chocan_por_exclusividad() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 30

    with pytest.raises(InvalidActionError):
        manager.accion_C_visitar_mercado(
            jugador,
            [_contratar(TipoHarina.BLANCA), _contratar(TipoHarina.CENTENO)],
        )
    assert jugador.contrato_molino is None


def test_segundo_contrato_rechazado_y_el_primero_intacto() -> None:
    """Uno por partida, sin cambio de harina y sin cancelacion."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 30
    manager.accion_C_visitar_mercado(jugador, [_contratar(TipoHarina.BLANCA)])
    monedas = jugador.monedas

    jugador.acciones_pa_usadas_hoy = []
    jugador.puntos_accion = 2
    with pytest.raises(RuleViolationError):
        manager.accion_C_visitar_mercado(jugador, [_contratar(TipoHarina.CENTENO)])

    assert jugador.contrato_molino == "Blanca"
    assert jugador.monedas == monedas


def test_sin_monedas_no_deja_rastro() -> None:
    """Fail-fast: la validacion completa precede a cualquier mutacion, asi que
    un contrato inasequible no consume PA ni deja el contrato a medias."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = PRECIO_CONTRATO_MOLINO[TipoHarina.CENTENO] - 1
    pa_antes = jugador.puntos_accion

    with pytest.raises(MissingResourceError):
        manager.accion_C_visitar_mercado(jugador, [_contratar(TipoHarina.CENTENO)])

    assert jugador.contrato_molino is None
    assert jugador.puntos_accion == pa_antes


def test_una_venta_puede_financiar_el_contrato_en_la_misma_visita() -> None:
    """El contrato entra en la simulacion de saldos como cualquier otro coste."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.reserva_harina["Blanca"] = 100
    jugador.monedas = 0

    manager.accion_C_visitar_mercado(
        jugador,
        [
            {"tipo_recurso": "Blanca", "operacion": "vender"},
            _contratar(TipoHarina.BLANCA),
        ],
    )

    assert jugador.contrato_molino == "Blanca"


def test_operacion_y_tipo_de_harina_se_validan() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.monedas = 30

    with pytest.raises(InvalidActionError):
        manager.accion_C_visitar_mercado(
            jugador,
            [{"tipo_recurso": RECURSO_MOLINO, "operacion": "vender"}],
        )
    with pytest.raises(InvalidActionError):
        manager.accion_C_visitar_mercado(
            jugador,
            [{
                "tipo_recurso": RECURSO_MOLINO,
                "operacion": "contratar",
                "tipo_harina": "Espelta",
            }],
        )
    assert jugador.contrato_molino is None


# ---------------------------------------------------------------------------
# La entrega nocturna (Fase III)
# ---------------------------------------------------------------------------


def test_entrega_cada_noche_la_harina_contratada() -> None:
    engine = _motor()
    jugador = engine.players[0]
    jugador.contrato_molino = "Centeno"
    antes = dict(jugador.reserva_harina)

    engine._entregar_rendimiento_molino(jugador)
    engine._entregar_rendimiento_molino(jugador)

    assert jugador.reserva_harina["Centeno"] == antes["Centeno"] + 2 * RENDIMIENTO_MOLINO_PCT
    assert jugador.reserva_harina["Blanca"] == antes["Blanca"]
    assert jugador.reserva_harina["Integral"] == antes["Integral"]


def test_sin_contrato_no_entrega_nada() -> None:
    engine = _motor()
    jugador = engine.players[0]
    antes = dict(jugador.reserva_harina)

    assert engine._entregar_rendimiento_molino(jugador) == 0
    assert jugador.reserva_harina == antes


def test_se_deriva_del_contrato_vivo() -> None:
    """No hay campo de produccion diaria cacheado: la entrega lee el contrato en
    el momento, igual que la renta lee el archivo vivo."""
    engine = _motor()
    jugador = engine.players[0]
    jugador.contrato_molino = "Blanca"
    engine._entregar_rendimiento_molino(jugador)

    jugador.contrato_molino = "Integral"
    integral_antes = jugador.reserva_harina["Integral"]
    blanca_antes = jugador.reserva_harina["Blanca"]
    engine._entregar_rendimiento_molino(jugador)

    assert jugador.reserva_harina["Integral"] == integral_antes + RENDIMIENTO_MOLINO_PCT
    assert jugador.reserva_harina["Blanca"] == blanca_antes


def test_la_entrega_emite_su_evento() -> None:
    """Es un cambio automatico sin intervencion del jugador, asi que el informe
    nocturno tiene que poder contarlo desde engine.eventos (ARCHITECTURE.md)."""
    engine = _motor()
    jugador = engine.players[0]
    jugador.contrato_molino = "Centeno"

    engine._entregar_rendimiento_molino(jugador)

    evento = [e for e in engine.eventos if e.tipo == EventoTipo.RENDIMIENTO_MOLINO][-1]
    assert evento.jugador_idx == 0
    assert evento.datos["tipo_harina"] == "Centeno"
    assert evento.datos["harina_pct"] == RENDIMIENTO_MOLINO_PCT


def test_la_fase_III_entrega_a_todos_los_contratados() -> None:
    engine = _motor()
    alba, bruno = engine.players
    alba.contrato_molino = "Blanca"
    engine.iniciar_dia()
    blanca_alba = alba.reserva_harina["Blanca"]
    blanca_bruno = bruno.reserva_harina["Blanca"]

    engine.pasar_turno(alba)
    engine.pasar_turno(bruno)
    engine.resolver_fase_III()

    assert alba.reserva_harina["Blanca"] == blanca_alba + RENDIMIENTO_MOLINO_PCT
    assert bruno.reserva_harina["Blanca"] == blanca_bruno


# ---------------------------------------------------------------------------
# El guardarrail de diseno: los tres precios amortizan el mismo dia
# ---------------------------------------------------------------------------


def test_amortizacion_al_cuarto_dia() -> None:
    """Los tres precios se escribieron valorando la entrega diaria al precio de
    COMPRA de la posicion inicial del visor: a las 4 noches el acumulado cubre
    el contrato y a las 3 no, en los tres tipos por igual.

    Que el horizonte sea COMUN es lo que hace que la presion temporal sea la
    misma en los tres y que elegir tipo siga siendo una pregunta sobre que
    harina necesitas, no sobre cual se recupera antes -- el mismo principio que
    reparte el horizonte de PRECIO_RENTA entre los tres grados. Sin este test,
    un reajuste de PRECIOS_HARINA o de PRECIO_CONTRATO_MOLINO lo rompe en
    silencio, porque nada en el codigo lee el horizonte.
    """
    for tipo, precio in PRECIO_CONTRATO_MOLINO.items():
        compra = PRECIOS_HARINA[tipo]["compra"][POSICION_HARINA_INICIAL - 1]
        # Valor entregado en N noches, en centesimas de Moneda para no usar
        # coma flotante: compra es el precio de 100% de harina.
        def acumulado(noches: int) -> int:
            return noches * compra * RENDIMIENTO_MOLINO_PCT

        assert acumulado(HORIZONTE_AMORTIZACION) >= precio * 100, (
            f"{tipo.value}: el contrato no se amortiza al dia "
            f"{HORIZONTE_AMORTIZACION}"
        )
        assert acumulado(HORIZONTE_AMORTIZACION - 1) < precio * 100, (
            f"{tipo.value}: el contrato se amortiza ANTES del dia "
            f"{HORIZONTE_AMORTIZACION}"
        )
