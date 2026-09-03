"""
tests/test_puntos_horneados.py -- el marcador "en vivo" de puntos de horneado
(`Player.puntos_horneados`) y su viaje al cliente via server/views.py, que
ademas enriquece cada HorneadoRecord del archivo con las @property que
dataclasses.asdict no incluye (`puntos_totales`, `zona_resultado`).
"""
from __future__ import annotations

import random

from models import HorneadoRecord, RECIPE_CATALOG
from server.sessions import RoomManager
from server.views import game_state_view


def _registro(receta_id: str, puntos_base: int, *, bono: bool, colapso: bool) -> HorneadoRecord:
    return HorneadoRecord(
        recipe=RECIPE_CATALOG[receta_id],
        posicion_final=12,
        puntos_base=puntos_base,
        bono_sabor_aplicado=bono,
        fue_colapso=colapso,
        datos_obtenidos=0,
        monedas_obtenidos=3,
    )


def _sesion_iniciada():
    random.seed(777)
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo", 2)
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)
    return sesion


def test_puntos_horneados_suma_exitosos_y_colapsos() -> None:
    sesion = _sesion_iniciada()
    jugador = sesion.engine.players[0]

    exito = _registro("pan_de_campo", 8, bono=True, colapso=False)
    colapso = _registro("focaccia", -3, bono=False, colapso=True)
    jugador.archivo_horneado_exitoso.append(exito)
    jugador.archivo_colapsos.append(colapso)

    # base + bono del exito, mas los puntos (negativos) del colapso.
    assert jugador.puntos_horneados == exito.puntos_totales + colapso.puntos_totales
    assert exito.puntos_totales == 8 + RECIPE_CATALOG["pan_de_campo"].bono_sabor_pts
    assert colapso.puntos_totales == -3


def test_vista_enriquece_los_registros_del_archivo() -> None:
    sesion = _sesion_iniciada()
    jugador = sesion.engine.players[0]
    jugador.archivo_horneado_exitoso.append(_registro("pan_de_campo", 8, bono=False, colapso=False))
    jugador.archivo_colapsos.append(_registro("focaccia", -3, bono=False, colapso=True))

    vista = game_state_view(sesion)
    datos_jugador = vista["players"][0]

    assert datos_jugador["puntos_horneados"] == jugador.puntos_horneados

    registro_exito = datos_jugador["archivo_horneado_exitoso"][0]
    assert registro_exito["puntos_totales"] == 8
    assert registro_exito["zona_resultado"] in ("optima", "baja")

    registro_colapso = datos_jugador["archivo_colapsos"][0]
    assert registro_colapso["puntos_totales"] == -3
    assert registro_colapso["zona_resultado"] == "colapso"
