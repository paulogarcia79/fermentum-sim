"""
disponibilidad.py — Disponibilidad de Acciones por Jugador
==============================================================
Calcula, para un jugador dado, si cada acción del catálogo se puede
*intentar* ahora mismo — comprobaciones baratas (PA, contaminación,
carpeta/estaciones vacías, mercado agotado, tecnología ya instalada) para
que un cliente remoto pueda habilitar o deshabilitar sus botones sin
reimplementar ninguna regla de negocio por su cuenta.

Esto NO reemplaza la validación de ``ActionManager``: sigue siendo la única
fuente de verdad al enviar una acción (fail-fast, ``ARCHITECTURE.md`` §3).
Una acción "habilitada" aquí puede seguir fallando al enviarse de verdad
(p. ej. Acción B habilitada porque hay una receta en carpeta y una estación
libre, pero el jugador no tiene la harina exacta que esa receta requiere) —
``acciones_disponibles`` solo evita los casos obvios y baratos de comprobar.

``insumos_receta`` es la excepción deliberada a esa frase: SÍ hace la cuenta
completa de harina y agua, pero **carta por carta** y para *enseñarla*, no
para decidir si el espacio se enciende. Son dos preguntas distintas —
"¿puedo pulsar el botón?" (del jugador, una vez) y "¿me alcanza para ESTA
receta?" (de cada carta de la carpeta) — y meter la segunda en el ``motivo``
de la Acción B daría una sola cadena para N recetas, que es justo lo que no
sirve cuando tienes dos en mano y solo una es viable.

Diseñado para incluirse en cada snapshot de estado que ``server/views.py``
construye, así el cliente nunca necesita duplicar estas reglas en
TypeScript — un lugar seguro de deriva entre cliente y servidor.
"""
from __future__ import annotations

from typing import Any, Dict, List

from actions import (
    COSTOS_TECNOLOGIA,
    ESPACIOS_CON_MARCADOR_NEUTRAL,
    HARINA_RECULTIVO_MANUAL,
)
from engine import (
    COSTE_REFRESCO_AGUA,
    GameEngine,
    PRECIO_DESCARTE,
    PRECIO_PLIEGUES,
    PRECIO_PLIEGUES_VITALIDAD,
    PRECIO_RECETA,
    PRECIO_RECETA_MAZO,
)
from models import DATOS_HORAS_EXTRAS, Player, Recipe


def acciones_disponibles(engine: GameEngine, player: Player) -> List[Dict[str, Any]]:
    """
    Returns:
        Lista de ``{"id": str, "habilitada": bool, "motivo": str}``, una
        entrada por acción del catálogo (mismos identificadores que
        ``server/commands.py:ACCIONES_QUE_TERMINAN_TURNO``). ``motivo`` es
        una cadena vacía cuando ``habilitada`` es ``True``.
    """
    contaminado = player.en_estado_contaminacion
    tiene_pa = player.puntos_accion > 0
    harina_total = sum(player.reserva_harina.values())
    tiene_recurso_alimentar = harina_total >= 10 or player.reserva_agua >= 2
    hay_estacion_activa = len(player.masas_activas) > 0
    # Una masa en crecimiento no se puede hornear (la Acción F la rechaza). Se mide
    # contra las zonas EFECTIVAS, igual que ActionManager, para que el botón y la
    # acción no puedan discrepar.
    ampliacion_optima = engine.ampliacion_zona_optima(player)
    hay_masa_horneable = any(
        not slot.recipe.esta_en_crecimiento(slot.posicion_track, ampliacion_optima)
        for _, slot in player.masas_activas
    )
    hay_estacion_libre = player.indice_estacion_disponible is not None
    hay_receta_visible = any(r is not None for r in engine.market.recetas_visibles)
    # Precio de la receta visible MÁS BARATA, no el mínimo del catálogo: lo que
    # se puede pagar depende de las 4 cartas que hoy están sobre la mesa, no de
    # lo que el catálogo tenga más barato.
    precio_receta_minimo = min(
        (PRECIO_RECETA[r.grado] for r in engine.market.recetas_visibles if r is not None),
        default=0,
    )
    # La Investigación a ciegas es el segundo camino de la Acción G y tiene su
    # propio suelo, plano y ajeno a lo que haya expuesto: con las 4 estaciones
    # vacías el espacio sigue siendo jugable si quedan cartas en el mazo (o
    # descarte que rebarajar) y 2 Monedas.
    puede_pagar_visible = hay_receta_visible and player.monedas >= precio_receta_minimo
    hay_carta_en_mazo = not engine.market.mazo_recetas_agotado
    puede_pagar_mazo = hay_carta_en_mazo and player.monedas >= PRECIO_RECETA_MAZO
    usados = player.acciones_pa_usadas_hoy

    def espacio_cerrado(id_: str) -> bool:
        """
        True si el espacio ``id_`` ya está agotado HOY para este jugador.

        No es lo mismo que "está en ``usados``": quien conserva el marcador
        neutral de las Horas Extras sin gastar puede volver una vez a cualquiera
        de los espacios de ``ESPACIOS_CON_MARCADOR_NEUTRAL``, así que esa casilla
        debe seguir encendida. Es el mismo criterio que aplica
        ``ActionManager._require_espacio_disponible``, que es quien manda; aquí
        se replica sólo para que el botón no mienta. Los Pliegues y el Descarte
        siguen midiéndose con el ``in`` crudo: cuestan 0 PA y quedan fuera del
        conjunto.
        """
        if id_ not in usados:
            return False
        return not (
            id_ in ESPACIOS_CON_MARCADOR_NEUTRAL and player.marcador_neutral_disponible
        )

    resultados: List[Dict[str, Any]] = []

    def agregar(id_: str, habilitada: bool, motivo_si_no: str) -> None:
        resultados.append(
            {"id": id_, "habilitada": habilitada, "motivo": "" if habilitada else motivo_si_no}
        )

    agregar(
        "A",
        not player.accion_alimentar_usada and tiene_recurso_alimentar,
        "Ya se usó hoy" if player.accion_alimentar_usada else "Sin harina ni agua suficiente",
    )

    agregar(
        "B",
        not espacio_cerrado("B")
        and tiene_pa
        and not contaminado
        and bool(player.carpeta_proyectos)
        and hay_estacion_libre
        and player.dados_inoculo >= 1,
        _motivo_B(player, tiene_pa, contaminado, hay_estacion_libre, espacio_cerrado("B")),
    )
    agregar(
        "C",
        not espacio_cerrado("C") and tiene_pa,
        "Ya usaste este espacio hoy" if espacio_cerrado("C") else "Sin PA",
    )
    # Coste de la mejora PENDIENTE más barata, no el mínimo del catálogo: es el
    # mismo razonamiento que en la Acción G, donde se mira el precio de las recetas
    # hoy VISIBLES y no el del catálogo entero. Quien ya instaló la Criopreservación
    # (2 Datos) tiene el escalón más barato en 3, así que con 2 Datos el espacio
    # debe apagarse aunque el catálogo siga conteniendo una mejora de 2.
    # `None` = no queda nada por instalar, un motivo distinto de «no puedo pagarlo».
    costo_mejora_minimo = min(
        (COSTOS_TECNOLOGIA[t] for t in player.tecnologias.pendientes),
        default=None,
    )
    if espacio_cerrado("D"):
        motivo_d = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_d = "Sin PA"
    elif costo_mejora_minimo is None:
        motivo_d = "Todas las mejoras ya están instaladas"
    else:
        motivo_d = "Sin Datos para ninguna mejora pendiente"
    agregar(
        "D",
        not espacio_cerrado("D")
        and tiene_pa
        and costo_mejora_minimo is not None
        and player.datos_investigacion >= costo_mejora_minimo,
        motivo_d,
    )
    # Acción E (Pliegues) se paga en Monedas, no en PA: no consulta `tiene_pa`.
    # Con Cámara B la variante 'recuperar_vitalidad' es legal SIN masas activas,
    # así que ese caso también habilita el espacio.
    puede_plegar_masa = hay_estacion_activa and player.monedas >= min(
        PRECIO_PLIEGUES.values()
    )
    puede_recuperar_vitalidad = (
        player.tecnologias.camara_b and player.monedas >= PRECIO_PLIEGUES_VITALIDAD
    )
    if "E" in usados:
        motivo_e = "Ya usaste este espacio hoy"
    elif not hay_estacion_activa and not player.tecnologias.camara_b:
        motivo_e = "Sin masas activas"
    else:
        motivo_e = "Sin Monedas"
    agregar(
        "E",
        "E" not in usados and (puede_plegar_masa or puede_recuperar_vitalidad),
        motivo_e,
    )
    # «Descarte»: 0 PA pero ocupa espacio, y sus DOS sentidos cobran en recursos
    # distintos, así que basta con poder pagar el escalón más barato de alguno —
    # un jugador sin Monedas sigue pudiendo subir la acidez con agua.
    puede_subir_acidez = player.reserva_agua >= min(COSTE_REFRESCO_AGUA.values())
    puede_bajar_acidez = player.monedas >= min(PRECIO_DESCARTE.values())
    if "descarte" in usados:
        motivo_descarte = "Ya usaste este espacio hoy"
    else:
        motivo_descarte = "Sin Monedas ni Agua"
    agregar(
        "descarte",
        "descarte" not in usados and (puede_subir_acidez or puede_bajar_acidez),
        motivo_descarte,
    )
    if espacio_cerrado("F"):
        motivo_f = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_f = "Sin PA"
    elif not hay_estacion_activa:
        motivo_f = "Sin masas activas"
    else:
        motivo_f = "La masa aún está creciendo"
    agregar(
        "F",
        not espacio_cerrado("F") and tiene_pa and hay_estacion_activa and hay_masa_horneable,
        motivo_f,
    )
    if espacio_cerrado("G"):
        motivo_g = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_g = "Sin PA"
    elif not hay_receta_visible and not hay_carta_en_mazo:
        motivo_g = "No hay recetas visibles ni cartas en el mazo"
    elif not hay_carta_en_mazo:
        motivo_g = "Sin Monedas para ninguna receta visible"
    elif not hay_receta_visible:
        motivo_g = f"Sin Monedas para investigar a ciegas ({PRECIO_RECETA_MAZO})"
    else:
        motivo_g = (
            "Sin Monedas para ninguna receta visible ni para investigar a ciegas "
            f"({PRECIO_RECETA_MAZO})"
        )
    agregar(
        "G",
        not espacio_cerrado("G") and tiene_pa and (puede_pagar_visible or puede_pagar_mazo),
        motivo_g,
    )
    agregar(
        "pedido_urgencia",
        player.datos_investigacion >= 1,
        "Sin Datos de Investigación",
    )
    agregar(
        "simposio",
        not espacio_cerrado("simposio")
        and tiene_pa
        and bool(player.archivo_horneado_exitoso),
        "Ya usaste este espacio hoy"
        if espacio_cerrado("simposio")
        else (
            "Sin PA"
            if not tiene_pa
            else "Sin horneados exitosos que sacrificar"
        ),
    )
    # La Jefatura es el único espacio GLOBAL del tablero: lo ocupa un jugador por
    # día en toda la mesa, así que no se consulta `usados` (que es por jugador)
    # sino la marca del motor. El motivo nombra a quien lo ocupó, porque «ya usado»
    # a secas se leería como el límite habitual de un espacio propio.
    jefatura_de = engine.jefatura_reclamada_por
    if jefatura_de is None:
        motivo_jefatura = "Sin PA"
    else:
        motivo_jefatura = (
            f"Ya la reclamó {engine.players[jefatura_de].nombre} hoy"
        )
    agregar(
        "jefatura",
        jefatura_de is None and tiene_pa,
        motivo_jefatura,
    )
    # El Mostrador es la única acción con costo de PA cuya escalera tiene un solo
    # peldaño: no hay espacio que consultar (no ocupa ninguno, ver
    # engine.MONEDAS_MOSTRADOR) ni recurso que exigir, así que teniendo PA está
    # siempre disponible. Ese es justamente su cometido — es el suelo, la acción
    # que garantiza que ningún turno con PA se quede sin nada que hacer.
    agregar("mostrador", tiene_pa, "Sin PA")
    agregar(
        "H",
        not espacio_cerrado("H")
        and contaminado
        and tiene_pa
        and harina_total >= HARINA_RECULTIVO_MANUAL,
        _motivo_emergencia(
            contaminado,
            tiene_pa,
            harina_total >= HARINA_RECULTIVO_MANUAL,
            espacio_cerrado("H"),
        ),
    )
    agregar(
        "I",
        not espacio_cerrado("I")
        and contaminado
        and tiene_pa
        and player.datos_investigacion >= 1,
        _motivo_emergencia(
            contaminado, tiene_pa, player.datos_investigacion >= 1, espacio_cerrado("I")
        ),
    )
    agregar(
        "horas_extras",
        not player.horas_extras_usadas
        and player.datos_investigacion >= DATOS_HORAS_EXTRAS,
        "Ya se usó hoy" if player.horas_extras_usadas else "Sin Datos de Investigación",
    )
    # Estasis Biológica: interruptor, no consumo. Se lista SIEMPRE (como H e I)
    # para que el espacio se vea apagado y el jugador aprenda que existe antes de
    # necesitarlo; sin marca de "ya usada", porque puede accionarse en los dos
    # sentidos cuantas veces se quiera. Sin puerta de PA ni de contaminación:
    # accionarlo con Vitalidad 0 es inocuo.
    agregar(
        "estasis",
        player.tecnologias.criopreservacion,
        "Requiere Criopreservación",
    )
    # Incubadora: el otro ajuste-no-consumo del juego, con la misma forma que la
    # Estasis salvo por una puerta más — el dial se fija SOBRE una masa, así que
    # sin masas activas no hay nada que ajustar. Los dos motivos van en escalera
    # porque son situaciones distintas: no tener la mejora es permanente, no tener
    # masas se arregla con una Acción B el mismo día.
    if not player.tecnologias.incubadora:
        agregar("incubadora", False, "Requiere Incubadora")
    else:
        agregar(
            "incubadora",
            any(slot is not None for slot in player.estaciones_fermentacion),
            "Sin masas en fermentación",
        )

    return resultados


def insumos_receta(engine: GameEngine, player: Player, receta: Recipe) -> Dict[str, Any]:
    """
    Cuenta, insumo a insumo, si ``player`` puede pagar HOY el coste de ``receta``.

    Solo mide los INSUMOS de la carta (las harinas impresas y el agua), nunca los
    bloqueos del jugador — PA, espacio ya usado, estación libre, dado de inóculo o
    contaminación. Esa mitad ya la dice ``acciones_disponibles`` una sola vez para
    la Acción B entera, y repetirla aquí por carta escribiría el mismo bloqueo en
    dos sitios: la carta diría "Sin PA" tres veces mientras el espacio ya está
    apagado por ese mismo motivo. Consecuencia buscada: "insumos completos" NO
    significa "Confirmar va a funcionar", significa "lo que falta, si falta algo,
    no es la despensa".

    El agua se pide a ``engine.agua_requerida`` en vez de leer ``receta.tokens_agua``
    para que el descuento de Alta Humedad salga aquí y en el cobro real de la
    Acción B por el mismo camino.

    Returns:
        ``{"harinas": [{"tipo", "necesita", "tiene", "falta"}, ...],
           "agua": {"necesita", "tiene", "falta"},
           "completos": bool}``

        Una fila por harina impresa (una si es Básica/Avanzada, dos si es
        Intermedia) y siempre una de agua, incluidas las que SÍ se pueden pagar:
        el cliente dibuja la lista entera con sus ✓ y sus ✗, así que devolver
        solo los faltantes obligaría a recomponer las demás. Las cantidades van
        en la unidad del dominio (harina en porcentaje, agua en tokens); darles
        formato es cosa de ``web/src/data/unidades.ts``.
    """
    harinas: List[Dict[str, Any]] = []
    for tipo, pct in receta.requisito_harina.items():
        tiene = player.reserva_harina.get(tipo, 0)
        harinas.append(
            {"tipo": tipo, "necesita": pct, "tiene": tiene, "falta": tiene < pct}
        )

    agua_necesaria = engine.agua_requerida(receta)
    agua = {
        "necesita": agua_necesaria,
        "tiene": player.reserva_agua,
        "falta": player.reserva_agua < agua_necesaria,
    }

    return {
        "harinas": harinas,
        "agua": agua,
        "completos": not agua["falta"] and not any(h["falta"] for h in harinas),
    }


def _motivo_B(
    player: Player, tiene_pa: bool, contaminado: bool, hay_estacion_libre: bool, usado_hoy: bool
) -> str:
    if usado_hoy:
        return "Ya usaste este espacio hoy"
    if not tiene_pa:
        return "Sin PA"
    if contaminado:
        return "Cultivo contaminado — ejecuta un Protocolo de Emergencia"
    if not player.carpeta_proyectos:
        return "Carpeta de Proyectos vacía"
    if not hay_estacion_libre:
        return "Sin estaciones de fermentación libres"
    return "Sin dados de inóculo disponibles"


def _motivo_emergencia(contaminado: bool, tiene_pa: bool, tiene_recursos: bool, usado_hoy: bool) -> str:
    if not contaminado:
        return "El cultivo no está contaminado"
    if usado_hoy:
        return "Ya usaste este espacio hoy"
    if not tiene_pa:
        return "Sin PA"
    if not tiene_recursos:
        return "Recursos insuficientes"
    return ""
