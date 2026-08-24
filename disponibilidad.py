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

from engine import GameEngine
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
    hay_estacion_libre = player.indice_estacion_disponible is not None
    hay_receta_visible = any(r is not None for r in engine.market.recetas_visibles)
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
    agregar(
        "D",
        "D" not in usados and tiene_pa,
        "Ya usaste este espacio hoy" if "D" in usados else "Sin PA",
    )
    agregar(
        "E",
        "E" not in usados and tiene_pa and hay_estacion_activa,
        "Ya usaste este espacio hoy"
        if "E" in usados
        else ("Sin PA" if not tiene_pa else "Sin masas activas"),
    )
    agregar(
        "F",
        "F" not in usados and tiene_pa and hay_estacion_activa,
        "Ya usaste este espacio hoy"
        if "F" in usados
        else ("Sin PA" if not tiene_pa else "Sin masas activas"),
    )
    agregar(
        "G",
        "G" not in usados and tiene_pa and hay_receta_visible,
        "Ya usaste este espacio hoy"
        if "G" in usados
        else ("Sin PA" if not tiene_pa else "No hay recetas visibles en el mercado"),
    )
    agregar(
        "pedido_urgencia",
        player.datos_investigacion >= 1,
        "Sin Datos de Investigación",
    )
    agregar(
        "simposio",
        "simposio" not in usados and tiene_pa and (bool(player.carpeta_proyectos) or hay_estacion_activa),
        "Ya usaste este espacio hoy"
        if "simposio" in usados
        else ("Sin PA" if not tiene_pa else "Carpeta y estaciones vacías"),
    )
    agregar(
        "H",
        "H" not in usados and contaminado and tiene_pa and harina_total >= 50,
        _motivo_emergencia(contaminado, tiene_pa, harina_total >= 50, "H" in usados),
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
