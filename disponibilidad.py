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
este módulo solo evita los casos obvios y baratos de comprobar, no repite
el cálculo completo de recursos por receta.

Diseñado para incluirse en cada snapshot de estado que ``server/views.py``
construye, así el cliente nunca necesita duplicar estas reglas en
TypeScript — un lugar seguro de deriva entre cliente y servidor.
"""
from __future__ import annotations

from typing import Any, Dict, List

from actions import COSTOS_TECNOLOGIA, HARINA_RECULTIVO_MANUAL
from engine import (
    COSTE_REFRESCO_AGUA,
    GameEngine,
    PRECIO_DESCARTE,
    PRECIO_PLIEGUES,
    PRECIO_PLIEGUES_VITALIDAD,
    PRECIO_RECETA,
)
from models import Player


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
    # Precio de la receta visible MÁS BARATA, no el mínimo global: el mazo es una
    # sola baraja, así que lo que se puede pagar depende de las 4 cartas que hoy
    # están sobre la mesa, no de lo que el catálogo tenga más barato.
    precio_receta_minimo = min(
        (PRECIO_RECETA[r.grado] for r in engine.market.recetas_visibles if r is not None),
        default=0,
    )
    usados = player.acciones_pa_usadas_hoy

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
        "B" not in usados
        and tiene_pa
        and not contaminado
        and bool(player.carpeta_proyectos)
        and hay_estacion_libre
        and player.dados_inoculo >= 1,
        _motivo_B(player, tiene_pa, contaminado, hay_estacion_libre, "B" in usados),
    )
    agregar(
        "C",
        "C" not in usados and tiene_pa,
        "Ya usaste este espacio hoy" if "C" in usados else "Sin PA",
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
    if "D" in usados:
        motivo_d = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_d = "Sin PA"
    elif costo_mejora_minimo is None:
        motivo_d = "Todas las mejoras ya están instaladas"
    else:
        motivo_d = "Sin Datos para ninguna mejora pendiente"
    agregar(
        "D",
        "D" not in usados
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
    if "F" in usados:
        motivo_f = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_f = "Sin PA"
    elif not hay_estacion_activa:
        motivo_f = "Sin masas activas"
    else:
        motivo_f = "La masa aún está creciendo"
    agregar(
        "F",
        "F" not in usados and tiene_pa and hay_estacion_activa and hay_masa_horneable,
        motivo_f,
    )
    if "G" in usados:
        motivo_g = "Ya usaste este espacio hoy"
    elif not tiene_pa:
        motivo_g = "Sin PA"
    elif not hay_receta_visible:
        motivo_g = "No hay recetas visibles en el mercado"
    else:
        motivo_g = "Sin Monedas para ninguna receta visible"
    agregar(
        "G",
        "G" not in usados
        and tiene_pa
        and hay_receta_visible
        and player.monedas >= precio_receta_minimo,
        motivo_g,
    )
    agregar(
        "pedido_urgencia",
        player.datos_investigacion >= 1,
        "Sin Datos de Investigación",
    )
    agregar(
        "simposio",
        "simposio" not in usados and tiene_pa and bool(player.archivo_horneado_exitoso),
        "Ya usaste este espacio hoy"
        if "simposio" in usados
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
    agregar(
        "H",
        "H" not in usados and contaminado and tiene_pa and harina_total >= HARINA_RECULTIVO_MANUAL,
        _motivo_emergencia(contaminado, tiene_pa, harina_total >= HARINA_RECULTIVO_MANUAL, "H" in usados),
    )
    agregar(
        "I",
        "I" not in usados and contaminado and tiene_pa and player.datos_investigacion >= 1,
        _motivo_emergencia(contaminado, tiene_pa, player.datos_investigacion >= 1, "I" in usados),
    )
    agregar(
        "horas_extras",
        not player.horas_extras_usadas and player.datos_investigacion >= 1,
        "Ya se usó hoy" if player.horas_extras_usadas else "Sin Datos de Investigación",
    )

    return resultados


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
