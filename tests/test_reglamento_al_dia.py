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
  · NO: la prosa. Un test no puede juzgar si un parrafo explica bien una regla,
    ni si una frase vieja sobrevivio contradiciendo a la nueva. Eso es revision
    humana, y la obligacion vive en CLAUDE.md, no aqui.

Hubo aqui una lista de `FRASES_PROHIBIDAS` (redacciones de reglas ya superadas que
no debian sobrevivir en el texto) y se quito **tras medirla**: inyectando la misma
contradiccion de dos formas, cazaba la frase exacta que alguien habia enumerado y
dejaba pasar la variante equivalente. Era el retrato de cuatro migraciones pasadas,
sin valor predictivo sobre la siguiente, que nadie iba a podar y que solo podia
crecer. Un test que comprueba reglas no debe acumular historia; si vuelve a
proponerse algo asi, que sea con la medicion delante.

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

from actions import (
    COSTOS_TECNOLOGIA,
    AGUA_PEDIDO_URGENCIA,
    HARINA_PEDIDO_URGENCIA,
    HARINA_RECULTIVO_MANUAL,
)
from engine import (
    DATOS_JEFATURA,
    DATOS_SIMPOSIO,
    PRECIO_AGUA,
    PRECIO_CONTRATO_MOLINO,
    PRECIO_RECETA,
    PRECIO_RENTA,
    PRECIOS_HARINA,
    RENDIMIENTO_MOLINO_PCT,
)
from models import (
    CLIMATE_CATALOG,
    COPIAS_POR_GRADO,
    Grado,
    PATROCINIO_CATALOG,
    Player,
    RECIPE_CATALOG,
    puntos_triangulares,
    TecnologiaID,
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
COL_GRADO, COL_COSTE, COL_AGUA, COL_DIANA = 1, 2, 4, 5
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
def test_recetas_acidez_diana_y_bono(tablas, doc) -> None:
    """
    La columna que este guardarrail NO cubria, y que el dial de Acidez toco
    entera: la Acidez Diana y, entre parentesis, su Bono de Sabor.

    Se comprueban las dos mitades por separado porque fallan por motivos
    distintos: la diana se desincroniza al reautorar una carta, y el bono al
    rebalancear la escala entera. La diana se compara como CONJUNTO de niveles
    (los reglamentos escriben "Nivel 1-2" o "[1, 2]" segun el documento, pero
    ambos significan lo mismo) mientras que el bono se compara exacto.
    """
    t = _tabla_recetas(tablas, doc)
    for receta in RECIPE_CATALOG.values():
        celda = t.fila(receta.nombre)[COL_DIANA]
        niveles = {int(n) for n in re.findall(r"\d+", celda.split("(")[0])}
        # "Nivel 1-2" abrevia un rango; el catalogo lo lista carta a carta.
        if len(niveles) == 2:
            lo, hi = min(niveles), max(niveles)
            niveles = set(range(lo, hi + 1))
        assert niveles == set(receta.acidez_diana), (
            f"{receta.nombre}: acidez diana {celda!r} vs {receta.acidez_diana}"
        )

        bono = re.search(r"\(\+(\d+)\)", celda)
        assert bono, f"{receta.nombre}: la celda {celda!r} no imprime el bono"
        assert int(bono.group(1)) == receta.bono_sabor_pts, (
            f"{receta.nombre}: bono de sabor impreso {bono.group(1)}, "
            f"el catalogo dice {receta.bono_sabor_pts}"
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
    """Las 5 posiciones del visor, compra y venta, por tipo de harina.

    El fragmento «pos» hace falta desde que el Contrato con el Molino trajo una
    segunda tabla encabezada por «Harina»: es exactamente la ambiguedad que
    _tabla existe para detectar, y se desambigua por cabecera, no aflojando la
    busqueda («Posición 1» en el .md, «Pos. 1» en el .html).
    """
    t = _tabla(tablas, doc, "pos", primera="Harina")
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


@AMBOS
def test_contrato_con_el_molino(tablas, doc) -> None:
    """Precio por tipo Y entrega nocturna, en la misma tabla.

    La entrega se comprueba celda a celda en las tres filas aunque sea el mismo
    numero en las tres: que sea PLANA es justo la regla de diseno (lo que escala
    es el precio), asi que una fila que se desviase seria una contradiccion del
    reglamento consigo mismo, no una erratа cosmetica.
    """
    t = _tabla(tablas, doc, "Contrato", "Entrega")
    for tipo, precio in PRECIO_CONTRATO_MOLINO.items():
        fila = t.fila(tipo.value)
        assert fila[1] == str(precio), f"contrato de {tipo.value}"
        assert f"{RENDIMIENTO_MOLINO_PCT}%" in fila[2], (
            f"{doc}: la entrega de {tipo.value} deberia ser "
            f"{RENDIMIENTO_MOLINO_PCT}%"
        )


# ===========================================================================
# Mazos y tecnologias
# ===========================================================================

@AMBOS
def test_mazo_de_clima(tablas, doc) -> None:
    """Nombre EXACTO y numero de copias de las 9 cartas.

    El nombre se compara literal a proposito. Hubo un tiempo en que el codigo
    decia «Fallo Refrigeración» y el reglamento «Fallo de Refrigeración», y este
    test toleraba los conectores para no fallar por eso; tolerar la diferencia
    era dejar viva una divergencia arbitraria entre las dos caras del mismo
    juego. Se unificaron los nombres y la tolerancia se fue con ellos.
    """
    t = _tabla(tablas, doc, primera="Evento")
    en_doc = {f[0]: f for f in t.filas}
    assert en_doc.keys() == {c.nombre for c in CLIMATE_CATALOG.values()}, (
        f"{doc}: las cartas de clima listadas no son las del catalogo"
    )
    for carta in CLIMATE_CATALOG.values():
        assert en_doc[carta.nombre][1] == str(carta.cantidad), (
            f"{carta.nombre}: copias en el mazo"
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
    "Desarrollo Tecnológico": "Desarrollo Tecnológico",
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


# Las DOS curvas triangulares que los reglamentos imprimen, contra la unica
# funcion que las deriva. La de Variedad llevaba desde su commit sin comprobar:
# era un hueco del contrato declarado de este fichero («todo numero que se pueda
# derivar del codigo»), no una politica, asi que entra con la de tecnologias.
#
# termino -> (rotulo de la primera celda de cabecera en el .md, n maximo)
#
# Los dos topes se DERIVAN, no se escriben: el de Variedad es el gatillo del
# quinto horneado y el de Desarrollo es cuantas mejoras existen. Escribir el
# segundo a mano es exactamente como se quedo obsoleto al anadir Comerciante --
# el reglamento seguia imprimiendo una curva de cuatro escalones y el test la
# daba por buena porque los dos decian «4».
CURVAS_TRIANGULARES = {
    # El 5 de Variedad sigue escrito porque el gatillo del quinto horneado es un
    # literal en engine.py y no una constante con nombre; el de Desarrollo si se
    # deriva, que es lo que lo mantiene al dia solo.
    "Variedad de Recetas": ("Recetas distintas", 5),
    "Desarrollo Tecnológico": ("Mejoras instaladas", len(TecnologiaID)),
}


def _curva(n_max: int) -> List[str]:
    """La curva tal y como la imprimen los reglamentos: 0, +1, +3, +6..."""
    return [
        str(v) if v == 0 else f"+{v}"
        for v in (puntos_triangulares(n) for n in range(n_max + 1))
    ]


@pytest.mark.parametrize("termino", sorted(CURVAS_TRIANGULARES))
def test_curvas_triangulares_del_md_celda_a_celda(tablas, termino) -> None:
    """En el .md cada curva es una tabla de verdad, asi que se compara entera."""
    rotulo, n_max = CURVAS_TRIANGULARES[termino]
    t = _tabla(tablas, "RULEBOOK.md", primera=rotulo)
    assert t.cabecera[1:] == [str(n) for n in range(n_max + 1)], (
        f"RULEBOOK.md, tabla «{rotulo}»: la cabecera debe ir de 0 a {n_max}"
    )
    assert t.fila("Puntos de Maestría")[1:] == _curva(n_max), (
        f"RULEBOOK.md, tabla «{rotulo}»: la curva impresa no es "
        f"models.puntos_triangulares. Termino: {termino}."
    )


@pytest.mark.parametrize("termino", sorted(CURVAS_TRIANGULARES))
def test_curvas_triangulares_del_html_en_su_propia_fila(tablas, termino) -> None:
    """En el .html las curvas son PROSA dentro de la tabla de 11.2, no tablas.

    Se busca la secuencia dentro de la celda de SU termino y no en la seccion
    entera a proposito: «0 / +1 / +3 / +6 / +10 / +15» contiene literalmente a
    «0 / +1 / +3 / +6 / +10», de modo que un `in` sobre todo el bloque daria por
    buena una fila de Desarrollo Tecnologico que no existiese.
    """
    _, n_max = CURVAS_TRIANGULARES[termino]
    tabla = _tabla(tablas, "RULEBOOK.html", "Componente", primera="#")
    filas = [f for f in tabla.filas if len(f) > 2 and f[1] == termino]
    assert len(filas) == 1, (
        f"RULEBOOK.html 11.2: esperaba 1 fila para «{termino}», encontre {len(filas)}"
    )
    esperado = " / ".join(_curva(n_max))
    assert esperado in filas[0][2], (
        f"RULEBOOK.html 11.2, «{termino}»: no encuentro la curva {esperado!r} "
        f"en su celda. Dice: {filas[0][2][:160]!r}"
    )


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


# PLAYER_STATE.md: cada token de agua vale un 5% de hidratacion. No hay
# constante en Python (`reserva_agua` ya cuenta tokens), pero los reglamentos
# imprimen SIEMPRE la notacion canonica `N (P%)`, asi que el test necesita el
# factor para construir la cifra que deberia leerse.
PCT_POR_TOKEN_AGUA = 5


@AMBOS
def test_cantidad_del_pedido_de_urgencia(docs, doc) -> None:
    """Las dos parcelas son FIJAS, y ambas cantidades son reglas de balance.

    La harina: media bolsa y no una entera, por el arbitraje de 1 Dato ->
    bolsa entera -> reventa. El agua: una cantidad fija y no la que el jugador
    escriba, porque una receta pide 10-17 tokens y un lote del 100% cuesta
    7-14 Monedas, de modo que 1 Dato compraba toda el agua de la partida.
    Ninguna de las dos es un detalle de formato.
    """
    bloque = _normalizar(_seccion(docs[doc], "Pedido de Urgencia", largo=2000))

    assert f"{HARINA_PEDIDO_URGENCIA}%" in bloque, (
        f"{doc}: el Pedido de Urgencia deberia entregar "
        f"{HARINA_PEDIDO_URGENCIA}% de harina"
    )
    assert "(100%)" not in bloque, (
        f"{doc}: el Pedido de Urgencia sigue anunciando una bolsa entera"
    )

    agua = f"{AGUA_PEDIDO_URGENCIA} ({AGUA_PEDIDO_URGENCIA * PCT_POR_TOKEN_AGUA}%)"
    assert agua in bloque, (
        f"{doc}: el Pedido de Urgencia deberia entregar {agua} de agua, "
        "en la notacion canonica `N (P%)`"
    )


@AMBOS
def test_la_jefatura_se_reclama_y_paga_datos(docs, doc) -> None:
    """Las dos mitades de la regla nueva, y la vieja explicitamente ausente.

    La asignacion automatica por Vitalidad no es una redaccion superada
    cualquiera: es la regla que ESTA ocupaba, asi que si sobrevive en §5.1 el
    reglamento se contradice a si mismo. Se comprueba en la seccion, no en todo
    el documento, porque la nota que explica el cambio si la menciona a
    proposito.
    """
    bloque = _seccion(docs[doc], "Actualización de Jerarquía", largo=1400)
    assert "reclam" in bloque.lower(), (
        f"{doc}: §5.1 no dice que la Jefatura se reclama"
    )
    assert not re.search(r"Vitalidad más alta|Vitalidad más alto", bloque), (
        f"{doc}: §5.1 sigue asignando la Jefatura por Vitalidad"
    )

    accion = _seccion(docs[doc], "Reclamar la Jefatura", largo=900)
    assert re.search(r"\b%d\b.{0,40}Dato" % DATOS_JEFATURA, accion), (
        f"{doc}: la acción no declara que paga {DATOS_JEFATURA} Dato"
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


@AMBOS
def test_el_vocabulario_de_zonas_es_el_vigente(docs, doc) -> None:
    """Las cuatro zonas tienen UN nombre cada una, el que dice el codigo.

    El renombrado a cuatro zonas (`zona_baja` -> `zona_pre_fermento`,
    `zona_sobrefermentada` -> `zona_colapso`) dejo atras once frases con los
    nombres viejos, entre ellas una leyenda de la pista que anunciaba TRES
    zonas al lado de una tabla con cuatro columnas. Ninguna tabla podia
    detectarlo: los datos estaban bien y solo el vocabulario estaba mal.

    Se comprueba el texto visible, no el HTML entero: los selectores CSS
    conservan `z-baja` / `z-sobre` a proposito (ver el comentario en el bloque
    de estilos), porque renombrar 48 identificadores que nadie lee solo puede
    salir mal.
    """
    visible = re.sub(r"<style.*?</style>", "", docs[doc], flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    for retirado in ("Zona Baja", "zona baja", "Sobre-fermentada", "sobrefermentada"):
        assert retirado not in visible, (
            f"{doc}: «{retirado}» es un nombre de zona RETIRADO. Las cuatro "
            "zonas son Crecimiento, Pre-fermento, Óptima y Colapso."
        )


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
