"""
tests/test_jefatura.py -- «Reclamar la Jefatura»: el orden de turno deja de
deducirse del estado y pasa a comprarse (ACTIONS_REGISTRY.md §Jefatura,
CORE_MECHANICS.md §2 Fase I).

Antes, el Investigador Jefe era automaticamente quien tuviera mas Vitalidad, con
los Datos como desempate. Eso no era una decision de nadie -- el orden de turno
se deducia del estado -- y dejaba al rol sin mas contenido que salir primero.
Ahora la Jefatura se reclama con 1 PA, paga DATOS_JEFATURA al reclamarla, y si
nadie la reclama se queda donde esta.

Dos cosas distinguen este espacio de todos los demas y son las que mas se
comprueban aqui: es GLOBAL (uno por dia en toda la mesa, no uno por jugador) y su
efecto es DIFERIDO (se cobra el Dato hoy, se abre primero manana).
"""
from __future__ import annotations

import random

import pytest

from actions import ActionManager
from bootstrap import create_game
from disponibilidad import acciones_disponibles
from engine import DATOS_JEFATURA, GameEngine
from exceptions import NotEnoughActionPointsError, RuleViolationError


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _jugar_dia_completo(engine: GameEngine) -> None:
    """Pasa turno con quien quede en la ronda y resuelve la noche.

    `pasar_turno` es la unica forma correcta de ceder una visita -- poner
    puntos_accion = 0 a mano dejaria al jugador elegible para siempre por sus
    acciones gratuitas (ver _jugador_elegible).
    """
    while engine.jugador_activo is not None:
        engine.pasar_turno(engine.jugador_activo)
    engine.resolver_fase_III()


# ---------------------------------------------------------------------------
# Reclamar: lo que cuesta y lo que paga
# ---------------------------------------------------------------------------


def test_reclamar_cuesta_un_pa_y_paga_un_dato() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    pa_antes, datos_antes = jugador.puntos_accion, jugador.datos_investigacion

    manager.accion_reclamar_jefatura(jugador)

    assert jugador.puntos_accion == pa_antes - 1
    assert jugador.datos_investigacion == datos_antes + DATOS_JEFATURA
    assert engine.jefatura_reclamada_por == engine.players.index(jugador)


def test_sin_pa_no_se_puede_reclamar() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.puntos_accion = 0

    with pytest.raises(NotEnoughActionPointsError):
        manager.accion_reclamar_jefatura(jugador)
    assert engine.jefatura_reclamada_por is None


def test_es_un_espacio_global_uno_por_dia_en_toda_la_mesa() -> None:
    """La diferencia con cualquier otro espacio: que lo ocupe un jugador se lo
    quita a TODOS, no solo a el. Por eso la marca vive en el motor y no en
    Player.acciones_pa_usadas_hoy."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    primero = engine.jugador_activo
    manager.accion_reclamar_jefatura(primero)

    segundo = next(p for p in engine.players if p is not primero)
    datos_antes = segundo.datos_investigacion
    pa_antes = segundo.puntos_accion

    with pytest.raises(RuleViolationError):
        manager.accion_reclamar_jefatura(segundo)

    # Fail-fast: el rechazo no le cobro nada al segundo.
    assert segundo.datos_investigacion == datos_antes
    assert segundo.puntos_accion == pa_antes
    assert engine.jefatura_reclamada_por == engine.players.index(primero)


def test_reclamar_termina_la_visita() -> None:
    """Es una accion principal como cualquier otra: ocupa el espacio del
    jugador y le gasta el PA, asi que la mesa avanza."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo

    manager.accion_reclamar_jefatura(jugador)

    assert "jefatura" in jugador.acciones_pa_usadas_hoy


# ---------------------------------------------------------------------------
# El efecto es de manana, no de hoy
# ---------------------------------------------------------------------------


def test_quien_reclama_abre_el_dia_siguiente() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    orden_hoy = list(engine.turno_orden)

    # Reclama el SEGUNDO de la fila, para que el cambio sea visible.
    segundo_idx = orden_hoy[1]
    segundo = engine.players[segundo_idx]
    while engine.jugador_activo is not segundo:
        engine.pasar_turno(engine.jugador_activo)
    manager.accion_reclamar_jefatura(segundo)

    # Hoy el orden no se rebaraja a media jornada.
    assert engine.turno_orden == orden_hoy

    _jugar_dia_completo(engine)
    engine.iniciar_dia()

    assert engine.turno_orden[0] == segundo_idx
    assert engine.jefe_investigador is segundo


def test_si_nadie_reclama_la_ficha_se_queda_donde_esta() -> None:
    """Semantica de ficha fisica: sin reclamacion no hay rotacion automatica que
    recordar, y la Jefatura sigue valiendo lo que valga para su dueno actual."""
    engine = _motor()
    engine.iniciar_dia()
    jefe_ayer = engine.jefe_investigador

    _jugar_dia_completo(engine)
    engine.iniciar_dia()

    assert engine.jefe_investigador is jefe_ayer


def test_la_reclamacion_se_consume_y_no_se_arrastra() -> None:
    """Reclamar el dia 1 da la Jefatura el dia 2, no tambien el 3."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    orden = list(engine.turno_orden)
    segundo = engine.players[orden[1]]
    while engine.jugador_activo is not segundo:
        engine.pasar_turno(engine.jugador_activo)
    manager.accion_reclamar_jefatura(segundo)

    _jugar_dia_completo(engine)
    engine.iniciar_dia()
    assert engine.jefatura_reclamada_por is None
    assert engine.jefe_investigador is segundo

    # Nadie reclama el dia 2: sigue siendo suya, no vuelve al de antes.
    _jugar_dia_completo(engine)
    engine.iniciar_dia()
    assert engine.jefe_investigador is segundo


def test_el_jefe_puede_reclamar_para_retener() -> None:
    """Reclamar siendo ya Jefe es legal y cuesta lo mismo: es la unica forma de
    impedir que otro compre la salida de manana."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jefe = engine.jefe_investigador
    while engine.jugador_activo is not jefe:
        engine.pasar_turno(engine.jugador_activo)

    manager.accion_reclamar_jefatura(jefe)
    _jugar_dia_completo(engine)
    engine.iniciar_dia()

    assert engine.jefe_investigador is jefe


def test_el_dia_1_lo_decide_la_iniciativa_del_patrocinio() -> None:
    """Lo unico que NO cambia: nadie ha podido reclamar todavia."""
    engine = _motor()
    engine.iniciar_dia()
    assert engine.turno_orden[0] == engine._orden_inicial_iniciativa[0]


def test_la_vitalidad_ya_no_decide_la_jefatura() -> None:
    """El guardarrail de la regla RETIRADA: subirle la Vitalidad a alguien ya no
    le da la salida. Sin este test, reintroducir el criterio automatico pasaria
    inadvertido para el resto de la suite."""
    engine = _motor()
    engine.iniciar_dia()
    jefe_dia_1 = engine.jefe_investigador
    otro = next(p for p in engine.players if p is not jefe_dia_1)
    otro.vitalidad = 6
    jefe_dia_1.vitalidad = 1

    _jugar_dia_completo(engine)
    engine.iniciar_dia()

    assert engine.jefe_investigador is jefe_dia_1


# ---------------------------------------------------------------------------
# Disponibilidad (lo que ve el cliente)
# ---------------------------------------------------------------------------


def _entrada_jefatura(engine: GameEngine, player) -> dict:
    return next(
        a for a in acciones_disponibles(engine, player) if a["id"] == "jefatura"
    )


def test_disponibilidad_apaga_el_espacio_para_todos_al_reclamarlo() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    primero = engine.jugador_activo
    segundo = next(p for p in engine.players if p is not primero)

    assert _entrada_jefatura(engine, segundo)["habilitada"] is True

    manager.accion_reclamar_jefatura(primero)

    entrada = _entrada_jefatura(engine, segundo)
    assert entrada["habilitada"] is False
    # El motivo nombra a quien lo ocupo: «ya usado» a secas se leeria como el
    # limite habitual de un espacio propio, que aqui no es lo que pasa.
    assert primero.nombre in entrada["motivo"]


def test_disponibilidad_sin_pa() -> None:
    engine = _motor()
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.puntos_accion = 0

    assert _entrada_jefatura(engine, jugador)["habilitada"] is False
