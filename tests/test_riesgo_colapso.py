"""
tests/test_riesgo_colapso.py -- prueba la prediccion de colapso del cultivo
base (`GameEngine.vitalidad_prevista` / `GameEngine.riesgo_colapso`), que
alimenta el aviso opcional de contaminacion en la UI.

Lo que se prueba aqui es que la PREDICCION coincide exactamente con lo que
`_aplicar_desgaste_metabolico` hace de verdad en la Fase III -- ambos comparten
`_delta_desgaste`, y el ultimo test lo verifica end-to-end jugando un dia real.
"""
from __future__ import annotations

import random

from engine import GameEngine
from main import setup_game
from models import EfectoClimatico


def _engine_2p() -> GameEngine:
    random.seed(4242)
    return setup_game(["Alba", "Bruno"])


def test_vitalidad_1_con_desgaste_estandar_es_riesgo() -> None:
    engine = _engine_2p()
    jugador = engine.players[0]
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    jugador.vitalidad = 1
    jugador.en_estado_contaminacion = False

    assert engine.vitalidad_prevista(jugador) == 0
    assert engine.riesgo_colapso(jugador) is True


def test_vitalidad_2_bajo_aletargamiento_invernal_es_riesgo() -> None:
    """Aletargamiento Invernal duplica el desgaste (-2), asi que un 2 tambien cae a 0."""
    engine = _engine_2p()
    jugador = engine.players[0]
    engine.environment.efecto_pasivo_activo = EfectoClimatico.ALETARGAMIENTO_INVERNAL
    jugador.vitalidad = 2
    jugador.en_estado_contaminacion = False

    assert engine.vitalidad_prevista(jugador) == 0
    assert engine.riesgo_colapso(jugador) is True

    # Con desgaste estandar, ese mismo 2 estaria a salvo.
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    assert engine.vitalidad_prevista(jugador) == 1
    assert engine.riesgo_colapso(jugador) is False


def test_criopreservacion_nunca_esta_en_riesgo() -> None:
    """Estasis Biologica ignora el desgaste por completo, incluso con Aletargamiento."""
    engine = _engine_2p()
    jugador = engine.players[0]
    jugador.tecnologias.criopreservacion = True
    jugador.vitalidad = 1
    jugador.en_estado_contaminacion = False

    for efecto in (EfectoClimatico.NINGUNO, EfectoClimatico.ALETARGAMIENTO_INVERNAL):
        engine.environment.efecto_pasivo_activo = efecto
        assert engine.vitalidad_prevista(jugador) == 1
        assert engine.riesgo_colapso(jugador) is False


def test_ya_contaminado_no_cuenta_como_riesgo_nuevo() -> None:
    """Seguir en 0 no es un episodio nuevo: no hay -3 PM adicional que avisar."""
    engine = _engine_2p()
    jugador = engine.players[0]
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    jugador.vitalidad = 0
    jugador.en_estado_contaminacion = True

    assert engine.vitalidad_prevista(jugador) == 0
    assert engine.riesgo_colapso(jugador) is False


def test_vitalidad_holgada_no_es_riesgo() -> None:
    engine = _engine_2p()
    jugador = engine.players[0]
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    jugador.vitalidad = 3
    jugador.en_estado_contaminacion = False

    assert engine.vitalidad_prevista(jugador) == 2
    assert engine.riesgo_colapso(jugador) is False


def test_la_prediccion_coincide_con_el_desgaste_real_del_dia() -> None:
    """
    La razon de ser de `_delta_desgaste` compartido: jugar un dia completo y
    comprobar que lo predicho durante la Fase II es exactamente lo que ocurrio.
    """
    random.seed(909)
    engine = setup_game(["Alba", "Bruno"])

    predicho: dict[str, int] = {}

    def turno(engine: GameEngine, player) -> None:
        # Durante la Fase II la carta de clima del dia ya esta resuelta,
        # asi que la prediccion debe ser exacta.
        predicho.setdefault(player.nombre, engine.vitalidad_prevista(player))
        engine.pasar_turno(player)

    engine.ejecutar_dia_laboratorio(ejecutar_turno_jugador=turno)

    assert predicho, "El callback de turno no llego a ejecutarse."
    for jugador in engine.players:
        assert jugador.vitalidad == predicho[jugador.nombre]
