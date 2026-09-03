"""
tests/test_incubadora.py -- el dial de avance de la Incubadora, masa por masa y
noche a noche.

El problema que esta accion resuelve, encontrado en una partida de prueba: el
`modificador_incubadora` se elegia en la Accion B y quedaba SELLADO en la masa
para siempre. Quien instalaba la Incubadora con una masa ya fermentando no podia
tocar su dial -- era un 0 que ninguna accion del juego alcanzaba --, asi que veia
colapsar esa masa sin poder frenarla, con la mejora recien pagada en Datos
puesta encima de la mesa. El reglamento ya prometia un ajuste "masa por masa" en
la Fase III; esto es lo que lo cumple.

Seis invariantes que este archivo existe para fijar, porque cada uno es un sitio
donde el diseno se puede deshacer en silencio:

  1. El dial se puede mover sobre una masa que empezo ANTES de instalar la
     mejora. Es el caso del playtest y la razon de ser del cambio entero.
  2. El ajuste dura UNA noche: la Fase III lo aplica y lo devuelve a 0, de modo
     que un dial olvidado no puede empujar una masa al colapso manana.
  3. Es un ajuste, no un consumo: no gasta PA, no ocupa espacio de accion, no
     cierra la visita y -- lo importante -- NO mantiene al jugador en la
     rotacion de visitas (`_jugador_elegible`).
  4. No emite ningun GameEvent. Es una accion de 0 PA, o sea que vive dentro de
     la ventana de deshacer, y `restaurar_checkpoint` reconstruye el motor
     entero: un evento aqui encogeria `engine.eventos` y dejaria colgados los
     punteros `since` de los clientes. Es el invariante que protege AvisoAccion.
     El rastro permanente lo deja el MASA_AVANZO de la Fase III.
  5. Frena de verdad y acelera de verdad: un -1 salva una masa que colapsaria y
     un +1 puede tirar una al colapso. El riesgo se permite a proposito.
  6. La Accion B ya no acepta el parametro. Un solo escritor para el campo.
"""
from __future__ import annotations

import pytest

from actions import ActionManager
from disponibilidad import acciones_disponibles
from engine import GameEngine, Market
from events import EventoTipo
from exceptions import InvalidActionError, RuleViolationError
from models import (
    Environment,
    FermentationSlot,
    Player,
    RECIPE_CATALOG,
    TecnologiaID,
    get_recetas_basicas,
)


def _partida(con_incubadora: bool = True) -> tuple[GameEngine, ActionManager, Player]:
    engine = GameEngine(
        players=[
            Player.crear_dia_1("Alba", get_recetas_basicas()[0]),
            Player.crear_dia_1("Bruno", get_recetas_basicas()[1]),
        ],
        environment=Environment.crear_inicial(),
        market=Market.crear_inicial(),
    )
    p1 = engine.players[0]
    p1.puntos_accion = 2
    p1.tecnologias.incubadora = con_incubadora
    return engine, ActionManager(engine), p1


def _masa(
    player: Player, receta_id: str, posicion: int, estacion: int = 0, dado: int = 1
) -> FermentationSlot:
    slot = FermentationSlot(
        recipe=RECIPE_CATALOG[receta_id],
        dado_inoculo=dado,
        posicion_track=posicion,
        bono_sabor=False,
        acidez_inicial=1,
    )
    player.estaciones_fermentacion[estacion] = slot
    return slot


# ---------------------------------------------------------------------------
# 1. Requisito y validacion
# ---------------------------------------------------------------------------


def test_requiere_la_tecnologia() -> None:
    _, manager, p1 = _partida(con_incubadora=False)
    slot = _masa(p1, "pan_de_molde", 3)

    with pytest.raises(RuleViolationError):
        manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    assert slot.modificador_incubadora == 0


def test_modificador_fuera_de_rango_se_rechaza() -> None:
    _, manager, p1 = _partida()
    slot = _masa(p1, "pan_de_molde", 3)

    for valor in (-2, 2, 5):
        with pytest.raises(InvalidActionError):
            manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=valor)

    assert slot.modificador_incubadora == 0


def test_estacion_vacia_o_inexistente_se_rechaza() -> None:
    _, manager, p1 = _partida()
    _masa(p1, "pan_de_molde", 3, estacion=0)

    # Estacion sin masa.
    with pytest.raises(RuleViolationError):
        manager.accion_auxiliar_incubadora(p1, slot_index=1, modificador=-1)
    # Estacion que no existe.
    with pytest.raises(RuleViolationError):
        manager.accion_auxiliar_incubadora(p1, slot_index=7, modificador=-1)


def test_el_dial_es_de_dos_sentidos_e_idempotente() -> None:
    _, manager, p1 = _partida()
    slot = _masa(p1, "pan_de_molde", 3)

    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)
    assert slot.modificador_incubadora == -1
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)
    assert slot.modificador_incubadora == -1
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=1)
    assert slot.modificador_incubadora == 1
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=0)
    assert slot.modificador_incubadora == 0


def test_cada_masa_lleva_su_propio_dial() -> None:
    """
    Es un ajuste por masa, no por jugador: con Camara B se tienen tres masas en
    posiciones distintas y el sentido de la mejora es frenar una mientras se
    empuja otra.
    """
    _, manager, p1 = _partida()
    a = _masa(p1, "pan_de_molde", 3, estacion=0)
    b = _masa(p1, "focaccia", 10, estacion=1)

    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=1, modificador=-1)

    assert a.modificador_incubadora == 1
    assert b.modificador_incubadora == -1


# ---------------------------------------------------------------------------
# 2. El caso del playtest: instalar la mejora con la masa ya en marcha
# ---------------------------------------------------------------------------


def test_ajusta_una_masa_que_empezo_antes_de_instalar_la_incubadora() -> None:
    """
    El bug original. La masa nace con el dial en 0 y la mejora llega despues:
    con el modificador sellado en la Accion B no habia forma de tocarlo, y la
    Incubadora recien comprada no servia para nada sobre lo que ya estaba en el
    tablero.
    """
    engine, manager, p1 = _partida(con_incubadora=False)
    slot = _masa(p1, "focaccia", 3)
    assert slot.modificador_incubadora == 0

    # La mejora se instala AHORA, con la masa ya fermentando.
    p1.datos_investigacion = 99
    p1.puntos_accion = 2
    manager.accion_D_implementar_mejora(p1, TecnologiaID.INCUBADORA)

    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    assert slot.modificador_incubadora == -1
    # Y el freno llega a la Fase III de esta misma noche.
    posicion_antes = slot.posicion_track
    engine._avanzar_masas_jugador(p1)
    esperado = (
        posicion_antes
        + engine._environment.temperatura_actual // 5
        + slot.dado_inoculo
        - 1
    )
    assert p1.estaciones_fermentacion[0] is not None
    assert p1.estaciones_fermentacion[0].posicion_track == esperado


# ---------------------------------------------------------------------------
# 3. La Fase III: aplica el dial y lo devuelve a 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("modificador", [-1, 0, 1])
def test_la_fase_III_aplica_el_dial(modificador: int) -> None:
    engine, manager, p1 = _partida()
    slot = _masa(p1, "pan_de_molde", 2, dado=2)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=modificador)

    engine._avanzar_masas_jugador(p1)

    vivo = p1.estaciones_fermentacion[0]
    assert vivo is not None
    esperado = 2 + engine._environment.temperatura_actual // 5 + 2 + modificador
    assert vivo.posicion_track == esperado


def test_el_dial_vuelve_a_cero_tras_aplicarse() -> None:
    """
    Dura una sola noche, como la suspension de la Estasis. Sin este reseteo un
    +1 puesto para adelantar una masa seguiria empujandola cada noche hasta el
    colapso, que es exactamente el fallo que esta accion vino a arreglar.
    """
    engine, manager, p1 = _partida()
    slot = _masa(p1, "pan_de_molde", 1, dado=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    engine._avanzar_masas_jugador(p1)

    vivo = p1.estaciones_fermentacion[0]
    assert vivo is not None
    assert vivo.modificador_incubadora == 0


def test_el_evento_de_avance_dice_que_modificador_se_aplico() -> None:
    """
    La accion no emite nada, asi que este evento es el UNICO rastro permanente
    del ajuste -- y el informe de Fase III lo necesita para explicar por que una
    masa avanzo una casilla menos de lo que su dado anunciaba.
    """
    engine, manager, p1 = _partida()
    _masa(p1, "pan_de_molde", 1, dado=1)
    _masa(p1, "focaccia", 1, dado=1, estacion=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    engine._avanzar_masas_jugador(p1)

    avances = [e for e in engine.eventos if e.tipo == EventoTipo.MASA_AVANZO]
    con_dial = next(a for a in avances if a.datos["estacion_idx"] == 0)
    sin_dial = next(a for a in avances if a.datos["estacion_idx"] == 1)

    assert con_dial.datos["modificador_incubadora"] == -1
    assert "Incubadora -1" in con_dial.mensaje
    assert sin_dial.datos["modificador_incubadora"] == 0
    assert "Incubadora" not in sin_dial.mensaje


def test_la_fase_II_tambien_empieza_sin_diales_pendientes() -> None:
    engine, manager, p1 = _partida()
    slot = _masa(p1, "pan_de_molde", 1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=1)

    engine.iniciar_dia()

    assert slot.modificador_incubadora == 0


# ---------------------------------------------------------------------------
# 4. Frena de verdad, y acelera de verdad
# ---------------------------------------------------------------------------


def test_un_menos_uno_salva_una_masa_que_colapsaria() -> None:
    engine, manager, p1 = _partida()
    receta = RECIPE_CATALOG["focaccia"]
    avance_base = engine._environment.temperatura_actual // 5 + 1
    # Justo en la primera casilla que colapsa tras avanzar; un -1 la deja fuera.
    posicion = receta.zona_colapso[0] - avance_base
    _masa(p1, "focaccia", posicion, dado=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    engine._avanzar_masas_jugador(p1)

    # Sigue viva: no hubo horneado de emergencia.
    assert p1.estaciones_fermentacion[0] is not None
    assert p1.archivo_colapsos == []


def test_un_mas_uno_puede_tirar_una_masa_al_colapso() -> None:
    """
    El sobrepaso es legal a proposito, igual que en la Accion E: el riesgo es el
    freno del dial. El cliente lo avisa con el corchete discontinuo y no lo
    impide.
    """
    engine, manager, p1 = _partida()
    receta = RECIPE_CATALOG["focaccia"]
    avance_base = engine._environment.temperatura_actual // 5 + 1
    # Una casilla por debajo del colapso tras avanzar; el +1 la mete dentro.
    posicion = receta.zona_colapso[0] - avance_base - 1
    _masa(p1, "focaccia", posicion, dado=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=1)

    engine._avanzar_masas_jugador(p1)

    assert p1.estaciones_fermentacion[0] is None
    assert len(p1.archivo_colapsos) == 1


# ---------------------------------------------------------------------------
# 5. Los dos invariantes estructurales
# ---------------------------------------------------------------------------


def test_no_cuesta_pa_ni_ocupa_espacio_de_accion() -> None:
    _, manager, p1 = _partida()
    _masa(p1, "pan_de_molde", 3)
    pa_antes = p1.puntos_accion

    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)

    assert p1.puntos_accion == pa_antes
    assert p1.acciones_pa_usadas_hoy == []


def test_no_cierra_la_visita() -> None:
    engine, manager, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None
    activo.tecnologias.incubadora = True
    _masa(activo, "pan_de_molde", 3)
    nonce = engine.turno_nonce

    manager.accion_auxiliar_incubadora(activo, slot_index=0, modificador=-1)

    assert engine.turno_nonce == nonce
    assert engine.jugador_activo is activo


def test_no_emite_ningun_evento() -> None:
    """
    Guardarrail del invariante de AvisoAccion: una accion de 0 PA ocurre dentro
    de la ventana de deshacer, y restaurar un checkpoint reconstruye el motor
    entero. Un evento aqui encogeria `engine.eventos` al deshacer.
    """
    engine, manager, p1 = _partida()
    _masa(p1, "pan_de_molde", 3)
    antes = len(engine.eventos)

    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=1)
    manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=0)

    assert len(engine.eventos) == antes


def test_no_mantiene_al_jugador_en_la_rotacion_de_visitas() -> None:
    """
    Un ajuste no es un recurso. Si el dial entrase en `_jugador_elegible`, todo
    dueno de la Incubadora con una masa en marcha cobraria una visita extra cada
    dia quisiera o no -- y seria una clausula sin final, porque el dial se puede
    mover en los dos sentidos indefinidamente.
    """
    engine, _, _ = _partida()
    engine.iniciar_dia()
    activo = engine.jugador_activo
    assert activo is not None

    activo.tecnologias.incubadora = True
    _masa(activo, "pan_de_molde", 3)
    activo.puntos_accion = 0
    activo.accion_alimentar_usada = True
    activo.horas_extras_usadas = True
    activo.datos_investigacion = 0
    activo.monedas = 0
    activo.reserva_agua = 0
    activo.acciones_pa_usadas_hoy = ["E", "descarte"]

    assert not engine._jugador_elegible(engine._players.index(activo))


# ---------------------------------------------------------------------------
# 6. La Accion B ya no escribe el campo
# ---------------------------------------------------------------------------


def test_la_accion_B_ya_no_acepta_el_modificador() -> None:
    """
    Un solo escritor para el campo. Mientras la B tambien lo escribia, el mismo
    numero significaba "esta noche" o "para siempre" segun quien lo pusiera, que
    es justo la ambiguedad que dejo al playtester sin poder frenar su masa.
    """
    _, manager, p1 = _partida()
    receta = p1.carpeta_proyectos[0]

    with pytest.raises(TypeError):
        manager.accion_B_iniciar_receta(  # type: ignore[call-arg]
            p1, receta, modificador_incubadora=-1
        )


def test_una_masa_recien_iniciada_nace_con_el_dial_a_cero() -> None:
    _, manager, p1 = _partida()
    receta = p1.carpeta_proyectos[0]
    for tipo, pct in receta.requisito_harina.items():
        p1.reserva_harina[tipo] = pct
    p1.reserva_agua = receta.tokens_agua

    slot = manager.accion_B_iniciar_receta(p1, receta)

    assert slot.modificador_incubadora == 0


# ---------------------------------------------------------------------------
# 7. Disponibilidad
# ---------------------------------------------------------------------------


def _entrada(engine: GameEngine, player: Player) -> dict:
    return next(a for a in acciones_disponibles(engine, player) if a["id"] == "incubadora")


def test_disponibilidad_apagada_sin_la_mejora() -> None:
    engine, _, p1 = _partida(con_incubadora=False)
    _masa(p1, "pan_de_molde", 3)
    entrada = _entrada(engine, p1)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "Requiere Incubadora"


def test_disponibilidad_apagada_sin_masas() -> None:
    """
    Motivo distinto del anterior a proposito: no tener la mejora es permanente y
    no tener masas se arregla con una Accion B el mismo dia. El tooltip es el
    unico sitio donde el jugador aprende cual de las dos le pasa.
    """
    engine, _, p1 = _partida()
    entrada = _entrada(engine, p1)
    assert entrada["habilitada"] is False
    assert entrada["motivo"] == "Sin masas en fermentación"


def test_disponibilidad_encendida_con_mejora_masa_y_sin_PA() -> None:
    """No tiene puerta de PA: es gratis y se puede accionar hasta el final del dia."""
    engine, _, p1 = _partida()
    _masa(p1, "pan_de_molde", 3)
    p1.puntos_accion = 0
    entrada = _entrada(engine, p1)
    assert entrada["habilitada"] is True
    assert entrada["motivo"] == ""
