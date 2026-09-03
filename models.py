"""
models.py — Motor Lógico de Fermentum
======================================
Define todas las entidades de datos puras del simulador del juego de mesa Fermentum.

Contenido:
  · Enumeraciones de dominio (Grado, TipoHarina, TecnologiaID, …)
  · Entidades inmutables del catálogo (Recipe, ClimateCard)
  · Entidades mutables de estado de partida (FermentationSlot, HorneadoRecord,
    Technologies, Player, Environment)
  · Catálogos maestros constantes (RECIPE_CATALOG, CLIMATE_CATALOG)
  · Funciones de utilidad para el setup inicial

Estándares aplicados (ARCHITECTURE.md):
  · Strict type hinting en todos los atributos, métodos y retornos (PEP 484)
  · @dataclass para todas las entidades; frozen=True en entidades de catálogo
  · Inmutabilidad del catálogo: RECIPE_CATALOG y CLIMATE_CATALOG son constantes
  · Separación de responsabilidades: sólo datos puros, sin lógica de turnos
  · Excepciones semánticas pertenecen a exceptions.py (fuera del alcance aquí)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
from types import MappingProxyType


# ===========================================================================
# SECCIÓN 1: ENUMERACIONES DE DOMINIO
# ===========================================================================


class Grado(str, Enum):
    """
    Nivel de complejidad de una receta de panificación.

    El grado NO se elige libremente: es una consecuencia de las harinas que la
    carta imprime (ver ``_grado_desde_harinas``). Se conserva como campo — y no
    como ``@property`` — porque ``dataclasses.asdict`` sólo serializa campos, y
    ``serialization.snapshot`` es lo que alimenta tanto el snapshot dorado como
    el estado que viaja al cliente. ``Recipe.__post_init__`` valida que el campo
    coincida con lo que implican las harinas, de modo que una carta mal
    etiquetada es un error de importación, no un fallo de renderizado.
    """

    BASICA = "Básica"
    INTERMEDIA = "Intermedia"
    AVANZADA = "Avanzada"


class TipoHarina(str, Enum):
    """Tipos de token de harina disponibles en el mercado central."""

    BLANCA = "Blanca"
    CENTENO = "Centeno"
    INTEGRAL = "Integral"


class TecnologiaID(str, Enum):
    """
    Identificadores de las mejoras de laboratorio (Zona 4 del tablero personal).
    Los valores de cadena coinciden con los nombres de atributo en Technologies.
    """

    INCUBADORA = "incubadora"
    CAMARA_B = "camara_b"
    MODULO_ANALITICO = "modulo_analitico"
    CRIOPRESERVACION = "criopreservacion"
    COMERCIANTE = "comerciante"

    @property
    def nombre_legible(self) -> str:
        """
        Nombre de la mejora tal y como se imprime en el tablero.

        Los valores del enum son nombres de atributo (``modulo_analitico``), no
        texto para leer: cualquier mensaje dirigido a un jugador debe pasar por
        aquí. Vive en el enum para que exista UNA tabla y no una por consumidor.
        """
        return {
            TecnologiaID.INCUBADORA: "Incubadora",
            TecnologiaID.CAMARA_B: "Cámara B",
            TecnologiaID.MODULO_ANALITICO: "Módulo Analítico",
            TecnologiaID.CRIOPRESERVACION: "Criopreservación",
            TecnologiaID.COMERCIANTE: "Comerciante",
        }[self]


class EfectoClimatico(str, Enum):
    """
    Efectos pasivos que una carta de clima puede activar durante la Fase III.
    Solo los efectos que alteran la resolución automática tienen entrada aquí.
    """

    NINGUNO = "ninguno"
    ALTA_HUMEDAD = "Alta Humedad"
    ALETARGAMIENTO_INVERNAL = "Aletargamiento Invernal"


class EfectoBiologico(str, Enum):
    """
    Efectos biológicos inmediatos de las cartas de clima, aplicados a todos
    los jugadores durante la Fase I (antes de las acciones).
    """

    NINGUNO = "ninguno"
    GANANCIA_VITALIDAD = "Ganancia Vitalidad"  # +1 Vitalidad a todos (máx 6)
    GANANCIA_ACIDEZ = "Ganancia Acidez"  # +1 Acidez a todos (máx 6)


# ===========================================================================
# SECCIÓN 2: ENTIDADES DE CATÁLOGO INMUTABLES
# ===========================================================================


HARINAS_ESPECIALES: Tuple[TipoHarina, ...] = (TipoHarina.CENTENO, TipoHarina.INTEGRAL)
"""
Harinas "especiales": las dos que no son el producto básico del mercado.
La Blanca es la harina común (la más barata de las tres pistas de la Bolsa,
2-6 Monedas la bolsa entera); Centeno e Integral cuestan 6-10 y 4-8, y son
las únicas que pueden sostener una receta Avanzada.
"""

PCT_RECETA_TOTAL: int = 100
"""Porcentaje de harina que consume CUALQUIER receta, sea cual sea su grado."""

VITALIDAD_INICIAL: int = 2
"""
Vitalidad del cultivo base de todo jugador al empezar la partida (PLAYER_STATE.md §2).

Es 2 y no 1 por una razón concreta: el desgaste metabólico de la Fase III resta -1 y
la Acción A repone +1 una vez al día, de modo que un jugador que alimenta a diario
ORBITA en su valor inicial. Partiendo de 1, la carta «Aletargamiento Invernal» (-2, dos
copias en un mazo de 30) lo dejaba en 0 -> contaminación inevitable, sin jugada posible
que la evitara: no era una decisión mal tomada, era el barajado. Partiendo de 2 la misma
carta lo deja en 1, y la contaminación vuelve a castigar lo que debe castigar, que es
descuidar el mantenimiento. Ver CLIMATE_LOGIC.md.
"""

ACIDEZ_EQUILIBRIO_CENTRO: int = 3
"""
Nivel de Acidez que corona el término «Madurez del Cultivo» (CORE_MECHANICS.md §3.3).

Es el centro exacto de la pista 0-6. Madurez ya no premia la acidez CRUDA sino el
EQUILIBRIO: un cultivo maduro es uno compensado, no uno maximamente ácido. El cambio
es la contrapartida de que la Acidez pasara a ser un dial bidireccional (la Acción
«Descarte»): mientras sólo subía, premiar el nivel bruto no tenía coste alguno y
empujaba a todo el mundo al mismo extremo. Ahora los dos extremos de la pista pagan
0 puntos, así que las recetas de diana extrema — Panettone y Brioche en 1,
Pumpernickel en 5-6 — cuestan Madurez mientras las sostienes, que es exactamente por
lo que su Bono de Sabor vale más (ver bono_sabor_pts en RECIPE_CATALOG).
"""

PUNTOS_EQUILIBRIO_MAX: int = 3
"""
Puntos de Madurez que otorga estar justo en ``ACIDEZ_EQUILIBRIO_CENTRO``.

El término completo es ``vitalidad + (PUNTOS_EQUILIBRIO_MAX - |acidez - centro|)``, que
decae un punto por casilla hacia cada lado y llega a 0 en los extremos 0 y 6. Vale 3 y
no otro número porque es la distancia del centro a cualquiera de los dos extremos: así
la caída llega a cero exactamente en el borde de la pista, sin necesidad de un clamp.
"""


def puntos_triangulares(n: int) -> int:
    """
    Curva triangular ``n*(n+1)//2``, compartida por los dos términos de
    AMPLITUD de la puntuación final: «Variedad de Recetas» (sobre las recetas
    distintas horneadas) y «Desarrollo Tecnológico» (sobre las mejoras
    instaladas). Ver CORE_MECHANICS.md §3.

    Escala 0, 1, 3, 6, 10, 15... es decir, incrementos 1, 2, 3, 4, 5: cada
    unidad nueva vale más que la anterior, de modo que repetir renuncia al
    incremento más grande disponible y no a un promedio.

    Vive suelta, y no dentro de las properties que la usan, por dos razones que
    se refuerzan: los reglamentos imprimen las DOS tablas y
    ``tests/test_reglamento_al_dia.py`` las contrasta celda a celda contra
    ESTA función, así que hay una sola derivación para dos tablas y ninguna
    puede desviarse en silencio; y que las dos curvas sean literalmente la
    misma es lo que permite al reglamento decir «la misma curva que Variedad»
    en vez de imprimir una segunda fórmula sin relación.
    """
    return n * (n + 1) // 2


AMPLIACION_OPTIMA_MODULO: int = 1
"""
Casillas que el Módulo Analítico añade a CADA lado de la zona óptima.

Vive aquí y no en engine.py porque ``Recipe.__post_init__`` lo necesita para validar
que el pre-fermento de una carta no se vacíe al ampliarse, y ``models`` no puede
importar ``engine`` (la dependencia va en un solo sentido). Su sitio natural es junto
a ``Recipe.zonas_efectivas``, donde ya vive toda la aritmética del ensanchado.

Es un efecto EN VIVO: se recalcula en cada resolución a partir de las tecnologías del
propietario, así que instalar el Módulo salva una masa que ya está fermentando. Como
la ampliación se come la zona de colapso por arriba, **también retrasa el umbral de
colapso**. El dial de la Incubadora llegó al mismo sitio por otro camino — lo fija su
dueño noche a noche en la Fase II en vez de recalcularse solo —, de modo que ninguna
de las dos mejoras deja ya fuera a una masa que empezó antes de comprarlas.
"""

ANCHO_MINIMO_PRE_FERMENTO: int = AMPLIACION_OPTIMA_MODULO + 1
"""
Casillas mínimas que debe imprimir el pre-fermento de una carta.

Se DERIVA de la ampliación en vez de ser un 2 escrito a mano: si el Módulo llegara a
ensanchar 2 casillas, este mínimo sube solo. Sin él, una carta con un pre-fermento de
una sola casilla lo veria desaparecer en un rango invertido al instalarse el Módulo.
"""


def _grado_desde_harinas(harinas: Tuple[Tuple[TipoHarina, int], ...]) -> Grado:
    """
    Deriva el grado de una receta a partir de las harinas que imprime.

    La regla es la definición del grado, no una heurística:
      · Una sola harina Blanca al 100%      -> Básica
      · Una sola harina especial al 100%    -> Avanzada
      · Dos harinas distintas al 50% cada una -> Intermedia

    Las dos formas legales (100 y 50+50) son exactamente las dos que la Bolsa
    de Harinas sabe vender: bolsa entera (10 tokens) y media bolsa (5 tokens).
    No existe un primitivo de compra por token suelto, así que un reparto
    90/10 sería impagable en el mercado.

    Raises:
        ValueError: Si el reparto no es ninguna de las dos formas legales
            (número de harinas, tipos repetidos o porcentajes incorrectos).
    """
    if len(harinas) == 1:
        (tipo, pct), = harinas
        if pct != PCT_RECETA_TOTAL:
            raise ValueError(
                f"Una receta de una sola harina debe pedir {PCT_RECETA_TOTAL}%; "
                f"recibido {pct}% de {tipo.value}."
            )
        return Grado.AVANZADA if tipo in HARINAS_ESPECIALES else Grado.BASICA

    if len(harinas) == 2:
        (tipo_a, pct_a), (tipo_b, pct_b) = harinas
        if tipo_a is tipo_b:
            raise ValueError(
                f"Una receta Intermedia mezcla dos harinas DISTINTAS; "
                f"recibido {tipo_a.value} dos veces."
            )
        mitad = PCT_RECETA_TOTAL // 2
        if pct_a != mitad or pct_b != mitad:
            raise ValueError(
                f"Una receta Intermedia se reparte {mitad}/{mitad} (media bolsa "
                f"de cada tipo); recibido {pct_a}/{pct_b}."
            )
        return Grado.INTERMEDIA

    raise ValueError(
        f"Una receta imprime una o dos harinas; recibidas {len(harinas)}."
    )


@dataclass(frozen=True)
class Recipe:
    """
    Representa una carta de receta del catálogo maestro.

    Inmutable (frozen=True): todas las instancias son referencias de solo lectura
    compartidas entre el catálogo, las carpetas de jugadores y las estaciones.

    Attributes:
        id: Identificador único de la receta (snake_case, ej. "pan_de_campo").
        nombre: Nombre legible para mostrar en la interfaz.
        grado: Nivel de complejidad (Básica / Intermedia / Avanzada). Derivado de
            ``harinas`` y validado en ``__post_init__``; ver ``_grado_desde_harinas``.
        harinas: Harinas impresas en la carta, como pares (tipo, porcentaje), en
            el orden en que deben mostrarse. Suman siempre 100%: una entrada al
            100% (Básica si es Blanca, Avanzada si es especial) o dos entradas
            distintas al 50% (Intermedia).
        hidratacion_pct: Porcentaje total de hidratación de la masa.
        tokens_agua: Cantidad de tokens de agua (5% c/u) requeridos para iniciarla.
        acidez_diana: Conjunto de niveles de acidez que activan el Bono de Sabor.
        bono_sabor_pts: Puntos de Maestría del bono de acidez impresos en la carta
            (GDD v0.0.2, Módulo IV §2 — columna "Bono"). Sigue siendo un campo
            IMPRESO y no una @property, por la misma razón que ``grado`` (ver
            ``__post_init__``): ``serialization.snapshot`` es ``dataclasses.asdict``
            y no serializa propiedades. Pero los 12 valores del catálogo NO son
            libres: se derivan de ``base(grado) + (1 si la diana está fuera del
            centro)``, con base Básica 1 / Intermedia 2 / Avanzada 3 y la distancia
            medida como la MÍNIMA de ``acidez_diana`` a ``ACIDEZ_EQUILIBRIO_CENTRO``
            (con un dial de acidez el jugador elige el extremo más cercano del rango).
            Es el reverso exacto de la Madurez por equilibrio: una diana extrema te
            saca del pico de Madurez mientras la sostienes, y el bono te paga por
            ello. ``tests/test_acidez_descarte.py`` verifica la regla sobre el
            catálogo entero, así que una carta nueva no puede salirse de ella.
        zona_crecimiento: Rango [inicio, fin] donde la masa todavía crece y NO es pan:
            no se puede hornear (Acción F la rechaza), así que no tiene pago asociado.
            Es además el caso por defecto: ver ``esta_en_crecimiento``.
        zona_pre_fermento: Rango [inicio, fin] donde la masa está cruda pero ya hornea,
            con puntos y monedas reducidos.
        zona_optima: Rango [inicio, fin] objetivo (puntos máximos y posible Dato extra).
        zona_colapso: Rango [inicio, fin] donde la masa colapsa automáticamente.
        puntos_pre_fermento: Puntos de Maestría al hornear dentro de zona_pre_fermento.
        puntos_optimos: Puntos de Maestría al hornear dentro de zona_optima.
        penalizacion_colapso: Puntos negativos aplicados en un horneado de emergencia.
        monedas_pre_fermento: Monedas cobradas al hornear y vender en zona_pre_fermento.
        monedas_optima: Monedas cobradas al hornear y vender en zona_optima.
        monedas_colapso: Monedas cobradas al hornear (automáticamente) en zona_colapso.
    """

    id: str
    nombre: str
    grado: Grado
    harinas: Tuple[Tuple[TipoHarina, int], ...]
    hidratacion_pct: int
    tokens_agua: int
    acidez_diana: Tuple[int, ...]
    bono_sabor_pts: int
    zona_crecimiento: Tuple[int, int]
    zona_pre_fermento: Tuple[int, int]
    zona_optima: Tuple[int, int]
    zona_colapso: Tuple[int, int]
    puntos_pre_fermento: int
    puntos_optimos: int
    penalizacion_colapso: int  # Valor negativo, ej. -2
    monedas_pre_fermento: int
    monedas_optima: int
    monedas_colapso: int

    def __post_init__(self) -> None:
        """
        Valida el reparto de zonas y que el grado coincida con las harinas impresas.

        Sólo valida: no asigna nada, así que es compatible con frozen=True.
        Como ``RECIPE_CATALOG`` es una constante de nivel de módulo, una carta
        mal etiquetada revienta en ``import models`` — nunca a mitad de partida.

        Raises:
            ValueError: Si el pre-fermento es tan estrecho que el Módulo Analítico lo
                vaciaría, si el reparto de harinas es ilegal, o si ``grado`` no es el
                que ese reparto implica.
        """
        ancho_pre_fermento = self.zona_pre_fermento[1] - self.zona_pre_fermento[0] + 1
        if ancho_pre_fermento < ANCHO_MINIMO_PRE_FERMENTO:
            raise ValueError(
                f"Receta '{self.id}': el pre-fermento mide {ancho_pre_fermento} "
                f"casilla(s) y se vaciaría al ampliarse la zona óptima "
                f"(mínimo {ANCHO_MINIMO_PRE_FERMENTO}, ver ANCHO_MINIMO_PRE_FERMENTO)."
            )

        esperado = _grado_desde_harinas(self.harinas)
        if self.grado is not esperado:
            impresas = " + ".join(f"{t.value} {p}%" for t, p in self.harinas)
            raise ValueError(
                f"Receta '{self.id}': declara grado '{self.grado.value}' pero "
                f"imprime {impresas}, que implica '{esperado.value}'."
            )

    # ------------------------------------------------------------------
    # Requerimiento de insumos (derivado de las harinas impresas)
    # ------------------------------------------------------------------

    @property
    def requisito_harina(self) -> Dict[str, int]:
        """
        Harinas requeridas como ``{nombre_tipo: porcentaje}``.

        Deliberadamente con la MISMA forma que ``Player.reserva_harina``, para que
        validar y cobrar el coste sea un único bucle sobre claves que coinciden
        (ver ``ActionManager._require_harinas`` y la Acción B).
        """
        return {tipo.value: pct for tipo, pct in self.harinas}

    # ------------------------------------------------------------------
    # Métodos de consulta de zona (sin efectos secundarios)
    # ------------------------------------------------------------------

    def zonas_efectivas(
        self, ampliacion: int = 0
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """
        Las CUATRO zonas del track tras aplicar una ampliación de la zona óptima.

        El Módulo Analítico ensancha la zona óptima ``ampliacion`` casillas por cada
        lado (``AMPLIACION_OPTIMA_MODULO``), a costa del pre-fermento por abajo y del
        colapso por arriba — es decir, **también retrasa el umbral de colapso**. Toda
        la aritmética del ensanchado vive AQUÍ y en ningún otro sitio.

        El **crecimiento nunca se amplía**: es lo que mantiene fija la frontera de "ya
        se puede hornear" aunque el jugador compre el Módulo a media fermentación.

        La ampliación es un efecto EN VIVO del propietario de la masa, no un valor
        sellado en la carta: por eso es un argumento y no un campo. La carta impresa
        (``ampliacion=0``) sigue siendo lo que se ve en el mercado.

        Args:
            ampliacion: Casillas que se añaden a cada lado de la zona óptima.

        Returns:
            ``(crecimiento, pre_fermento, optima, colapso)`` ya ampliadas.
        """
        crecimiento = self.zona_crecimiento
        pre_fermento = (self.zona_pre_fermento[0], self.zona_pre_fermento[1] - ampliacion)
        optima = (self.zona_optima[0] - ampliacion, self.zona_optima[1] + ampliacion)
        colapso = (self.zona_colapso[0] + ampliacion, self.zona_colapso[1])
        return crecimiento, pre_fermento, optima, colapso

    def esta_en_crecimiento(self, posicion: int, ampliacion: int = 0) -> bool:
        """
        Retorna True si la masa todavía está creciendo y no es pan: no se puede
        hornear (Acción F la rechaza).

        Es el CAJÓN DE SASTRE a propósito, no un rango cerrado: cualquier posición que
        no caiga en pre-fermento, óptima ni colapso cuenta como crecimiento —
        incluida la 0, donde nace toda masa recién inoculada y que no pertenece a
        ninguna zona impresa. Que el caso por defecto sea el que NO paga nada es
        justamente lo que cierra el agujero que existía cuando el caso por defecto
        era el pre-fermento, que sí paga.
        """
        _, pre_fermento, optima, colapso = self.zonas_efectivas(ampliacion)
        return not (
            pre_fermento[0] <= posicion <= pre_fermento[1]
            or optima[0] <= posicion <= optima[1]
            or posicion >= colapso[0]
        )

    def esta_en_pre_fermento(self, posicion: int, ampliacion: int = 0) -> bool:
        """Retorna True si la masa está cruda pero ya hornea con puntos reducidos."""
        _, pre_fermento, _, _ = self.zonas_efectivas(ampliacion)
        return pre_fermento[0] <= posicion <= pre_fermento[1]

    def esta_en_zona_optima(self, posicion: int, ampliacion: int = 0) -> bool:
        """Retorna True si la posición está dentro del rango de horneado óptimo."""
        _, _, optima, _ = self.zonas_efectivas(ampliacion)
        return optima[0] <= posicion <= optima[1]

    def esta_en_colapso(self, posicion: int, ampliacion: int = 0) -> bool:
        """
        Retorna True si la posición alcanzó el colapso estructural.
        Gatilla un horneado automático de emergencia en la Fase III.
        """
        _, _, _, colapso = self.zonas_efectivas(ampliacion)
        return posicion >= colapso[0]

    def es_centro_exacto(self, posicion: int) -> bool:
        """
        Retorna True si la posición es el punto central exacto de la zona óptima.
        El centro exacto otorga un Dato extra con el Módulo Analítico instalado.

        NO acepta ``ampliacion`` a propósito: ensanchar simétricamente no mueve el
        centro, porque ``(a - n + b + n) // 2 == (a + b) // 2`` para cualquier n. Una
        zona más ancha perdona más, pero acertar el centro exacto sigue siendo
        igual de difícil — la precisión sigue siendo una destreza real.
        """
        inicio, fin = self.zona_optima
        return posicion == (inicio + fin) // 2

    def acidez_activa_bono(self, acidez_actual: int) -> bool:
        """
        Comprueba si el nivel de acidez dado coincide con la acidez_diana de la receta.
        Se invoca al sellar el Cubo de Laboratorio en la Acción B (Iniciar Receta).
        """
        return acidez_actual in self.acidez_diana


@dataclass(frozen=True)
class ClimateCard:
    """
    Representa un tipo de carta del mazo de Clima.

    Inmutable: funciona como plantilla. El mazo construido contiene referencias
    a estas instancias (ver build_climate_deck()).

    Attributes:
        id: Identificador único del tipo de carta (snake_case).
        nombre: Nombre del evento climático para mostrar.
        cantidad: Número de copias de esta carta en el mazo maestro (30 total).
        modificador_termico: Variación de temperatura en °C aplicada al entorno.
        efecto_biologico: Efecto instantáneo aplicado en Fase I a todos los jugadores.
        efecto_pasivo: Condición especial vigente durante la resolución de Fase III.
    """

    id: str
    nombre: str
    cantidad: int
    modificador_termico: int
    efecto_biologico: EfectoBiologico
    efecto_pasivo: EfectoClimatico


@dataclass(frozen=True)
class PatrocinioCard:
    """
    Carta de Patrocinio (GDD v0.0.2, Módulo I §6.4 / Anexo B) — determina, para
    el Día 1 únicamente, el orden de turno y los recursos iniciales de un jugador.

    Se reparte 1 carta (de un mazo de 8, barajado) a cada jugador sentado en
    `bootstrap.create_game()`. El jugador con menor `iniciativa` recibe el token
    de Investigador Jefe y actúa primero; el resto se ordena ascendentemente.

    Attributes:
        iniciativa: Prioridad de turno del Día 1 (1 = primero / Investigador Jefe).
        tipo_harina: Tipo de harina otorgado al desplegar insumos.
        harina_pct: Cantidad de harina otorgada, en porcentaje (100 = 1 bolsa,
            200 = 2 bolsas).
        agua_tokens: Tokens de agua otorgados (cada uno = 5% de hidratación).
        monedas: Monedas otorgadas.
        datos: Datos de Investigación otorgados. Se reparten de forma inversa a
            las Monedas de la carta (la que menos dinero da, más investigación),
            de modo que el patrocinador tacaño compense con conocimiento. Sin
            ellos el juego se queda sin fuente de Datos hasta el primer horneado
            en Óptima, porque el Simposio Técnico ahora exige sacrificar un
            horneado del archivo (ver ACTIONS_REGISTRY.md §Simposio).
    """

    iniciativa: int
    tipo_harina: TipoHarina
    harina_pct: int
    agua_tokens: int
    monedas: int
    datos: int


# ===========================================================================
# SECCIÓN 3: ENTIDADES DE ESTADO DE PARTIDA (MUTABLES)
# ===========================================================================


@dataclass
class FermentationSlot:
    """
    Masa activa en una estación de fermentación (Zona 2 del tablero personal).
    Creada al ejecutar la Acción B (Iniciar Receta) y destruida al hornear.

    Attributes:
        recipe: Referencia a la carta de receta del catálogo (solo lectura).
        dado_inoculo: Valor sellado del dado = Vitalidad del jugador al iniciar (1–6).
            Determina la velocidad de fermentación de esta masa específica.
        posicion_track: Posición acumulada en el track de fermentación (inicia en 0).
        bono_sabor: True si la acidez al iniciar estaba dentro de acidez_diana.
            Se sella el Cubo de Laboratorio en la carta si es True.
        modificador_incubadora: Ajuste de avance de ESTA NOCHE (-1 / 0 / +1).
            Lo fija su dueño durante la Fase II con la acción gratuita
            ``incubadora`` (requiere la tecnología del mismo nombre), masa por
            masa, y la Fase III lo pone de nuevo a 0 tras aplicarlo
            (``GameEngine._avanzar_masas_jugador``). **No se sella al iniciar la
            receta**: una masa que ya estaba fermentando cuando se instaló la
            Incubadora también se puede ajustar, que es justo el caso en el que
            un modificador sellado dejaba la mejora sin efecto.
        acidez_inicial: Acidez del jugador en el momento de sellar esta masa
            (Registro de pH de la carta). Solo informativo para la UI —
            `bono_sabor` ya es el booleano autoritativo que engine.py usa al
            hornear; este valor deja ver, en retrospectiva, qué acidez quedó
            registrada frente a `recipe.acidez_diana`.
    """

    recipe: Recipe
    dado_inoculo: int  # Campo requerido — debe ser 1-6 (= Vitalidad al iniciar)
    posicion_track: int = 0
    bono_sabor: bool = False
    modificador_incubadora: int = 0  # -1, 0 o +1
    acidez_inicial: int = 0

    def __post_init__(self) -> None:
        # Validaciones de integridad de datos en el origen.
        # Las violaciones de regla de negocio (ej. PA insuficientes) se
        # gestionan en engine.py mediante excepciones de exceptions.py.
        if not (1 <= self.dado_inoculo <= 6):
            raise ValueError(
                f"dado_inoculo debe estar entre 1 y 6 (= Vitalidad al iniciar). "
                f"Recibido: {self.dado_inoculo}"
            )
        if self.modificador_incubadora not in (-1, 0, 1):
            raise ValueError(
                f"modificador_incubadora debe ser -1, 0 o 1. "
                f"Recibido: {self.modificador_incubadora}"
            )

    def calcular_avance(self, temperatura_actual: int) -> int:
        """
        Calcula el avance de la masa durante la Fase III (Cinética Biológica).

        Fórmula (CLIMATE_LOGIC.md §3):
            Avance_Final = (temperatura_actual // 5) + dado_inoculo + modificador_incubadora

        El ``dado_inoculo`` está sellado desde la Acción B; el
        ``modificador_incubadora`` es el ajuste que su dueño fijó para esta
        noche concreta y que la Fase III limpia después de aplicarlo.

        Args:
            temperatura_actual: Temperatura del laboratorio en el turno actual (°C).

        Returns:
            Número de casillas que avanza esta masa en su track de fermentación.
        """
        return (temperatura_actual // 5) + self.dado_inoculo + self.modificador_incubadora


@dataclass(frozen=True)
class HorneadoRecord:
    """
    Registro inmutable de una receta completada (horneado exitoso o colapso).
    Almacenado en `archivo_horneado_exitoso` o `archivo_colapsos` del jugador.

    Attributes:
        recipe: Carta de receta completada.
        posicion_final: Posición del track en el momento del horneado.
        puntos_base: Puntos de Maestría obtenidos por la zona del track.
            Positivos si zona óptima/baja, negativo (penalizacion_colapso) si colapso.
        bono_sabor_aplicado: True si el Cubo de Laboratorio estaba sellado en la carta.
        fue_colapso: True si el horneado fue de emergencia (masa sobrefermentada).
        datos_obtenidos: Datos de Investigación recibidos al hornear.
            0 si fue colapso o si la posición no es zona óptima.
        monedas_obtenidos: Monedas recibidas al hornear y vender (Acción F), ya
            incluyendo el Bono de Sabor de +2 Monedas si aplica (GDD v0.0.2 Módulo III §F).
        ampliacion_aplicada: Casillas de ampliación de la zona óptima vigentes para el
            propietario en el momento del horneado (Módulo Analítico). Se SELLA aquí
            porque ``zona_resultado`` se deriva de las zonas: sin este campo, un
            horneado que puntuó como óptimo gracias al Módulo se archivaría para
            siempre como "baja" al releerlo contra las zonas impresas.
    """

    recipe: Recipe
    posicion_final: int
    puntos_base: int
    bono_sabor_aplicado: bool
    fue_colapso: bool
    datos_obtenidos: int = 0
    monedas_obtenidos: int = 0
    ampliacion_aplicada: int = 0

    @property
    def puntos_totales(self) -> int:
        """Suma de puntos base y bono de sabor para este horneado."""
        bonus = self.recipe.bono_sabor_pts if self.bono_sabor_aplicado else 0
        return self.puntos_base + bonus

    @property
    def puntos_bono_sabor(self) -> int:
        """Puntos de Maestría otorgados por el Bono de Sabor (0 si no se aplicó)."""
        return self.recipe.bono_sabor_pts if self.bono_sabor_aplicado else 0

    @property
    def datos_generados(self) -> int:
        """Alias de ``datos_obtenidos`` (Datos de Investigación ganados al hornear)."""
        return self.datos_obtenidos

    @property
    def zona_resultado(self) -> str:
        """
        Zona del track de fermentación en la que se resolvió este horneado.

        Un colapso (automático o manual desde zona sobrefermentada) siempre
        resuelve en "colapso", replicando la lógica de puntuación de
        ``GameEngine._calcular_puntos_zona``.
        """
        amp = self.ampliacion_aplicada
        if self.fue_colapso or self.recipe.esta_en_colapso(self.posicion_final, amp):
            return "colapso"
        if self.recipe.esta_en_zona_optima(self.posicion_final, amp):
            return "optima"
        # Nunca "crecimiento": la Acción F rechaza una masa que todavía crece, y el
        # colapso automático solo dispara en la zona de colapso. Todo registro
        # archivado nació en pre-fermento, óptima o colapso.
        return "pre_fermento"


@dataclass
class Technologies:
    """
    Estado de las mejoras de laboratorio instaladas (Zona 4 del tablero personal).

    Regla de negocio (validada en engine.py, ACTIONS_REGISTRY.md §2D): cada mejora
    individual solo puede instalarse UNA vez por partida, pero un jugador puede
    llegar a instalar varias mejoras distintas a lo largo de la partida; esta
    clase únicamente registra qué está instalado.

    Attributes:
        incubadora: Permite ajuste local de temperatura ±5°C en la Fase III
            para una masa específica (``FermentationSlot.modificador_incubadora``
            = ±1). Es un **dial que se fija cada noche** con la acción gratuita
            ``incubadora`` durante la Fase II, no un valor sellado al iniciar la
            receta: instalarla salva una masa que ya está fermentando, igual que
            el Módulo Analítico. La Fase III devuelve el dial a 0 tras aplicarlo,
            así que un ajuste olvidado no arrastra a la noche siguiente.
        camara_b: Desbloquea la Estación 03 (índice 2) y mejora la Acción E (Pliegues):
            permite repartir los espacios comprados entre dos masas (no aumenta
            cuántos se compran) y habilita la variante de recuperar +1 Vitalidad.
        modulo_analitico: Genera +1 Dato al hornear en centro exacto y
            habilita el inicio de recetas de grado Avanzado.
        criopreservacion: Efecto pasivo "Estasis Biológica" — durante la Fase III,
            el cultivo base ignora el desgaste metabólico normal (no resta Vitalidad).
            La Estasis es el estado **por defecto**, pero su dueño puede suspenderla
            para una noche concreta con la acción gratuita ``estasis``
            (``Player.estasis_suspendida``): sin esa válvula, alimentar a diario
            empuja la Vitalidad a 6 y la deja clavada ahí, y como la Acción B sella
            el Dado de Inóculo con la Vitalidad del día, las recetas Avanzadas
            (zona óptima de 2-3 casillas) se vuelven inhorneables justo para quien
            pagó la mejora.
        comerciante: Mejores condiciones de compra en la Acción C: cada transacción
            de COMPRA de la visita (bolsa o media bolsa de harina, lote de agua,
            firma del Contrato con el Molino) cuesta ``DESCUENTO_COMERCIANTE``
            Monedas menos, con suelo de 1. **No toca el lado de venta** y **no
            altera el movimiento del visor** — ver ``actions.DESCUENTO_COMERCIANTE``.
    """

    incubadora: bool = False
    camara_b: bool = False
    modulo_analitico: bool = False
    criopreservacion: bool = False
    comerciante: bool = False

    def esta_activa(self, tecnologia: TecnologiaID) -> bool:
        """Retorna True si la tecnología especificada está instalada."""
        return bool(getattr(self, tecnologia.value))

    def activar(self, tecnologia: TecnologiaID) -> None:
        """Marca una tecnología como instalada. Sin validaciones: responsabilidad del engine."""
        setattr(self, tecnologia.value, True)

    @property
    def cantidad_instaladas(self) -> int:
        """Número de mejoras actualmente instaladas (cada una, como máximo 1 vez por partida)."""
        return sum(
            [
                self.incubadora,
                self.camara_b,
                self.modulo_analitico,
                self.criopreservacion,
                self.comerciante,
            ]
        )

    @property
    def pendientes(self) -> Tuple[TecnologiaID, ...]:
        """
        Mejoras que este jugador todavía NO tiene instaladas, es decir, las
        únicas que la Acción D puede comprar ahora mismo.

        Recorre ``TecnologiaID`` en vez de enumerar los cinco atributos a mano
        (como sí hace ``cantidad_instaladas``, que ya existía) para que una
        sexta tecnología entre aquí sola: quien la añada solo tiene que declarar
        el miembro del enum y su precio en ``actions.COSTOS_TECNOLOGIA``.

        Es un ``@property``, así que ``dataclasses.asdict`` no lo serializa y ni
        el snapshot dorado ni los pickles persistidos cambian de forma.
        """
        return tuple(t for t in TecnologiaID if not self.esta_activa(t))


@dataclass
class Player:
    """
    Estado completo del tablero personal de un investigador (jugador).

    Cubre:
      · Zona 1: Cultivo Base (Masa Madre) — vitalidad y acidez
      · Zona 2: Estaciones de Fermentación — hasta 3 masas activas
      · Zona 4: Tecnologías de Laboratorio
      · Archivos de Cartas: carpeta de proyectos y archivos de resultados
      · Recursos económicos: datos de investigación, tokens de insumos
      · Seguimiento de turno: PA disponibles, uso de horas extras

    Inicialización recomendada:
        player = Player.crear_dia_1(nombre="Investigador 1", receta_inicial=receta)
    """

    nombre: str

    # ------------------------------------------------------------------
    # Zona 1: Cultivo Base (Masa Madre)
    # ------------------------------------------------------------------

    vitalidad: int = 0
    """Nivel de actividad de la levadura. Rango estricto: [0, 6]."""

    acidez: int = 0
    """Perfil ácido del cultivo base. Rango estricto: [0, 6]."""

    en_estado_contaminacion: bool = False
    """
    True si la vitalidad llegó a 0 y aún no se ejecutó un Protocolo de Emergencia
    (Acción H o I). Mientras está activo, algunas acciones pueden bloquearse.
    """

    # ------------------------------------------------------------------
    # Atributos Operativos y Económicos
    # ------------------------------------------------------------------

    puntos_accion: int = 0
    """
    PA disponibles en la Fase II actual.
    Se reinician a 2 al inicio de cada Fase II; pueden subir a 3 con Horas Extras.
    """

    datos_investigacion: int = 0
    """Moneda técnica: compra mejoras de laboratorio, PA extra (Horas Extras) y
    permite el Pedido de Urgencia. Distinta de `monedas` (la divisa comercial)."""

    monedas: int = 0
    """
    Divisa comercial del juego (GDD v0.0.2). Se gana al hornear y vender (Acción F)
    y se gasta en Visitar el Mercado (Acción C) para comprar harina/agua.
    """

    reserva_harina: Dict[str, int] = field(
        default_factory=lambda: {"Blanca": 0, "Centeno": 0, "Integral": 0}
    )
    """
    Reserva de harina por tipo. Las claves son los nombres de los tipos
    ("Blanca", "Centeno", "Integral") y los valores son porcentajes en
    múltiplos de 10 (ej. 100 = una bolsa completa, 0 = sin reserva).
    """

    contrato_molino: Optional[str] = None
    """
    Tipo de harina del Contrato con el Molino firmado por este jugador, o None si
    no ha firmado ninguno. Las claves son las mismas que ``reserva_harina``
    ("Blanca", "Centeno", "Integral") precisamente para que la entrega nocturna
    sea ``reserva_harina[contrato_molino] += RENDIMIENTO_MOLINO_PCT``, sin
    traducción de por medio.

    Un solo contrato por jugador y para siempre: se firma en la Acción C pagando
    ``PRECIO_CONTRATO_MOLINO[tipo]`` una vez, y a partir de esa noche el molino
    entrega ``RENDIMIENTO_MOLINO_PCT`` de esa harina en cada Fase III. Es la
    única fuente de harina que no pasa por el mercado, y existe porque sin ella
    vender harina no era una línea económica: la única forma de tener harina era
    comprarla, y comprar mueve el visor en tu contra antes de que puedas vender.

    Es un campo, no una propiedad derivada: el contrato es una decisión del
    jugador que nada más en el estado permite reconstruir.
    """

    accion_alimentar_usada: bool = False
    """
    True si la Acción A (Alimentar) ya fue ejecutada este turno de Fase II.
    Se reinicia a False al inicio de cada Fase II.
    """

    reserva_agua: int = 0
    """
    Total de tokens de hidratación disponibles.
    Cada unidad representa un 5% de hidratación (ej. 12 tokens = 60%).
    """

    # ------------------------------------------------------------------
    # Zona 2: Estaciones de Fermentación (3 ranuras)
    # ------------------------------------------------------------------

    estaciones_fermentacion: List[Optional[FermentationSlot]] = field(
        default_factory=lambda: [None, None, None]
    )
    """
    Lista de 3 ranuras de fermentación [estacion_01, estacion_02, estacion_03].
    · Índices 0 y 1: siempre disponibles.
    · Índice 2 (Estación 03): bloqueada hasta que tecnologias.camara_b == True.
    None indica estación libre; FermentationSlot indica masa en curso.
    """

    dados_inoculo: int = 0
    """
    Cantidad de dados físicos disponibles para iniciar nuevas masas (máximo 3).
    Se consume 1 al ejecutar Acción B (Iniciar Receta).
    Se recupera 1 al ejecutar Acción F (Hornear).
    """

    # ------------------------------------------------------------------
    # Zona 4: Tecnologías de Laboratorio
    # ------------------------------------------------------------------

    tecnologias: Technologies = field(default_factory=Technologies)

    # ------------------------------------------------------------------
    # Archivos de Cartas
    # ------------------------------------------------------------------

    carpeta_proyectos: List[Recipe] = field(default_factory=list)
    """
    Recetas investigadas pendientes de iniciar (estado inactivo).
    Límite estricto: máximo 3 cartas. Acción G (Investigar Protocolo) las agrega.
    """

    archivo_horneado_exitoso: List[HorneadoRecord] = field(default_factory=list)
    """
    Registros de recetas horneadas con puntuación positiva.
    Gatillo de fin de partida: len(archivo_horneado_exitoso) >= 5.
    """

    archivo_colapsos: List[HorneadoRecord] = field(default_factory=list)
    """
    Registros de recetas retiradas de emergencia (sobrefermentadas) con puntuación negativa.
    No cuenta para el gatillo de fin de partida.
    """

    # ------------------------------------------------------------------
    # Seguimiento de Turno (se resetea al inicio de cada Fase II)
    # ------------------------------------------------------------------

    horas_extras_usadas: bool = False
    """
    Indica si ya se usó la acción auxiliar 'Horas Extras' en el día actual.
    Solo se puede usar una vez por día. Se resetea en resetear_puntos_accion().
    """

    estasis_suspendida: bool = False
    """
    True si el jugador ha suspendido la Estasis Biológica para la Fase III de HOY,
    es decir, si ha pedido que su cultivo base sufra el desgaste metabólico normal
    esta noche pese a tener la Criopreservación instalada.

    Solo tiene sentido con ``tecnologias.criopreservacion``; en cualquier otro
    jugador es inerte (el desgaste ya se aplica de todos modos). La bandera la
    limpia la propia Fase III tras aplicar el desgaste
    (``GameEngine._aplicar_desgaste_metabolico``), de modo que la Estasis se
    reactiva sola cada día y un ajuste olvidado no puede contaminar a nadie.

    **No es un marcador de "ya usada"**: la acción ``estasis`` es un interruptor
    de dos sentidos que puede accionarse cuantas veces se quiera, así que este
    campo NO participa en ``GameEngine._jugador_elegible`` — no otorga visitas.
    """

    acciones_pa_usadas_hoy: List[str] = field(default_factory=list)
    """
    Ids de espacios de acción con costo de PA (B, C, D, E, F, G, H, I,
    'simposio') que este jugador ya visitó en el Día de Laboratorio actual
    -- cada espacio solo puede visitarse una vez por día. Se llena en
    Player.consumir_punto_accion() y se reinicia a [] al inicio de cada
    Fase II (engine.py:_preparar_fase_II). Pedido de Urgencia (0 PA) y las
    acciones gratuitas (Alimentar, Horas Extras) no participan de esta
    lista -- tienen sus propias banderas de una vez por día.
    """

    # ------------------------------------------------------------------
    # Seguimiento de Penalizaciones Acumuladas
    # ------------------------------------------------------------------

    contador_contaminaciones: int = 0
    """
    Número de episodios en los que la Vitalidad llegó a 0 durante la partida.
    Cada episodio aplica -3 Puntos de Maestría al final del juego.
    """

    # ==================================================================
    # FACTORY METHOD — Inicialización correcta para el Día 1
    # ==================================================================

    @classmethod
    def crear_dia_1(
        cls,
        nombre: str,
        receta_inicial: Recipe,
        harina_inicial: Optional[Dict[str, int]] = None,
        agua_inicial: int = 0,
        monedas_iniciales: int = 0,
        datos_iniciales: int = 0,
    ) -> "Player":
        """
        Crea e inicializa un jugador con el estado exacto descrito en PLAYER_STATE.md §2.

        Valores simétricos fijados en el Día 1 para todos los jugadores:
          · vitalidad = 2 (VITALIDAD_INICIAL), acidez = 1
          · dados_inoculo = 3, puntos_accion = 0
          · carpeta_proyectos = [receta_inicial]
          · todas las tecnologías inactivas

        Los recursos iniciales (harina, agua, monedas) provienen de la Carta de
        Patrocinio repartida en el setup (GDD v0.0.2, Módulo I §6.4 / Anexo B) —
        ver `bootstrap.create_game()`, que reparte `PATROCINIO_CATALOG` y pasa los
        valores de la carta de cada jugador a estos parámetros. `datos_iniciales`
        es 0 para todos los jugadores bajo el setup actual (la tabla de Patrocinios
        no incluye Datos de Investigación); se deja como parámetro explícito para
        no romper otros puntos de construcción directa de `Player`.

        Args:
            nombre: Nombre o identificador del investigador.
            receta_inicial: Carta de receta de grado 'Básica' asignada aleatoriamente
                (usar seleccionar_receta_inicial() para elección automática).
            harina_inicial: Harina adicional otorgada por la Carta de Patrocinio,
                p. ej. {"Blanca": 100} o {"Blanca": 200}. Se suma sobre la reserva
                base vacía {"Blanca": 0, "Centeno": 0, "Integral": 0}.
            agua_inicial: Tokens de agua (5% c/u) otorgados por la Carta de Patrocinio.
            monedas_iniciales: Monedas otorgadas por la Carta de Patrocinio.
            datos_iniciales: Datos de Investigación iniciales (0 por defecto).

        Returns:
            Instancia de Player completamente configurada para el inicio de partida.

        Raises:
            ValueError: Si receta_inicial no es de grado Básica (regla del setup).
        """
        if receta_inicial.grado != Grado.BASICA:
            raise ValueError(
                f"La receta inicial del Día 1 debe ser de grado '{Grado.BASICA.value}'. "
                f"Recibido: '{receta_inicial.grado.value}' (id='{receta_inicial.id}')."
            )
        player = cls(nombre=nombre)
        player._aplicar_setup_dia_1(
            receta_inicial,
            harina_inicial=harina_inicial,
            agua_inicial=agua_inicial,
            monedas_iniciales=monedas_iniciales,
            datos_iniciales=datos_iniciales,
        )
        return player

    def _aplicar_setup_dia_1(
        self,
        receta_inicial: Recipe,
        harina_inicial: Optional[Dict[str, int]] = None,
        agua_inicial: int = 0,
        monedas_iniciales: int = 0,
        datos_iniciales: int = 0,
    ) -> None:
        """Aplica los valores de inicialización del Día 1 (PLAYER_STATE.md §2)."""
        reserva_harina: Dict[str, int] = {"Blanca": 0, "Centeno": 0, "Integral": 0}
        for tipo, cantidad in (harina_inicial or {}).items():
            reserva_harina[tipo] = reserva_harina.get(tipo, 0) + cantidad

        self.vitalidad = VITALIDAD_INICIAL
        self.acidez = 1
        self.datos_investigacion = datos_iniciales
        self.monedas = monedas_iniciales
        self.dados_inoculo = 3
        self.puntos_accion = 0  # Se asignan 2 al llegar a la Fase II del primer día
        self.reserva_harina = reserva_harina
        self.reserva_agua = agua_inicial
        self.tecnologias = Technologies()
        self.estaciones_fermentacion = [None, None, None]
        self.carpeta_proyectos = [receta_inicial]
        self.archivo_horneado_exitoso = []
        self.archivo_colapsos = []
        self.horas_extras_usadas = False
        self.estasis_suspendida = False
        self.en_estado_contaminacion = False
        self.contador_contaminaciones = 0
        self.accion_alimentar_usada = False

    # ==================================================================
    # MÉTODOS DE MODIFICACIÓN DE ESTADO (con clamping y efectos secundarios)
    # ==================================================================

    def ajustar_vitalidad(self, delta: int) -> None:
        """
        Modifica la vitalidad aplicando el clamp [0, 6].

        Si el resultado es 0 y el jugador no estaba ya contaminado, activa el
        estado de contaminación e incrementa el contador de penalizaciones.
        El motor debe ofrecer al jugador los Protocolos de Emergencia (H o I).

        Args:
            delta: Incremento (positivo) o decremento (negativo) de vitalidad.
        """
        nuevo_valor: int = max(0, min(6, self.vitalidad + delta))
        self.vitalidad = nuevo_valor
        if self.vitalidad == 0 and not self.en_estado_contaminacion:
            self.en_estado_contaminacion = True
            self.contador_contaminaciones += 1

    def ajustar_acidez(self, delta: int) -> None:
        """
        Modifica la acidez aplicando el clamp [0, 6].

        Args:
            delta: Incremento (positivo) o decremento (negativo) de acidez.
        """
        self.acidez = max(0, min(6, self.acidez + delta))

    def resetear_puntos_accion(self) -> None:
        """
        Reinicia los PA a 2 al comienzo de la Fase II del turno del jugador.
        También resetea el uso de Horas Extras para el día.
        """
        self.puntos_accion = 2
        self.horas_extras_usadas = False

    def ocupar_espacio_accion(self, espacio_accion_id: str) -> None:
        """
        Registra `espacio_accion_id` en acciones_pa_usadas_hoy, bloqueando ese
        espacio para el resto del día, SIN gastar PA.

        Existe separado de `consumir_punto_accion` porque la Acción E (Pliegues)
        se paga en Monedas y no en PA, pero conserva la regla "un espacio, una
        visita por día" (ACTIONS_REGISTRY.md §1). Precondición: el llamador debe
        verificar que espacio_accion_id no esté ya en la lista ANTES de llamar.
        """
        self.acciones_pa_usadas_hoy.append(espacio_accion_id)

    def consumir_punto_accion(self, espacio_accion_id: str) -> None:
        """
        Decrementa 1 PA del jugador y registra `espacio_accion_id` en
        acciones_pa_usadas_hoy, bloqueando ese espacio para el resto del día.
        Precondición: el llamador debe verificar puntos_accion >= 1 y que
        espacio_accion_id no esté ya en acciones_pa_usadas_hoy ANTES de llamar.
        """
        self.puntos_accion -= 1
        self.ocupar_espacio_accion(espacio_accion_id)

    def otorgar_punto_accion_extra(self) -> None:
        """
        Aplica el efecto de la acción auxiliar 'Horas Extras' (+1 PA).
        Precondición: el engine debe verificar que horas_extras_usadas == False
        y que datos_investigacion >= 1 antes de llamar.
        """
        self.puntos_accion += 1
        self.horas_extras_usadas = True

    # ==================================================================
    # PROPIEDADES DE CONSULTA DE ESTADO (solo lectura)
    # ==================================================================

    @property
    def indice_estacion_disponible(self) -> Optional[int]:
        """
        Retorna el índice de la primera estación de fermentación libre disponible,
        o None si todas están ocupadas o bloqueadas.

        La Estación 03 (índice 2) requiere tecnologias.camara_b == True.
        """
        for i, slot in enumerate(self.estaciones_fermentacion):
            if slot is None:
                if i == 2 and not self.tecnologias.camara_b:
                    continue  # Estación 03 bloqueada sin Cámara B
                return i
        return None

    @property
    def masas_activas(self) -> List[Tuple[int, FermentationSlot]]:
        """
        Retorna lista de (índice_estación, slot) de todas las masas en fermentación.
        Útil para iterar en la Fase III sin filtrar None manualmente.
        """
        return [
            (i, slot)
            for i, slot in enumerate(self.estaciones_fermentacion)
            if slot is not None
        ]

    @property
    def total_tokens_recursos(self) -> int:
        """
        Total de tokens de insumos sin utilizar (harina + agua).
        Usado para el cálculo de la penalización por desperdicio al final del juego.
        """
        return sum(v // 10 for v in self.reserva_harina.values()) + self.reserva_agua

    @property
    def puntos_penalizacion_contaminacion(self) -> int:
        """Puntos negativos acumulados por episodios de vitalidad = 0 (-3 por c/u)."""
        return self.contador_contaminaciones * -3

    @property
    def puntos_horneados(self) -> int:
        """
        Puntos acumulados por horneados hasta ahora: la suma de
        ``HorneadoRecord.puntos_totales`` (base + bono de sabor) de TODOS los
        registros, exitosos y colapsos (los colapsos aportan puntos negativos).

        Es exactamente la pareja de términos 1+2 (Puntos Base + Puntos de
        Sabor) de ``puntos_maestria_final``, expresada por registro — el
        marcador "en vivo" que la UI muestra durante la partida, a diferencia
        de la proyección final que además suma madurez, conversión de riqueza
        y penalizaciones.
        """
        return sum(
            r.puntos_totales
            for r in self.archivo_horneado_exitoso + self.archivo_colapsos
        )

    @property
    def recetas_distintas_horneadas(self) -> int:
        """
        Número de recetas DISTINTAS (por ``Recipe.id``) horneadas con éxito.

        Sólo cuenta ``archivo_horneado_exitoso``: un colapso nunca suma
        variedad. La razón no es estética sino de incentivos — un colapso es
        gratis de provocar (iniciar una masa y dejar que la Fase III la
        hornee sola al sobrefermentar), así que contarlo convertiría el bono
        de variedad en algo que se cosecha sin hornear bien nada.

        El mazo físico reparte copias de cada carta
        (``COPIAS_POR_GRADO``), de modo que hornear dos Pan Graham cuenta
        como UNA sola clase: lo que se premia es la amplitud del repertorio,
        no el número de horneados.
        """
        return len({r.recipe.id for r in self.archivo_horneado_exitoso})

    @property
    def puntos_variedad(self) -> int:
        """
        Puntos de Maestría del término «Variedad de Recetas» (CORE_MECHANICS.md §3).

        Curva triangular sobre ``recetas_distintas_horneadas``::

            n:   0   1   2   3   4    5
            PM:  0   1   3   6  10   15

        Es decir ``puntos_triangulares``: cada clase nueva vale más que la
        anterior. La escalada es deliberada — como la partida termina al quinto
        horneado exitoso, el tope real es 5, y repetir una carta una sola vez
        renuncia al incremento más grande disponible (5 PM) en vez de a un
        promedio.
        """
        return puntos_triangulares(self.recetas_distintas_horneadas)

    @property
    def puntos_desarrollo_tecnologico(self) -> int:
        """
        Puntos de Maestría del término «Desarrollo Tecnológico»
        (CORE_MECHANICS.md §3).

        La misma curva triangular que «Variedad de Recetas», sobre las mejoras
        de laboratorio INSTALADAS (``Technologies.cantidad_instaladas``)::

            n:   0   1   2   3   4   5
            PM:  0   1   3   6  10  15

        El tope es 15, igual que el de Variedad: hay cinco mejoras y la partida
        termina al quinto horneado exitoso, así que las dos curvas se cortan en
        el mismo sitio. La curva no se topa a mano en ningún caso — se acaba
        donde se acaba el recuento, que es lo que permite añadir una quinta
        mejora sin tocar la puntuación.

        **Sin ponderar por coste**: Criopreservación (2 Datos) cuenta
        exactamente igual que Cámara B (4), del mismo modo que una Básica y una
        Avanzada cuentan una clase cada una en Variedad pese a costar 1 y 3
        Monedas. Lo que se premia es la amplitud del laboratorio, no lo que
        costó montarlo. La consecuencia — comprar primero lo barato es
        estrictamente correcto — está aceptada: es un empujón de ORDEN, no una
        línea dominante, porque el incremento más grande sigue exigiendo las
        cuatro y la mejora que te saltes es justo la que querías.

        A diferencia de Variedad, este término **nunca baja**: el Simposio
        Técnico saca un horneado del archivo, pero nada desinstala una mejora
        (``Technologies`` no tiene inversa de ``activar``). La asimetría es
        deliberada, no un descuido pendiente de arreglar.
        """
        return puntos_triangulares(self.tecnologias.cantidad_instaladas)

    @property
    def puntos_equilibrio_acidez(self) -> int:
        """
        Mitad de Acidez del término «Madurez del Cultivo» (CORE_MECHANICS.md §3.3).

        ``PUNTOS_EQUILIBRIO_MAX - |acidez - ACIDEZ_EQUILIBRIO_CENTRO|``: 3 puntos justo
        en el centro de la pista, un punto menos por casilla hacia cada lado, 0 en los
        extremos 0 y 6. No necesita ``max(0, ...)`` porque el centro está a distancia 3
        de ambos bordes y ``Player.acidez`` ya vive acotada en [0, 6]
        (``ajustar_acidez``), de modo que el resultado nunca puede ser negativo.

        Es una @property y no un cálculo suelto dentro de ``desglose_maestria`` porque
        la UI necesita explicar el término (dónde está el pico) sin duplicar la
        fórmula, igual que ``vitalidad_prevista`` se calcula en el servidor y no en
        TypeScript.
        """
        distancia = abs(self.acidez - ACIDEZ_EQUILIBRIO_CENTRO)
        return PUNTOS_EQUILIBRIO_MAX - distancia

    @property
    def desglose_maestria(self) -> Dict[str, int]:
        """
        Los 8 términos de la puntuación final, por separado y ya en orden de
        presentación (CORE_MECHANICS.md §3).

        Única fuente de verdad de la fórmula: ``puntos_maestria_final`` no es
        más que la suma de estos valores, y la pantalla de ranking web recorre
        el mapa en lugar de recalcular los términos por su cuenta. Antes de
        existir, la aritmética estaba además duplicada a mano en la CLI, que
        llevaba tiempo omitiendo «Conversión de Riqueza» y por tanto imprimía
        un desglose que no sumaba su propio TOTAL. Esa duplicación es lo que
        este mapa existe para impedir.

        El ORDEN DE INSERCIÓN es carga útil, no decoración: es el orden en
        que lo pintan todos los consumidores (positivos primero,
        penalizaciones al final).

        Returns:
            Mapa ordenado {nombre_del_término: puntos}. Los valores pueden
            ser negativos (Desperdicio, Contaminación, y Base si hubo
            colapsos).
        """
        todos_los_horneados: List[HorneadoRecord] = (
            self.archivo_horneado_exitoso + self.archivo_colapsos
        )
        return {
            # 1. Puntos base de recetas
            "Base": sum(r.puntos_base for r in todos_los_horneados),
            # 2. Puntos de sabor (bono de acidez sellado en cada carta)
            "Sabor": sum(
                r.recipe.bono_sabor_pts
                for r in todos_los_horneados
                if r.bono_sabor_aplicado
            ),
            # 3. Madurez del cultivo base al final de la partida
            "Madurez": self.vitalidad + self.puntos_equilibrio_acidez,
            # 4. Amplitud del repertorio horneado (curva triangular)
            "Variedad de Recetas": self.puntos_variedad,
            # 5. Amplitud del laboratorio construido (la MISMA curva triangular)
            "Desarrollo Tecnológico": self.puntos_desarrollo_tecnologico,
            # 6. Penalización por desperdicio de insumos (-1 por cada 3 tokens)
            "Desperdicio": -(self.total_tokens_recursos // 3),
            # 7. Penalización por episodios de contaminación
            "Contaminación": self.puntos_penalizacion_contaminacion,
            # 8. Conversión de riqueza (+1 pt por cada 5 Monedas restantes)
            "Conversión de Riqueza": self.monedas // 5,
        }

    @property
    def puntos_maestria_final(self) -> int:
        """
        Calcula el total de Puntos de Maestría al final de la partida.

        Componentes (CORE_MECHANICS.md §3), ver ``desglose_maestria``:
          1. Puntos Base   : suma de puntos de todas las recetas horneadas (positivos + negativos)
          2. Puntos de Sabor: suma de bono_sabor_pts de registros con bono_sabor_aplicado == True
          3. Madurez del Cultivo: vitalidad + (3 - |acidez - 3|), ver puntos_equilibrio_acidez
          4. Variedad de Recetas: puntos_triangulares(recetas distintas horneadas con éxito)
          5. Desarrollo Tecnológico: puntos_triangulares(mejoras de laboratorio instaladas)
          6. Penalización Desperdicio: -1 pt por cada 3 tokens de insumos sin usar
          7. Penalización Contaminación: -3 pts × contador_contaminaciones
          8. Conversión de Riqueza: +1 pt por cada 5 Monedas restantes en la reserva final

        Debe invocarse únicamente al final del día que termina la partida.
        """
        return sum(self.desglose_maestria.values())

    def __repr__(self) -> str:
        return (
            f"Player(nombre={self.nombre!r}, "
            f"vitalidad={self.vitalidad}, acidez={self.acidez}, "
            f"PA={self.puntos_accion}, datos={self.datos_investigacion}, "
            f"masas_activas={len(self.masas_activas)}, "
            f"horneados={len(self.archivo_horneado_exitoso)})"
        )


@dataclass
class Environment:
    """
    Estado global del tablero central (compartido entre todos los jugadores).

    Gestiona la temperatura del laboratorio, el mazo de clima y el avance base
    de fermentación (Ábaco). El Investigador Jefe (jugador con mayor vitalidad)
    lidera la Fase I que modifica este estado.

    Inicialización recomendada:
        env = Environment.crear_inicial()
    """

    temperatura_actual: int = 20
    """Temperatura del laboratorio en °C. Inicia en 20°C; modificada cada Fase I."""

    dia_actual: int = 1
    """Ronda/día de laboratorio en curso. Incrementa al finalizar cada ciclo completo."""

    efecto_pasivo_activo: EfectoClimatico = EfectoClimatico.NINGUNO
    """
    Efecto pasivo de la carta de clima del día vigente.
    Modifica la resolución de la Fase III (ej. Aletargamiento Invernal → -2 Vitalidad).
    Se sobrescribe con cada nueva carta revelada en la Fase I.
    """

    mazo_clima: List[ClimateCard] = field(default_factory=list)
    """Cartas de clima restantes por revelar. Vaciar este mazo es un gatillo de fin de juego."""

    descarte_clima: List[ClimateCard] = field(default_factory=list)
    """Cartas ya reveladas. Se barajan de vuelta al mazo si este se agota."""

    ultima_carta_clima: Optional[ClimateCard] = field(default=None)
    """Última carta de clima revelada en la Fase I. Usada por la CLI para mostrar el evento."""

    # ==================================================================
    # FACTORY METHOD — Estado Inicial del Juego
    # ==================================================================

    @classmethod
    def crear_inicial(cls) -> "Environment":
        """
        Crea el entorno con el estado exacto de inicio de partida:
          · Temperatura base: 20°C
          · Mazo de clima completo (30 cartas) barajado aleatoriamente
          · Sin efectos pasivos activos
          · Día 1

        Returns:
            Instancia de Environment lista para el inicio de la partida.
        """
        env = cls()
        env.temperatura_actual = 20
        env.dia_actual = 1
        env.efecto_pasivo_activo = EfectoClimatico.NINGUNO
        env.mazo_clima = build_climate_deck()
        random.shuffle(env.mazo_clima)
        env.descarte_clima = []
        env.ultima_carta_clima = None
        return env

    # ==================================================================
    # PROPIEDADES DE CONSULTA
    # ==================================================================

    @property
    def avance_base(self) -> int:
        """
        Casillas base de avance térmico (Ábaco de Fermentación).
        Fórmula (CLIMATE_LOGIC.md §1): temperatura_actual // 5
        Ejemplos: 20°C → 4, 25°C → 5, 30°C → 6, 15°C → 3
        """
        return self.temperatura_actual // 5

    @property
    def mazo_agotado(self) -> bool:
        """
        Retorna True si el mazo de clima se ha vaciado.
        Agotar el mazo es uno de los dos gatillos de fin de partida.
        """
        return len(self.mazo_clima) == 0

    @property
    def desgaste_vitalidad_fase_3(self) -> int:
        """
        Retorna el decremento de Vitalidad que se aplica al cultivo base en la Fase III.
        Estándar: -1. Con Aletargamiento Invernal activo: -2.
        """
        if self.efecto_pasivo_activo == EfectoClimatico.ALETARGAMIENTO_INVERNAL:
            return -2
        return -1

    # ==================================================================
    # MÉTODOS DE MODIFICACIÓN DE ESTADO
    # ==================================================================

    def aplicar_carta_clima(self, carta: ClimateCard) -> None:
        """
        Aplica el modificador térmico de una carta al entorno y activa su efecto pasivo.
        Llamar DESPUÉS de resetear la temperatura a la base si el diseño lo requiere.

        Args:
            carta: Carta de clima revelada durante la Fase I.
        """
        self.ultima_carta_clima = carta
        self.temperatura_actual += carta.modificador_termico
        self.efecto_pasivo_activo = carta.efecto_pasivo

    def resetear_temperatura_base(self) -> None:
        """
        Resetea la temperatura al valor base de 20°C antes de aplicar la carta del día.
        Invocar al inicio de cada Fase I, antes de aplicar_carta_clima().
        """
        self.temperatura_actual = 20

    def __repr__(self) -> str:
        return (
            f"Environment(día={self.dia_actual}, "
            f"temp={self.temperatura_actual}°C, "
            f"avance_base={self.avance_base}, "
            f"efecto_pasivo={self.efecto_pasivo_activo.value!r}, "
            f"cartas_restantes={len(self.mazo_clima)})"
        )


# ===========================================================================
# SECCIÓN 4: CATÁLOGO MAESTRO DE RECETAS (CONSTANTE INMUTABLE)
# ===========================================================================

_RECIPE_CATALOG_DATA: Dict[str, Recipe] = {
    # --- BÁSICAS: una bolsa entera de Blanca (9-12 puntos) ---
    "pan_de_campo": Recipe(
        id="pan_de_campo",
        nombre="Pan de Campo",
        grado=Grado.BASICA,
        harinas=((TipoHarina.BLANCA, 100),),
        hidratacion_pct=60,
        tokens_agua=12,
        acidez_diana=(3,),
        bono_sabor_pts=1,
        zona_crecimiento=(1, 5),
        zona_pre_fermento=(6, 10),
        zona_optima=(11, 15),
        zona_colapso=(16, 20),
        puntos_pre_fermento=4,
        puntos_optimos=10,
        penalizacion_colapso=-2,
        monedas_pre_fermento=10,
        monedas_optima=14,
        monedas_colapso=8,
    ),
    # La zona óptima más ancha del juego (6 espacios): la carta indulgente.
    "pan_de_molde": Recipe(
        id="pan_de_molde",
        nombre="Pan de Molde",
        grado=Grado.BASICA,
        harinas=((TipoHarina.BLANCA, 100),),
        hidratacion_pct=55,
        tokens_agua=11,
        acidez_diana=(1, 2),
        bono_sabor_pts=2,
        zona_crecimiento=(1, 3),
        zona_pre_fermento=(4, 8),
        zona_optima=(9, 14),
        zona_colapso=(15, 20),
        puntos_pre_fermento=3,
        puntos_optimos=9,
        penalizacion_colapso=-2,
        monedas_pre_fermento=9,
        monedas_optima=13,
        monedas_colapso=7,
    ),
    "baguette": Recipe(
        id="baguette",
        nombre="Baguette",
        grado=Grado.BASICA,
        harinas=((TipoHarina.BLANCA, 100),),
        hidratacion_pct=65,
        tokens_agua=13,
        acidez_diana=(2,),
        bono_sabor_pts=2,
        zona_crecimiento=(1, 5),
        zona_pre_fermento=(6, 11),
        zona_optima=(12, 15),
        zona_colapso=(16, 20),
        puntos_pre_fermento=5,
        puntos_optimos=11,
        penalizacion_colapso=-2,
        monedas_pre_fermento=11,
        monedas_optima=15,
        monedas_colapso=9,
    ),
    "focaccia": Recipe(
        id="focaccia",
        nombre="Focaccia",
        grado=Grado.BASICA,
        harinas=((TipoHarina.BLANCA, 100),),
        hidratacion_pct=75,
        tokens_agua=15,
        acidez_diana=(1, 2),
        bono_sabor_pts=2,
        zona_crecimiento=(1, 4),
        zona_pre_fermento=(5, 9),
        zona_optima=(10, 14),
        zona_colapso=(15, 20),
        puntos_pre_fermento=3,
        puntos_optimos=12,
        penalizacion_colapso=-3,
        monedas_pre_fermento=12,
        monedas_optima=16,
        monedas_colapso=10,
    ),

    # --- INTERMEDIAS: media bolsa de dos harinas distintas (13-16 puntos) ---
    # La única Intermedia sin requisito tecnológico: la entrada al escalón medio.
    "miche": Recipe(
        id="miche",
        nombre="Miche",
        grado=Grado.INTERMEDIA,
        harinas=((TipoHarina.BLANCA, 50), (TipoHarina.INTEGRAL, 50)),
        hidratacion_pct=70,
        tokens_agua=14,
        acidez_diana=(3, 4),
        bono_sabor_pts=2,
        zona_crecimiento=(1, 5),
        zona_pre_fermento=(6, 11),
        zona_optima=(12, 16),
        zona_colapso=(17, 20),
        puntos_pre_fermento=5,
        puntos_optimos=13,
        penalizacion_colapso=-4,
        monedas_pre_fermento=10,
        monedas_optima=14,
        monedas_colapso=7,
    ),
    "pizza_napolitana": Recipe(
        id="pizza_napolitana",
        nombre="Pizza Napolitana",
        grado=Grado.INTERMEDIA,
        harinas=((TipoHarina.BLANCA, 50), (TipoHarina.INTEGRAL, 50)),
        hidratacion_pct=62,
        tokens_agua=13,
        acidez_diana=(3,),
        bono_sabor_pts=2,
        zona_crecimiento=(1, 5),
        zona_pre_fermento=(6, 10),
        zona_optima=(11, 14),
        zona_colapso=(15, 20),
        puntos_pre_fermento=4,
        puntos_optimos=14,
        penalizacion_colapso=-4,
        monedas_pre_fermento=9,
        monedas_optima=15,
        monedas_colapso=6,
    ),
    "brioche": Recipe(
        id="brioche",
        nombre="Brioche",
        grado=Grado.INTERMEDIA,
        harinas=((TipoHarina.BLANCA, 50), (TipoHarina.CENTENO, 50)),
        hidratacion_pct=52,
        tokens_agua=11,
        acidez_diana=(1,),
        bono_sabor_pts=3,
        zona_crecimiento=(1, 7),
        zona_pre_fermento=(8, 14),
        zona_optima=(15, 17),
        zona_colapso=(18, 20),
        puntos_pre_fermento=5,
        puntos_optimos=16,
        penalizacion_colapso=-6,
        monedas_pre_fermento=8,
        monedas_optima=15,
        monedas_colapso=5,
    ),
    # Ventana óptima de 2 espacios y el mayor Bono de Sabor del juego:
    # no es la carta de más puntos, sino la de más sabor.
    "panettone": Recipe(
        id="panettone",
        nombre="Panettone",
        grado=Grado.INTERMEDIA,
        harinas=((TipoHarina.BLANCA, 50), (TipoHarina.CENTENO, 50)),
        hidratacion_pct=47,
        tokens_agua=10,
        acidez_diana=(1,),
        bono_sabor_pts=3,
        zona_crecimiento=(1, 10),
        zona_pre_fermento=(11, 16),
        zona_optima=(17, 18),
        zona_colapso=(19, 20),
        puntos_pre_fermento=8,
        puntos_optimos=16,
        penalizacion_colapso=-8,
        monedas_pre_fermento=7,
        monedas_optima=16,
        monedas_colapso=4,
    ),

    # --- AVANZADAS: una bolsa entera de harina especial (17-20 puntos) ---
    "hogaza_centeno": Recipe(
        id="hogaza_centeno",
        nombre="Hogaza Centeno",
        grado=Grado.AVANZADA,
        harinas=((TipoHarina.CENTENO, 100),),
        hidratacion_pct=67,
        tokens_agua=14,
        acidez_diana=(4, 5),
        bono_sabor_pts=4,
        zona_crecimiento=(1, 6),
        zona_pre_fermento=(7, 12),
        zona_optima=(13, 16),
        zona_colapso=(17, 20),
        puntos_pre_fermento=6,
        puntos_optimos=17,
        penalizacion_colapso=-5,
        monedas_pre_fermento=11,
        monedas_optima=18,
        monedas_colapso=8,
    ),
    "pan_semillas": Recipe(
        id="pan_semillas",
        nombre="Pan Semillas",
        grado=Grado.AVANZADA,
        harinas=((TipoHarina.INTEGRAL, 100),),
        hidratacion_pct=78,
        tokens_agua=16,
        acidez_diana=(3, 4),
        bono_sabor_pts=3,
        zona_crecimiento=(1, 6),
        zona_pre_fermento=(7, 13),
        zona_optima=(14, 16),
        zona_colapso=(17, 20),
        puntos_pre_fermento=6,
        puntos_optimos=17,
        penalizacion_colapso=-5,
        monedas_pre_fermento=10,
        monedas_optima=17,
        monedas_colapso=7,
    ),
    "pan_graham": Recipe(
        id="pan_graham",
        nombre="Pan Graham",
        grado=Grado.AVANZADA,
        harinas=((TipoHarina.INTEGRAL, 100),),
        hidratacion_pct=80,
        tokens_agua=16,
        acidez_diana=(4, 5),
        bono_sabor_pts=4,
        zona_crecimiento=(1, 6),
        zona_pre_fermento=(7, 13),
        zona_optima=(14, 17),
        zona_colapso=(18, 20),
        puntos_pre_fermento=6,
        puntos_optimos=19,
        penalizacion_colapso=-6,
        monedas_pre_fermento=9,
        monedas_optima=17,
        monedas_colapso=6,
    ),
    # El techo del catálogo: centeno puro, la acidez diana más alta y la
    # ventana óptima más estrecha (3 espacios) frente a un colapso de -8.
    "pumpernickel": Recipe(
        id="pumpernickel",
        nombre="Pumpernickel",
        grado=Grado.AVANZADA,
        harinas=((TipoHarina.CENTENO, 100),),
        hidratacion_pct=85,
        tokens_agua=17,
        acidez_diana=(5, 6),
        bono_sabor_pts=4,
        zona_crecimiento=(1, 9),
        zona_pre_fermento=(10, 15),
        zona_optima=(16, 18),
        zona_colapso=(19, 20),
        puntos_pre_fermento=8,
        puntos_optimos=20,
        penalizacion_colapso=-8,
        monedas_pre_fermento=7,
        monedas_optima=19,
        monedas_colapso=3,
    ),
}

RECIPE_CATALOG: Mapping[str, Recipe] = MappingProxyType(_RECIPE_CATALOG_DATA)
"""
Catálogo maestro de recetas. Solo lectura en tiempo de ejecución (MappingProxyType).
Contiene las 12 recetas del juego: 4 Básicas + 4 Intermedias + 4 Avanzadas.
Todas las referencias a recetas en el estado del juego apuntan a estas instancias.

El grado de cada carta lo dictan sus harinas (``_grado_desde_harinas``), y
``Recipe.__post_init__`` lo verifica al construir este diccionario: una carta mal
etiquetada aborta ``import models``, no una partida a medias.

Bandas de ``puntos_optimos`` por grado, sin solape (RECIPE_DATABASE.md §3):
Básica 9-12, Intermedia 13-16, Avanzada 17-20. Las Monedas y el ancho de las
zonas NO están bandeados: siguen siendo el eje que distingue una carta de puntos
baratos de una carta caja-fuerte dentro del mismo grado.

Son 4 Básicas y no 3 porque ``bootstrap.create_game`` reparte una Básica distinta
por jugador (hasta 4) y ciclaba ``i % len`` con sólo tres.
"""


# ===========================================================================
# SECCIÓN 5: CATÁLOGO DEL MAZO DE CLIMA (CONSTANTE INMUTABLE)
# ===========================================================================

_CLIMATE_CATALOG_DATA: Dict[str, ClimateCard] = {
    "estabilidad_termica": ClimateCard(
        id="estabilidad_termica",
        nombre="Estabilidad Térmica",
        cantidad=10,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "fallo_refrigeracion": ClimateCard(
        id="fallo_refrigeracion",
        nombre="Fallo de Refrigeración",
        cantidad=4,
        modificador_termico=5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "ola_de_calor": ClimateCard(
        id="ola_de_calor",
        nombre="Ola de Calor",
        cantidad=2,
        modificador_termico=10,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "corriente_de_aire": ClimateCard(
        id="corriente_de_aire",
        nombre="Corriente de Aire",
        cantidad=4,
        modificador_termico=-5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "fallo_calefaccion": ClimateCard(
        id="fallo_calefaccion",
        nombre="Fallo de Calefacción",
        cantidad=2,
        modificador_termico=-10,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "alta_humedad": ClimateCard(
        id="alta_humedad",
        nombre="Alta Humedad",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.ALTA_HUMEDAD,
    ),
    "explosion_levaduras": ClimateCard(
        id="explosion_levaduras",
        nombre="Explosión de Levaduras",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.GANANCIA_VITALIDAD,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "acidificacion_acelerada": ClimateCard(
        id="acidificacion_acelerada",
        nombre="Acidificación Acelerada",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.GANANCIA_ACIDEZ,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "aletargamiento_invernal": ClimateCard(
        id="aletargamiento_invernal",
        nombre="Aletargamiento Invernal",
        cantidad=2,
        modificador_termico=-5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.ALETARGAMIENTO_INVERNAL,
    ),
}

CLIMATE_CATALOG: Mapping[str, ClimateCard] = MappingProxyType(_CLIMATE_CATALOG_DATA)
"""
Catálogo maestro del mazo de Clima. Solo lectura en tiempo de ejecución.
9 tipos de carta · 30 instancias totales en el mazo (según campo `cantidad`).
"""


# ===========================================================================
# SECCIÓN 5B: CATÁLOGO DE PATROCINIOS INICIALES (CONSTANTE INMUTABLE)
# ===========================================================================

PATROCINIO_CATALOG: Tuple[PatrocinioCard, ...] = (
    PatrocinioCard(iniciativa=1, tipo_harina=TipoHarina.BLANCA, harina_pct=100, agua_tokens=2, monedas=9, datos=0),
    PatrocinioCard(iniciativa=2, tipo_harina=TipoHarina.BLANCA, harina_pct=100, agua_tokens=6, monedas=8, datos=0),
    PatrocinioCard(iniciativa=3, tipo_harina=TipoHarina.BLANCA, harina_pct=100, agua_tokens=12, monedas=6, datos=1),
    PatrocinioCard(iniciativa=4, tipo_harina=TipoHarina.INTEGRAL, harina_pct=100, agua_tokens=6, monedas=8, datos=0),
    PatrocinioCard(iniciativa=5, tipo_harina=TipoHarina.INTEGRAL, harina_pct=100, agua_tokens=12, monedas=6, datos=1),
    PatrocinioCard(iniciativa=6, tipo_harina=TipoHarina.CENTENO, harina_pct=100, agua_tokens=6, monedas=8, datos=0),
    PatrocinioCard(iniciativa=7, tipo_harina=TipoHarina.CENTENO, harina_pct=100, agua_tokens=12, monedas=6, datos=1),
    PatrocinioCard(iniciativa=8, tipo_harina=TipoHarina.BLANCA, harina_pct=200, agua_tokens=20, monedas=4, datos=2),
)
"""
Mazo maestro de 8 Cartas de Patrocinio (GDD v0.0.2, Anexo B). `bootstrap.create_game()`
baraja una copia de esta tupla y reparte 1 carta por jugador sentado (1-4 jugadores).
"""


# ===========================================================================
# SECCIÓN 6: FUNCIONES DE UTILIDAD PARA EL SETUP
# ===========================================================================


COPIAS_POR_GRADO: Mapping[Grado, int] = MappingProxyType({
    Grado.BASICA: 4,
    Grado.INTERMEDIA: 3,
    Grado.AVANZADA: 2,
})
"""
Copias de cada protocolo en el mazo físico de recetas (RULEBOOK.md §12).

Las Básicas son comunes y las Avanzadas escasas: la rareza es una barrera
independiente del precio -- no basta con poder pagar una Avanzada, tiene que
salir. Con 4 protocolos por grado: 4·4 + 4·3 + 4·2 = 36 cartas.

Va por GRADO y no por carta (a diferencia de ``ClimateCard.cantidad``, que es un
campo por carta) porque el grado ya lo derivan las harinas impresas: una tabla
por carta serían 12 números derivables que podrían desmentir al reglamento.
"""

TOTAL_MAZO_RECETAS: int = 36
"""Tamaño del mazo físico de recetas. Ver ``COPIAS_POR_GRADO``."""


def expandir_copias(recetas: Iterable[Recipe]) -> List[Recipe]:
    """
    Expande cada protocolo a sus copias físicas según ``COPIAS_POR_GRADO``.

    Retorna la lista SIN barajar, igual que ``build_climate_deck``: el orden
    aleatorio lo aplica quien construye el mazo (``Market.crear_inicial``), que
    además retira las Básicas ya repartidas antes de barajar.

    Las copias son la MISMA instancia repetida: ``Recipe`` es ``frozen=True``, así
    que compartir referencias es seguro y es lo que ya hace el mazo de clima.
    """
    deck: List[Recipe] = []
    for receta in recetas:
        deck.extend([receta] * COPIAS_POR_GRADO[receta.grado])
    return deck


def build_recipe_deck() -> List[Recipe]:
    """
    Mazo de recetas completo (36 cartas), sin barajar.

    Es el mazo que usa ``Market.crear_inicial``, que le retira las Básicas ya
    repartidas y lo baraja entero. Fija además la integridad del catálogo en un
    solo sitio, igual que ``build_climate_deck`` para el clima.

    Raises:
        AssertionError: Si el total no suma exactamente TOTAL_MAZO_RECETAS.
    """
    deck: List[Recipe] = expandir_copias(RECIPE_CATALOG.values())
    assert len(deck) == TOTAL_MAZO_RECETAS, (
        f"El mazo de recetas debe tener exactamente {TOTAL_MAZO_RECETAS} cartas, "
        f"el catálogo actual genera {len(deck)}."
    )
    return deck


def build_climate_deck() -> List[ClimateCard]:
    """
    Construye el mazo de clima completo expandiendo cada carta según su `cantidad`.

    Retorna la lista sin barajar (30 cartas); el orden aleatorio lo aplica
    Environment.crear_inicial() con random.shuffle().

    Returns:
        Lista de 30 referencias a ClimateCard del catálogo inmutable.

    Raises:
        AssertionError: Si el total no suma exactamente 30 cartas (integridad del catálogo).
    """
    deck: List[ClimateCard] = []
    for card in CLIMATE_CATALOG.values():
        deck.extend([card] * card.cantidad)
    assert len(deck) == 30, (
        f"El mazo de clima debe tener exactamente 30 cartas, "
        f"el catálogo actual genera {len(deck)}."
    )
    return deck


TENDENCIA_MODIFICADORES: Tuple[int, ...] = (-2,) + (-1,) * 7 + (0,) * 5 + (1,) * 7 + (2,) * 1
"""
Mazo del Mercado de Tendencias (GDD v0.0.2, Módulo II §6): 21 cartas cuyo valor
desplaza simultáneamente los 3 visores de la Bolsa de Harinas (Market.posiciones_harina).
Distribución: -2×1, -1×7, 0×5, +1×7, +2×1.
"""


def build_tendencias_deck() -> List[int]:
    """
    Construye el mazo de Tendencias de Mercado (21 cartas, sin barajar).

    Returns:
        Lista de 21 modificadores enteros; el orden aleatorio lo aplica quien
        posea el mazo (Market.crear_inicial()) con random.shuffle().

    Raises:
        AssertionError: Si el total no suma exactamente 21 cartas.
    """
    deck: List[int] = list(TENDENCIA_MODIFICADORES)
    assert len(deck) == 21, (
        f"El mazo de Tendencias de Mercado debe tener exactamente 21 cartas, "
        f"el catálogo actual genera {len(deck)}."
    )
    return deck


def get_recetas_basicas() -> List[Recipe]:
    """
    Retorna todas las recetas de grado 'Básica' del catálogo maestro.
    Usada en el setup del Día 1 para obtener el mazo de recetas iniciales.

    Returns:
        Lista de Recipe con grado == Grado.BASICA.
    """
    return [r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA]


def get_recetas_intermedias() -> List[Recipe]:
    """
    Retorna todas las recetas de grado 'Intermedia' del catálogo maestro.

    Returns:
        Lista de Recipe con grado == Grado.INTERMEDIA.
    """
    return [r for r in RECIPE_CATALOG.values() if r.grado == Grado.INTERMEDIA]


def get_recetas_avanzadas() -> List[Recipe]:
    """
    Retorna todas las recetas de grado 'Avanzada' del catálogo maestro.
    Usada para construir el mazo del mercado central.

    Returns:
        Lista de Recipe con grado == Grado.AVANZADA.
    """
    return [r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA]


def seleccionar_receta_inicial() -> Recipe:
    """
    Selecciona aleatoriamente una receta de grado 'Básica' para el inicio de partida.

    Abstrae el azar para facilitar el mocking en pruebas unitarias:
    en tests, reemplazar esta función con un stub determinista.

    Returns:
        Una Recipe de grado Básica elegida al azar del catálogo.

    Raises:
        RuntimeError: Si el catálogo no contiene recetas básicas (error de configuración).
    """
    basicas: List[Recipe] = get_recetas_basicas()
    if not basicas:
        raise RuntimeError(
            "No hay recetas de grado 'Básica' disponibles en RECIPE_CATALOG. "
            "Verificar la integridad del catálogo."
        )
    return random.choice(basicas)
