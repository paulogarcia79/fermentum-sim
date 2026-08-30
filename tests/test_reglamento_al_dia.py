"""
tests/test_reglamento_al_dia.py -- guardarrail contra la deriva entre el CODIGO y
los reglamentos de jugador (RULEBOOK.md + RULEBOOK.html).

Por que existe: los reglamentos se quedaron atras DOS veces seguidas sin que nada
lo detectara. «Variedad de Recetas» anadio un septimo termino de puntuacion y un
criterio de desempate nuevo sin tocarlos, e «Ingresos de Panaderia» repitio el
olvido. La causa es estructural: ningun test leia esos ficheros, y que
`context/*.md` estuviera al dia hacia el hueco invisible desde el codigo.

Que cubre y que NO:

  · SI: todo numero de los reglamentos que se puede derivar del codigo -- las 12
    recetas celda a celda, los 8 Patrocinios, las tres tablas de precios, los
    mazos, los costes de tecnologia, la renta y el numero de terminos de
    puntuacion. Y ademas que RULEBOOK.md y RULEBOOK.html digan LO MISMO entre si,
    que es el fallo tipico al mantenerlos a mano en paralelo.
  · NO: la prosa. Un test no puede juzgar si un parrafo explica bien una regla.
    Para eso esta la lista de `FRASES_PROHIBIDAS`, que solo comprueba que no
    sobreviva la redaccion de una regla ya superada -- el fallo concreto que se
    repitio, no una revision de estilo.

Si este test falla tras un cambio de reglas deliberado, la respuesta NO es relajar
la asercion: es actualizar los cuatro sitios (codigo, context/*.md, RULEBOOK.md y
RULEBOOK.html), que es justamente lo que exige CLAUDE.md.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Sequence

import pytest

from actions import COSTOS_TECNOLOGIA, HARINA_RECULTIVO_MANUAL
from engine import (
    DATOS_SIMPOSIO,
    PRECIO_AGUA,
    PRECIO_RECETA,
    PRECIO_RENTA,
    PRECIOS_HARINA,
)
from models import (
    CLIMATE_CATALOG,
    COPIAS_POR_GRADO,
    Grado,
    PATROCINIO_CATALOG,
    Player,
    RECIPE_CATALOG,
    TENDENCIA_MODIFICADORES,
    TipoHarina,
    VITALIDAD_INICIAL,
    build_recipe_deck,
)

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MD = RAIZ / "RULEBOOK.md"
RUTA_HTML = RAIZ / "RULEBOOK.html"


# ===========================================================================
# Extraccion de tablas
# ===========================================================================

def _normalizar(celda: str) -> str:
    """Deja una celda comparable entre Markdown y HTML.

    Unifica lo que solo es presentacion: etiquetas, entidades, los tres guiones
    tipograficos (- - -), el signo menos Unicode y el enfasis de Markdown.
    """
    texto = re.sub(r"<[^>]+>", " ", celda)
    texto = texto.replace("&nbsp;", " ").replace(" ", " ")
    texto = texto.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    for guion in ("−", "–", "—"):  # menos, en-dash, em-dash
        texto = texto.replace(guion, "-")
    texto = texto.replace("**", "").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", texto).strip()


class Tabla:
    """Una tabla del reglamento: cabecera + filas, ya normalizadas.

    Se extraen tablas enteras y no filas sueltas porque los nombres de grado
    («Básica») encabezan filas en cuatro tablas distintas, y los de harina en
    dos: buscar por primera celda en todo el documento es ambiguo por diseno.
    """

    def __init__(self, cabecera: List[str], filas: List[List[str]]) -> None:
        self.cabecera = cabecera
        self.filas = filas

    def fila(self, clave: str) -> List[str]:
        """La unica fila cuya primera celda es `clave`."""
        encontradas = [f for f in self.filas if f and f[0] == clave]
        assert len(encontradas) == 1, (
            f"esperaba 1 fila que empiece por {clave!r} en la tabla "
            f"{self.cabecera}, encontre {len(encontradas)}"
        )
        return encontradas[0]

    def fila_que_empieza_por(self, prefijo: str) -> List[str]:
        encontradas = [f for f in self.filas if f and f[0].startswith(prefijo)]
        assert len(encontradas) == 1, (
            f"esperaba 1 fila que empiece por {prefijo!r} en la tabla "
            f"{self.cabecera}, encontre {len(encontradas)}"
        )
        return encontradas[0]


def _tablas_md(texto: str) -> List[Tabla]:
    tablas: List[Tabla] = []
    actual: List[List[str]] = []
    for linea in texto.split("\n") + [""]:
        linea = linea.strip()
        if linea.startswith("|"):
            celdas = [_normalizar(c) for c in linea.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in celdas):  # separador
                actual.append(celdas)
            continue
        if actual:
            tablas.append(Tabla(actual[0], actual[1:]))
            actual = []
    return tablas


def _tablas_html(texto: str) -> List[Tabla]:
    tablas: List[Tabla] = []
    for bloque in re.findall(r"<table>(.*?)</table>", texto, re.S):
        cabecera = [
            _normalizar(c)
            for c in re.findall(r"<th[^>]*>(.*?)</th>", bloque.split("</thead>")[0], re.S)
        ]
        filas = [
            [_normalizar(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            for tr in re.findall(r"<tr>(.*?)</tr>", bloque, re.S)
        ]
        tablas.append(Tabla(cabecera, [f for f in filas if f]))
    return tablas


@pytest.fixture(scope="module")
def md() -> str:
    return RUTA_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html() -> str:
    return RUTA_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def docs(md: str, html: str) -> Dict[str, str]:
    return {"RULEBOOK.md": md, "RULEBOOK.html": html}


@pytest.fixture(scope="module")
def tablas(md: str, html: str) -> Dict[str, List[Tabla]]:
    return {"RULEBOOK.md": _tablas_md(md), "RULEBOOK.html": _tablas_html(html)}


def _tabla(
    tablas: Dict[str, List[Tabla]],
    doc: str,
    *fragmentos: str,
    primera: str = "",
) -> Tabla:
    """La unica tabla de `doc` que casa con el criterio dado.

    Se busca por fragmentos de cabecera y no por cabecera exacta porque el .md y
    el .html rotulan distinto («Cantidad» vs «Cant.», «Posición 1» vs «Pos. 1»):
    lo que tiene que coincidir son los datos, no los rotulos. `primera` exige
    ademas que la primera celda de la cabecera sea exactamente esa, que es lo
    que desambigua tablas parecidas (Clima y Tendencias comparten «Modificador»
    y «Cantidad»).
    """
    candidatas = [
        t for t in tablas[doc]
        if (not primera or (t.cabecera and t.cabecera[0] == primera))
        and all(any(f.lower() in c.lower() for c in t.cabecera) for f in fragmentos)
    ]
    criterio = f"primera={primera!r} " if primera else ""
    assert len(candidatas) == 1, (
        f"{doc}: esperaba 1 tabla con {criterio}cabecera que contenga {fragmentos}, "
        f"encontre {len(candidatas)}: {[t.cabecera for t in candidatas]}"
    )
    return candidatas[0]


def _seccion(texto: str, titulo: str, largo: int = 3000) -> str:
    """El texto que sigue al ULTIMO encabezado que menciona `titulo`.

    Se toma el ultimo y no el primero porque el indice y las referencias
    cruzadas mencionan las secciones antes de que empiecen.
    """
    posiciones = [
        m.start()
        for m in re.finditer(re.escape(titulo), texto)
        if re.search(r"(^|\n)\s*(#{2,4} |<h[23])[^\n]{0,80}$",
                     texto[max(0, m.start() - 120):m.start()])
    ]
    assert posiciones, f"no encuentro un encabezado que contenga {titulo!r}"
    return texto[posiciones[-1] : posiciones[-1] + largo]


# Los dos ficheros son el mismo reglamento, asi que toda tabla derivada del
# codigo se comprueba contra AMBOS con el mismo cuerpo de test.
AMBOS = pytest.mark.parametrize("doc", ["RULEBOOK.md", "RULEBOOK.html"])

# La tabla de recetas: 12 columnas, la primera es el nombre de la carta.
COL_GRADO, COL_COSTE, COL_AGUA = 1, 2, 4
COL_ZONAS, COL_PUNTOS, COL_MONEDAS = 6, 10, 11


def _tabla_recetas(tablas, doc):
    return _tabla(tablas, doc, primera="Receta")


# ===========================================================================
# Las 12 recetas, celda a celda
# ===========================================================================

@AMBOS
def test_recetas_grado_y_coste(tablas, doc) -> None:
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        fila = t.fila(receta.nombre)
        assert fila[COL_GRADO] == receta.grado.value, f"{receta.nombre}: grado"
        assert fila[COL_COSTE] == str(PRECIO_RECETA[receta.grado]), (
            f"{receta.nombre}: coste de adquisicion"
        )


@AMBOS
def test_recetas_agua_e_hidratacion(tablas, doc) -> None:
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        fila = t.fila(receta.nombre)
        assert fila[COL_AGUA] == f"{receta.tokens_agua} ({receta.hidratacion_pct}%)", (
            f"{receta.nombre}: agua/hidratacion"
        )


@AMBOS
def test_recetas_cuatro_zonas(tablas, doc) -> None:
    """Las 4 zonas del track. Es lo que el jugador lee para medir su riesgo de
    colapso, asi que una zona mal impresa es peor que un pago mal impreso."""
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        fila = t.fila(receta.nombre)
        zonas = [
            receta.zona_crecimiento,
            receta.zona_pre_fermento,
            receta.zona_optima,
            receta.zona_colapso,
        ]
        for offset, (ini, fin) in enumerate(zonas):
            assert fila[COL_ZONAS + offset] == f"{ini}-{fin}", (
                f"{receta.nombre}: zona en la columna {COL_ZONAS + offset}"
            )


@AMBOS
def test_recetas_puntos(tablas, doc) -> None:
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        esperado = (
            f"{receta.puntos_pre_fermento} / {receta.puntos_optimos} / "
            f"{receta.penalizacion_colapso}"
        )
        assert t.fila(receta.nombre)[COL_PUNTOS] == esperado, f"{receta.nombre}: puntos"


@AMBOS
def test_recetas_monedas(tablas, doc) -> None:
    """El pago del momento de hornear: lo que se recorto al introducir los
    Ingresos de Panaderia y lo que quedo desincronizado durante dos commits."""
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        esperado = (
            f"{receta.monedas_pre_fermento} / {receta.monedas_optima} / "
            f"{receta.monedas_colapso}"
        )
        assert t.fila(receta.nombre)[COL_MONEDAS] == esperado, (
            f"{receta.nombre}: monedas al hornear"
        )


@AMBOS
def test_no_sobran_ni_faltan_recetas(tablas, doc) -> None:
    """Retirar una carta del catalogo tiene que borrarla del reglamento, no solo
    cambiarle los numeros."""
    t = _tabla_recetas(tablas, doc)
    assert {f[0] for f in t.filas} == {r.nombre for r in RECIPE_CATALOG.values()}


# ===========================================================================
# Preparacion de la partida
# ===========================================================================

@AMBOS
def test_cartas_de_patrocinio(tablas, doc) -> None:
    """Incluye la columna de Datos, que es nueva: anadir una columna a la
    cabecera y olvidarla en las filas es el fallo tipico al editar a mano."""
    t = _tabla(tablas, doc, primera="Iniciativa")
    for carta in PATROCINIO_CATALOG:
        fila = t.fila(str(carta.iniciativa))
        assert carta.tipo_harina.value in fila[1], f"iniciativa {carta.iniciativa}: harina"
        assert f"{carta.harina_pct}%" in fila[1], f"iniciativa {carta.iniciativa}: pct"
        assert fila[2].startswith(str(carta.agua_tokens)), (
            f"iniciativa {carta.iniciativa}: agua"
        )
        assert fila[3] == str(carta.monedas), f"iniciativa {carta.iniciativa}: monedas"
        assert fila[4] == (str(carta.datos) if carta.datos else "-"), (
            f"iniciativa {carta.iniciativa}: datos"
        )


@AMBOS
def test_vitalidad_inicial(docs, doc) -> None:
    """VITALIDAD_INICIAL = 2 no es cosmetico: desde 1, «Aletargamiento Invernal»
    provocaba una contaminacion inevitable jugara como jugara el jugador."""
    assert re.search(
        r"Vitalidad inicia en .{0,25}Nivel %d" % VITALIDAD_INICIAL, docs[doc]
    ), f"{doc} no dice que la Vitalidad inicia en Nivel {VITALIDAD_INICIAL}"


# ===========================================================================
# Precios
# ===========================================================================

@AMBOS
def test_bolsa_de_harinas(tablas, doc) -> None:
    """Las 5 posiciones del visor, compra y venta, por tipo de harina."""
    t = _tabla(tablas, doc, primera="Harina")
    for tipo in TipoHarina:
        fila = t.fila_que_empieza_por(tipo.value)
        precios = PRECIOS_HARINA[tipo]
        for i in range(5):
            numeros = [int(n) for n in re.findall(r"\d+", fila[1 + i])]
            compra, venta = precios["compra"][i], precios["venta"][i]
            assert compra in numeros and venta in numeros, (
                f"{tipo.value} posicion {i + 1}: {fila[1 + i]!r} no contiene "
                f"compra={compra} y venta={venta}"
            )


@AMBOS
def test_suministro_hidrico(tablas, doc) -> None:
    t = _tabla(tablas, doc, primera="Temperatura")
    lotes = [10, 30, 60, 100]
    for temp, por_lote in PRECIO_AGUA.items():
        fila = t.fila_que_empieza_por(str(temp))
        for i, lote in enumerate(lotes):
            assert fila[1 + i] == str(por_lote[lote]), f"{temp}C lote {lote}%"


@AMBOS
def test_renta_de_panaderia(tablas, doc) -> None:
    """La tabla que introdujo el mecanismo: 1/2/3 Monedas por noche y grado."""
    t = _tabla(tablas, doc, "Monedas por noche")
    for grado, monedas in PRECIO_RENTA.items():
        assert t.fila(grado.value)[1] == str(monedas), f"renta de {grado.value}"


# ===========================================================================
# Mazos y tecnologias
# ===========================================================================

def _clave_clima(nombre: str) -> str:
    """Nombre de carta de clima comparable entre el codigo y el reglamento.

    Se ignoran los conectores («de», «del»): el codigo llama a la carta «Fallo
    Refrigeración» y el reglamento «Fallo de Refrigeración». Es una diferencia de
    redaccion en un nombre de pantalla, no una regla, y este test comprueba
    REGLAS -- exigir la cadena exacta convertiria una mejora de estilo en un
    fallo de suite. Lo que si se exige es que esten las 9 cartas y que las copias
    cuadren, que es lo que afecta a la partida.
    """
    return re.sub(r"\b(de|del)\b", " ", nombre.lower()).replace(" ", "")


@AMBOS
def test_mazo_de_clima(tablas, doc) -> None:
    t = _tabla(tablas, doc, primera="Evento")
    en_doc = {_clave_clima(f[0]): f for f in t.filas}
    for carta in CLIMATE_CATALOG.values():
        clave = _clave_clima(carta.nombre)
        assert clave in en_doc, f"{doc}: falta la carta de clima {carta.nombre!r}"
        assert en_doc[clave][1] == str(carta.cantidad), (
            f"{carta.nombre}: copias en el mazo"
        )
    assert len(en_doc) == len(CLIMATE_CATALOG), (
        f"{doc} lista {len(en_doc)} cartas de clima y el catalogo tiene "
        f"{len(CLIMATE_CATALOG)}"
    )


@AMBOS
def test_mazo_de_tendencias(tablas, doc) -> None:
    from collections import Counter

    t = _tabla(tablas, doc, primera="Modificador")
    for modificador, cantidad in Counter(TENDENCIA_MODIFICADORES).items():
        etiqueta = f"+{modificador}" if modificador > 0 else str(modificador)
        assert t.fila(etiqueta)[1] == str(cantidad), f"tendencia {etiqueta}"


@AMBOS
def test_composicion_del_mazo_de_recetas(tablas, doc) -> None:
    """4/3/2 copias por grado = 16+12+8 = 36 cartas fisicas."""
    t = _tabla(tablas, doc, "Protocolos", "Copias")
    for grado, copias in COPIAS_POR_GRADO.items():
        protocolos = sum(1 for r in RECIPE_CATALOG.values() if r.grado == grado)
        fila = t.fila(grado.value)
        assert fila[1] == str(protocolos), f"{grado.value}: protocolos"
        assert fila[2] == str(copias), f"{grado.value}: copias de cada uno"
        assert fila[3] == str(protocolos * copias), f"{grado.value}: cartas"
    assert t.fila_que_empieza_por("Total")[-1] == str(len(build_recipe_deck())) == "36"


@AMBOS
def test_costes_de_tecnologia(tablas, doc) -> None:
    t = _tabla(tablas, doc, primera="Tecnología")
    for tecnologia, costo in COSTOS_TECNOLOGIA.items():
        fila = t.fila(tecnologia.nombre_legible)
        assert str(costo) in fila[1], f"{tecnologia.nombre_legible}: coste en Datos"


# ===========================================================================
# Puntuacion: el termino que se olvido
# ===========================================================================

# Los nombres del reglamento no son las claves de `Player.desglose_maestria` (uno
# esta escrito para jugadores y el otro para el codigo), asi que el puente se
# declara aqui a mano. Es tabla corta a proposito: si el codigo gana un termino,
# este fichero falla hasta que alguien lo escriba tambien en el reglamento.
TERMINOS_EN_EL_REGLAMENTO = {
    "Base": "Puntos Base",
    "Sabor": "Puntos de Sabor",
    "Madurez": "Madurez del Cultivo",
    "Variedad de Recetas": "Variedad de Recetas",
    "Desperdicio": "Penalización por Desperdicio",
    "Contaminación": "Penalización por Contaminación",
    "Conversión de Riqueza": "Conversión de Riqueza",
}


def test_el_puente_de_terminos_cubre_el_desglose_del_codigo() -> None:
    assert list(Player(nombre="x").desglose_maestria) == list(TERMINOS_EN_EL_REGLAMENTO), (
        "Player.desglose_maestria cambio de terminos o de orden. Actualiza "
        "TERMINOS_EN_EL_REGLAMENTO y, sobre todo, RULEBOOK.md/.html 11.2."
    )


@AMBOS
def test_todos_los_terminos_de_puntuacion_estan_en_el_reglamento(docs, doc) -> None:
    """El fallo real: el codigo aplicaba 7 terminos y el reglamento listaba 6."""
    faltan = [n for n in TERMINOS_EN_EL_REGLAMENTO.values() if n not in docs[doc]]
    assert not faltan, f"{doc} no menciona estos terminos de puntuacion: {faltan}"


@AMBOS
def test_variedad_es_el_primer_desempate(docs, doc) -> None:
    bloque = _seccion(docs[doc], "Desempate", largo=900)
    pos_variedad = bloque.find("distintas")
    pos_vitalidad = bloque.find("Vitalidad")
    assert pos_variedad != -1, f"{doc}: el desempate no menciona las recetas distintas"
    assert pos_vitalidad != -1, f"{doc}: el desempate no menciona la Vitalidad"
    assert pos_variedad < pos_vitalidad, (
        f"{doc}: las recetas distintas deben ser el PRIMER criterio de desempate, "
        "por delante de la Vitalidad (CORE_MECHANICS.md seccion Desempate)."
    )


# ===========================================================================
# Reglas que no viven en ninguna tabla
# ===========================================================================

@AMBOS
def test_coste_del_protocolo_h(docs, doc) -> None:
    i = docs[doc].index("Re-cultivo Manual")
    assert f"{HARINA_RECULTIVO_MANUAL}%" in docs[doc][i : i + 300], (
        f"{doc}: el Protocolo H deberia costar {HARINA_RECULTIVO_MANUAL}% de harina"
    )


@AMBOS
def test_datos_del_simposio(docs, doc) -> None:
    """El Simposio paga por grado (1/2/3), no una cantidad fija."""
    bloque = _seccion(docs[doc], "Simposio Técnico")
    for grado, datos in DATOS_SIMPOSIO.items():
        assert re.search(r"%s.{0,60}?%d" % (grado.value, datos), bloque, re.S), (
            f"{doc}: el Simposio no declara {datos} Datos para {grado.value}"
        )


# ===========================================================================
# Redacciones superadas
# ===========================================================================

# Solo entran aqui frases que describian una regla que YA NO EXISTE. No es una
# revision de estilo: cada entrada corresponde a una regla concreta cuya
# redaccion vieja sobrevivio en la prosa despues de arreglar las tablas -- el
# fallo que se repitio dos veces.
FRASES_PROHIBIDAS = [
    ("+1 Dato de Investigación inmediato", "el Simposio paga por grado, no +1 fijo"),
    ("Simposio Técnico</strong> la descarta", "ya no se puede abandonar una masa"),
    ("**Simposio Técnico** la descarta", "ya no se puede abandonar una masa"),
    ("Vitalidad y Acidez inician en", "la Vitalidad ya no arranca igual que la Acidez"),
]


@AMBOS
def test_no_sobrevive_la_redaccion_de_reglas_superadas(docs, doc) -> None:
    encontradas = [(f, m) for f, m in FRASES_PROHIBIDAS if f in docs[doc]]
    assert not encontradas, (
        f"{doc} conserva la redaccion de reglas ya superadas: {encontradas}"
    )


# ===========================================================================
# Los dos ficheros son el mismo reglamento
# ===========================================================================

def test_los_dos_ficheros_coinciden_en_la_tabla_de_recetas(tablas) -> None:
    """Se mantienen a mano en paralelo, sin script que genere uno del otro, asi
    que la deriva ENTRE ELLOS es tan probable como la deriva contra el codigo."""
    en_md = {f[0]: tuple(f) for f in _tabla_recetas(tablas, "RULEBOOK.md").filas}
    en_html = {f[0]: tuple(f) for f in _tabla_recetas(tablas, "RULEBOOK.html").filas}
    assert en_md.keys() == en_html.keys(), "las recetas listadas no coinciden"
    distintas = {k: (en_md[k], en_html[k]) for k in en_md if en_md[k] != en_html[k]}
    assert not distintas, f"filas de receta distintas entre .md y .html: {distintas}"


def test_el_html_esta_bien_formado_y_sus_tablas_cuadran(html) -> None:
    """Anadir una columna en el <thead> y olvidarla en el <tbody> no rompe nada
    visible, pero descuadra la tabla. Es lo que casi pasa al meter la columna de
    Datos en las Cartas de Patrocinio."""

    class Verificador(HTMLParser):
        VACIAS = {"br", "img", "hr", "meta", "link", "input", "source", "col"}

        def __init__(self) -> None:
            super().__init__()
            self.pila: List[str] = []
            self.errores: List[str] = []

        def handle_starttag(self, tag, attrs):
            if tag not in self.VACIAS:
                self.pila.append(tag)

        def handle_endtag(self, tag):
            if tag in self.VACIAS:
                return
            if not self.pila or self.pila[-1] != tag:
                self.errores.append(f"</{tag}> descuadra en {self.getpos()}")
            if self.pila:
                self.pila.pop()

    verificador = Verificador()
    verificador.feed(html)
    assert not verificador.errores, verificador.errores[:5]
    assert not verificador.pila, f"etiquetas sin cerrar: {verificador.pila}"

    for bloque in re.findall(r"<table>(.*?)</table>", html, re.S):
        columnas = len(re.findall(r"<th[ >]", bloque.split("</thead>")[0]))
        if not columnas:
            continue
        for fila in re.findall(r"<tr>((?:<td.*?</td>)+)</tr>", bloque, re.S):
            celdas = len(re.findall(r"<td[ >]", fila))
            assert celdas == columnas, (
                f"tabla de {columnas} columnas con una fila de {celdas}: "
                f"{_normalizar(fila)[:90]}"
            )
