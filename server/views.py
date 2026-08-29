"""
server/views.py — Vista de Estado Redactada para Clientes Remotos
=====================================================================
Construye el dict JSON que se envía a los clientes HTTP a partir de
``serialization.snapshot()``, con dos cambios:

  1. **Redacción**: ``Environment.mazo_clima`` (el mazo de clima restante,
     en orden) y ``Market.mazo_recetas`` (el mazo de recetas restante) se
     reemplazan por su longitud. Son la única información del estado del
     juego que ningún jugador conocería en la partida física — el resto
     (cartas de clima ya reveladas, recetas ya vistas en el mercado,
     carpetas de proyectos de cualquier jugador) es información pública
     según las reglas (ACTIONS_REGISTRY.md §2G: la Carpeta de Proyectos es
     boca arriba). Enviar ``snapshot()`` sin este paso le daría a cualquier
     jugador conocimiento perfecto de las próximas cartas de clima y
     recetas — la única forma en que "serializar todo" es activamente
     incorrecta aquí.
  2. **Campos de turno/fase**: añade lo que un cliente necesita para saber
     de quién es el turno y si su propia solicitud podría estar basada en
     un estado obsoleto (``fase_actual``, ``turno_nonce``,
     ``jugador_en_turno_idx``, ``jefe_investigador_idx``, ``turno_orden``) —
     datos que viven en el motor, no en las entidades de dominio
     serializables. ``turno_orden`` es la secuencia completa de índices de
     jugador en orden de juego del día (``[0]`` = Investigador Jefe);
     información pública, sin redacción.
  3. **Disponibilidad de acciones**: ``acciones_disponibles``, una lista
     por jugador (ver ``disponibilidad.py``) para que un cliente pueda
     habilitar/deshabilitar sus propios botones sin reimplementar ninguna
     regla — la vista es la misma para cualquier solicitante (no hay
     información oculta entre jugadores en este juego), así que cada
     cliente simplemente indexa por su propio ``player_index``.
  4. **Puntuación**: ``Player.puntos_maestria_final`` y
     ``GameEngine.calcular_ranking_final`` son ``@property``/métodos, no
     campos de dataclass — ``dataclasses.asdict`` no los incluye. Se
     calculan aquí (``puntos_maestria_final`` por jugador, ``ranking`` con
     el resultado de ``calcular_ranking_final``) en vez de que el cliente
     reimplemente la fórmula de puntuación de ``CORE_MECHANICS.md`` §3 en
     TypeScript — el mismo principio que la disponibilidad de acciones.
  5. **Mazo de Tendencias de Mercado**: ``Market.mazo_tendencias`` (el mazo
     de Tendencias restante, en orden) se reemplaza por su longitud —
     mismo tratamiento que el mazo de clima y el mazo de recetas. Su
     descarte (``descarte_tendencias``) sí es información pública, igual
     que el descarte de clima/recetas, y se serializa sin cambios.
  6. **Color de jugador y voto de fin anticipado**: ``Seat.color`` y
     ``GameSession.votos_fin_anticipado`` viven en la capa de sala
     (``server/sessions.py``), no en el ``Player``/``GameEngine`` de
     dominio — así que ``game_state_view`` recibe la ``GameSession``
     completa (no solo el ``engine``) para poder anexar ambos a la vista.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from disponibilidad import acciones_disponibles
from serialization import snapshot

if TYPE_CHECKING:
    from server.sessions import GameSession


def game_state_view(sesion: "GameSession") -> Dict[str, Any]:
    """Construye la vista de estado redactada de una partida en curso."""
    engine = sesion.engine
    assert engine is not None, "game_state_view requiere una partida iniciada."
    estado = snapshot(engine)

    entorno = estado["environment"]
    entorno["cartas_clima_restantes"] = len(entorno.pop("mazo_clima"))

    mercado = estado["market"]
    mercado["mazo_recetas_restantes"] = len(mercado.pop("mazo_recetas"))
    mercado["mazo_tendencias_restantes"] = len(mercado.pop("mazo_tendencias"))

    jugador_activo = engine.jugador_activo
    jefe = engine.jefe_investigador

    estado["fase_actual"] = engine.fase_actual.value
    estado["turno_nonce"] = engine.turno_nonce
    estado["jugador_en_turno_idx"] = (
        engine.players.index(jugador_activo) if jugador_activo is not None else None
    )
    estado["jefe_investigador_idx"] = engine.players.index(jefe) if jefe is not None else None
    # Secuencia completa de turno del día (índices en players, [0] = Jefe).
    # Tras el fin de partida conserva el orden del último día — inofensivo:
    # el panel de orden solo se muestra mientras se juega.
    estado["turno_orden"] = engine.turno_orden
    estado["acciones_disponibles"] = [
        acciones_disponibles(engine, jugador) for jugador in engine.players
    ]
    # Campos derivados que `dataclasses.asdict` no incluye (son @property o
    # métodos del engine) más el color, que vive en el asiento y no en el
    # jugador de dominio. `vitalidad_prevista`/`en_riesgo_colapso` se calculan
    # aquí y no en el cliente a propósito: la fórmula del desgaste (incluida la
    # exención por Criopreservación y el -2 de Aletargamiento Invernal) es una
    # regla de CLIMATE_LOGIC.md y no debe duplicarse en TypeScript.
    for datos_jugador, jugador, asiento in zip(estado["players"], engine.players, sesion.seats):
        datos_jugador["puntos_maestria_final"] = jugador.puntos_maestria_final
        datos_jugador["puntos_horneados"] = jugador.puntos_horneados
        datos_jugador["color"] = asiento.color
        datos_jugador["vitalidad_prevista"] = engine.vitalidad_prevista(jugador)
        datos_jugador["en_riesgo_colapso"] = engine.riesgo_colapso(jugador)
        # Los HorneadoRecord del archivo llevan dos @property que asdict no
        # incluye y que el cliente no debe recalcular (la zona en particular
        # es lógica de reglas): se inyectan aquí, registro por registro.
        for clave_archivo, registros in (
            ("archivo_horneado_exitoso", jugador.archivo_horneado_exitoso),
            ("archivo_colapsos", jugador.archivo_colapsos),
        ):
            for datos_registro, registro in zip(datos_jugador[clave_archivo], registros):
                datos_registro["puntos_totales"] = registro.puntos_totales
                datos_registro["zona_resultado"] = registro.zona_resultado
    estado["ranking"] = [
        {"posicion": posicion, "player_idx": engine.players.index(jugador)}
        for posicion, jugador in engine.calcular_ranking_final()
    ]
    estado["votos_fin_anticipado"] = sorted(sesion.votos_fin_anticipado)

    return estado
