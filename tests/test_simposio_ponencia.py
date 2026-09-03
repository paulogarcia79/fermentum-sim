"""
tests/test_simposio_ponencia.py -- el Simposio Tecnico tiene dos modos bajo un
mismo espacio: `sacrificar` (un horneado del Archivo, sin cambios) y `ponencia`
(PRECIO_DATO_SIMPOSIO Monedas por Dato, hasta MAX_DATOS_PONENCIA por visita, sin
tocar el Archivo).

Los invariantes que se fijan aqui:

  · La ponencia no toca `archivo_horneado_exitoso` ni `market.descarte_recetas`
    -- es la diferencia entera con el sacrificio, y por tanto lo que hay que
    comprobar en cada caso feliz.
  · **Los DOS modos exigen un Archivo no vacio.** Esa puerta compartida es lo
    que impide que las Monedas del Patrocinio sean un grifo de Datos el Dia 1, y
    lo que permite que `disponibilidad.py` no cambie ni una linea.
  · El precio es exactamente `datos * PRECIO_DATO_SIMPOSIO`, y **la tecnologia
    Comerciante no lo descuenta**: `DESCUENTO_COMERCIANTE` es de la Accion C.
  · Fail-fast: toda llamada rechazada deja Monedas, Datos, Archivo, PA y
    `acciones_pa_usadas_hoy` intactos. Un rechazo no puede consumir la visita.
  · Ningun modo emite `GameEvent` -- como toda accion menos la F. `len(eventos)`
    no se mueve, que es el invariante que protege la ventana de deshacer.
  · Los parametros cruzados (`sacrificar` con `datos`, `ponencia` con `indice`)
    son ilegales por construccion, igual que en el Pedido de Urgencia: el modo
    es un discriminador, no una sugerencia.
"""
from __future__ import annotations

import random

import pytest

from actions import ActionManager
from bootstrap import create_game
from engine import (
    DATOS_SIMPOSIO,
    GameEngine,
    MAX_DATOS_PONENCIA,
    PRECIO_DATO_SIMPOSIO,
)
from exceptions import (
    EspacioAccionYaUsadoError,
    InvalidActionError,
    MissingResourceError,
    RuleViolationError,
)
from models import Grado, HorneadoRecord, RECIPE_CATALOG
from server.commands import resolver_comando

BASICA = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA)
AVANZADA = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA)


def _registro(recipe) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=recipe,
        posicion_final=recipe.zona_optima[0],
        puntos_base=recipe.puntos_optimos,
        bono_sabor_aplicado=False,
        fue_colapso=False,
        datos_obtenidos=0,
        monedas_obtenidos=0,
        ampliacion_aplicada=0,
    )


def _partida(*, monedas: int = 30, archivo=(BASICA,)):
    """Motor determinista con un jugador listo para visitar el Simposio."""
    random.seed(4321)
    engine: GameEngine = create_game(["Alba", "Bruno"])
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.monedas = monedas
    jugador.datos_investigacion = 0
    jugador.archivo_horneado_exitoso = [_registro(r) for r in archivo]
    return engine, manager, jugador


# ---------------------------------------------------------------------------
# Los precios son cifras de equilibrio, no de formato
# ---------------------------------------------------------------------------


def test_el_precio_es_la_tasa_de_conversion_de_riqueza() -> None:
    """5 Monedas por Dato = lo que «Conversion de Riqueza» paga por 5 Monedas
    (+1 PM). Un Dato comprado cuesta exactamente el punto que ese dinero habria
    puntuado, asi que la ponencia es un trueque a la par y no dinero regalado."""
    _, _, jugador = _partida(monedas=5)
    assert PRECIO_DATO_SIMPOSIO == 5
    assert jugador.desglose_maestria["Conversión de Riqueza"] == 1


def test_el_tope_iguala_al_mejor_sacrificio() -> None:
    """Una bolsa nunca rinde en una visita mas Datos que sacrificar una
    Avanzada: es lo que le deja al sacrificio un papel propio."""
    assert MAX_DATOS_PONENCIA == DATOS_SIMPOSIO[Grado.AVANZADA] == 3


# ---------------------------------------------------------------------------
# Ponencia: el camino feliz
# ---------------------------------------------------------------------------


def test_la_ponencia_cobra_monedas_y_no_toca_el_archivo() -> None:
    engine, manager, jugador = _partida(monedas=30)
    descarte_antes = list(engine.market.descarte_recetas)

    devuelto = manager.accion_simposio_tecnico(jugador, "ponencia", datos=2)

    assert devuelto == 2
    assert jugador.datos_investigacion == 2
    assert jugador.monedas == 30 - 2 * PRECIO_DATO_SIMPOSIO
    # Lo que distingue este modo del sacrificio:
    assert len(jugador.archivo_horneado_exitoso) == 1
    assert engine.market.descarte_recetas == descarte_antes
    # Cuesta 1 PA y ocupa el espacio, como cualquier accion principal.
    assert jugador.puntos_accion == 1
    assert "simposio" in jugador.acciones_pa_usadas_hoy


def test_la_ponencia_cobra_el_tope_completo() -> None:
    _, manager, jugador = _partida(monedas=15)
    assert manager.accion_simposio_tecnico(jugador, "ponencia", datos=3) == 3
    assert jugador.monedas == 0
    assert jugador.datos_investigacion == 3


def test_el_comerciante_no_descuenta_la_ponencia() -> None:
    """DESCUENTO_COMERCIANTE abarata las compras de la Accion C y nada mas.
    Los 5 Monedas por Dato los paga toda la mesa por igual."""
    _, manager, jugador = _partida(monedas=30)
    jugador.tecnologias.comerciante = True

    manager.accion_simposio_tecnico(jugador, "ponencia", datos=2)

    assert jugador.monedas == 30 - 2 * PRECIO_DATO_SIMPOSIO


# ---------------------------------------------------------------------------
# Sacrificio: sigue igual con la firma nueva
# ---------------------------------------------------------------------------


def test_el_sacrificio_sigue_pagando_por_grado() -> None:
    engine, manager, jugador = _partida(archivo=(AVANZADA,))

    devuelto = manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)

    assert devuelto == DATOS_SIMPOSIO[Grado.AVANZADA] == 3
    assert jugador.datos_investigacion == 3
    assert jugador.archivo_horneado_exitoso == []
    assert AVANZADA in engine.market.descarte_recetas
    assert jugador.monedas == 30  # el sacrificio no cuesta dinero


# ---------------------------------------------------------------------------
# La puerta compartida y los rechazos (todos fail-fast)
# ---------------------------------------------------------------------------


def _estado(jugador):
    return (
        jugador.monedas,
        jugador.datos_investigacion,
        len(jugador.archivo_horneado_exitoso),
        jugador.puntos_accion,
        frozenset(jugador.acciones_pa_usadas_hoy),
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"modo": "sacrificar", "indice": 0},
        {"modo": "ponencia", "datos": 1},
    ],
    ids=["sacrificar", "ponencia"],
)
def test_los_dos_modos_exigen_un_pan_en_el_archivo(kwargs) -> None:
    """La puerta es compartida a proposito: sin ella, las Monedas del
    Patrocinio serian un grifo de Datos el Dia 1."""
    _, manager, jugador = _partida(archivo=())
    antes = _estado(jugador)

    with pytest.raises(RuleViolationError):
        manager.accion_simposio_tecnico(jugador, **kwargs)

    assert _estado(jugador) == antes


def test_la_ponencia_sin_monedas_se_rechaza_sin_gastar_nada() -> None:
    _, manager, jugador = _partida(monedas=4)
    antes = _estado(jugador)

    with pytest.raises(MissingResourceError):
        manager.accion_simposio_tecnico(jugador, "ponencia", datos=1)

    assert _estado(jugador) == antes


@pytest.mark.parametrize(
    "kwargs",
    [
        {"modo": "ponencia", "datos": 0},
        {"modo": "ponencia", "datos": MAX_DATOS_PONENCIA + 1},
        {"modo": "ponencia", "datos": True},
        {"modo": "ponencia", "datos": "2"},
        {"modo": "sacrificar", "indice": 7},
        {"modo": "congreso", "datos": 1},
        {"modo": "sacrificar", "indice": 0, "datos": 1},
        {"modo": "ponencia", "datos": 1, "indice": 0},
        {"modo": "sacrificar"},
        {"modo": "ponencia"},
    ],
    ids=[
        "cero-datos",
        "por-encima-del-tope",
        "booleano-colandose-como-uno",
        "datos-de-texto",
        "indice-fuera-de-rango",
        "modo-desconocido",
        "sacrificio-con-datos",
        "ponencia-con-indice",
        "sacrificio-sin-indice",
        "ponencia-sin-datos",
    ],
)
def test_llamadas_malformadas_no_tocan_el_estado(kwargs) -> None:
    _, manager, jugador = _partida()
    antes = _estado(jugador)

    with pytest.raises(InvalidActionError):
        manager.accion_simposio_tecnico(jugador, **kwargs)

    assert _estado(jugador) == antes


def test_una_visita_elige_un_modo_y_solo_uno() -> None:
    """El espacio es uno por dia, asi que la exclusividad entre modos no
    necesita codigo propio: la da el espacio."""
    _, manager, jugador = _partida(monedas=30)
    manager.accion_simposio_tecnico(jugador, "ponencia", datos=1)

    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)

    assert len(jugador.archivo_horneado_exitoso) == 1


def test_ningun_modo_emite_eventos() -> None:
    """Como toda accion menos la F. Es el invariante que protege los punteros
    `since` de los clientes a traves de un deshacer."""
    engine, manager, jugador = _partida(monedas=30)
    antes = len(engine.eventos)

    manager.accion_simposio_tecnico(jugador, "ponencia", datos=1)
    assert len(engine.eventos) == antes

    engine2, manager2, jugador2 = _partida()
    antes2 = len(engine2.eventos)
    manager2.accion_simposio_tecnico(jugador2, "sacrificar", indice=0)
    assert len(engine2.eventos) == antes2


# ---------------------------------------------------------------------------
# El cable: los parametros son un discriminador, como en el Pedido de Urgencia
# ---------------------------------------------------------------------------


def _por_cable(params):
    random.seed(4321)
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.monedas = 30
    jugador.datos_investigacion = 0
    jugador.archivo_horneado_exitoso = [_registro(BASICA)]
    manager = ActionManager(engine)
    return resolver_comando(engine, manager, jugador, "simposio", params)


def test_el_cable_acepta_las_dos_formas() -> None:
    assert _por_cable({"modo": "ponencia", "datos": 2}) == 2
    assert _por_cable({"modo": "sacrificar", "indice": 0}) == DATOS_SIMPOSIO[
        Grado.BASICA
    ]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"indice": 0},
        {"modo": "ponencia"},
        {"modo": "ponencia", "datos": "2"},
        {"modo": 3, "datos": 1},
    ],
    ids=["vacio", "forma-antigua", "sin-datos", "datos-de-texto", "modo-no-string"],
)
def test_el_cable_rechaza_las_formas_invalidas(params) -> None:
    with pytest.raises(InvalidActionError):
        _por_cable(params)
