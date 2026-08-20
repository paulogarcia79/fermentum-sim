"""
server/commands.py — Despacho de Comandos de Acción
======================================================
Traduce un comando de acción recibido por HTTP (JSON ya parseado: un
identificador de acción + un dict de parámetros) en la llamada
correspondiente a ``ActionManager``, y cierra la visita del jugador con
``GameEngine.terminar_turno_actual()`` cuando la acción lo requiere.

Este módulo es el único lugar del proyecto donde vive la tabla
"¿qué acciones terminan el turno?" que la Milestone 1 dejó pendiente para
la capa de comandos (Acción A y Horas Extras NO terminan el turno; el resto
sí). Un "Pasar" explícito no pasa por aquí — ``server/app.py`` lo despacha
directamente a ``GameEngine.pasar_turno()``, que ya cierra la visita él mismo.

Deliberadamente NO reimplementa ninguna validación de reglas: cada método de
``ActionManager`` ya valida sus propias precondiciones y lanza la excepción
``FermentumError`` semántica correspondiente (fail-fast, ARCHITECTURE.md
§3). Este módulo solo resuelve lo que HTTP no puede transportar directamente
— referencias de objeto (``Recipe`` para la Acción B, vía ``carpeta_index``)
y miembros de enum (``TecnologiaID``, ``TipoHarina`` para el Pedido de
Urgencia de la Acción C) — y deja que ``ActionManager`` decida si la acción
es válida.
"""
from __future__ import annotations

from typing import Any, Dict

from actions import ActionManager
from engine import GameEngine
from exceptions import InvalidActionError
from models import Player, TecnologiaID, TipoHarina

# Acciones que terminan la visita del jugador al completarse con éxito.
# Ver Milestone 1 (engine.py): Acción A y Horas Extras son gratuitas y NO
# terminan el turno por sí mismas; todas las demás sí.
ACCIONES_QUE_TERMINAN_TURNO: Dict[str, bool] = {
    "A": False,
    "B": True,
    "C": True,
    "D": True,
    "E": True,
    "F": True,
    "G": True,
    "simposio": True,
    "H": True,
    "I": True,
    "horas_extras": False,
}

ACCIONES_VALIDAS = frozenset(ACCIONES_QUE_TERMINAN_TURNO)


def resolver_comando(
    engine: GameEngine,
    manager: ActionManager,
    player: Player,
    accion: str,
    params: Dict[str, Any],
) -> Any:
    """
    Despacha un comando de acción y cierra la visita del jugador si
    corresponde (ver ``ACCIONES_QUE_TERMINAN_TURNO``).

    Args:
        engine: Motor de la partida.
        manager: ``ActionManager`` construido sobre ``engine``.
        player: Jugador que ejecuta la acción. El llamador (``server/app.py``)
            es responsable de verificar que sea el ``jugador_activo`` antes
            de invocar esta función — no se repite aquí la verificación.
        accion: Identificador de la acción (una clave de
            ``ACCIONES_QUE_TERMINAN_TURNO``).
        params: Parámetros crudos ya deserializados del cuerpo JSON.

    Returns:
        El valor de retorno del método de ``ActionManager`` invocado
        (``None``, un ``FermentationSlot`` o un ``HorneadoRecord``).

    Raises:
        InvalidActionError: Identificador de acción desconocido, o un
            parámetro con un tipo/valor que no se puede resolver (p. ej.
            una tecnología o tipo de harina inexistente).
        FermentumError: Cualquier excepción semántica de ``ActionManager``
            se propaga sin modificar; ninguna mutación de turno ocurre en
            ese caso porque ``ActionManager`` ya es fail-fast.
    """
    if accion not in ACCIONES_VALIDAS:
        raise InvalidActionError(
            f"Acción desconocida: {accion!r}. Válidas: {sorted(ACCIONES_VALIDAS)}."
        )

    resultado = _despachar(manager, player, accion, params)

    if ACCIONES_QUE_TERMINAN_TURNO[accion]:
        engine.terminar_turno_actual()

    return resultado


def _despachar(
    manager: ActionManager,
    player: Player,
    accion: str,
    params: Dict[str, Any],
) -> Any:
    if accion == "A":
        return manager.accion_A_alimentar(
            player,
            usar_harina=params.get("usar_harina", True),
            tipo_harina=params.get("tipo_harina"),
            usar_agua=params.get("usar_agua", True),
        )

    if accion == "B":
        carpeta_index = _requerir_int(params, "carpeta_index")
        if not (0 <= carpeta_index < len(player.carpeta_proyectos)):
            raise InvalidActionError(
                f"carpeta_index={carpeta_index} fuera de rango. La carpeta "
                f"de '{player.nombre}' tiene {len(player.carpeta_proyectos)} recetas."
            )
        receta = player.carpeta_proyectos[carpeta_index]
        receta_id_esperado = params.get("receta_id")
        if receta_id_esperado is not None and receta_id_esperado != receta.id:
            raise InvalidActionError(
                "Estado del cliente desactualizado: la receta en "
                f"carpeta_index={carpeta_index} ya no es {receta_id_esperado!r} "
                f"(ahora es {receta.id!r})."
            )
        return manager.accion_B_iniciar_receta(
            player, receta, modificador_incubadora=params.get("modificador_incubadora", 0)
        )

    if accion == "C":
        if params.get("urgencia", False):
            harina_urgencia = params.get("harina_urgencia")
            return manager.accion_C_adquirir_insumos(
                player,
                urgencia=True,
                harina_urgencia=(
                    _resolver_tipo_harina(harina_urgencia) if harina_urgencia is not None else None
                ),
                agua_tokens_urgencia=params.get("agua_tokens_urgencia", 0),
            )
        return manager.accion_C_adquirir_insumos(
            player, indice_slot=_requerir_int(params, "indice_slot")
        )

    if accion == "D":
        return manager.accion_D_implementar_mejora(
            player, _resolver_tecnologia(params.get("tecnologia"))
        )

    if accion == "E":
        return manager.accion_E_tecnica_pliegues(
            player,
            slot_index=_requerir_int(params, "slot_index"),
            opcion_camara_b=params.get("opcion_camara_b", "avanzar"),
            slot_index_2=params.get("slot_index_2"),
        )

    if accion == "F":
        return manager.accion_F_hornear(player, slot_index=_requerir_int(params, "slot_index"))

    if accion == "G":
        return manager.accion_G_investigar_protocolo(
            player,
            indice_mercado=_requerir_int(params, "indice_mercado"),
            indice_descartar=params.get("indice_descartar"),
        )

    if accion == "simposio":
        return manager.accion_simposio_tecnico(
            player,
            origen=params.get("origen", ""),
            indice=_requerir_int(params, "indice"),
        )

    if accion == "H":
        return manager.accion_H_recultivo_manual(player)

    if accion == "I":
        return manager.accion_I_inoculo_emergencia(player)

    if accion == "horas_extras":
        return manager.accion_auxiliar_horas_extras(player)

    raise AssertionError(f"accion {accion!r} pasó la validación pero no tiene despacho")  # inalcanzable


def _requerir_int(params: Dict[str, Any], clave: str) -> int:
    valor = params.get(clave)
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise InvalidActionError(f"'{clave}' debe ser un entero. Recibido: {valor!r}.")
    return valor


def _resolver_tipo_harina(valor: Any) -> TipoHarina:
    try:
        return TipoHarina(valor)
    except ValueError:
        raise InvalidActionError(
            f"tipo_harina inválido: {valor!r}. Debe ser uno de "
            f"{[t.value for t in TipoHarina]}."
        ) from None


def _resolver_tecnologia(valor: Any) -> TecnologiaID:
    try:
        return TecnologiaID(valor)
    except ValueError:
        raise InvalidActionError(
            f"tecnologia inválida: {valor!r}. Debe ser una de "
            f"{[t.value for t in TecnologiaID]}."
        ) from None
