"""
events.py — Flujo de Eventos del Motor de Fermentum
======================================================
Define el registro estructurado de sucesos que ``GameEngine`` emite a medida
que resuelve cada Día de Laboratorio.

Motivación: antes de este módulo, la única forma de saber qué pasó durante
la Fase III (avances de masa, colapsos automáticos, desgaste, contaminación)
era comparar un snapshot del estado "antes" contra el estado "después"
(``main.py:_snapshot_jugador`` / ``_reporte_fermentacion``). Ese enfoque
funciona para una CLI de un solo proceso, pero es insuficiente para
cualquier cliente remoto: un colapso estructural puede costarle a un
jugador varios puntos de Maestría sin que haya tomado ninguna decisión, y
ese jugador debe ser *informado* del suceso, no dejado a inferirlo de un
diff de estado.

``GameEngine`` mantiene internamente el registro completo de eventos de la
partida (propiedad ``eventos``) y opcionalmente reenvía cada evento, en el
momento en que se emite, a un ``EventSink`` inyectado (Inyección de
Dependencias — ``ARCHITECTURE.md`` §1) para que un llamador externo (p. ej.
un futuro servidor) pueda transmitirlos en vivo sin sondear la lista.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class EventoTipo(str, Enum):
    """Catálogo de tipos de evento que ``GameEngine`` puede emitir."""

    JEFE_ASIGNADO = "jefe_asignado"
    CLIMA_REVELADO = "clima_revelado"
    MERCADO_REFRESCADO = "mercado_refrescado"
    MASA_AVANZO = "masa_avanzo"
    HORNEADO = "horneado"
    DESGASTE = "desgaste"
    CONTAMINACION = "contaminacion"
    FIN_DE_PARTIDA = "fin_de_partida"


@dataclass(frozen=True)
class GameEvent:
    """
    Registro inmutable de un suceso ocurrido durante la partida.

    Attributes:
        tipo: Categoría del evento (ver ``EventoTipo``).
        dia: Día de Laboratorio (``Environment.dia_actual``) en el que ocurrió.
        jugador_idx: Índice del jugador afectado en ``GameEngine.players``,
            o ``None`` si el evento es global (p. ej. clima, mercado).
        datos: Payload estructurado específico del tipo de evento (ver los
            puntos de emisión en ``engine.py`` para el esquema de cada tipo).
        mensaje: Descripción legible en español, lista para mostrarse tal
            cual en una interfaz (CLI o web) sin lógica de formato adicional.
    """

    tipo: EventoTipo
    dia: int
    jugador_idx: Optional[int]
    datos: Dict[str, Any] = field(default_factory=dict)
    mensaje: str = ""


EventSink = Callable[[GameEvent], None]
"""
Alias de tipo para un sumidero de eventos: cualquier invocable que reciba
un ``GameEvent`` recién emitido (p. ej. para reenviarlo a clientes
conectados). ``GameEngine`` siempre conserva el registro completo en su
propia lista interna (``GameEngine.eventos``) independientemente de si se
inyecta un sink o no; el sink es solo un gancho adicional de reenvío.
"""
