"""
tests/test_horas_extras.py -- «Horas Extras» y su marcador neutral
(ACTIONS_REGISTRY.md §3 «Horas Extras», actions.ESPACIOS_CON_MARCADOR_NEUTRAL).

La accion no se usaba, y el motivo no era el precio. El juego valora 1 Dato en
1 Punto de Maestria (`PRECIO_DATO_SIMPOSIO` = 5 Monedas = la tasa de Conversion
de Riqueza) y Reclamar la Jefatura es el trueque INVERSO -- 1 PA por 1 Dato mas
el orden de turno --, de modo que comprar Horas Extras era estar en el lado malo
de un intercambio que la mesa ya ofrecia. Lo que estaba mal era lo que compraba:
por la regla "un espacio, una visita por dia", el 3er PA solo podia pagar un
espacio DISTINTO y sin estrenar, que muchos dias era el Mostrador (1 Moneda) o
nada. El precio no se toco; se anadio el marcador neutral.

Los invariantes que este fichero fija, en orden de cuanto duele romperlos:

1. **Se gasta solo al repetir.** Si el PA extra cae en un espacio libre, el
   jugador conserva el marcador. Es lo que hace que adelantar las Horas Extras
   no castigue nunca, y lo primero que rompe una implementacion del tipo "la
   siguiente accion puede repetir".
2. **Uno por dia, y solo uno.** La tercera visita al mismo espacio falla. El
   marcador vive como la UNICA entrada duplicada de `acciones_pa_usadas_hoy`,
   asi que "solo uno" y "no hay campo nuevo" son la misma frase.
3. **Los tres excluidos.** Jefatura (su bloqueo es de la mesa), Pliegues y
   Descarte (cuestan 0 PA). Cada uno por un motivo distinto, y cada uno seria
   un abuso distinto.
4. **Fail-fast.** Un intento de repetir que falle mas tarde deja el marcador
   intacto: se valida al comprobar el espacio, se gasta al registrar la visita.
"""
from __future__ import annotations

import random

import pytest

from actions import (
    ActionManager,
    COSTOS_TECNOLOGIA,
    ESPACIOS_CON_MARCADOR_NEUTRAL,
)
from bootstrap import create_game
from disponibilidad import acciones_disponibles
from engine import GameEngine
from server.commands import describir_accion
from server.views import game_state_view
from exceptions import (
    EspacioAccionYaUsadoError,
    MissingResourceError,
    RuleViolationError,
)
from models import DATOS_HORAS_EXTRAS, TecnologiaID


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _por_id(resultado, id_):
    return next(a for a in resultado if a["id"] == id_)


def _visitar_mercado(manager: ActionManager, jugador) -> None:
    """Una Accion C barata: comprar media bolsa de Blanca, la mas barata."""
    manager.accion_C_visitar_mercado(
        jugador,
        [{"tipo_recurso": "Blanca", "operacion": "comprar_media"}],
    )


# ---------------------------------------------------------------------------
# 1. Lo que entrega, y que el marcador solo se gasta al repetir
# ---------------------------------------------------------------------------


def test_entrega_pa_y_marcador_por_un_dato() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    pa_antes = jugador.puntos_accion

    manager.accion_auxiliar_horas_extras(jugador)

    assert jugador.puntos_accion == pa_antes + 1
    assert jugador.datos_investigacion == 3 - DATOS_HORAS_EXTRAS
    assert jugador.horas_extras_usadas is True
    assert jugador.marcador_neutral_disponible is True
    assert jugador.espacio_repetido_hoy is None


def test_sin_datos_se_rechaza_y_no_deja_marcador() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 0

    with pytest.raises(MissingResourceError):
        manager.accion_auxiliar_horas_extras(jugador)

    assert jugador.marcador_neutral_disponible is False
    assert jugador.puntos_accion == 2


def test_un_espacio_nuevo_no_gasta_el_marcador() -> None:
    """El invariante 1: el PA extra en una casilla libre NO consume nada.

    Es lo que permite pedir las Horas Extras al principio del turno para
    asegurar el Dato sin arriesgarse a desperdiciar la repeticion.
    """
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)

    assert jugador.acciones_pa_usadas_hoy == ["C"]
    assert jugador.marcador_neutral_disponible is True
    assert jugador.espacio_repetido_hoy is None


def test_repetir_gasta_el_marcador_y_deja_la_entrada_duplicada() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)
    _visitar_mercado(manager, jugador)

    assert jugador.acciones_pa_usadas_hoy == ["C", "C"]
    assert jugador.espacio_repetido_hoy == "C"
    assert jugador.marcador_neutral_disponible is False


def test_la_tercera_visita_al_mismo_espacio_falla() -> None:
    """El invariante 2. Con 3 PA el jugador tiene con que intentarlo."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)
    _visitar_mercado(manager, jugador)
    jugador.puntos_accion = 2  # PA de sobra: lo que corta es el marcador, no el PA

    with pytest.raises(EspacioAccionYaUsadoError):
        _visitar_mercado(manager, jugador)

    assert jugador.acciones_pa_usadas_hoy == ["C", "C"]


def test_sin_horas_extras_repetir_sigue_prohibido() -> None:
    """La regla no se aflojo para todos: sin el marcador, nada cambia."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.monedas = 60

    _visitar_mercado(manager, jugador)

    with pytest.raises(EspacioAccionYaUsadoError):
        _visitar_mercado(manager, jugador)


def test_el_orden_dentro_del_turno_es_indiferente() -> None:
    """Gastar los 2 PA base primero y pedir las Horas Extras despues llega al
    mismo sitio que pedirlas al empezar: el marcador no caduca dentro del dia."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    jugador.tecnologias.criopreservacion = False

    _visitar_mercado(manager, jugador)
    manager.accion_D_implementar_mejora(jugador, TecnologiaID.CRIOPRESERVACION)
    assert jugador.puntos_accion == 0

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)

    assert jugador.espacio_repetido_hoy == "C"
    assert jugador.puntos_accion == 0


# ---------------------------------------------------------------------------
# 2. Los tres excluidos, cada uno por su motivo
# ---------------------------------------------------------------------------


def test_el_conjunto_son_los_ocho_espacios_de_pa_por_jugador() -> None:
    """Pinta el conjunto entero: quitar o anadir un id es una regla, no un
    detalle, y los tres ausentes lo estan cada uno por un motivo distinto."""
    assert ESPACIOS_CON_MARCADOR_NEUTRAL == {
        "B",
        "C",
        "D",
        "F",
        "G",
        "simposio",
        "H",
        "I",
    }
    for excluido in ("jefatura", "E", "descarte", "mostrador"):
        assert excluido not in ESPACIOS_CON_MARCADOR_NEUTRAL


def test_la_jefatura_no_se_repite_ni_con_marcador() -> None:
    """Su bloqueo es de la MESA, no de tu color: el marcador no tiene ahi nada
    que cubrir. El motor la corta antes incluso de mirar el espacio propio."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3

    manager.accion_auxiliar_horas_extras(jugador)
    manager.accion_reclamar_jefatura(jugador)

    with pytest.raises(RuleViolationError):
        manager.accion_reclamar_jefatura(jugador)

    assert jugador.marcador_neutral_disponible is True


def test_los_pliegues_no_se_repiten_ni_gastan_el_marcador() -> None:
    """Cuestan 0 PA: el marcador viaja con una accion de PA y aqui no hay
    ninguna. Dejarlos entrar convertiria 1 Dato en una segunda escalera."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    manager.accion_auxiliar_horas_extras(jugador)

    receta = jugador.carpeta_proyectos[0]
    for harina, pct in receta.harinas:
        jugador.reserva_harina[harina.value] = 100
    jugador.reserva_agua = 40
    manager.accion_B_iniciar_receta(jugador, receta)

    manager.accion_E_tecnica_pliegues(jugador, reparto={0: 1})
    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_E_tecnica_pliegues(jugador, reparto={0: 1})

    assert jugador.marcador_neutral_disponible is True


def test_el_descarte_no_se_repite_ni_gasta_el_marcador() -> None:
    """El Descarte esta cerrado DOS veces, y conviene saberlo.

    Ademas de quedar fuera del conjunto, tiene su propia guarda escrita a mano
    en `accion_descarte_acidez` (un `"descarte" in acciones_pa_usadas_hoy` que
    precede a `_require_espacio_disponible`). Medido: meter "descarte" en el
    conjunto NO abre la repeticion, porque esa guarda la corta antes. Por eso
    lo que aqui se fija de verdad no es el rechazo -- que ocurriria igual --
    sino que el intento **no consume el marcador**, que es lo unico que el
    conjunto decide en este caso.
    """
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    jugador.acidez = 3
    manager.accion_auxiliar_horas_extras(jugador)

    manager.accion_descarte_acidez(jugador, "bajar", 1)
    with pytest.raises(EspacioAccionYaUsadoError):
        manager.accion_descarte_acidez(jugador, "bajar", 1)

    assert jugador.marcador_neutral_disponible is True


# ---------------------------------------------------------------------------
# 3. Fail-fast
# ---------------------------------------------------------------------------


def test_una_repeticion_que_falla_despues_no_gasta_el_marcador() -> None:
    """El invariante 4: se valida al comprobar el espacio, se gasta al
    registrar la visita, asi que entre medias no se pierde nada."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)

    # Segunda visita a C, pero sin Monedas para pagarla: el espacio la deja
    # pasar y la transaccion la rechaza.
    jugador.monedas = 0
    with pytest.raises(MissingResourceError):
        _visitar_mercado(manager, jugador)

    assert jugador.acciones_pa_usadas_hoy == ["C"]
    assert jugador.marcador_neutral_disponible is True


# ---------------------------------------------------------------------------
# 4. Disponibilidad: la casilla no puede mentir
# ---------------------------------------------------------------------------


def test_la_casilla_repetible_sigue_encendida_hasta_gastar_el_marcador() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)

    assert _por_id(acciones_disponibles(engine, jugador), "C")["habilitada"] is True

    _visitar_mercado(manager, jugador)

    fila = _por_id(acciones_disponibles(engine, jugador), "C")
    assert fila["habilitada"] is False
    assert fila["motivo"] == "Ya usaste este espacio hoy"


def test_sin_marcador_la_casilla_usada_se_apaga_como_siempre() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.monedas = 60

    _visitar_mercado(manager, jugador)

    assert _por_id(acciones_disponibles(engine, jugador), "C")["habilitada"] is False


def test_el_espacio_de_descarte_no_se_reenciende_con_el_marcador() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    jugador.acidez = 3
    manager.accion_auxiliar_horas_extras(jugador)

    manager.accion_descarte_acidez(jugador, "bajar", 1)

    fila = _por_id(acciones_disponibles(engine, jugador), "descarte")
    assert fila["habilitada"] is False
    assert fila["motivo"] == "Ya usaste este espacio hoy"


def test_el_espacio_de_pliegues_no_se_reenciende_con_el_marcador() -> None:
    """A diferencia del Descarte, los Pliegues NO tienen guarda propia: aqui el
    conjunto es lo unico que los protege, y por eso este es el pin que importa
    de los dos."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    manager.accion_auxiliar_horas_extras(jugador)

    receta = jugador.carpeta_proyectos[0]
    for harina, _pct in receta.harinas:
        jugador.reserva_harina[harina.value] = 100
    jugador.reserva_agua = 40
    manager.accion_B_iniciar_receta(jugador, receta)
    manager.accion_E_tecnica_pliegues(jugador, reparto={0: 1})

    fila = _por_id(acciones_disponibles(engine, jugador), "E")
    assert fila["habilitada"] is False
    assert fila["motivo"] == "Ya usaste este espacio hoy"


# ---------------------------------------------------------------------------
# 6. El dia siguiente
# ---------------------------------------------------------------------------


def test_el_marcador_se_limpia_al_empezar_el_dia() -> None:
    """No hay codigo que lo limpie: vive en `acciones_pa_usadas_hoy`, que la
    Fase II vacia, y en la bandera, que `resetear_puntos_accion` apaga."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)
    _visitar_mercado(manager, jugador)
    assert jugador.espacio_repetido_hoy == "C"

    for p in engine.players:
        engine.pasar_turno(p)
    engine.resolver_fase_III()
    engine.iniciar_dia()

    assert jugador.acciones_pa_usadas_hoy == []
    assert jugador.espacio_repetido_hoy is None
    assert jugador.marcador_neutral_disponible is False


# ---------------------------------------------------------------------------
# 7. Lo que sale por el cable
# ---------------------------------------------------------------------------


def test_el_registro_marca_la_repeticion_y_solo_la_repeticion() -> None:
    """La coletilla se reconoce contando la entrada duplicada, que solo puede
    existir una: si tras la accion el id aparece dos veces, la repeticion es
    ESTA. La primera visita al mismo espacio no la lleva."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    params = {"transacciones": [{"tipo_recurso": "Blanca", "operacion": "comprar_media"}]}

    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)
    primera = describir_accion(engine, jugador, "C", params, None)
    assert "marcador neutral" not in primera

    _visitar_mercado(manager, jugador)
    segunda = describir_accion(engine, jugador, "C", params, None)
    assert segunda.endswith("repitió el espacio con el marcador neutral de Horas Extras")


def test_la_linea_de_horas_extras_anuncia_el_marcador() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3

    manager.accion_auxiliar_horas_extras(jugador)
    frase = describir_accion(engine, jugador, "horas_extras", {}, None)

    assert "marcador neutral" in frase
    assert f"−{DATOS_HORAS_EXTRAS} Dato" in frase


def test_la_vista_publica_los_dos_campos() -> None:
    """Son @property, asi que `dataclasses.asdict` no los trae: si nadie los
    inyecta en `views.py`, el peon gris no se puede dibujar."""
    from server.sessions import RoomManager

    salas = RoomManager()
    sala, _host = salas.crear_sala("Alba", color="rojo")
    salas.unirse(sala.id, "Bruno", color="verde")
    salas.iniciar(sala.id, sala.host_token)
    engine = sala.engine
    manager = ActionManager(engine)
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 3
    jugador.monedas = 60
    manager.accion_auxiliar_horas_extras(jugador)
    _visitar_mercado(manager, jugador)
    _visitar_mercado(manager, jugador)

    vista = game_state_view(sala)
    fila = vista["players"][engine.players.index(jugador)]

    assert fila["espacio_repetido_hoy"] == "C"
    assert fila["marcador_neutral_disponible"] is False
