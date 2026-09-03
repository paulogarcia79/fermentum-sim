"""
tests/test_renta_panaderia.py -- «Ingresos de Panaderia»: una receta horneada con
exito deja de ser historial y pasa a rendir Monedas cada Fase III
(CORE_MECHANICS.md §2, engine.PRECIO_RENTA), y el Simposio Tecnico -- la unica
accion que saca un registro del archivo -- corta ese ingreso al sacrificarlo
(ACTIONS_REGISTRY.md §Simposio, engine.DATOS_SIMPOSIO).

El guardarrail que de verdad importa aqui es que la renta se DERIVA del archivo
vivo y no se cachea en ningun sitio: es lo que hace que «si el registro sale del
archivo, su ingreso desaparece» se cumpla solo, sin codigo que lo coordine.
"""
from __future__ import annotations

import random

from actions import ActionManager
from bootstrap import create_game
from engine import DATOS_SIMPOSIO, GameEngine, PRECIO_RENTA
from events import EventoTipo
from exceptions import InvalidActionError, RuleViolationError
from models import FermentationSlot, Grado, HorneadoRecord, RECIPE_CATALOG

# Una carta de cada grado, para cubrir las tres tasas de PRECIO_RENTA.
BASICA = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA)
INTERMEDIA = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.INTERMEDIA)
AVANZADA = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA)

# El horizonte de amortizacion con el que se autoraron los pagos por zona de
# RECIPE_CATALOG: cada horneado recupera su pago antiguo al tercer dia.
HORIZONTE_AMORTIZACION = 3


def _registro(recipe, *, colapso: bool = False) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=recipe,
        posicion_final=recipe.zona_optima[0],
        puntos_base=recipe.puntos_optimos,
        bono_sabor_aplicado=False,
        fue_colapso=colapso,
        datos_obtenidos=0,
        monedas_obtenidos=0,
        ampliacion_aplicada=0,
    )


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


# ---------------------------------------------------------------------------
# La renta en si
# ---------------------------------------------------------------------------


def test_tasa_por_grado() -> None:
    """La renta se indexa por grado, como PRECIO_RECETA / COPIAS_POR_GRADO."""
    assert PRECIO_RENTA[Grado.BASICA] == 1
    assert PRECIO_RENTA[Grado.INTERMEDIA] == 2
    assert PRECIO_RENTA[Grado.AVANZADA] == 3
    # Todas las cartas del catalogo tienen tasa: un grado nuevo sin entrada
    # reventaria aqui y no en mitad de una Fase III.
    for receta in RECIPE_CATALOG.values():
        assert receta.grado in PRECIO_RENTA


def test_archivo_vacio_no_cobra_ni_emite() -> None:
    engine = _motor()
    jugador = engine.players[0]
    monedas_antes = jugador.monedas

    assert engine._cobrar_renta_panaderia(jugador) == 0
    assert jugador.monedas == monedas_antes
    assert not [e for e in engine.eventos if e.tipo == EventoTipo.RENTA_PANADERIA]


def test_suma_todos_los_registros_del_archivo() -> None:
    engine = _motor()
    jugador = engine.players[0]
    jugador.archivo_horneado_exitoso = [
        _registro(BASICA), _registro(INTERMEDIA), _registro(AVANZADA)
    ]
    monedas_antes = jugador.monedas

    cobrado = engine._cobrar_renta_panaderia(jugador)

    assert cobrado == 1 + 2 + 3
    assert jugador.monedas == monedas_antes + 6


def test_un_colapso_no_paga_nada() -> None:
    """Provocar un colapso es gratis (iniciar una masa y dejar que la Fase III la
    hornee sola), asi que pagarlo regalaria la renta sin hornear bien nada --
    el mismo argumento de incentivos que rige «Variedad de Recetas»."""
    engine = _motor()
    jugador = engine.players[0]
    jugador.archivo_colapsos = [_registro(AVANZADA, colapso=True)] * 3
    assert engine._cobrar_renta_panaderia(jugador) == 0


def test_emite_evento_con_desglose() -> None:
    engine = _motor()
    jugador = engine.players[0]
    jugador.archivo_horneado_exitoso = [_registro(BASICA), _registro(AVANZADA)]

    engine._cobrar_renta_panaderia(jugador)

    eventos = [e for e in engine.eventos if e.tipo == EventoTipo.RENTA_PANADERIA]
    assert len(eventos) == 1
    assert eventos[0].jugador_idx == 0
    assert eventos[0].datos["monedas_recibidas"] == 4
    assert [d["monedas"] for d in eventos[0].datos["desglose"]] == [1, 3]


def test_se_deriva_del_archivo_vivo_nunca_se_cachea() -> None:
    """El guardarrail: mutar la lista a mano cambia el cobro de la noche
    siguiente sin que nada mas se entere. Si alguien introdujera un campo
    Player.renta_diaria o sellara la tasa en HorneadoRecord, esto fallaria."""
    engine = _motor()
    jugador = engine.players[0]
    jugador.archivo_horneado_exitoso = [_registro(AVANZADA), _registro(AVANZADA)]
    assert engine._cobrar_renta_panaderia(jugador) == 6

    jugador.archivo_horneado_exitoso.pop()
    assert engine._cobrar_renta_panaderia(jugador) == 3

    jugador.archivo_horneado_exitoso.clear()
    assert engine._cobrar_renta_panaderia(jugador) == 0


def test_amortizacion_al_tercer_dia() -> None:
    """El pago por zona se recorto en PRECIO_RENTA[grado] * 3, asi que a los 3
    dias el acumulado iguala exactamente lo que pagaba la carta antes. Es el
    principio que fija los 36 numeros de RECIPE_CATALOG, y vale para los tres
    grados por igual: esa igualdad es la razon de que el horizonte sea comun."""
    for receta in (BASICA, INTERMEDIA, AVANZADA):
        engine = _motor()
        jugador = engine.players[0]
        renta = PRECIO_RENTA[receta.grado]
        pago_antiguo = receta.monedas_optima + renta * HORIZONTE_AMORTIZACION

        jugador.archivo_horneado_exitoso = [_registro(receta)]
        acumulado = receta.monedas_optima
        for _ in range(HORIZONTE_AMORTIZACION):
            acumulado += engine._cobrar_renta_panaderia(jugador)

        assert acumulado == pago_antiguo


def test_se_cobra_la_misma_noche_del_horneado() -> None:
    """Un horneado hecho en la Fase II de hoy ya esta en el archivo cuando corre
    la Fase III, asi que cobra esa misma noche. Por eso no hace falta saber en
    que dia se horneo cada registro."""
    engine = _motor()
    jugador = engine.players[0]
    engine.iniciar_dia()

    receta = jugador.carpeta_proyectos[0]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta,
        dado_inoculo=1,
        posicion_track=receta.zona_optima[0],
        bono_sabor=False,
        modificador_incubadora=0,
    )
    engine.resolver_horneado(jugador, 0)
    assert len(jugador.archivo_horneado_exitoso) == 1

    monedas_antes = jugador.monedas
    cobrado = engine._cobrar_renta_panaderia(jugador)
    assert cobrado == PRECIO_RENTA[receta.grado]
    assert jugador.monedas == monedas_antes + cobrado


def test_fase_iii_paga_a_todos_los_jugadores() -> None:
    engine = _motor()
    engine.players[0].archivo_horneado_exitoso = [_registro(AVANZADA)]
    engine.players[1].archivo_horneado_exitoso = [_registro(BASICA)]
    antes = [p.monedas for p in engine.players]

    engine.fase_III_fermentacion()

    assert engine.players[0].monedas == antes[0] + 3
    assert engine.players[1].monedas == antes[1] + 1


# ---------------------------------------------------------------------------
# El Simposio Tecnico: la unica salida del archivo
# ---------------------------------------------------------------------------


def test_simposio_paga_datos_por_grado() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.archivo_horneado_exitoso = [_registro(AVANZADA)]
    datos_antes = jugador.datos_investigacion

    devuelto = manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)

    assert devuelto == DATOS_SIMPOSIO[Grado.AVANZADA] == 3
    assert jugador.datos_investigacion == datos_antes + 3
    assert jugador.archivo_horneado_exitoso == []
    # La carta fisica vuelve al descarte y puede reaparecer al rebarajar.
    assert AVANZADA in engine.market.descarte_recetas


def test_simposio_corta_la_renta_y_los_puntos() -> None:
    """Sacrificar un registro le quita a la vez su renta, sus puntos base y su
    escalon de Variedad -- todo sin una linea de codigo que lo coordine, porque
    las tres cosas se derivan de la misma lista."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.archivo_horneado_exitoso = [_registro(AVANZADA), _registro(BASICA)]

    renta_antes = engine._cobrar_renta_panaderia(jugador)
    puntos_antes = jugador.puntos_horneados
    variedad_antes = jugador.puntos_variedad
    assert renta_antes == 4
    assert jugador.recetas_distintas_horneadas == 2

    manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)  # sacrifica la Avanzada

    assert engine._cobrar_renta_panaderia(jugador) == 1
    assert jugador.puntos_horneados == puntos_antes - AVANZADA.puntos_optimos
    assert jugador.recetas_distintas_horneadas == 1
    assert jugador.puntos_variedad < variedad_antes


def test_simposio_rechaza_archivo_vacio_sin_gastar_pa() -> None:
    """Fail-fast: valida antes de mutar, asi que un rechazo no consume el PA ni
    ocupa el espacio de accion."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.archivo_horneado_exitoso = []

    try:
        manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)
        raise AssertionError("deberia haber lanzado RuleViolationError")
    except RuleViolationError:
        pass

    assert jugador.puntos_accion == 2
    assert "simposio" not in jugador.acciones_pa_usadas_hoy


def test_simposio_rechaza_indice_fuera_de_rango_sin_gastar_pa() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.archivo_horneado_exitoso = [_registro(BASICA)]

    try:
        manager.accion_simposio_tecnico(jugador, "sacrificar", indice=7)
        raise AssertionError("deberia haber lanzado InvalidActionError")
    except InvalidActionError:
        pass

    assert jugador.puntos_accion == 2
    assert len(jugador.archivo_horneado_exitoso) == 1


def test_simposio_puede_retrasar_el_fin_de_partida() -> None:
    """Consecuencia emergente que se documenta, no se corrige: un jugador en 4/5
    puede sacrificar un horneado para bajar a 3/5. Es carisimo, asi que es una
    jugada legitima. Lo que NO puede es revertir un final ya disparado."""
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    jugador.puntos_accion = 2
    jugador.archivo_horneado_exitoso = [_registro(BASICA) for _ in range(4)]

    assert not engine.partida_terminada
    manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)
    assert len(jugador.archivo_horneado_exitoso) == 3
    assert not engine.partida_terminada


def test_el_gatillo_de_fin_de_partida_no_se_revierte() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    jugador = engine.players[0]
    engine.iniciar_dia()
    jugador.archivo_horneado_exitoso = [_registro(BASICA) for _ in range(4)]

    # El quinto horneado exitoso dispara el final...
    receta = jugador.carpeta_proyectos[0]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta,
        dado_inoculo=1,
        posicion_track=receta.zona_optima[0],
        bono_sabor=False,
        modificador_incubadora=0,
    )
    engine.resolver_horneado(jugador, 0)
    assert engine.partida_terminada

    # ...y sacrificar uno despues no lo deshace: el flag esta enclavado.
    jugador.puntos_accion = 2
    manager.accion_simposio_tecnico(jugador, "sacrificar", indice=0)
    assert engine.partida_terminada
