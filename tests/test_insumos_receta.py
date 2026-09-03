"""
tests/test_insumos_receta.py -- la cuenta de insumos por carta de la carpeta.

Nace de una partida real: el jugador tenia DOS recetas en la Carpeta de Proyectos,
se olvido de la que habia comprado el dia anterior y gasto un Dato en un Pedido de
Urgencia para conseguir algo que ya podia pagar. La carpeta vive en la tercera
sub-zona de `MiTablero.vue` y a 1366x768 cae por debajo del pliegue de scroll, asi
que la senal se movio al sitio donde el jugador mira cuando decide: el espacio de
accion. Para pintarla hace falta saber, CARTA POR CARTA, si los insumos alcanzan.

Lo que este archivo fija:

  1. `engine.agua_requerida` es la fuente unica del descuento de Alta Humedad, y
     lo que `insumos_receta` ensena es exactamente lo que la Accion B cobra. Esta
     es la deriva que motivo el cambio: `ModalB.vue` calculaba el agua en
     TypeScript sin el descuento, asi que en un dia humedo marcaba con una cruz
     una receta que el servidor habria aceptado.
  2. La cuenta es por INSUMOS, nunca por bloqueos del jugador (PA, dado, estacion,
     contaminacion). Esos ya los dice `acciones_disponibles` una vez para la
     accion entera; repetirlos por carta escribiria el mismo motivo dos veces.
  3. Devuelve TODAS las filas, tambien las que si se pueden pagar, porque el
     cliente dibuja la lista completa con sus marcas.
  4. La vista la inyecta SOLO en `carpeta_proyectos`: las del mercado no son de
     nadie y las de estaciones/archivos ya estan pagadas.
"""
from __future__ import annotations

import random

from actions import ActionManager
from bootstrap import create_game
from disponibilidad import insumos_receta
from models import EfectoClimatico, RECIPE_CATALOG
from server.sessions import RoomManager
from server.views import game_state_view


def _partida_sin_efecto_climatico():
    """
    Partida iniciada con el efecto pasivo fijado a NINGUNO.

    `iniciar_dia` roba carta de clima, asi que sin fijarlo estos casos medirian
    el agua contra un descuento que la baraja reparte al azar -- pasarian o
    fallarian segun la tirada. El caso de Alta Humedad pone el efecto a mano.
    """
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    return engine


def _fila(insumos, tipo):
    return next(h for h in insumos["harinas"] if h["tipo"] == tipo)


def _sesion_iniciada():
    random.seed(777)
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo", 2)
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)
    return sesion


# ---------------------------------------------------------------------------
# 1. La cuenta basica
# ---------------------------------------------------------------------------

def test_con_todo_pagado_no_falta_nada() -> None:
    engine = _partida_sin_efecto_climatico()
    jugador = engine.players[0]
    receta = RECIPE_CATALOG["pan_de_campo"]  # Basica: Blanca 100%, 12 tokens de agua

    jugador.reserva_harina["Blanca"] = 100
    jugador.reserva_agua = receta.tokens_agua

    insumos = insumos_receta(engine, jugador, receta)

    assert insumos["completos"] is True
    assert insumos["agua"] == {"necesita": 12, "tiene": 12, "falta": False}
    assert insumos["harinas"] == [
        {"tipo": "Blanca", "necesita": 100, "tiene": 100, "falta": False}
    ]


def test_una_intermedia_senala_la_mitad_que_falta_y_solo_esa() -> None:
    # Con una Intermedia "te falta harina" no dice cual comprar: es justo el caso
    # que obliga a devolver una fila por tipo en vez de un booleano.
    engine = _partida_sin_efecto_climatico()
    jugador = engine.players[0]
    receta = RECIPE_CATALOG["brioche"]  # Blanca 50% + Centeno 50%

    jugador.reserva_harina["Blanca"] = 50
    jugador.reserva_harina["Centeno"] = 20
    jugador.reserva_agua = 100

    insumos = insumos_receta(engine, jugador, receta)

    assert insumos["completos"] is False
    assert _fila(insumos, "Blanca")["falta"] is False
    assert _fila(insumos, "Centeno") == {
        "tipo": "Centeno",
        "necesita": 50,
        "tiene": 20,
        "falta": True,
    }


def test_el_agua_sola_basta_para_marcar_incompleta() -> None:
    engine = _partida_sin_efecto_climatico()
    jugador = engine.players[0]
    receta = RECIPE_CATALOG["pan_de_campo"]

    jugador.reserva_harina["Blanca"] = 100
    jugador.reserva_agua = receta.tokens_agua - 1

    insumos = insumos_receta(engine, jugador, receta)

    assert insumos["completos"] is False
    assert insumos["agua"]["falta"] is True
    assert all(h["falta"] is False for h in insumos["harinas"])


# ---------------------------------------------------------------------------
# 2. Alta Humedad: el pin de la deriva
# ---------------------------------------------------------------------------

def test_alta_humedad_descuenta_un_token_de_agua() -> None:
    engine = _partida_sin_efecto_climatico()
    jugador = engine.players[0]
    receta = RECIPE_CATALOG["pan_de_campo"]

    jugador.reserva_harina["Blanca"] = 100
    jugador.reserva_agua = receta.tokens_agua - 1

    # Mismo estado de despensa, dos climas: solo cambia el veredicto del agua.
    engine.environment.efecto_pasivo_activo = EfectoClimatico.NINGUNO
    seco = insumos_receta(engine, jugador, receta)

    engine.environment.efecto_pasivo_activo = EfectoClimatico.ALTA_HUMEDAD
    humedo = insumos_receta(engine, jugador, receta)

    assert seco["agua"]["necesita"] == receta.tokens_agua
    assert seco["agua"]["falta"] is True
    assert seco["completos"] is False

    assert humedo["agua"]["necesita"] == receta.tokens_agua - 1
    assert humedo["agua"]["falta"] is False
    assert humedo["completos"] is True


def test_lo_que_se_ensena_es_lo_que_la_accion_B_cobra() -> None:
    # La garantia de fondo: no que las dos cuentas coincidan hoy, sino que solo
    # exista UNA. Si `agua_requerida` cambia, cambian las dos a la vez.
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    acciones = ActionManager(engine)
    receta = jugador.carpeta_proyectos[0]

    engine.environment.efecto_pasivo_activo = EfectoClimatico.ALTA_HUMEDAD
    for tipo, pct in receta.requisito_harina.items():
        jugador.reserva_harina[tipo] = pct
    jugador.reserva_agua = 100
    jugador.vitalidad = max(1, jugador.vitalidad)

    anunciado = insumos_receta(engine, jugador, receta)["agua"]["necesita"]
    agua_antes = jugador.reserva_agua

    acciones.accion_B_iniciar_receta(jugador, receta)

    assert agua_antes - jugador.reserva_agua == anunciado
    assert anunciado == receta.tokens_agua - 1


# ---------------------------------------------------------------------------
# 3. Solo mide insumos, no bloqueos del jugador
# ---------------------------------------------------------------------------

def test_ignora_los_bloqueos_que_ya_dice_la_disponibilidad() -> None:
    engine = _partida_sin_efecto_climatico()
    jugador = engine.players[0]
    receta = RECIPE_CATALOG["pan_de_campo"]

    jugador.reserva_harina["Blanca"] = 100
    jugador.reserva_agua = receta.tokens_agua
    # Sin PA, sin dados y contaminado: la Accion B esta apagada de tres maneras
    # distintas y aun asi la despensa alcanza, que es lo unico que aqui se mide.
    jugador.puntos_accion = 0
    jugador.dados_inoculo = 0
    jugador.vitalidad = 0

    assert insumos_receta(engine, jugador, receta)["completos"] is True


# ---------------------------------------------------------------------------
# 4. La inyeccion de la vista
# ---------------------------------------------------------------------------

def test_la_vista_solo_lo_pone_en_la_carpeta() -> None:
    sesion = _sesion_iniciada()
    engine = sesion.engine
    jugador = engine.players[0]
    acciones = ActionManager(engine)

    # Una masa en marcha para que haya una receta en estacion que comparar.
    receta = jugador.carpeta_proyectos[0]
    for tipo, pct in receta.requisito_harina.items():
        jugador.reserva_harina[tipo] = pct
    jugador.reserva_agua = 100
    acciones.accion_B_iniciar_receta(jugador, receta)
    jugador.carpeta_proyectos.append(RECIPE_CATALOG["pan_de_molde"])

    vista = game_state_view(sesion)
    datos_jugador = vista["players"][0]

    en_carpeta = datos_jugador["carpeta_proyectos"][0]
    assert "insumos" in en_carpeta
    assert en_carpeta["insumos"] == insumos_receta(
        engine, jugador, RECIPE_CATALOG["pan_de_molde"]
    )

    en_estacion = next(e for e in datos_jugador["estaciones_fermentacion"] if e)
    assert "insumos" not in en_estacion["recipe"]

    for carta in vista["market"]["recetas_visibles"]:
        if carta is not None:
            assert "insumos" not in carta
