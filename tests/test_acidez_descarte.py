"""
tests/test_acidez_descarte.py -- la Acidez despues de dejar de ser un trinquete.

Antes de este cambio la Acidez solo sabia subir: arrancaba en 1, la Accion A la
empujaba +1 por dia con agua, la carta «Acidificacion Acelerada» sumaba otro +1
sin que nadie lo pidiera, y las unicas dos cosas que la bajaban (Protocolos H e
I) exigian estar ya contaminado. El Bono de Sabor, que se sella comparando la
acidez contra el rango impreso de la carta, era por tanto una loteria: las
dianas bajas solo eran alcanzables al principio de la partida y las altas solo
al final. El de 8 PM de Panettone (diana `(1,)`) era inalcanzable en cuanto la
acidez pasaba de 1.

Este archivo fija las cuatro piezas que arreglan eso, cada una en un sitio
donde el diseno se puede deshacer en silencio:

  1. La accion «Descarte» mueve la acidez en LOS DOS sentidos, cobrando en
     recursos distintos: subir cuesta Agua, bajar cuesta Monedas.
  2. Sobrevive al no costar PA gracias al tope de "un espacio, una visita por
     dia" -- exactamente el mismo argumento que la Accion E, porque las Monedas
     son renovables y el precio por si solo no limita nada.
  3. `Madurez` dejo de premiar la acidez CRUDA y premia el EQUILIBRIO, asi que
     los dos extremos de la pista pagan 0 y una diana extrema cuesta puntos
     mientras la sostienes.
  4. Los 12 `bono_sabor_pts` del catalogo se DERIVAN de grado x distancia al
     centro. Es el reverso de (3): la carta te paga justamente por el sitio de
     la pista que la Madurez te cobra.

La Accion A ya no toca la Acidez en absoluto; eso se cubre en
test_actions_suite.py, junto al resto de su comportamiento.
"""
from __future__ import annotations

import pytest

from actions import ActionManager, OPERACIONES_ACIDEZ
from engine import (
    COSTE_REFRESCO_AGUA,
    GameEngine,
    Market,
    PRECIO_DESCARTE,
)
from exceptions import (
    EspacioAccionYaUsadoError,
    InvalidActionError,
    MissingResourceError,
)
from models import (
    ACIDEZ_EQUILIBRIO_CENTRO,
    Environment,
    Grado,
    Player,
    PUNTOS_EQUILIBRIO_MAX,
    RECIPE_CATALOG,
)


def _partida() -> tuple[GameEngine, ActionManager, Player]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    engine = GameEngine([p1, p2], Environment.crear_inicial(), Market.crear_inicial())
    p1.puntos_accion = 2
    p1.monedas = 30
    p1.reserva_agua = 30
    p1.acidez = 3
    return engine, ActionManager(engine), p1


# ---------------------------------------------------------------------------
# 1. Las dos escaleras
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("niveles", sorted(COSTE_REFRESCO_AGUA))
def test_subir_cobra_agua_y_mueve_la_acidez(niveles: int) -> None:
    _, manager, p = _partida()
    agua0, monedas0 = p.reserva_agua, p.monedas

    manager.accion_descarte_acidez(p, operacion="subir", niveles=niveles)

    assert p.acidez == 3 + niveles
    assert p.reserva_agua == agua0 - COSTE_REFRESCO_AGUA[niveles]
    assert p.monedas == monedas0, "subir no debe costar Monedas"


@pytest.mark.parametrize("niveles", sorted(PRECIO_DESCARTE))
def test_bajar_cobra_monedas_y_mueve_la_acidez(niveles: int) -> None:
    _, manager, p = _partida()
    agua0, monedas0 = p.reserva_agua, p.monedas

    manager.accion_descarte_acidez(p, operacion="bajar", niveles=niveles)

    assert p.acidez == 3 - niveles
    assert p.monedas == monedas0 - PRECIO_DESCARTE[niveles]
    assert p.reserva_agua == agua0, "bajar no debe costar Agua"


def test_las_escaleras_son_crecientes_al_margen() -> None:
    """
    El volumen nunca es un descuento -- la misma regla que documenta
    PRECIO_PLIEGUES. Sin esto, el escalon grande seria la jugada por defecto
    en vez de una inversion.
    """
    for escalera in (PRECIO_DESCARTE, COSTE_REFRESCO_AGUA):
        niveles = sorted(escalera)
        marginales = [
            escalera[n] - escalera[a] for a, n in zip(niveles, niveles[1:])
        ]
        assert marginales == sorted(marginales)
        assert all(m > 0 for m in marginales)
        # Estrictamente creciente: el 2o nivel cuesta mas que el 1o, etc.
        assert marginales[0] < marginales[-1]


def test_los_dos_sentidos_cobran_recursos_distintos() -> None:
    """
    La asimetria es deliberada y protege al jugador arruinado: sin una sola
    Moneda todavia conserva un sentido del dial.
    """
    recursos = {recurso for _, recurso, _ in OPERACIONES_ACIDEZ.values()}
    assert recursos == {"agua", "monedas"}


# ---------------------------------------------------------------------------
# 2. Topes, clamp y atomicidad
# ---------------------------------------------------------------------------


def test_el_espacio_se_ocupa_una_vez_por_dia() -> None:
    _, manager, p = _partida()
    manager.accion_descarte_acidez(p, operacion="bajar", niveles=1)
    assert "descarte" in p.acciones_pa_usadas_hoy

    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_descarte_acidez(p, operacion="subir", niveles=1)


def test_no_gasta_pa_ni_cierra_la_visita() -> None:
    """
    Es 0 PA y vive en el grupo de Gratuitas: quien la usa sigue teniendo sus
    dos PA intactos para una accion principal en la misma visita.
    """
    _, manager, p = _partida()
    manager.accion_descarte_acidez(p, operacion="bajar", niveles=1)
    assert p.puntos_accion == 2


def test_el_clamp_no_cobra_de_mas_ni_desborda() -> None:
    _, manager, p = _partida()
    p.acidez = 5
    monedas0 = p.monedas
    manager.accion_descarte_acidez(p, operacion="subir", niveles=3)
    assert p.acidez == 6, "ajustar_acidez recorta en 6"
    assert p.reserva_agua == 30 - COSTE_REFRESCO_AGUA[3], (
        "el clamp no devuelve el sobrante: se paga el escalon pedido"
    )
    assert p.monedas == monedas0

    _, manager, p = _partida()
    p.acidez = 1
    manager.accion_descarte_acidez(p, operacion="bajar", niveles=3)
    assert p.acidez == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operacion": "mezclar", "niveles": 1},
        {"operacion": "subir", "niveles": 0},
        {"operacion": "subir", "niveles": 4},
        {"operacion": "bajar", "niveles": -1},
    ],
)
def test_parametros_invalidos_no_mutan_nada(kwargs: dict) -> None:
    _, manager, p = _partida()
    antes = (p.acidez, p.monedas, p.reserva_agua, list(p.acciones_pa_usadas_hoy))

    with pytest.raises(InvalidActionError):
        manager.accion_descarte_acidez(p, **kwargs)

    assert (p.acidez, p.monedas, p.reserva_agua, list(p.acciones_pa_usadas_hoy)) == antes


def test_sin_recurso_no_cobra_ni_ocupa_el_espacio() -> None:
    """Fail-fast: un rechazo no puede quemar el espacio del dia."""
    _, manager, p = _partida()
    p.monedas = 0
    p.reserva_agua = 0

    with pytest.raises(MissingResourceError):
        manager.accion_descarte_acidez(p, operacion="bajar", niveles=1)
    with pytest.raises(MissingResourceError):
        manager.accion_descarte_acidez(p, operacion="subir", niveles=1)

    assert p.acciones_pa_usadas_hoy == []
    assert p.acidez == 3


def test_un_jugador_sin_pa_sigue_elegible_por_el_espacio_de_descarte() -> None:
    """
    Sin la clausula en `_jugador_elegible`, quien gastara sus 2 PA nunca
    alcanzaria su Descarte del dia. Basta con poder pagar el escalon mas
    barato de ALGUNO de los dos sentidos, porque cobran recursos distintos.
    """
    engine, _, p = _partida()
    engine.iniciar_dia()
    idx = engine._players.index(p)

    p.puntos_accion = 0
    p.accion_alimentar_usada = True
    p.horas_extras_usadas = True
    p.datos_investigacion = 0
    p.acciones_pa_usadas_hoy = ["E"]

    p.monedas, p.reserva_agua = min(PRECIO_DESCARTE.values()), 0
    assert engine._jugador_elegible(idx), "con Monedas puede bajar"

    p.monedas, p.reserva_agua = 0, min(COSTE_REFRESCO_AGUA.values())
    assert engine._jugador_elegible(idx), "sin Monedas pero con agua puede subir"

    p.monedas, p.reserva_agua = 0, 0
    assert not engine._jugador_elegible(idx)

    p.monedas, p.reserva_agua = 30, 30
    p.acciones_pa_usadas_hoy = ["E", "descarte"]
    assert not engine._jugador_elegible(idx)


# ---------------------------------------------------------------------------
# 3. Madurez por equilibrio
# ---------------------------------------------------------------------------


def test_la_curva_de_equilibrio_es_un_pico_en_el_centro() -> None:
    p = Player(nombre="x")
    curva = []
    for acidez in range(7):
        p.acidez = acidez
        curva.append(p.puntos_equilibrio_acidez)

    assert curva == [0, 1, 2, 3, 2, 1, 0]
    assert curva[ACIDEZ_EQUILIBRIO_CENTRO] == PUNTOS_EQUILIBRIO_MAX
    assert curva[0] == curva[-1] == 0, "los dos extremos pagan lo mismo: nada"
    assert min(curva) >= 0, "la formula no necesita clamp; no puede ser negativa"


def test_madurez_suma_vitalidad_entera_mas_el_equilibrio() -> None:
    p = Player(nombre="x")
    for vitalidad in range(7):
        for acidez in range(7):
            p.vitalidad, p.acidez = vitalidad, acidez
            assert p.desglose_maestria["Madurez"] == vitalidad + p.puntos_equilibrio_acidez


def test_madurez_sigue_siendo_un_solo_termino_en_su_sitio() -> None:
    """
    El orden de insercion de `desglose_maestria` ES el orden de presentacion
    para RankingView.vue y la numeracion de CORE_MECHANICS.md §3.
    Partir el termino en dos renumeraria las cuatro superficies a la vez.
    """
    claves = list(Player(nombre="x").desglose_maestria)
    assert claves.count("Madurez") == 1
    assert claves.index("Madurez") == 2


def test_subir_la_acidez_ya_no_es_gratis_en_puntos() -> None:
    """
    El bug que este cambio cierra: con `ceil((vit + acidez) / 2)` la acidez
    cruda nunca era mala, asi que el trinquete era ademas la jugada optima.
    """
    p = Player(nombre="x")
    p.vitalidad = 2
    p.acidez = ACIDEZ_EQUILIBRIO_CENTRO
    en_el_pico = p.desglose_maestria["Madurez"]
    p.acidez = 6
    assert p.desglose_maestria["Madurez"] < en_el_pico


# ---------------------------------------------------------------------------
# 4. El bono impreso se deriva del grado y de la distancia al centro
# ---------------------------------------------------------------------------

BASE_BONO_POR_GRADO = {Grado.BASICA: 1, Grado.INTERMEDIA: 2, Grado.AVANZADA: 3}


def _distancia_al_centro(receta) -> int:
    """Minima, no media: con un dial el jugador elige el extremo mas cercano."""
    return min(abs(v - ACIDEZ_EQUILIBRIO_CENTRO) for v in receta.acidez_diana)


@pytest.mark.parametrize("receta", list(RECIPE_CATALOG.values()), ids=lambda r: r.id)
def test_cada_carta_cumple_la_regla_del_bono(receta) -> None:
    esperado = BASE_BONO_POR_GRADO[receta.grado] + (
        1 if _distancia_al_centro(receta) >= 1 else 0
    )
    assert receta.bono_sabor_pts == esperado, (
        f"{receta.id}: bono impreso {receta.bono_sabor_pts}, la regla dice {esperado}. "
        "Los 12 valores se derivan, no se autoran a mano."
    )


def test_las_dianas_extremas_pagan_mas_que_las_centradas() -> None:
    """
    El cierre del bucle con la Madurez por equilibrio: la carta compensa
    exactamente el sitio de la pista que la Madurez cobra. Si esto se invierte,
    el juego estaria empujando al jugador a los dos lados a la vez.
    """
    for grado in Grado:
        cartas = [r for r in RECIPE_CATALOG.values() if r.grado == grado]
        centradas = [r for r in cartas if _distancia_al_centro(r) == 0]
        extremas = [r for r in cartas if _distancia_al_centro(r) >= 1]
        if not centradas or not extremas:
            continue
        assert max(r.bono_sabor_pts for r in centradas) < min(
            r.bono_sabor_pts for r in extremas
        ), f"{grado.value}: una diana centrada paga tanto como una extrema"
