"""
tests/test_disponibilidad.py -- prueba disponibilidad.acciones_disponibles,
la disponibilidad de acciones "barata" que server/views.py incluye en cada
snapshot para que un cliente remoto pueda habilitar/deshabilitar sus
propios botones sin reimplementar reglas de ActionManager.
"""
from __future__ import annotations

from disponibilidad import acciones_disponibles
from main import setup_game


def _por_id(resultado, id_):
    return next(r for r in resultado if r["id"] == id_)


def test_dia_1_recien_iniciado_B_habilitada_H_e_I_no() -> None:
    engine = setup_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "B")["habilitada"] is True  # tiene la receta inicial, PA, estacion libre
    assert _por_id(resultado, "H")["habilitada"] is False
    assert _por_id(resultado, "I")["habilitada"] is False
    assert _por_id(resultado, "H")["motivo"] != ""


def test_sin_pa_deshabilita_acciones_de_costo_pero_no_las_gratuitas() -> None:
    engine = setup_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.puntos_accion = 0

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "B")["habilitada"] is False
    assert _por_id(resultado, "B")["motivo"] == "Sin PA"
    assert _por_id(resultado, "F")["habilitada"] is False
    # Accion A es gratuita (0 PA): sigue habilitada si hay recursos.
    assert _por_id(resultado, "A")["habilitada"] is True


def test_contaminado_habilita_protocolos_de_emergencia_segun_recursos() -> None:
    engine = setup_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.en_estado_contaminacion = True
    p1.reserva_harina = {"Blanca": 50, "Centeno": 0, "Integral": 0}
    p1.reserva_agua = 0
    p1.datos_investigacion = 0

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "H")["habilitada"] is True  # 50% de harina, sin costo de agua
    assert _por_id(resultado, "I")["habilitada"] is False  # sin datos
    assert _por_id(resultado, "I")["motivo"] == "Recursos insuficientes"
    # Estando contaminado, Accion B queda bloqueada aunque el resto de
    # precondiciones se cumplan (ACTIONS_REGISTRY.md SS3).
    assert _por_id(resultado, "B")["habilitada"] is False


def test_accion_ya_usada_se_refleja_como_deshabilitada() -> None:
    engine = setup_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.accion_alimentar_usada = True
    p1.horas_extras_usadas = True

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "A")["habilitada"] is False
    assert _por_id(resultado, "A")["motivo"] == "Ya se usó hoy"
    assert _por_id(resultado, "horas_extras")["habilitada"] is False
