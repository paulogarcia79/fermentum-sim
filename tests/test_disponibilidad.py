"""
tests/test_disponibilidad.py -- prueba disponibilidad.acciones_disponibles,
la disponibilidad de acciones "barata" que server/views.py incluye en cada
snapshot para que un cliente remoto pueda habilitar/deshabilitar sus
propios botones sin reimplementar reglas de ActionManager.
"""
from __future__ import annotations

from actions import COSTOS_TECNOLOGIA
from disponibilidad import acciones_disponibles
from bootstrap import create_game
from models import TecnologiaID


def _por_id(resultado, id_):
    return next(r for r in resultado if r["id"] == id_)


def test_dia_1_recien_iniciado_B_habilitada_H_e_I_no() -> None:
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "B")["habilitada"] is True  # tiene la receta inicial, PA, estacion libre
    assert _por_id(resultado, "H")["habilitada"] is False
    assert _por_id(resultado, "I")["habilitada"] is False
    assert _por_id(resultado, "H")["motivo"] != ""


def test_sin_pa_deshabilita_acciones_de_costo_pero_no_las_gratuitas() -> None:
    engine = create_game(["Alba", "Bruno"])
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
    engine = create_game(["Alba", "Bruno"])
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
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.accion_alimentar_usada = True
    p1.horas_extras_usadas = True

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "A")["habilitada"] is False
    assert _por_id(resultado, "A")["motivo"] == "Ya se usó hoy"
    assert _por_id(resultado, "horas_extras")["habilitada"] is False


# ---------------------------------------------------------------------------
# Accion D (Implementar Mejora): el espacio solo se enciende si el jugador
# puede pagar AL MENOS UNA de las mejoras que todavia no tiene instaladas.
# ---------------------------------------------------------------------------


def test_D_sin_datos_se_apaga_y_el_motivo_habla_de_datos() -> None:
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.datos_investigacion = 0

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "D")["habilitada"] is False
    assert _por_id(resultado, "D")["motivo"] == "Sin Datos para ninguna mejora pendiente"


def test_D_sin_pa_gana_al_motivo_de_datos() -> None:
    # La escalera de motivos es la misma que la de la Accion G: el PA se
    # comprueba antes que el recurso, asi que un jugador sin PA y sin Datos lee
    # "Sin PA" -- lo que primero le impide actuar, no lo ultimo.
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.datos_investigacion = 0
    p1.puntos_accion = 0

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "D")["habilitada"] is False
    assert _por_id(resultado, "D")["motivo"] == "Sin PA"


def test_D_con_todo_instalado_se_apaga_aunque_sobren_datos() -> None:
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.datos_investigacion = 10
    for tecnologia in TecnologiaID:
        p1.tecnologias.activar(tecnologia)

    resultado = acciones_disponibles(engine, p1)

    assert _por_id(resultado, "D")["habilitada"] is False
    assert _por_id(resultado, "D")["motivo"] == "Todas las mejoras ya están instaladas"


def test_D_mide_contra_la_mejora_pendiente_mas_barata_no_contra_el_catalogo() -> None:
    # La Criopreservacion (2 Datos) es la mejora mas barata del catalogo, asi que
    # con exactamente 2 Datos el espacio se enciende... hasta que ya la tienes:
    # entonces el escalon mas barato que queda es 3 y los mismos 2 Datos ya no
    # compran nada. Si la implementacion mirase min(COSTOS_TECNOLOGIA.values())
    # en vez de las pendientes, la segunda mitad de esta prueba fallaria.
    barata = min(COSTOS_TECNOLOGIA[t] for t in TecnologiaID)
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    p1 = engine.players[0]
    p1.datos_investigacion = barata

    assert _por_id(acciones_disponibles(engine, p1), "D")["habilitada"] is True

    mas_barata = min(TecnologiaID, key=lambda t: COSTOS_TECNOLOGIA[t])
    p1.tecnologias.activar(mas_barata)

    resultado = acciones_disponibles(engine, p1)
    assert _por_id(resultado, "D")["habilitada"] is False
    assert _por_id(resultado, "D")["motivo"] == "Sin Datos para ninguna mejora pendiente"
