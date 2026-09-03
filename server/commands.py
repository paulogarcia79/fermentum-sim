"""
server/commands.py — Despacho de Comandos de Acción
======================================================
Traduce un comando de acción recibido por HTTP (JSON ya parseado: un
identificador de acción + un dict de parámetros) en la llamada
correspondiente a ``ActionManager``, y cierra la visita del jugador con
``GameEngine.terminar_turno_actual()`` cuando la acción lo requiere.

Este módulo es el único lugar del proyecto donde vive la tabla
"¿qué acciones terminan el turno?" que la Milestone 1 dejó pendiente para
la capa de comandos (Acciones A y E, Horas Extras y Pedido de Urgencia NO
terminan el turno; el resto sí). Un "Pasar" explícito no pasa por aquí — ``server/app.py`` lo despacha
directamente a ``GameEngine.pasar_turno()``, que ya cierra la visita él mismo.

Deliberadamente NO reimplementa ninguna validación de reglas: cada método de
``ActionManager`` ya valida sus propias precondiciones y lanza la excepción
``FermentumError`` semántica correspondiente (fail-fast, ARCHITECTURE.md
§3). Este módulo solo resuelve lo que HTTP no puede transportar directamente
— referencias de objeto (``Recipe`` para la Acción B, vía ``carpeta_index``)
y miembros de enum (``TecnologiaID``, ``TipoHarina`` para el Pedido de
Urgencia) — y deja que ``ActionManager`` decida si la acción es válida.

También vive aquí ``describir_accion``, que redacta la línea en español que
el registro de la partida (``server/sessions.py:EntradaRegistro``) guarda
por cada movimiento. Está en este módulo y no en la vista porque es aquí
donde los parámetros del wire ya están resueltos y donde se tiene a mano el
valor de retorno de ``ActionManager`` — el mismo motivo por el que
``engine.py`` redacta ``GameEvent.mensaje`` en el punto de la mutación en
vez de dejar que el cliente lo reconstruya.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from actions import (
    AGUA_PEDIDO_URGENCIA,
    ActionManager,
    OPERACIONES_ACIDEZ,
    OPERACIONES_HARINA,
    RECURSO_MOLINO,
)
from engine import CANTIDAD_BOLSA_PCT, DATOS_JEFATURA, GameEngine
from exceptions import InvalidActionError
from models import FermentationSlot, HorneadoRecord, Player, TecnologiaID, TipoHarina

# Acciones que terminan la visita del jugador al completarse con éxito.
# Ver Milestone 1 (engine.py): Acciones A y E, Horas Extras, Pedido de Urgencia,
# Estasis Biológica e Incubadora son gratuitas (0 PA) y NO terminan el turno por
# sí mismas; todas las demás sí.
# La Acción E es gratuita en PA pero se paga en Monedas, y aun así conserva la
# regla "un espacio, una visita por día" (ACTIONS_REGISTRY.md §1).
ACCIONES_QUE_TERMINAN_TURNO: Dict[str, bool] = {
    "A": False,
    "B": True,
    "C": True,
    "D": True,
    "E": False,
    "descarte": False,
    "F": True,
    "G": True,
    "simposio": True,
    "jefatura": True,
    "H": True,
    "I": True,
    "horas_extras": False,
    "pedido_urgencia": False,
    "estasis": False,
    "incubadora": False,
}

# Acciones que REVELAN información oculta al resolverse (robar de un mazo
# boca abajo, tirar un dado, ...). Hoy NINGUNA lo hace -- se verificó por
# auditoría: actions.py no importa random ni toca mazo_recetas/mazo_clima/
# mazo_tendencias; todos los robos ocultos viven en fase_I_ambiente,
# automáticos, fuera de la ventana de deshacer. El contrato para el futuro:
# una acción marcada True aquí obliga a RE-TOMAR el checkpoint de visita
# justo después de resolverse (server/app.py) -- lo revelado se convierte en
# el nuevo piso del deshacer, nunca se des-revela -- y su modal en la UI
# debe avisar de antemano que ese paso no se puede deshacer (ver
# ACCIONES_QUE_REVELAN en web/src/data/descripcionesAcciones.ts, el espejo).
ACCIONES_QUE_REVELAN: Dict[str, bool] = {accion: False for accion in ACCIONES_QUE_TERMINAN_TURNO}

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
            tipo_harina=params.get("tipo_harina"),
        )

    if accion == "descarte":
        return manager.accion_descarte_acidez(
            player,
            operacion=params.get("operacion"),
            niveles=_requerir_int(params, "niveles"),
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
        return manager.accion_B_iniciar_receta(player, receta)

    if accion == "C":
        transacciones = params.get("transacciones")
        if not isinstance(transacciones, list):
            raise InvalidActionError(
                "Acción C (Visitar el Mercado) requiere 'transacciones' "
                f"como una lista. Recibido: {transacciones!r}."
            )
        return manager.accion_C_visitar_mercado(player, transacciones=transacciones)

    if accion == "D":
        return manager.accion_D_implementar_mejora(
            player, _resolver_tecnologia(params.get("tecnologia"))
        )

    if accion == "E":
        return manager.accion_E_tecnica_pliegues(
            player,
            opcion=params.get("opcion", "avanzar"),
            reparto=_reparto_pliegues(params.get("reparto")),
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
        # `indice` indexa ahora `archivo_horneado_exitoso`: el Simposio se paga
        # sacrificando un horneado exitoso, no descartando de carpeta/estación.
        return manager.accion_simposio_tecnico(
            player,
            indice=_requerir_int(params, "indice"),
        )

    if accion == "jefatura":
        # Sin parámetros: el espacio es único en la mesa y su único efecto
        # configurable es quién lo ocupa, que ya viene en `player`.
        return manager.accion_reclamar_jefatura(player)

    if accion == "H":
        return manager.accion_H_recultivo_manual(player)

    if accion == "I":
        return manager.accion_I_inoculo_emergencia(player)

    if accion == "horas_extras":
        return manager.accion_auxiliar_horas_extras(player)

    if accion == "estasis":
        suspender = params.get("suspender")
        if not isinstance(suspender, bool):
            raise InvalidActionError(
                f"'suspender' debe ser un booleano. Recibido: {suspender!r}."
            )
        return manager.accion_auxiliar_estasis(player, suspender=suspender)

    if accion == "incubadora":
        slot_index = params.get("slot_index")
        modificador = params.get("modificador")
        # `isinstance(True, int)` es cierto en Python, así que un booleano colado
        # en cualquiera de los dos se rechaza explícitamente: un `true` en el JSON
        # no debe pasar por un 1.
        if not isinstance(slot_index, int) or isinstance(slot_index, bool):
            raise InvalidActionError(
                f"'slot_index' debe ser un entero. Recibido: {slot_index!r}."
            )
        if not isinstance(modificador, int) or isinstance(modificador, bool):
            raise InvalidActionError(
                f"'modificador' debe ser un entero. Recibido: {modificador!r}."
            )
        return manager.accion_auxiliar_incubadora(
            player, slot_index=slot_index, modificador=modificador
        )

    if accion == "pedido_urgencia":
        recurso = params.get("recurso")
        if not isinstance(recurso, str):
            raise InvalidActionError(
                f"'recurso' debe ser 'harina' o 'agua'. Recibido: {recurso!r}."
            )
        harina = params.get("harina")
        return manager.accion_auxiliar_pedido_urgencia(
            player,
            recurso=recurso,
            harina=(_resolver_tipo_harina(harina) if harina is not None else None),
        )

    raise AssertionError(f"accion {accion!r} pasó la validación pero no tiene despacho")  # inalcanzable


def _requerir_int(params: Dict[str, Any], clave: str) -> int:
    valor = params.get(clave)
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise InvalidActionError(f"'{clave}' debe ser un entero. Recibido: {valor!r}.")
    return valor


def _reparto_pliegues(valor: Any) -> Optional[Dict[int, int]]:
    """
    Normaliza el 'reparto' de la Acción E a ``{slot_index: espacios}`` con
    claves ``int``.

    JSON solo admite claves de tipo string, así que el cliente envía
    ``{"0": 2}`` y aquí se convierte a ``{0: 2}``, que es lo que
    ``ActionManager`` espera. Los rangos y el total los valida la acción;
    esto solo resuelve lo que el transporte no puede transmitir.
    """
    if valor is None:
        return None
    if not isinstance(valor, dict):
        raise InvalidActionError(
            f"'reparto' debe ser un objeto {{slot_index: espacios}}. Recibido: {valor!r}."
        )
    reparto: Dict[int, int] = {}
    for clave, espacios in valor.items():
        try:
            slot_index = int(clave)
        except (TypeError, ValueError):
            raise InvalidActionError(
                f"Las claves de 'reparto' deben ser índices de estación enteros. "
                f"Recibido: {clave!r}."
            )
        if not isinstance(espacios, int) or isinstance(espacios, bool):
            raise InvalidActionError(
                f"Los valores de 'reparto' deben ser enteros. Recibido: {espacios!r}."
            )
        reparto[slot_index] = espacios
    return reparto


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


# ===========================================================================
# Redacción del registro de movimientos
# ===========================================================================

MENSAJES_MOVIMIENTO: Dict[str, str] = {
    "pasar": "Pasó el turno",
    "deshacer": "Deshizo su visita",
    "pase_forzado": "Le pasaron el turno por inactividad (forzó {nombre})",
}
"""
Frases de los tres movimientos que no pasan por ``/actions`` y por tanto no
tienen entrada en ``describir_accion``. ``pase_forzado`` se formatea con el
nombre de quien pidió el pase: la entrada del registro guarda en
``jugador_idx`` a quién se lo pasaron, así que sin esto no quedaría rastro
de quién lo forzó.
"""

_ZONAS_HORNEADO: Dict[str, str] = {
    "optima": "zona Óptima",
    "pre_fermento": "Pre-fermento",
    "colapso": "Colapso",
}


def describir_accion(
    engine: GameEngine,
    player: Player,
    accion: str,
    params: Dict[str, Any],
    resultado: Any,
) -> str:
    """
    Redacta la línea del registro para una acción ya ejecutada con éxito.

    Contrato: llamar DESPUÉS de que ``resolver_comando`` haya devuelto sin
    excepción y ANTES de ``_avanzar_fase_si_corresponde``. Lee estado
    posterior a la acción (el ``HorneadoRecord`` de la F, la receta que la G
    acaba de meter en la carpeta), lo cual es seguro porque lo único que
    ``resolver_comando`` hace tras despachar es ``terminar_turno_actual()``,
    que solo mueve el cursor y el nonce del turno.

    El nombre del actor se omite a propósito: el cliente lo antepone con el
    color del asiento, así que incluirlo aquí lo duplicaría.

    Args:
        engine: Motor de la partida (para leer el mercado tras la acción).
        player: Jugador que ejecutó la acción.
        accion: Identificador de la acción, ya validado.
        params: Los mismos parámetros crudos que recibió ``resolver_comando``.
        resultado: Valor de retorno de ``ActionManager`` (``None``, un
            ``FermentationSlot``, un ``HorneadoRecord`` o un ``int``).

    Returns:
        Una frase en español, sin el nombre del jugador.
    """
    if accion == "A":
        return f"Alimentó el cultivo con {params.get('tipo_harina')}"

    if accion == "descarte":
        operacion = params.get("operacion")
        niveles = params.get("niveles")
        signo, recurso, escalera = OPERACIONES_ACIDEZ[operacion]
        coste = escalera.get(niveles, 0)
        unidad = "tokens de agua" if recurso == "agua" else "Monedas"
        marca = "+" if signo > 0 else "−"
        return f"Descarte: Acidez {marca}{niveles} ({coste} {unidad})"

    if accion == "B":
        assert isinstance(resultado, FermentationSlot)
        # Identidad, no igualdad: dos estaciones pueden alojar la misma receta.
        indice = next(
            (i for i, s in enumerate(player.estaciones_fermentacion) if s is resultado),
            None,
        )
        donde = f" en Estación {indice + 1}" if indice is not None else ""
        sabor = " con Bono de Sabor sellado" if resultado.bono_sabor else ""
        return f"Inició {resultado.recipe.nombre}{donde}{sabor}"

    if accion == "C":
        return "Mercado: " + " · ".join(
            _describir_transaccion(t) for t in params.get("transacciones", [])
        )

    if accion == "D":
        return f"Instaló {_resolver_tecnologia(params.get('tecnologia')).nombre_legible}"

    if accion == "E":
        if params.get("opcion", "avanzar") == "recuperar_vitalidad":
            return "Pliegues: recuperó +1 Vitalidad"
        reparto = _reparto_pliegues(params.get("reparto"))
        detalle = ", ".join(
            f"+{espacios} en Estación {slot + 1}" for slot, espacios in sorted(reparto.items())
        )
        return f"Pliegues: {detalle}"

    if accion == "F":
        assert isinstance(resultado, HorneadoRecord)
        zona = _ZONAS_HORNEADO.get(resultado.zona_resultado, resultado.zona_resultado)
        extra = f" (+{resultado.datos_obtenidos} Datos)" if resultado.datos_obtenidos else ""
        return (
            f"Horneó {resultado.recipe.nombre} en {zona}: "
            f"{resultado.puntos_totales} PM, {resultado.monedas_obtenidos} Monedas{extra}"
        )

    if accion == "G":
        # La receta investigada es la última que entró en la carpeta.
        nombre = player.carpeta_proyectos[-1].nombre if player.carpeta_proyectos else "una receta"
        return f"Investigó el protocolo {nombre}"

    if accion == "simposio":
        # El Simposio devuelve la carta sacrificada al descarte del mercado.
        descarte = engine.market.descarte_recetas
        nombre = descarte[-1].nombre if descarte else "un horneado"
        return f"Publicó {nombre} en el Simposio (+{resultado} Datos)"

    if accion == "jefatura":
        return f"Reclamó la Jefatura de Investigación (+{DATOS_JEFATURA} Datos)"

    if accion == "H":
        return "Re-cultivo Manual: limpió la Contaminación"

    if accion == "I":
        return "Inóculo de Emergencia: limpió la Contaminación"

    if accion == "horas_extras":
        return "Horas Extras: +1 PA (−1 Dato)"

    if accion == "estasis":
        if params.get("suspender"):
            return "Suspendió la Estasis Biológica por esta noche"
        return "Reactivó la Estasis Biológica"

    if accion == "incubadora":
        # El dial ya está escrito en la masa cuando esto se llama (va después de
        # `resolver_comando`), así que el nombre de la receta sale del propio slot
        # en vez de repetirse en los params.
        idx = params.get("slot_index")
        modificador = params.get("modificador")
        nombre_masa = ""
        if isinstance(idx, int) and 0 <= idx <= 2:
            slot = player.estaciones_fermentacion[idx]
            if slot is not None:
                nombre_masa = f" ({slot.recipe.nombre})"
        estacion = f"Est-{(idx + 1):02d}" if isinstance(idx, int) else "una estación"
        if modificador:
            return f"Incubadora: {estacion}{nombre_masa} a {modificador:+d} esta noche"
        return f"Incubadora: {estacion}{nombre_masa} sin ajuste"

    if accion == "pedido_urgencia":
        if params.get("recurso") == "agua":
            return f"Pedido de Urgencia: {AGUA_PEDIDO_URGENCIA} tokens de agua"
        return f"Pedido de Urgencia: media bolsa de {params.get('harina')}"

    raise AssertionError(f"accion {accion!r} sin descripción de registro")  # inalcanzable


def _describir_transaccion(transaccion: Any) -> str:
    """Una transacción de la Acción C, en palabras."""
    if not isinstance(transaccion, dict):
        return "una operación"
    tipo = transaccion.get("tipo_recurso")
    if tipo == RECURSO_MOLINO:
        return f"firmó el Contrato con el Molino ({transaccion.get('tipo_harina')})"
    if tipo == "agua":
        return f"compró un lote de agua del {transaccion.get('lote_pct')}%"
    operacion = transaccion.get("operacion")
    fila = OPERACIONES_HARINA.get(operacion)
    if fila is None:
        return f"operó {tipo}"
    direccion, cantidad = fila
    verbo = "compró" if direccion == "comprar" else "vendió"
    tamano = "una bolsa" if cantidad == CANTIDAD_BOLSA_PCT else "media bolsa"
    return f"{verbo} {tamano} de {tipo}"
