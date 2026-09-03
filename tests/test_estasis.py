"""
tests/test_estasis.py -- la Estasis Biologica, la valvula de escape de la
Criopreservacion.

El problema que esta accion resuelve: la Accion B SELLA el `dado_inoculo` con
la Vitalidad del dia y ninguna otra accion del juego la BAJA a proposito (el
Descarte solo mueve la Acidez). Quien tiene Criopreservacion y alimenta a
diario sube 2->6 y se queda clavado en 6, asi que sus masas avanzan 9-11
casillas por noche contra las 2-3 casillas de zona optima de una Avanzada: la
mejora que se pago en Datos inhabilitaba el tramo alto del catalogo justo para
su dueno.

Cinco invariantes que este archivo existe para fijar, porque cada uno es un
sitio donde el diseno se puede deshacer en silencio:

  1. La suspension dura UNA noche: la Fase III limpia la bandera despues de
     aplicar el desgaste, de modo que un ajuste olvidado no puede contaminar.
  2. Es un ajuste, no un consumo: no gasta PA, no ocupa espacio de accion, no
     cierra la visita y -- lo importante -- NO mantiene al jugador en la
     rotacion de visitas (`_jugador_elegible`).
  3. La prediccion no puede divergir del efecto: `vitalidad_prevista` y el
     desgaste real leen el mismo `_delta_desgaste`, incluido el -2 de
     Aletargamiento Invernal.
  4. No emite ningun GameEvent. Es una accion de 0 PA, o sea que vive dentro de
     la ventana de deshacer, y `restaurar_checkpoint` reconstruye el motor
     entero: un evento aqui encogeria `engine.eventos` al deshacer y dejaria
     colgados los punteros `since` de los clientes. Es el invariante que
     protege AvisoAccion.
  5. Requiere la tecnologia. Sin Criopreservacion la accion se rechaza, y
     `disponibilidad` apaga el espacio con su motivo.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from disponibilidad import acciones_disponibles
from engine import GameEngine, Market
from events import EventoTipo
from exceptions import InvalidActionError, RuleViolationError
from models import (
    EfectoClimatico,
    Environment,
    Player,
    RECIPE_CATALOG,
)


def _partida(con_crio: bool = True) -> tuple[GameEngine, ActionManager, Player]:
    recetas = list(RECIPE_CATALOG.values())
    p1 = Player.crear_dia_1("Alba", recetas[0])
    p2 = Player.crear_dia_1("Bruno", recetas[1])
    engine = GameEngine([p1, p2], Environment.crear_inicial(), Market.crear_inicial())
    p1.puntos_accion = 2
    p1.tecnologias.criopreservacion = con_crio
    return engine, ActionManager(engine), p1


# ---------------------------------------------------------------------------
# 1. Requisito y validacion
# ---------------------------------------------------------------------------


def test_requiere_criopreservacion() -> None:
    _, manager, p1 = _partida(con_crio=False)
    with pytest.raises(RuleViolationError):
        manager.accion_auxiliar_estasis(p1, suspender=True)
    assert p1.estasis_suspendida is False


def test_suspender_debe_ser_booleano() -> None:
    _, manager, p1 = _partida()
    with pytest.raises(InvalidActionError):
        manager.accion_auxiliar_estasis(p1, suspender="si")  # type: ignore[arg-type]


def test_es_un_interruptor_de_dos_sentidos_e_idempotente() -> None:
    _, manager, p1 = _partida()

    manager.accion_auxiliar_estasis(p1, suspender=True)
    assert p1.estasis_suspendida is True
    manager.accion_auxiliar_estasis(p1, suspender=True)
    assert p1.estasis_suspendida is True
    manager.accion_auxiliar_estasis(p1, suspender=False)
    assert p1.estasis_suspendida is False


def test_no_cuesta_pa_ni_ocupa_espacio_de_accion() -> None:
    _, manager, p1 = _partida()
    pa_antes = p1.puntos_accion

    manager.accion_auxiliar_estasis(p1, suspender=True)

    assert p1.puntos_accion == pa_antes
    assert p1.acciones_pa_usadas_hoy == []


def test_no_cierra_la_visita() -> None:
    """El nonce de turno solo se mueve cuando una visita se cierra de verdad."""
    engine, manager, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None
    activo.tecnologias.criopreservacion = True
    nonce = engine.turno_nonce

    manager.accion_auxiliar_estasis(activo, suspender=True)

    assert engine.turno_nonce == nonce
    assert engine.jugador_activo is activo


# ---------------------------------------------------------------------------
# 2. El efecto sobre el desgaste, y la prediccion que lo anuncia
# ---------------------------------------------------------------------------


def test_la_estasis_activa_sigue_ignorando_el_desgaste() -> None:
    engine, _, p1 = _partida()
    p1.vitalidad = 4
    assert engine._delta_desgaste(p1) == 0
    assert engine.vitalidad_prevista(p1) == 4


def test_suspendida_sufre_el_desgaste_normal() -> None:
    engine, manager, p1 = _partida()
    p1.vitalidad = 4

    manager.accion_auxiliar_estasis(p1, suspender=True)

    assert engine._delta_desgaste(p1) == -1
    assert engine.vitalidad_prevista(p1) == 3


def test_suspendida_bajo_aletargamiento_pierde_dos() -> None:
    """
    El -2 de «Aletargamiento Invernal» tambien alcanza a quien renuncia a su
    Estasis: la suspension devuelve al jugador al desgaste que le tocaria sin
    la mejora, no a un -1 fijo.
    """
    engine, manager, p1 = _partida()
    engine._environment.efecto_pasivo_activo = EfectoClimatico.ALETARGAMIENTO_INVERNAL
    p1.vitalidad = 4

    manager.accion_auxiliar_estasis(p1, suspender=True)

    assert engine._delta_desgaste(p1) == -2
    assert engine.vitalidad_prevista(p1) == 2


def test_la_proyeccion_alterna_enseña_el_ajuste_contrario() -> None:
    """
    Lo que ModalEstasis.vue pinta: las dos cifras de esta noche a la vez, sin
    que el cliente calcule ninguna. Con la Estasis activa la alterna es la del
    desgaste, y viceversa.
    """
    engine, manager, p1 = _partida()
    p1.vitalidad = 5

    assert engine.vitalidad_prevista(p1) == 5
    assert engine.vitalidad_prevista_alterna(p1) == 4

    manager.accion_auxiliar_estasis(p1, suspender=True)

    assert engine.vitalidad_prevista(p1) == 4
    assert engine.vitalidad_prevista_alterna(p1) == 5


def test_suspender_hasta_cero_es_un_riesgo_de_colapso_anunciado() -> None:
    engine, manager, p1 = _partida()
    p1.vitalidad = 1

    assert engine.riesgo_colapso(p1) is False

    manager.accion_auxiliar_estasis(p1, suspender=True)

    assert engine.riesgo_colapso(p1) is True


# ---------------------------------------------------------------------------
# 3. La Fase III: aplica el desgaste y REACTIVA la Estasis
# ---------------------------------------------------------------------------


def test_la_fase_III_desgasta_y_reactiva_la_estasis() -> None:
    engine, manager, p1 = _partida()
    p1.vitalidad = 5

    manager.accion_auxiliar_estasis(p1, suspender=True)
    engine._aplicar_desgaste_metabolico()

    assert p1.vitalidad == 4
    # Reactivada sola: manana vuelve a ignorar el desgaste sin hacer nada.
    assert p1.estasis_suspendida is False
    assert engine._delta_desgaste(p1) == 0


def test_el_evento_de_desgaste_dice_si_la_estasis_estaba_suspendida() -> None:
    """
    La accion no emite nada (ver mas abajo), asi que este evento es el UNICO
    rastro permanente de la suspension -- y el informe de Fase III lo necesita
    para explicar por que un dueno de la Criopreservacion perdio Vitalidad.
    """
    engine, manager, p1 = _partida()
    p1.vitalidad = 5

    manager.accion_auxiliar_estasis(p1, suspender=True)
    engine._aplicar_desgaste_metabolico()

    desgastes = [e for e in engine.eventos if e.tipo == EventoTipo.DESGASTE]
    mio = [e for e in desgastes if e.jugador_idx == 0][-1]
    ajeno = [e for e in desgastes if e.jugador_idx == 1][-1]

    assert mio.datos["estasis_suspendida"] is True
    assert "Estasis suspendida" in mio.mensaje
    assert ajeno.datos["estasis_suspendida"] is False
    assert "Estasis suspendida" not in ajeno.mensaje


# ---------------------------------------------------------------------------
# 4. Los dos invariantes estructurales
# ---------------------------------------------------------------------------


def test_no_emite_ningun_evento() -> None:
    """
    Guardarraíl del invariante de AvisoAccion: una accion de 0 PA ocurre dentro
    de la ventana de deshacer, y restaurar un checkpoint reconstruye el motor
    entero. Un evento aqui encogeria `engine.eventos` al deshacer.
    """
    engine, manager, p1 = _partida()
    antes = len(engine.eventos)

    manager.accion_auxiliar_estasis(p1, suspender=True)
    manager.accion_auxiliar_estasis(p1, suspender=False)

    assert len(engine.eventos) == antes


def test_no_mantiene_al_jugador_en_la_rotacion_de_visitas() -> None:
    """
    Un ajuste no es un recurso. Si la Estasis entrase en `_jugador_elegible`,
    todo dueno de la Criopreservacion cobraria una visita extra cada dia
    quisiera o no -- y ademas seria una clausula sin final, porque el
    interruptor se puede accionar en los dos sentidos indefinidamente.
    """
    engine, _, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None

    activo.tecnologias.criopreservacion = True
    activo.puntos_accion = 0
    activo.accion_alimentar_usada = True
    activo.horas_extras_usadas = True
    activo.datos_investigacion = 0
    activo.monedas = 0
    activo.reserva_agua = 0
    activo.acciones_pa_usadas_hoy = ["E", "descarte"]

    assert not engine._jugador_elegible(engine._players.index(activo))


# ---------------------------------------------------------------------------
# 5. Disponibilidad
# ---------------------------------------------------------------------------


def _estasis(engine: GameEngine, player: Player) -> dict:
    return next(a for a in acciones_disponibles(engine, player) if a["id"] == "estasis")


def test_disponibilidad_apagada_sin_la_mejora() -> None:
    engine, _, p1 = _partida(con_crio=False)
    entrada = _estasis(engine, p1)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "Requiere Criopreservación"


def test_disponibilidad_encendida_con_la_mejora_y_sin_PA() -> None:
    """No tiene puerta de PA: es gratis y se puede accionar hasta el final del dia."""
    engine, _, p1 = _partida()
    p1.puntos_accion = 0
    entrada = _estasis(engine, p1)
    assert entrada["habilitada"] is True
    assert entrada["motivo"] == ""
