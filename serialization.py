"""
serialization.py — Estado del Motor como JSON
=================================================
Convierte el estado de un ``GameEngine`` a estructuras planas (dict/list) de
tipos nativos de JSON, sin decidir qué parte de ese estado debería ser
visible para un cliente remoto — esa es la responsabilidad de
``server/views.py`` (redacción de información futura oculta: mazos
restantes).

Este módulo existe porque ``dataclasses.asdict`` ya basta por sí solo: cada
entidad de estado (``Player``, ``Environment``, ``Market``, ``Recipe``,
``FermentationSlot``, ``HorneadoRecord``...) es un ``@dataclass``, y cada
enumeración de dominio hereda de ``str`` además de ``Enum``
(``class TipoHarina(str, Enum)``), así que sus miembros ya son instancias de
``str`` y ``json.dumps`` los serializa directamente sin ninguna capa de
esquema adicional (pydantic, marshmallow, etc.).
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List

from engine import GameEngine


def snapshot(engine: GameEngine) -> Dict[str, Any]:
    """
    Serializa el estado completo (sin redactar) de una partida.

    Returns:
        Dict con las claves ``players`` (lista, una por jugador en el orden
        de ``engine.players``), ``environment``, ``market`` y
        ``partida_terminada``. Todos los valores son de tipos nativos de
        JSON (dict/list/str/int/bool/None) — listo para ``json.dumps``.
    """
    return {
        "players": [dataclasses.asdict(p) for p in engine.players],
        "environment": dataclasses.asdict(engine.environment),
        "market": dataclasses.asdict(engine.market),
        "partida_terminada": engine.partida_terminada,
    }
