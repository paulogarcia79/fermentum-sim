"""
tests/test_mostrador.py -- «Turno de Mostrador»: el suelo del tablero
(ACTIONS_REGISTRY.md §2 «Mostrador», engine.MONEDAS_MOSTRADOR).

Un jugador podia tener PA y ninguna jugada util -- carpeta vacia, masa aun en
Crecimiento, 0 Monedas, 0 Datos y la Jefatura ya reclamada por otro -- y su
unica salida era `pasar_turno`, que ademas renuncia a las acciones gratuitas del
resto del dia. Los PA sobrantes se perdian en silencio: la Fase III nunca lee
`puntos_accion`.

Los cuatro invariantes que este fichero existe para fijar, en orden de cuanto
duele romperlos:

1. **No ocupa espacio de accion.** Es la unica accion con costo de PA que se
   puede repetir el mismo dia, y es deliberado: un jugador tiene 2 PA y el hueco
   puede darse dos veces. Un espacio de una visita por dia resolveria la mitad
   del problema. `"mostrador"` nunca entra en `acciones_pa_usadas_hoy`.
2. **Esta siempre disponible teniendo PA**, sin condiciones. No se apaga porque
   el jugador tenga otras cosas que hacer: esa condicion no es observable (la
   Accion C figura habilitada casi siempre) y un guardia asi quitaria el suelo
   justo cuando hace falta. Se autolimita siendo debil, no estando cerrada.
3. **Cuesta PA de verdad y termina la visita**, como toda accion Principal.
4. **Sigue disponible con la Jefatura ya reclamada por otro**, que es el caso
   que motivo la accion: la Jefatura es el otro sumidero de PA siempre visible,
   pero es global, asi que solo salva al primero que la toma.
"""
from __future__ import annotations

import random

import pytest

from actions import ActionManager
from bootstrap import create_game
from disponibilidad import acciones_disponibles
from engine import MONEDAS_MOSTRADOR, GameEngine
from exceptions import NotEnoughActionPointsError


def _motor() -> GameEngine:
    random.seed(4321)
    return create_game(["Alba", "Bruno"])


def _por_id(resultado, id_):
    return next(a for a in resultado if a["id"] == id_)


# ---------------------------------------------------------------------------
# Lo que cuesta y lo que paga
# ---------------------------------------------------------------------------


def test_cuesta_un_pa_y_paga_monedas() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    pa_antes, monedas_antes = jugador.puntos_accion, jugador.monedas

    manager.accion_turno_mostrador(jugador)

    assert jugador.puntos_accion == pa_antes - 1
    assert jugador.monedas == monedas_antes + MONEDAS_MOSTRADOR


def test_sin_pa_se_rechaza_y_no_muta_nada() -> None:
    """Fail-fast: valida antes de tocar el estado, como toda ActionManager."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.puntos_accion = 0
    monedas_antes = jugador.monedas

    with pytest.raises(NotEnoughActionPointsError):
        manager.accion_turno_mostrador(jugador)

    assert jugador.monedas == monedas_antes
    assert jugador.puntos_accion == 0


def test_no_necesita_recursos_de_ningun_tipo() -> None:
    """El suelo tiene que estar ahi para un jugador arruinado del todo: es
    exactamente el estado que motivo la accion."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.monedas = 0
    jugador.datos_investigacion = 0
    jugador.reserva_agua = 0
    jugador.reserva_harina = {tipo: 0 for tipo in jugador.reserva_harina}
    jugador.carpeta_proyectos.clear()

    manager.accion_turno_mostrador(jugador)

    assert jugador.monedas == MONEDAS_MOSTRADOR


# ---------------------------------------------------------------------------
# El invariante principal: no ocupa espacio, luego se repite
# ---------------------------------------------------------------------------


def test_no_ocupa_espacio_de_accion() -> None:
    """La unica accion con costo de PA fuera de `acciones_pa_usadas_hoy`. Si
    algun dia entra ahi, deja de poder repetirse y el segundo PA vuelve a
    quedarse hueco."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo

    manager.accion_turno_mostrador(jugador)

    assert "mostrador" not in jugador.acciones_pa_usadas_hoy
    assert jugador.acciones_pa_usadas_hoy == []


def test_se_puede_repetir_hasta_agotar_los_pa() -> None:
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.puntos_accion = 2
    monedas_antes = jugador.monedas

    manager.accion_turno_mostrador(jugador)
    manager.accion_turno_mostrador(jugador)

    assert jugador.puntos_accion == 0
    assert jugador.monedas == monedas_antes + 2 * MONEDAS_MOSTRADOR

    with pytest.raises(NotEnoughActionPointsError):
        manager.accion_turno_mostrador(jugador)


def test_el_pa_extra_de_horas_extras_tambien_sirve() -> None:
    """La cadena completa: 1 Dato -> +1 PA -> 1 Moneda. Es legal y es
    deliberadamente mal negocio -- un Dato vale mucho mas que una Moneda -- lo
    que confirma que el Mostrador no abre ningun bucle de recursos."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.datos_investigacion = 1
    jugador.puntos_accion = 0

    manager.accion_auxiliar_horas_extras(jugador)
    manager.accion_turno_mostrador(jugador)

    assert jugador.puntos_accion == 0
    assert jugador.datos_investigacion == 0


# ---------------------------------------------------------------------------
# Disponibilidad: el suelo, siempre que haya PA
# ---------------------------------------------------------------------------


def test_disponible_con_pa_y_apagada_sin_pa() -> None:
    engine = _motor()
    engine.iniciar_dia()
    jugador = engine.jugador_activo

    entrada = _por_id(acciones_disponibles(engine, jugador), "mostrador")
    assert entrada["habilitada"] is True

    jugador.puntos_accion = 0
    entrada = _por_id(acciones_disponibles(engine, jugador), "mostrador")
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "Sin PA"


def test_sigue_disponible_tras_usarla_el_mismo_dia() -> None:
    """El espejo en `disponibilidad.py` del invariante de arriba: si algun dia
    consultara `acciones_pa_usadas_hoy`, la casilla se apagaria tras el primer
    uso y el cliente mentiria sobre una accion que el motor si acepta."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    jugador.puntos_accion = 2

    manager.accion_turno_mostrador(jugador)

    assert _por_id(acciones_disponibles(engine, jugador), "mostrador")["habilitada"] is True


def test_sigue_disponible_aunque_otro_tenga_la_jefatura() -> None:
    """El caso que motivo la accion. La Jefatura era el otro sumidero de PA
    siempre visible, pero es un espacio GLOBAL: solo salva al primero que llega.
    El segundo jugador se quedaba sin nada, y ahi es donde entra el Mostrador."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    primero = engine.jugador_activo
    manager.accion_reclamar_jefatura(primero)
    engine.terminar_turno_actual()

    segundo = engine.jugador_activo
    assert segundo is not primero
    assert _por_id(acciones_disponibles(engine, segundo), "jefatura")["habilitada"] is False
    assert _por_id(acciones_disponibles(engine, segundo), "mostrador")["habilitada"] is True


def test_un_jugador_sin_ninguna_otra_accion_conserva_el_mostrador() -> None:
    """El hueco entero, reproducido: sin recursos, sin recetas, sin masas y con
    la Jefatura tomada, el Mostrador es lo unico que queda encendido de todo lo
    que cuesta PA. Antes, aqui solo se podia pasar turno."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    primero = engine.jugador_activo
    manager.accion_reclamar_jefatura(primero)
    engine.terminar_turno_actual()

    jugador = engine.jugador_activo
    jugador.monedas = 0
    jugador.datos_investigacion = 0
    jugador.reserva_agua = 0
    jugador.reserva_harina = {tipo: 0 for tipo in jugador.reserva_harina}
    jugador.carpeta_proyectos.clear()

    encendidas = {
        a["id"] for a in acciones_disponibles(engine, jugador) if a["habilitada"]
    }
    # C sigue encendida porque `disponibilidad` no simula transacciones: es
    # justamente por eso que el Mostrador no puede condicionarse a "no tener
    # nada mejor que hacer" -- esa condicion no es observable.
    assert "mostrador" in encendidas


# ---------------------------------------------------------------------------
# El dia: termina la visita y no sobrevive a la noche
# ---------------------------------------------------------------------------


def test_los_pa_se_reinician_cada_dia() -> None:
    """No acumula nada entre dias: lo unico que persiste es la Moneda."""
    engine = _motor()
    manager = ActionManager(engine)
    engine.iniciar_dia()
    jugador = engine.jugador_activo
    manager.accion_turno_mostrador(jugador)
    monedas = jugador.monedas

    while engine.jugador_activo is not None:
        engine.pasar_turno(engine.jugador_activo)
    engine.resolver_fase_III()
    engine.iniciar_dia()

    assert jugador.puntos_accion == 2
    assert jugador.monedas >= monedas
