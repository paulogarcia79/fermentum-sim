"""
tests/test_patrocinio.py -- la Carta de Patrocinio sobrevive al reparto.

`bootstrap.create_game` desmenuzaba la carta en `Player.crear_dia_1` y la tiraba:
lo unico que quedaba era la permutacion del Dia 1, y un jugador no tenia forma
de saber que carta le habia tocado ni por que salia en la posicion que salia.
Ahora la carta queda en `Player.patrocinio` como registro para la interfaz, que
la revela al arrancar la partida. Ninguna regla la lee despues del Dia 1.

Lo que se comprueba aqui nunca se habia afirmado: que la carta que un jugador
conserva es exactamente la que le pago sus recursos (el mapeo `dealt[i] ->
players[i]`), que no hay dos iguales en la mesa, y que el orden del Dia 1 es el
que sus iniciativas dictan -- sin meter la mano en `_orden_inicial_iniciativa`.
"""
from __future__ import annotations

import random

from bootstrap import create_game
from models import PATROCINIO_CATALOG, Player, PatrocinioCard, get_recetas_basicas
from server.sessions import RoomManager
from server.views import game_state_view


def test_cada_jugador_conserva_la_carta_que_le_pago_sus_recursos() -> None:
    for semilla in range(20):
        random.seed(semilla)
        engine = create_game(["Alba", "Bruno", "Cloe", "Dani"])
        for jugador in engine.players:
            carta = jugador.patrocinio
            assert isinstance(carta, PatrocinioCard)
            assert carta in PATROCINIO_CATALOG
            assert jugador.monedas == carta.monedas
            assert jugador.datos_investigacion == carta.datos
            assert jugador.reserva_agua == carta.agua_tokens
            assert jugador.reserva_harina[carta.tipo_harina.value] == carta.harina_pct


def test_no_hay_dos_cartas_iguales_en_la_mesa() -> None:
    for semilla in range(20):
        random.seed(semilla)
        engine = create_game(["Alba", "Bruno", "Cloe", "Dani"])
        iniciativas = [p.patrocinio.iniciativa for p in engine.players]
        assert len(set(iniciativas)) == len(iniciativas)


def test_el_orden_del_dia_1_es_el_de_las_iniciativas() -> None:
    """La afirmacion publica de la regla: `turno_orden` es lo que la vista
    envia, y tiene que ser los indices ordenados por la iniciativa de la carta
    que cada jugador conserva."""
    for semilla in range(20):
        random.seed(semilla)
        engine = create_game(["Alba", "Bruno", "Cloe"])
        engine.iniciar_dia()
        esperado = sorted(
            range(len(engine.players)),
            key=lambda i: engine.players[i].patrocinio.iniciativa,
        )
        assert engine.turno_orden == esperado
        assert engine.jefe_investigador is engine.players[esperado[0]]


def test_un_jugador_construido_sin_carta_no_tiene_patrocinio() -> None:
    jugador = Player.crear_dia_1("Alba", get_recetas_basicas()[0])
    assert jugador.patrocinio is None


def test_la_vista_envia_la_carta_de_cada_jugador() -> None:
    """Viaja por `serialization.snapshot` (es un campo, no una @property), asi
    que la vista no tiene que inyectar nada -- pero la forma del diccionario es
    lo que `types.ts` espeja, y eso si hay que fijarlo."""
    salas = RoomManager()
    sesion, _anfitrion = salas.crear_sala("Alba", "rojo")
    salas.unirse(sesion.id, "Bruno", "azul")
    salas.iniciar(sesion.id, sesion.host_token)

    vista = game_state_view(sesion)
    for jugador, fila in zip(sesion.engine.players, vista["players"]):
        carta = fila["patrocinio"]
        assert set(carta) == {
            "iniciativa", "tipo_harina", "harina_pct", "agua_tokens", "monedas", "datos",
        }
        assert carta["iniciativa"] == jugador.patrocinio.iniciativa
        assert carta["tipo_harina"] == jugador.patrocinio.tipo_harina.value
