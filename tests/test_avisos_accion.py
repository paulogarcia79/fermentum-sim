"""
tests/test_avisos_accion.py -- el canal efímero de acciones de jugador
(``server/sessions.py:AvisoAccion``), que es lo que permite al cliente sonar
un efecto distinto por acción y refrescar el estado en el acto.

Es un canal aparte del log de eventos, y las dos propiedades que lo hacen
seguro son justo lo que se prueba aquí:

  · Un frame de aviso NO lleva línea ``id:``, así que el navegador no mueve
    su ``Last-Event-ID`` -- un aviso no puede descolocar el puntero de resume
    del log de eventos, que es un índice dentro de ``engine.eventos``.
  · Un aviso NO entra en ``engine.eventos``, así que un deshacer (que hace
    ``pickle.loads`` del motor entero) no puede dejar el puntero de ningún
    cliente por delante del servidor. El último test es el guardarraíl de ese
    invariante: si algún día una acción gratuita empezara a emitir un
    ``GameEvent``, ese test se pone rojo antes de que nadie lo note en vivo.

Igual que en tests/test_sse.py, el generador SSE no se consume de extremo a
extremo (el TestClient de Starlette se cuelga con un ``StreamingResponse``
genuinamente abierto): se observa la difusión enganchando una cola falsa a la
``GameSession`` viva, y el formato de frame se prueba sobre la función pura.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from starlette.testclient import TestClient

from events import EventoTipo, GameEvent
from models import RECIPE_CATALOG, FermentationSlot, HorneadoRecord
from server.app import _formatear_sse, _formatear_sse_aviso, crear_app
from server.sessions import AvisoAccion


class _ColaFalsa:
    """Sustituto de asyncio.Queue: difundir_* solo usa put_nowait()."""

    def __init__(self) -> None:
        self.recibidos: List[Any] = []

    def put_nowait(self, item: Any) -> None:
        self.recibidos.append(item)

    def acciones(self) -> List[str]:
        return [i.accion for i in self.recibidos if isinstance(i, AvisoAccion)]


def _partida_iniciada() -> Tuple[TestClient, str, Dict[str, str], Any]:
    """Sala de 2 jugadores ya empezada. Devuelve tambien la GameSession viva
    (via app.state.salas) para poder engancharle un suscriptor falso."""
    random.seed(21)
    cliente = TestClient(crear_app())

    r = cliente.post("/games", json={"nombre": "Alba", "color": "rojo"})
    d = r.json()
    room_id, host_token = d["room_id"], d["host_token"]
    tokens = {"Alba": d["player_token"]}

    r = cliente.post(f"/games/{room_id}/join", json={"nombre": "Bruno", "color": "azul"})
    tokens["Bruno"] = r.json()["player_token"]

    cliente.post(f"/games/{room_id}/start", headers={"X-Player-Token": host_token})
    sesion = cliente.app.state.salas.obtener(room_id)  # type: ignore[attr-defined]
    return cliente, room_id, tokens, sesion


def _token_del_jugador_en_turno(cliente: TestClient, room_id: str, tokens: Dict[str, str]) -> str:
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    idx = r.json()["jugador_en_turno_idx"]
    return tokens["Alba"] if idx == 0 else tokens["Bruno"]


def _indice_del_jugador_en_turno(cliente: TestClient, room_id: str, tokens: Dict[str, str]) -> int:
    r = cliente.get(f"/games/{room_id}/state", headers={"X-Player-Token": tokens["Alba"]})
    return int(r.json()["jugador_en_turno_idx"])


def _sembrar_horneado(sesion: Any, jugador_idx: int) -> None:
    """Mete un horneado exitoso en el archivo del jugador indicado.

    El Simposio Técnico exige sacrificar uno y el Día 1 nadie tiene ninguno.
    Se toca el engine vivo directamente porque lo que este módulo prueba es el
    canal de avisos, no cómo se llega a tener un horneado.
    """
    jugador = sesion.engine.players[jugador_idx]
    receta = jugador.carpeta_proyectos[0]
    jugador.archivo_horneado_exitoso.append(
        HorneadoRecord(
            recipe=receta,
            posicion_final=receta.zona_optima[0],
            puntos_base=receta.puntos_optimos,
            bono_sabor_aplicado=False,
            fue_colapso=False,
            datos_obtenidos=1,
            monedas_obtenidos=receta.monedas_optima,
            ampliacion_aplicada=0,
        )
    )


# ---------------------------------------------------------------------------
# Formato de frame
# ---------------------------------------------------------------------------


def test_frame_de_aviso_no_lleva_id_y_va_por_su_propio_canal() -> None:
    """La propiedad que sostiene todo el diseño: sin `id:`, el navegador no
    mueve Last-Event-ID; con `event: accion`, el frame llega a un listener
    propio y no al onmessage del log de eventos."""
    frame = _formatear_sse_aviso(AvisoAccion(accion="C", jugador_idx=1))

    assert frame.startswith("event: accion\n")
    assert "id:" not in frame
    assert '"accion": "C"' in frame
    assert '"jugador_idx": 1' in frame

    # Contraste con un evento del log, que sí numera.
    evento = GameEvent(tipo=EventoTipo.CLIMA_REVELADO, dia=1, jugador_idx=None, mensaje="x")
    assert _formatear_sse(7, evento).startswith("id: 7\n")


# ---------------------------------------------------------------------------
# Difusión
# ---------------------------------------------------------------------------


def test_difundir_accion_llega_a_todos_los_suscriptores() -> None:
    _cliente, _room_id, _tokens, sesion = _partida_iniciada()
    cola_1, cola_2 = _ColaFalsa(), _ColaFalsa()
    sesion.suscriptores.extend([cola_1, cola_2])

    sesion.difundir_accion("F", 1)

    esperado = AvisoAccion(accion="F", jugador_idx=1)
    assert cola_1.recibidos == [esperado]
    assert cola_2.recibidos == [esperado]


def test_accion_valida_difunde_un_aviso() -> None:
    cliente, room_id, tokens, sesion = _partida_iniciada()
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)

    # Simposio Técnico: sacrifica un horneado exitoso del archivo por Datos.
    # El Día 1 nadie ha horneado todavia, asi que se siembra un registro en el
    # engine vivo — sigue siendo la accion con menos precondiciones de recursos.
    _sembrar_horneado(sesion, _indice_del_jugador_en_turno(cliente, room_id, tokens))

    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "simposio", "params": {"modo": "sacrificar", "indice": 0}},
    )
    assert r.status_code == 200, r.text
    assert cola.acciones() == ["simposio"]


def test_accion_rechazada_no_difunde_nada() -> None:
    """Fail-fast: ActionManager valida y revienta antes de mutar, asi que una
    acción rechazada no debe sonar en ninguna pestaña."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Índice de archivo inexistente -> el Simposio revienta antes de tocar nada.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "simposio", "params": {"modo": "sacrificar", "indice": 99}},
    )
    assert r.status_code >= 400
    assert cola.acciones() == []


def test_pasar_y_deshacer_tambien_difunden() -> None:
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Acción gratuita (no cierra la visita) -> deja checkpoint -> se puede deshacer.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"harina": {"Blanca": 10}}},
    )
    assert r.status_code == 200, r.text

    r = cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text

    r = cliente.post(f"/games/{room_id}/pass", headers={"X-Player-Token": token})
    assert r.status_code == 200, r.text

    assert cola.acciones() == ["A", "deshacer", "pasar"]


# ---------------------------------------------------------------------------
# El invariante que obligó a que esto NO fuera un GameEvent
# ---------------------------------------------------------------------------


def test_accion_gratuita_y_deshacer_no_alteran_el_log_de_eventos() -> None:
    """Guardarraíl: los avisos no entran en engine.eventos, asi que deshacer
    (un pickle.loads del motor entero) no puede encoger el log y dejar el
    puntero `since` de un cliente por delante del servidor."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    antes = len(sesion.engine.eventos)

    cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "A", "params": {"harina": {"Blanca": 10}}},
    )
    assert len(sesion.engine.eventos) == antes

    cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    # `sesion.engine` es un objeto NUEVO tras restaurar el checkpoint.
    assert len(sesion.engine.eventos) == antes


def test_descarte_y_deshacer_no_alteran_el_log_de_eventos() -> None:
    """
    Mismo invariante para «Descarte». Es la razon por la que la accion NO emite
    ningun GameEvent pese a cambiar estado visible: al ser 0 PA vive dentro de
    la ventana de deshacer, y `restaurar_checkpoint` repone el motor desde un
    pickle -- un evento suyo haria ENCOGER `engine.eventos` al deshacer.
    """
    cliente, room_id, tokens, sesion = _partida_iniciada()
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    antes = len(sesion.engine.eventos)

    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "descarte", "params": {"operacion": "bajar", "niveles": 1}},
    )
    assert r.status_code == 200, r.text
    assert len(sesion.engine.eventos) == antes

    cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert len(sesion.engine.eventos) == antes


def test_estasis_y_deshacer_no_alteran_el_log_de_eventos() -> None:
    """
    Mismo invariante para «Estasis Biológica», y aquí importa doblemente: la
    accion cambia una bandera que la Fase III LEE esa misma noche, asi que la
    tentacion de anunciarla con un GameEvent es real. No lo hace -- al ser 0 PA
    vive dentro de la ventana de deshacer, y `restaurar_checkpoint` repone el
    motor desde un pickle, de modo que un evento suyo haria ENCOGER
    `engine.eventos`. El rastro lo deja el DESGASTE de la Fase III.
    """
    cliente, room_id, tokens, sesion = _partida_iniciada()
    idx = _indice_del_jugador_en_turno(cliente, room_id, tokens)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    sesion.engine.players[idx].tecnologias.criopreservacion = True
    antes = len(sesion.engine.eventos)

    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "estasis", "params": {"suspender": True}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["players"][idx]["estasis_suspendida"] is True
    # La proyeccion que ve el cliente ya refleja el desgaste de esta noche.
    jugador = r.json()["players"][idx]
    assert jugador["vitalidad_prevista"] == max(0, jugador["vitalidad"] - 1)
    assert len(sesion.engine.eventos) == antes

    cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert len(sesion.engine.eventos) == antes


def test_incubadora_y_deshacer_no_alteran_el_log_de_eventos() -> None:
    """
    Mismo invariante para el dial de la Incubadora, y por el mismo motivo que la
    Estasis: escribe un campo que la Fase III LEE esa misma noche, asi que la
    tentacion de anunciarlo con un GameEvent es real. No lo hace -- al ser 0 PA
    vive dentro de la ventana de deshacer, y `restaurar_checkpoint` repone el
    motor desde un pickle, de modo que un evento suyo haria ENCOGER
    `engine.eventos`. El rastro lo deja el MASA_AVANZO de la Fase III.
    """
    cliente, room_id, tokens, sesion = _partida_iniciada()
    idx = _indice_del_jugador_en_turno(cliente, room_id, tokens)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    jugador = sesion.engine.players[idx]
    jugador.tecnologias.incubadora = True
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=RECIPE_CATALOG["pan_de_molde"],
        dado_inoculo=1,
        posicion_track=3,
        bono_sabor=False,
        acidez_inicial=1,
    )
    antes = len(sesion.engine.eventos)

    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "incubadora", "params": {"slot_index": 0, "modificador": -1}},
    )
    assert r.status_code == 200, r.text
    estaciones = r.json()["players"][idx]["estaciones_fermentacion"]
    assert estaciones[0]["modificador_incubadora"] == -1
    assert len(sesion.engine.eventos) == antes

    cliente.post(f"/games/{room_id}/undo", headers={"X-Player-Token": token})
    assert len(sesion.engine.eventos) == antes


def test_incubadora_emite_su_aviso_y_lo_rechazado_no_suena() -> None:
    """El canal efimero: la accion suena en todas las pestañas, pero una
    rechazada (sin la mejora instalada) no emite ningun aviso."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    idx = _indice_del_jugador_en_turno(cliente, room_id, tokens)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    jugador = sesion.engine.players[idx]
    jugador.estaciones_fermentacion[0] = FermentationSlot(
        recipe=RECIPE_CATALOG["pan_de_molde"],
        dado_inoculo=1,
        posicion_track=3,
        bono_sabor=False,
        acidez_inicial=1,
    )
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Sin la Incubadora: rechazada, y por tanto muda.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "incubadora", "params": {"slot_index": 0, "modificador": -1}},
    )
    assert r.status_code >= 400
    assert "incubadora" not in cola.acciones()

    jugador.tecnologias.incubadora = True
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "incubadora", "params": {"slot_index": 0, "modificador": -1}},
    )
    assert r.status_code == 200, r.text
    assert cola.acciones() == ["incubadora"]


def test_estasis_emite_su_aviso_y_lo_rechazado_no_suena() -> None:
    """El canal efimero: la accion suena en todas las pestañas, pero una
    rechazada (sin la mejora instalada) no emite ningun aviso."""
    cliente, room_id, tokens, sesion = _partida_iniciada()
    idx = _indice_del_jugador_en_turno(cliente, room_id, tokens)
    token = _token_del_jugador_en_turno(cliente, room_id, tokens)
    cola = _ColaFalsa()
    sesion.suscriptores.append(cola)

    # Sin Criopreservación: rechazada, y por tanto muda.
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "estasis", "params": {"suspender": True}},
    )
    assert r.status_code >= 400
    assert "estasis" not in cola.acciones()

    sesion.engine.players[idx].tecnologias.criopreservacion = True
    r = cliente.post(
        f"/games/{room_id}/actions",
        headers={"X-Player-Token": token},
        json={"accion": "estasis", "params": {"suspender": True}},
    )
    assert r.status_code == 200, r.text
    assert cola.acciones() == ["estasis"]
