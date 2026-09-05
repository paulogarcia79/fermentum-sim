"""
tests/test_robustness.py -- prueba las tres piezas de la Milestone 6:
pase forzado de un jugador inactivo, limpieza de salas ociosas, y
persistencia duradera en disco (server/persistence.py).

conftest.py redirige server.persistence.DATA_DIR a un directorio temporal
por prueba (autouse), asi que estas pruebas pueden escribir/leer archivos
reales sin tocar el data/games/ del propio repositorio.
"""
from __future__ import annotations

import time

import pytest

from server import persistence
from server.errors import NoActiveTurnError, PlayerNotInactiveError
from server.sessions import (
    RoomManager,
    RoomStatus,
    UMBRAL_INACTIVIDAD_SEGUNDOS,
    UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS,
)


def _sala_en_curso(salas: RoomManager):
    sesion, _anfitrion = salas.crear_sala("Alba", "rojo")
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)
    return sesion


# ===========================================================================
# Pase forzado por inactividad
# ===========================================================================


def test_forzar_pase_falla_si_el_jugador_no_esta_inactivo() -> None:
    salas = RoomManager()
    sesion = _sala_en_curso(salas)

    with pytest.raises(PlayerNotInactiveError):
        sesion.forzar_pase_por_inactividad()


def test_forzar_pase_funciona_tras_el_umbral_de_inactividad() -> None:
    salas = RoomManager()
    sesion = _sala_en_curso(salas)
    jugador_activo_idx = sesion.engine.players.index(sesion.engine.jugador_activo)
    sesion.seats[jugador_activo_idx].last_seen = time.time() - UMBRAL_INACTIVIDAD_SEGUNDOS - 1

    sesion.forzar_pase_por_inactividad()

    assert sesion.engine.jugador_activo is not sesion.engine.players[jugador_activo_idx]


def test_forzar_pase_sin_turno_activo_lanza_error() -> None:
    salas = RoomManager()
    sesion, _anfitrion = salas.crear_sala("Alba", "rojo")  # aun en LOBBY, sin engine

    with pytest.raises(NoActiveTurnError):
        sesion.forzar_pase_por_inactividad()


# ===========================================================================
# Limpieza de salas inactivas
# ===========================================================================


def test_limpiar_inactivas_elimina_solo_las_realmente_ociosas() -> None:
    salas = RoomManager()
    vieja, _a = salas.crear_sala("Alba", "rojo")
    nueva, _b = salas.crear_sala("Carla", "azul")

    vieja.creado_en = time.time() - UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS - 1
    vieja.seats[0].last_seen = vieja.creado_en

    eliminadas = salas.limpiar_inactivas()

    assert eliminadas == [vieja.id]
    with pytest.raises(Exception):
        salas.obtener(vieja.id)
    salas.obtener(nueva.id)  # no lanza: sigue existiendo


def test_limpiar_inactivas_respeta_el_umbral_mas_largo_de_partidas_en_curso() -> None:
    salas = RoomManager()
    sesion = _sala_en_curso(salas)
    # Inactiva mas alla del umbral de LOBBY pero NO del de EN_CURSO (mucho mas largo).
    hace = time.time() - UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS - 10
    for asiento in sesion.seats:
        asiento.last_seen = hace

    eliminadas = salas.limpiar_inactivas()

    assert eliminadas == []
    assert sesion.status == RoomStatus.EN_CURSO
    salas.obtener(sesion.id)  # sigue existiendo


def test_limpiar_inactivas_borra_tambien_el_snapshot_en_disco() -> None:
    salas = RoomManager()
    sesion, _a = salas.crear_sala("Alba", "rojo")
    sesion.creado_en = time.time() - UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS - 1
    sesion.seats[0].last_seen = sesion.creado_en

    ruta = persistence.DATA_DIR / f"{sesion.id}.pkl"
    assert ruta.exists()  # crear_sala ya persiste

    salas.limpiar_inactivas()

    assert not ruta.exists()


# ===========================================================================
# Persistencia duradera (pickle en disco)
# ===========================================================================


def test_guardar_y_cargar_todas_recupera_una_partida_en_curso() -> None:
    salas = RoomManager()
    sesion = _sala_en_curso(salas)
    jugador_antes = sesion.engine.jugador_activo.nombre
    eventos_antes = len(sesion.engine.eventos)

    recuperadas = list(persistence.cargar_todas())

    assert len(recuperadas) == 1
    restaurada = recuperadas[0]
    assert restaurada.id == sesion.id
    assert restaurada.status == RoomStatus.EN_CURSO
    assert restaurada.engine.jugador_activo.nombre == jugador_antes
    assert len(restaurada.engine.eventos) == eventos_antes
    assert restaurada.suscriptores == []  # nunca se restauran suscriptores SSE viejos


def test_privada_sobrevive_al_viaje_por_disco() -> None:
    """`RoomManager.salas_abiertas` lee `privada` en cada peticion del listado
    publico, asi que una sala restaurada sin ese atributo no rompe su propia
    fila: rompe la portada entera. Por eso el pickle se versiona (ver
    persistence.VERSION_FORMATO), y por eso esto se comprueba."""
    salas = RoomManager()
    salas.crear_sala("Nil", "verde", privada=True)
    publica, _a = salas.crear_sala("Alba", "rojo")

    salas_nuevas = RoomManager()
    for sesion in persistence.cargar_todas():
        salas_nuevas.restaurar(sesion)

    # La publica se lista y la privada no: el filtro sigue leyendo bien el
    # atributo despues del viaje por disco, y la publica esta ahi para que la
    # asercion no pueda pasar simplemente por una lista vacia.
    assert [s.id for s in salas_nuevas.salas_abiertas()] == [publica.id]


def test_el_patrocinio_sobrevive_al_viaje_por_disco() -> None:
    """`Player.patrocinio` es un campo nuevo del pickle (VERSION_FORMATO 20): la
    app lo revela al arrancar y `types.ts` lo espera en cada snapshot, asi que
    una sesion restaurada tiene que traerlo intacto, no como `None`."""
    salas = RoomManager()
    sesion = _sala_en_curso(salas)
    cartas = [p.patrocinio for p in sesion.engine.players]
    assert all(c is not None for c in cartas)

    salas_nuevas = RoomManager()
    for restaurada in persistence.cargar_todas():
        salas_nuevas.restaurar(restaurada)

    recuperada = salas_nuevas.obtener(sesion.id)
    assert [p.patrocinio for p in recuperada.engine.players] == cartas


def test_partida_restaurada_sigue_siendo_jugable() -> None:
    """La prueba de fuego: tras 'reiniciar' (recargar desde disco), la
    partida debe seguir aceptando acciones y avanzando turnos con
    normalidad -- no solo mostrar el estado congelado."""
    salas_originales = RoomManager()
    sesion = _sala_en_curso(salas_originales)

    salas_nuevas = RoomManager()
    for restaurada in persistence.cargar_todas():
        salas_nuevas.restaurar(restaurada)

    sesion_restaurada = salas_nuevas.obtener(sesion.id)
    jugador = sesion_restaurada.engine.jugador_activo
    sesion_restaurada.engine.pasar_turno(jugador)

    assert sesion_restaurada.engine.jugador_activo is not None
    assert sesion_restaurada.engine.turno_nonce == 1


def test_cargar_todas_descarta_un_archivo_con_version_de_formato_distinta() -> None:
    salas = RoomManager()
    salas.crear_sala("Alba", "rojo")

    import pickle

    ruta = next(persistence.DATA_DIR.glob("*.pkl"))
    version, sesion = pickle.loads(ruta.read_bytes())
    ruta.write_bytes(pickle.dumps((version + 1, sesion)))

    recuperadas = list(persistence.cargar_todas())

    assert recuperadas == []
    assert not ruta.exists()  # se descarta el archivo obsoleto, no se deja ahi
