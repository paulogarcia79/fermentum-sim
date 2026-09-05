"""
tests/test_registro_acciones.py -- El registro de movimientos de la partida
===========================================================================

Cubre ``GameSession.registro_acciones`` (server/sessions.py:EntradaRegistro):
el log append-only de qué hizo cada jugador, que el panel "Registro" del
cliente intercala con los eventos automáticos del motor.

Las dos propiedades que dan forma al diseño y que se pinchan aquí:

1. **Vive fuera del motor, así que un deshacer no lo encoge.** Es la misma
   razón por la que ``AvisoAccion`` no es un ``GameEvent``: las acciones
   gratuitas ocurren dentro de la ventana de deshacer y
   ``restaurar_checkpoint`` hace ``pickle.loads`` del motor entero, así que
   una entrada dentro de ``engine.eventos`` haría ENCOGER su longitud y
   dejaría el puntero ``since`` de cada cliente por delante del servidor.
   ``test_registro_no_altera_el_log_de_eventos`` lo afirma desde este lado.

2. **Append-only.** Deshacer marca (``deshecha``) y anexa; no borra. Un
   tablero que "des-ocurre" sin dejar rastro es peor que una línea tachada,
   sobre todo para los rivales que ya oyeron el sonido de la acción.

Y el detalle de ordenación: ``pos_eventos`` se toma ANTES de la mutación,
porque la Acción F emite su ``HORNEADO`` durante el propio despacho y
"Horneó X" debe leerse por delante de ese evento
(``test_pos_eventos_de_hornear_precede_a_su_evento``).
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Tuple

from starlette.testclient import TestClient

from actions import ActionManager
from bootstrap import create_game
from engine import MONEDAS_MOSTRADOR
from events import EventoTipo
from models import RECIPE_CATALOG, FermentationSlot, TecnologiaID, TipoHarina
from server import persistence
from server.app import crear_app
from server.commands import describir_accion, resolver_comando
from server.sessions import UMBRAL_INACTIVIDAD_SEGUNDOS, RoomManager, RoomStatus


def _partida_2p() -> Tuple[TestClient, str, Dict[str, str], Any]:
    """Sala de 2 jugadores ya empezada, más la GameSession viva."""
    random.seed(21)
    cliente = TestClient(crear_app())

    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    d = r.json()
    room_id, host_token = d["room_id"], d["host_token"]
    tokens = {"Alba": d["player_token"], "host": host_token}

    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
    tokens["Bruno"] = r.json()["player_token"]

    cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    sesion = cliente.app.state.salas.obtener(room_id)  # type: ignore[attr-defined]
    return cliente, room_id, tokens, sesion


def _token_en_turno(cliente: TestClient, room_id: str, tokens: Dict[str, str]) -> str:
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    return tokens["Alba"] if r.json()["jugador_en_turno_idx"] == 0 else tokens["Bruno"]


def _otro_token(cliente: TestClient, room_id: str, tokens: Dict[str, str]) -> str:
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    return tokens["Bruno"] if r.json()["jugador_en_turno_idx"] == 0 else tokens["Alba"]


def _accion(cliente, room_id, token, accion, params=None):
    return cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": accion, "params": params or {}},
    )


def _alimentar(cliente, room_id, token):
    return _accion(cliente, room_id, token, "A", {"harina": {"Blanca": 10}})


def _ids(sesion) -> List[str]:
    return [e.accion for e in sesion.registro_acciones]


# ===========================================================================
# Anexado básico
# ===========================================================================


def test_accion_aceptada_agrega_una_entrada() -> None:
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)
    idx = sesion.engine.players.index(sesion.engine.jugador_activo)

    assert _alimentar(cliente, room_id, token).status_code == 200

    assert len(sesion.registro_acciones) == 1
    entrada = sesion.registro_acciones[0]
    assert entrada.seq == 1
    assert entrada.accion == "A"
    assert entrada.jugador_idx == idx
    assert entrada.dia == 1
    assert entrada.deshecha is False
    assert entrada.mensaje == "Alimentó el cultivo con Blanca"


def test_accion_rechazada_no_agrega_nada() -> None:
    """Mismo orden que protege al checkpoint: la entrada se anexa DESPUÉS de
    que la mutación tuvo éxito, así que una acción rechazada no deja línea."""
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)

    r = _accion(cliente, room_id, token, "A", {"harina": {"Trigo Sarraceno": 10}})

    assert r.status_code >= 400
    assert sesion.registro_acciones == []


def test_la_vista_incluye_el_registro() -> None:
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)
    assert _alimentar(cliente, room_id, token).status_code == 200

    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    registro = r.json()["registro_acciones"]

    assert len(registro) == len(sesion.registro_acciones)
    entrada = sesion.registro_acciones[0]
    assert registro[0] == {
        "seq": entrada.seq,
        "accion": entrada.accion,
        "jugador_idx": entrada.jugador_idx,
        "dia": entrada.dia,
        "pos_eventos": entrada.pos_eventos,
        "mensaje": entrada.mensaje,
        "deshecha": entrada.deshecha,
    }


# ===========================================================================
# Pasar, deshacer y pase forzado
# ===========================================================================


def test_pasar_y_deshacer_dejan_su_propia_linea() -> None:
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)

    assert _alimentar(cliente, room_id, token).status_code == 200
    assert cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token}).status_code == 200
    assert cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": token}).status_code == 200

    assert _ids(sesion) == ["A", "deshacer", "pasar"]
    assert [e.deshecha for e in sesion.registro_acciones] == [True, False, False]
    assert sesion.registro_acciones[1].mensaje == "Deshizo su visita"
    assert sesion.registro_acciones[2].mensaje == "Pasó el turno"


def test_pase_forzado_tiene_id_propio_y_nombra_a_quien_lo_forzo() -> None:
    """El AvisoAccion sigue siendo "pasar" (es el canal de sonido, y un pase
    forzado suena igual); solo el registro los distingue, porque solo él
    necesita decir quién lo forzó."""
    cliente, room_id, tokens, sesion = _partida_2p()
    idx_activo = sesion.engine.players.index(sesion.engine.jugador_activo)
    solicitante = _otro_token(cliente, room_id, tokens)
    nombre_solicitante = next(a.nombre for a in sesion.seats if a.token == solicitante)
    # Después de resolver los tokens: cada petición autenticada refresca
    # `last_seen`, así que envejecer antes de consultar el estado no serviría.
    sesion.seats[idx_activo].last_seen = time.time() - UMBRAL_INACTIVIDAD_SEGUNDOS - 1

    r = cliente.post(f"/games/{room_id}/force-pass", headers={"X-Player-Token": solicitante})
    assert r.status_code == 200, r.text

    assert _ids(sesion) == ["pase_forzado"]
    entrada = sesion.registro_acciones[0]
    assert entrada.jugador_idx == idx_activo  # a quién se lo pasaron
    assert f"forzó {nombre_solicitante}" in entrada.mensaje


def test_deshacer_marca_solo_la_visita_en_curso() -> None:
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)

    assert _alimentar(cliente, room_id, token).status_code == 200
    assert _accion(
        cliente, room_id, token, "descarte", {"operacion": "subir", "niveles": 1}
    ).status_code == 200
    assert cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token}).status_code == 200

    assert _ids(sesion) == ["A", "descarte", "deshacer"]
    assert [e.deshecha for e in sesion.registro_acciones] == [True, True, False]

    # Segunda visita gratuita + deshacer: el checkpoint se re-toma con la
    # longitud NUEVA, así que el segundo deshacer solo alcanza lo nuevo.
    assert _alimentar(cliente, room_id, token).status_code == 200
    assert cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token}).status_code == 200

    assert _ids(sesion) == ["A", "descarte", "deshacer", "A", "deshacer"]
    assert [e.deshecha for e in sesion.registro_acciones] == [True, True, False, True, False]


# ===========================================================================
# Ordenación frente al log de eventos
# ===========================================================================


def test_pos_eventos_de_hornear_precede_a_su_evento() -> None:
    """Acción F emite HORNEADO durante el despacho, así que su entrada debe
    apuntar al índice de ESE evento -- se lee justo por delante de él."""
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)
    jugador = sesion.engine.jugador_activo
    receta = jugador.carpeta_proyectos[0]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta,
        dado_inoculo=1,
        posicion_track=receta.zona_optima[0],
        bono_sabor=False,
        modificador_incubadora=0,
    )
    eventos_antes = len(sesion.engine.eventos)

    r = _accion(cliente, room_id, token, "F", {"slot_index": 0})
    assert r.status_code == 200, r.text

    entrada = next(e for e in sesion.registro_acciones if e.accion == "F")
    assert entrada.pos_eventos == eventos_antes
    assert sesion.engine.eventos[entrada.pos_eventos].tipo == EventoTipo.HORNEADO
    assert entrada.mensaje.startswith("Horneó ")


def test_registro_no_altera_el_log_de_eventos() -> None:
    """El invariante de AvisoAccion, dicho desde el otro lado: el registro
    crece con cada movimiento y ``engine.eventos`` no se entera -- ni siquiera
    tras un deshacer, que reemplaza el motor entero."""
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)
    antes = len(sesion.engine.eventos)

    assert _alimentar(cliente, room_id, token).status_code == 200
    assert len(sesion.engine.eventos) == antes

    assert cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token}).status_code == 200
    # `sesion.engine` es un objeto NUEVO tras restaurar el checkpoint.
    assert len(sesion.engine.eventos) == antes
    assert len(sesion.registro_acciones) == 2


# ===========================================================================
# Persistencia y reinicio
# ===========================================================================


def test_persistencia_conserva_el_registro() -> None:
    cliente, room_id, tokens, sesion = _partida_2p()
    token = _token_en_turno(cliente, room_id, tokens)
    assert _alimentar(cliente, room_id, token).status_code == 200
    original = list(sesion.registro_acciones)
    marca = sesion.checkpoint_registro_len

    recuperadas = {s.id: s for s in persistence.cargar_todas()}
    restaurada = recuperadas[room_id]

    assert restaurada.registro_acciones == original
    assert restaurada.checkpoint_registro_len == marca
    # Y sigue siendo funcional: deshacer sobre la sesión recargada marca lo
    # que anexó la visita, igual que antes de morir el proceso.
    restaurada.restaurar_checkpoint()
    assert [e.deshecha for e in restaurada.registro_acciones] == [True]


def test_reiniciar_a_lobby_vacia_el_registro() -> None:
    salas = RoomManager()
    sesion, _ = salas.crear_sala("Alba", "rojo")
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)
    sesion.registrar_accion("A", 0, "Alimentó el cultivo con Blanca", 0)
    sesion.status = RoomStatus.TERMINADA

    sesion.reiniciar_a_lobby(sesion.host_token)

    assert sesion.registro_acciones == []


# ===========================================================================
# Redacción de los mensajes
# ===========================================================================


def _motor_y_jugador():
    random.seed(7)
    engine = create_game(["Alba", "Bruno"])
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    return engine, ActionManager(engine), jugador


def _describir(engine, manager, jugador, accion, params):
    resultado = resolver_comando(engine, manager, jugador, accion, params)
    return describir_accion(engine, jugador, accion, params, resultado)


def test_mensaje_de_mercado_enumera_cada_transaccion() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 60
    params = {
        "transacciones": [
            {"tipo_recurso": "Centeno", "operacion": "comprar"},
            {"tipo_recurso": "Blanca", "operacion": "vender_media"},
            {"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": 30},
        ]
    }
    jugador.reserva_harina[TipoHarina.BLANCA.value] = 100

    mensaje = _describir(engine, manager, jugador, "C", params)

    assert mensaje == (
        "Mercado: compró una bolsa de Centeno · vendió media bolsa de Blanca "
        "· compró un lote de agua del 30%"
    )


def test_mensaje_de_mejora_usa_el_nombre_legible() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.datos_investigacion = 10

    mensaje = _describir(
        engine, manager, jugador, "D", {"tecnologia": TecnologiaID.CAMARA_B.value}
    )

    assert mensaje == f"Instaló {TecnologiaID.CAMARA_B.nombre_legible}"


def test_mensaje_del_mostrador_nombra_la_moneda() -> None:
    """`describir_accion` revienta en TIEMPO DE EJECUCION para una accion sin
    rama (su AssertionError final), no al importar: una accion nueva sin linea
    de registro solo se descubre jugandola. De ahi este caso."""
    engine, manager, jugador = _motor_y_jugador()

    mensaje = _describir(engine, manager, jugador, "mostrador", {})

    assert mensaje == f"Atendió el mostrador (+{MONEDAS_MOSTRADOR} Moneda)"


def test_mensaje_de_pliegues_detalla_el_reparto() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 30
    receta = jugador.carpeta_proyectos[0]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=receta, dado_inoculo=1, posicion_track=1
    )

    mensaje = _describir(
        engine, manager, jugador, "E", {"opcion": "avanzar", "reparto": {"0": 2}}
    )

    assert mensaje == "Pliegues: +2 en Estación 1"


def test_mensaje_de_pliegues_con_vitalidad() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 30
    jugador.vitalidad = 1
    jugador.tecnologias.camara_b = True  # la variante de Vitalidad la exige

    mensaje = _describir(
        engine, manager, jugador, "E", {"opcion": "recuperar_vitalidad", "reparto": {}}
    )

    assert mensaje == "Pliegues: recuperó +1 Vitalidad"


def test_mensaje_del_descarte_nombra_recurso_y_sentido() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.reserva_agua = 40
    subir = _describir(
        engine, manager, jugador, "descarte", {"operacion": "subir", "niveles": 1}
    )
    assert subir == "Descarte: Acidez +1 (2 tokens de agua)"

    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 40
    jugador.acidez = 4
    bajar = _describir(
        engine, manager, jugador, "descarte", {"operacion": "bajar", "niveles": 1}
    )
    assert bajar.startswith("Descarte: Acidez −1 (")
    assert bajar.endswith("Monedas)")


def test_mensaje_de_la_estasis_en_sus_dos_sentidos() -> None:
    """
    La Estasis es el unico interruptor del juego, asi que su linea del registro
    tiene que decir HACIA DONDE se movio: "suspendio" y "reactivo" describen
    estados opuestos de la misma noche y una sola frase generica no serviria.
    """
    engine, manager, jugador = _motor_y_jugador()
    jugador.tecnologias.criopreservacion = True

    suspender = _describir(engine, manager, jugador, "estasis", {"suspender": True})
    assert suspender == "Suspendió la Estasis Biológica por esta noche"

    reactivar = _describir(engine, manager, jugador, "estasis", {"suspender": False})
    assert reactivar == "Reactivó la Estasis Biológica"


def test_mensaje_de_la_incubadora_nombra_la_masa_y_el_sentido() -> None:
    """
    El dial es por masa, asi que la linea tiene que decir SOBRE CUAL se movio:
    con dos o tres estaciones ocupadas, "ajusto la Incubadora" no le dice nada a
    un oponente que solo ve el registro. Y el 0 se redacta aparte porque quitar
    un ajuste es un movimiento distinto de ponerlo.
    """
    engine, manager, jugador = _motor_y_jugador()
    jugador.tecnologias.incubadora = True
    jugador.estaciones_fermentacion[1] = FermentationSlot(
        recipe=RECIPE_CATALOG["pan_de_molde"],
        dado_inoculo=1,
        posicion_track=3,
        bono_sabor=False,
        acidez_inicial=1,
    )

    frena = _describir(
        engine, manager, jugador, "incubadora", {"slot_index": 1, "modificador": -1}
    )
    assert frena == "Incubadora: Est-02 (Pan de Molde) a -1 esta noche"

    quita = _describir(
        engine, manager, jugador, "incubadora", {"slot_index": 1, "modificador": 0}
    )
    assert quita == "Incubadora: Est-02 (Pan de Molde) sin ajuste"


def test_mensaje_del_pedido_de_urgencia_en_sus_dos_ramas() -> None:
    from actions import AGUA_PEDIDO_URGENCIA

    engine, manager, jugador = _motor_y_jugador()
    jugador.datos_investigacion = 5
    agua = _describir(engine, manager, jugador, "pedido_urgencia", {"recurso": "agua"})
    assert agua == f"Pedido de Urgencia: {AGUA_PEDIDO_URGENCIA} tokens de agua"

    engine, manager, jugador = _motor_y_jugador()
    jugador.datos_investigacion = 5
    harina = _describir(
        engine,
        manager,
        jugador,
        "pedido_urgencia",
        {"recurso": "harina", "harina": "Centeno"},
    )
    assert harina == "Pedido de Urgencia: media bolsa de Centeno"


def test_mensaje_del_simposio_en_sus_dos_modos() -> None:
    """La ponencia no retira ninguna carta, asi que su linea no puede nombrar
    una: dice lo que costo, que es la unica cifra que el modo aporta."""
    from engine import DATOS_SIMPOSIO, PRECIO_DATO_SIMPOSIO
    from models import Grado, HorneadoRecord, RECIPE_CATALOG

    basica = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA)

    def registro():
        return HorneadoRecord(
            recipe=basica,
            posicion_final=basica.zona_optima[0],
            puntos_base=basica.puntos_optimos,
            bono_sabor_aplicado=False,
            fue_colapso=False,
            datos_obtenidos=0,
            monedas_obtenidos=0,
            ampliacion_aplicada=0,
        )

    engine, manager, jugador = _motor_y_jugador()
    jugador.archivo_horneado_exitoso = [registro()]
    jugador.monedas = 30
    ponencia = _describir(
        engine, manager, jugador, "simposio", {"modo": "ponencia", "datos": 2}
    )
    assert ponencia == (
        f"Presentó una ponencia en el Simposio "
        f"(+2 Datos, -{2 * PRECIO_DATO_SIMPOSIO} Monedas)"
    )

    engine, manager, jugador = _motor_y_jugador()
    jugador.archivo_horneado_exitoso = [registro()]
    sacrificio = _describir(
        engine, manager, jugador, "simposio", {"modo": "sacrificar", "indice": 0}
    )
    assert sacrificio == (
        f"Publicó {basica.nombre} en el Simposio "
        f"(+{DATOS_SIMPOSIO[Grado.BASICA]} Datos)"
    )


def test_mensaje_de_iniciar_receta_nombra_la_estacion() -> None:
    engine, manager, jugador = _motor_y_jugador()
    receta = jugador.carpeta_proyectos[0]
    for tipo, pct in receta.harinas:
        jugador.reserva_harina[tipo.value] = 100
    jugador.reserva_agua = 60

    mensaje = _describir(engine, manager, jugador, "B", {"carpeta_index": 0})

    assert mensaje.startswith(f"Inició {receta.nombre} en Estación ")


def test_mensaje_de_investigar_nombra_la_receta_tomada() -> None:
    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 40
    esperada = engine.market.recetas_visibles[0]

    mensaje = _describir(engine, manager, jugador, "G", {"indice_mercado": 0})

    assert mensaje == f"Investigó el protocolo {esperada.nombre}"


def test_mensaje_de_investigar_a_ciegas_dice_que_salio_del_mazo() -> None:
    """
    La carta robada es publica en cuanto entra en la carpeta, pero de donde
    salio no se ve en ningun otro sitio: el registro es el unico rastro de que
    alguien pago a ciegas en vez de elegir de la mesa.
    """
    engine, manager, jugador = _motor_y_jugador()
    jugador.monedas = 40
    esperada = engine.market.mazo_recetas[0]

    mensaje = _describir(engine, manager, jugador, "G", {"origen": "mazo"})

    assert mensaje == f"Investigó a ciegas el protocolo {esperada.nombre} (robado del mazo)"
