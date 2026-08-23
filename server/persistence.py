"""
server/persistence.py — Persistencia Duradera de Salas en Disco
====================================================================
Guarda un snapshot de cada ``GameSession`` en ``data/games/{id}.pkl``
después de cada mutación, y los recarga al arrancar el proceso — para que
un reinicio accidental del servidor durante una sesión de juego (un
despliegue, un crash, un reinicio manual) no se lleve por delante partidas
en curso.

Se eligió ``pickle`` sobre un códec JSON hecho a mano: ``GameEngine``
mantiene estado interno de la máquina de turno (``Fase``, orden, cursor,
nonce, jugadores que ya pasaron — ver ``engine.py`` Milestone 1) sin
ningún getter/setter pensado para serialización externa; reconstruirlo
desde JSON exigiría agregar esa superficie a ``engine.py`` solo para este
propósito. ``pickle`` serializa y restaura cualquier grafo de objetos de
Python — incluidas referencias circulares, como
``GameEngine._event_sink`` apuntando de vuelta a
``GameSession.difundir_evento`` — sin ningún código de serialización
propio (confirmado empíricamente: ``GameSession`` con un ``GameEngine`` en
curso, incluidos suscriptores SSE activos, hace round-trip correctamente).

``GameSession.__getstate__``/``__setstate__`` excluyen ``lock`` y
``suscriptores`` del pickle — ambos son artefactos del proceso en curso
(un ``asyncio.Lock``/``asyncio.Queue`` no tiene sentido fuera del event
loop que los creó) y se reconstruyen vacíos/nuevos al cargar.

**Limitación aceptada explícitamente**: un pickle es frágil frente a
cambios de forma en las clases — un campo nuevo o renombrado en
``Player``/``GameSession``/etc. puede hacer que un pickle viejo no cargue.
Se versiona el archivo (``VERSION_FORMATO``) y se descarta con un log
claro en vez de fallar en silencio si la versión no coincide — "un
despliegue con cambios de esquema puede terminar partidas en curso" es una
limitación aceptada de este nivel de persistencia, no un descuido.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from server.sessions import GameSession

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/games")
VERSION_FORMATO = 3
"""
Bumped a 3: la revisión de reglas GDD v0.0.2 cambió la forma de `Player`
(`monedas` nuevo, `crear_dia_1` con parámetros de Patrocinio en vez de
`player_index`), `Recipe` (`puntos_baja`, `monedas_baja/optima/sobre`
nuevos), `Market` (`suministros`/`SupplyLote` eliminados; `posiciones_harina`,
`mazo_tendencias`, `descarte_tendencias` nuevos) y `GameEngine.__init__`
(`orden_inicial` nuevo) -- un pickle viejo con la forma anterior debe
descartarse limpiamente en vez de cargar a medias y fallar con
AttributeError la primera vez que el código nuevo toque alguno de esos
campos. (Bumped a 2: `Seat` ganó `color` y `GameSession` ganó
`votos_fin_anticipado` desde la versión 1.)
"""


def guardar(sesion: "GameSession") -> None:
    """
    Escribe (o sobreescribe) el snapshot de una sala en disco.

    Escritura atómica (escribe a un archivo temporal y lo renombra encima
    del definitivo) para que un crash a mitad de escritura nunca deje un
    ``.pkl`` corrupto. No lanza excepciones: un fallo de persistencia no
    debe tumbar una petición que ya aplicó correctamente la mutación en
    memoria — solo se registra en el log.
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ruta = DATA_DIR / f"{sesion.id}.pkl"
        ruta_temporal = ruta.with_suffix(".pkl.tmp")
        with ruta_temporal.open("wb") as f:
            pickle.dump((VERSION_FORMATO, sesion), f)
        ruta_temporal.replace(ruta)
    except Exception:
        logger.exception("No se pudo guardar la sala %s en disco.", sesion.id)


def borrar(room_id: str) -> None:
    """Elimina el snapshot en disco de una sala (p. ej. al limpiarla por inactividad)."""
    (DATA_DIR / f"{room_id}.pkl").unlink(missing_ok=True)


def cargar_todas() -> Iterator["GameSession"]:
    """
    Recarga todas las salas persistidas en ``data/games/`` al arrancar el
    proceso. Un archivo con versión de formato distinta o corrupto se
    descarta (se borra, con un log claro) en vez de abortar el arranque
    del servidor por una sola sala ilegible.
    """
    if not DATA_DIR.exists():
        return
    for ruta in sorted(DATA_DIR.glob("*.pkl")):
        try:
            with ruta.open("rb") as f:
                version, sesion = pickle.load(f)
            if version != VERSION_FORMATO:
                logger.warning(
                    "Descartando %s: versión de formato %s (esperada %s).",
                    ruta, version, VERSION_FORMATO,
                )
                ruta.unlink(missing_ok=True)
                continue
        except Exception:
            logger.exception("Descartando snapshot ilegible: %s", ruta)
            ruta.unlink(missing_ok=True)
            continue
        yield sesion
