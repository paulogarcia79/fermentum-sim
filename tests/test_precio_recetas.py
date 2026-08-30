"""
tests/test_precio_recetas.py -- adquirir una receta cuesta Monedas (Accion G), y
ninguna receta esta restringida por tecnologia.

Las recetas eran lo unico gratis del juego: la Accion G costaba 1 PA y nada mas,
asi que el mercado era una cola y no una economia. A la vez, 7 de las 12 cartas
declaraban `req_tecnologico`, de modo que la mitad interesante del catalogo estaba
fuera de alcance hasta comprar una mejora sin relacion. Este archivo fija el cambio
de un freno por el otro.

Tres cosas que existe para fijar, porque cada una se rompe en silencio:

  1. El precio sale de PRECIO_RECETA[grado] y es ADITIVO sobre el 1 PA. Una sola
     tabla, indexada por un grado que ya derivan las harinas impresas.
  2. Fail-fast REAL: `market.tomar_receta` RETIRA la carta del mercado, asi que
     validar las Monedas despues de tomarla destruiria una carta cada vez que un
     jugador pobre lo intenta. El test comprueba que la carta sigue ahi.
  3. Ninguna puerta tecnologica: `Recipe` ya no tiene donde escribirla.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from bootstrap import create_game
from disponibilidad import acciones_disponibles
from engine import PRECIO_RECETA, GameEngine, Market
from exceptions import MissingResourceError
from models import Environment, Grado, Player, RECIPE_CATALOG, get_recetas_basicas


def _motor() -> tuple[GameEngine, ActionManager, Player]:
    engine = GameEngine(
        players=[
            Player.crear_dia_1("Alba", get_recetas_basicas()[0]),
            Player.crear_dia_1("Bruno", get_recetas_basicas()[1]),
        ],
        environment=Environment.crear_inicial(),
        market=Market.crear_inicial(),
    )
    player = engine.players[0]
    player.puntos_accion = 2
    player.carpeta_proyectos = []
    return engine, ActionManager(engine), player


def _colocar(engine: GameEngine, slot: int, receta_id: str) -> None:
    engine.market.recetas_visibles[slot] = RECIPE_CATALOG[receta_id]


def _disponibilidad_g(engine: GameEngine, player: Player) -> dict:
    return next(a for a in acciones_disponibles(engine, player) if a["id"] == "G")


# ===========================================================================
# 1. El precio, por grado
# ===========================================================================


def test_la_tabla_de_precios_escala_con_el_grado() -> None:
    assert PRECIO_RECETA[Grado.BASICA] == 1
    assert PRECIO_RECETA[Grado.INTERMEDIA] == 2
    assert PRECIO_RECETA[Grado.AVANZADA] == 3
    assert set(PRECIO_RECETA) == set(Grado), "todo grado debe tener precio"


@pytest.mark.parametrize(
    "receta_id",
    ["pan_de_campo", "miche", "pumpernickel"],
    ids=["basica", "intermedia", "avanzada"],
)
def test_accion_G_cobra_el_precio_del_grado(receta_id: str) -> None:
    engine, manager, player = _motor()
    _colocar(engine, 0, receta_id)
    receta = RECIPE_CATALOG[receta_id]
    player.monedas = 10

    manager.accion_G_investigar_protocolo(player, indice_mercado=0)

    assert player.monedas == 10 - PRECIO_RECETA[receta.grado]
    assert player.carpeta_proyectos == [receta]


def test_el_precio_es_aditivo_sobre_el_PA() -> None:
    """El PA sigue siendo la escasez real: el precio no lo sustituye."""
    engine, manager, player = _motor()
    _colocar(engine, 0, "pan_de_campo")
    player.monedas = 10

    manager.accion_G_investigar_protocolo(player, indice_mercado=0)

    assert player.puntos_accion == 1
    assert "G" in player.acciones_pa_usadas_hoy


# ===========================================================================
# 2. Fail-fast: una G rechazada no destruye la carta del mercado
# ===========================================================================


def test_G_sin_monedas_se_rechaza_y_la_carta_sigue_en_el_mercado() -> None:
    """
    El orden importa de verdad: `tomar_receta` retira la carta del mercado. Si el
    cobro se validara despues, cada intento de un jugador sin Monedas borraria una
    carta del mercado para todos.
    """
    engine, manager, player = _motor()
    _colocar(engine, 0, "pumpernickel")
    player.monedas = PRECIO_RECETA[Grado.AVANZADA] - 1

    with pytest.raises(MissingResourceError):
        manager.accion_G_investigar_protocolo(player, indice_mercado=0)

    assert engine.market.recetas_visibles[0] is RECIPE_CATALOG["pumpernickel"]
    assert player.carpeta_proyectos == []
    assert player.puntos_accion == 2
    assert player.monedas == PRECIO_RECETA[Grado.AVANZADA] - 1


def test_alcanza_justo_para_la_carta() -> None:
    engine, manager, player = _motor()
    _colocar(engine, 0, "pumpernickel")
    player.monedas = PRECIO_RECETA[Grado.AVANZADA]

    manager.accion_G_investigar_protocolo(player, indice_mercado=0)

    assert player.monedas == 0


# ===========================================================================
# 3. La receta del Dia 1 es gratis; el mercado no
# ===========================================================================


def test_la_receta_repartida_en_el_setup_no_cuesta_monedas() -> None:
    """Se reparte en la preparacion, no se compra: el patrocinio llega intacto."""
    engine = create_game(["Alba", "Bruno"])
    for player in engine.players:
        assert len(player.carpeta_proyectos) == 1
        assert player.monedas > 0


# ===========================================================================
# 4. disponibilidad: G se apaga si no alcanza para NINGUNA carta visible
# ===========================================================================


def test_G_se_apaga_sin_monedas_para_la_mas_barata_visible() -> None:
    engine, _, player = _motor()
    for slot in range(len(engine.market.recetas_visibles)):
        _colocar(engine, slot, "pumpernickel")
    player.monedas = PRECIO_RECETA[Grado.AVANZADA] - 1

    entrada = _disponibilidad_g(engine, player)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "Sin Monedas para ninguna receta visible"


def test_G_sigue_encendida_si_alcanza_para_la_mas_barata() -> None:
    """
    El minimo se toma sobre las cartas VISIBLES, no sobre el catalogo: con solo
    Avanzadas a la vista, poder pagar una Basica no sirve de nada.
    """
    engine, _, player = _motor()
    for slot in range(len(engine.market.recetas_visibles)):
        _colocar(engine, slot, "pumpernickel")
    _colocar(engine, 2, "pan_de_campo")
    player.monedas = PRECIO_RECETA[Grado.BASICA]

    assert _disponibilidad_g(engine, player)["habilitada"] is True


# ===========================================================================
# 5. Ninguna receta esta restringida por tecnologia
# ===========================================================================


def test_una_avanzada_se_inicia_sin_ninguna_tecnologia() -> None:
    engine, manager, player = _motor()
    receta = RECIPE_CATALOG["pumpernickel"]
    player.carpeta_proyectos = [receta]
    player.vitalidad = 3
    player.dados_inoculo = 3
    player.reserva_agua = receta.tokens_agua + 5
    for tipo, pct in receta.requisito_harina.items():
        player.reserva_harina[tipo] = pct
    assert not player.tecnologias.modulo_analitico

    slot = manager.accion_B_iniciar_receta(player, receta)

    assert slot.recipe is receta
