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
VERSION_FORMATO = 16
"""
Bumped a 16: `Technologies` gana `comerciante`, la quinta mejora de laboratorio.
Un pickle viejo trae `Technologies` sin ese campo, y la primera compra de la
Accion C tras restaurar lo leeria (ademas de `cantidad_instaladas`, que puntua).

Bumped a 15: `GameEngine` gana `_jefatura_reclamada_por`. La Jefatura ya no se
deduce de la Vitalidad: se reclama con un espacio de accion y la reclamacion
pendiente vive en el motor. Un pickle viejo trae motores sin ese atributo, y la
primera Fase I tras restaurar lo leeria.

Bumped a 14: `Player` gana `contrato_molino`, el Contrato con el Molino que produce
harina cada Fase III. Un pickle viejo trae `Player`s sin el campo, y al restaurarse
`_entregar_rendimiento_molino` leeria un atributo inexistente en la primera noche.

Bumped a 13: la Acidez pasa a ser un dial bidireccional (accion «Descarte») y eso
arrastra dos cambios de economia que un pickle viejo no tiene forma de reflejar. Los
12 `bono_sabor_pts` del catalogo se recortaron y re-derivaron sobre grado x distancia
al centro, y `Recipe` es un campo impreso que viaja DENTRO del pickle en cuatro sitios
(carpeta, estaciones, mercado, archivos), asi que una partida restaurada seguiria
pagando los bonos de la economia anterior. Ademas `Madurez` dejo de premiar la acidez
cruda: una partida a medias guardada bajo la formula vieja puntuaria distinto al
reanudarse. Mismo criterio que el bump de Ingresos de Panaderia.

Bumped a 11: `Recipe` cambia de forma otra vez -- la pista de fermentacion pasa de
tres zonas a CUATRO (`zona_crecimiento` nueva, y `zona_baja`/`zona_sobrefermentada`
renombradas a `zona_pre_fermento`/`zona_colapso`, con sus pagos). Un pickle viejo trae
Recipes con la forma de tres zonas.

Bumped a 10: dos formas persistidas cambian a la vez -- `Recipe` PIERDE
`req_tecnologico` (ninguna receta esta ya restringida por tecnologia) y
`HorneadoRecord` GANA `ampliacion_aplicada` (la ampliacion de zona optima del Modulo
Analitico vigente al hornear, sellada para que `zona_resultado` no reetiquete despues
un horneado optimo como "baja"). Un pickle viejo trae objetos con la forma anterior.

Bumped a 9: `Recipe` cambió de forma -- `harina_base: TipoHarina` pasó a
`harinas: Tuple[Tuple[TipoHarina, int], ...]` (recetas de una o dos harinas,
grados Básica/Intermedia/Avanzada) y el catálogo se re-escaló a 12 cartas. Un
pickle viejo contiene objetos `Recipe` sin `harinas`, que reventarían la primera
vez que una vista intente renderizarlos; descartarlos al cargar convierte eso en
una línea de log. Las partidas en curso al desplegar se pierden: asumido.

Bumped a 6: `Player` ganó `acciones_pa_usadas_hoy` (espacios de acción con
costo de PA ya visitados hoy -- ver PLAYER_STATE.md) -- un pickle viejo sin
ese campo debe descartarse limpiamente en vez de fallar la primera vez que
el engine intente leerlo.

Bumped a 5: `GameSession` ganó `max_jugadores` (capacidad de sala elegida
por el host al crearla) -- un pickle viejo sin ese campo debe descartarse
limpiamente en vez de cargar a medias.

Bumped a 4: `FermentationSlot` ganó `acidez_inicial` (Registro de pH de la
carta de receta, sellado en Acción B). Bumped a 3: la revisión de reglas
GDD v0.0.2 cambió la forma de `Player` (`monedas` nuevo, `crear_dia_1` con
parámetros de Patrocinio en vez de `player_index`), `Recipe` (`puntos_baja`,
`monedas_baja/optima/sobre` nuevos), `Market` (`suministros`/`SupplyLote`
eliminados; `posiciones_harina`, `mazo_tendencias`, `descarte_tendencias`
nuevos) y `GameEngine.__init__` (`orden_inicial` nuevo). Bumped a 2: `Seat`
ganó `color` y `GameSession` ganó `votos_fin_anticipado` desde la versión 1.
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
