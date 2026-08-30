# RECIPE_DATABASE (Fermentum)
**Descripción General:** Este archivo contiene el catálogo maestro de los protocolos de panificación (recetas). Define los parámetros matemáticos, requerimientos de insumos y los rangos de las zonas de fermentación para el cálculo de colapsos y puntuaciones.
**Nota Aclaratoria** Inicio Condicional: Al iniciar una receta, el sistema debe comprobar que el jugador tiene, para **cada** tipo que la carta imprime, al menos el porcentaje pedido en `reserva_harina[tipo]`, y restarlo. El total es siempre **10 Tokens de Harina, 10 (100%)** — una bolsa entera —, repartido entre uno o dos tipos según el grado (ver §4). `Recipe.requisito_harina` expone ese requisito con la misma forma que `Player.reserva_harina` (`{tipo: porcentaje}`) precisamente para que validar y cobrar sean un único bucle.

## 1. Esquema de Datos (Data Schema)
Para la simulación, cada entidad de tipo `Receta` debe contener los siguientes atributos lógicos:
* `id` (String): Identificador único de la receta.
* `grado` (String): "Básica", "Intermedia" o "Avanzada". **No se escribe a mano: se deriva de `harinas`** (ver §4) y `Recipe.__post_init__` verifica que el campo coincida, de modo que una carta mal etiquetada aborta `import models` en vez de renderizarse mal.
* `harinas` (List[Tuple[String, Integer]]): Las harinas impresas en la carta, como pares `(tipo, porcentaje)` en orden de impresión. **Suman siempre 100%** (una bolsa) — lo único que varía es entre cuántos tipos se reparte:
  * Una entrada al 100% → una bolsa entera de un tipo.
  * Dos entradas distintas al 50% → media bolsa de cada uno.
  No existe ninguna otra forma legal, y no es una restricción arbitraria: la Bolsa de Harinas solo vende bolsa entera (`comprar`) y media bolsa (`comprar_media`). Un reparto 90/10 exigiría comprar tokens sueltos, que el mercado no ofrece.
* `hidratacion_pct` (Integer): Porcentaje total de hidratación.
* `tokens_agua` (Integer): Cantidad de **Tokens de Agua** del 5% requeridos. Se obtiene **redondeando hacia arriba**: `ceil(hidratacion_pct / 5)`. Ej.: 60% → 12 tokens exactos; 62% → 13 tokens (12,4 redondeado hacia arriba). Por eso `tokens_agua * 5` **no** reproduce siempre `hidratacion_pct` y la hidratación impresa debe leerse siempre de su propio campo, nunca deducirse del conteo de tokens.
* `acidez_diana` (List[int]): Rango de niveles de Acidez que otorgan el Bono de Sabor al iniciar la receta.
* `zona_baja` (Tuple[int, int]): Rango del track donde la masa está cruda (otorga pocos puntos, `puntos_baja`, y 0 Datos).
* `zona_optima` (Tuple[int, int]): Rango del track objetivo (otorga puntos máximos, Datos extra en el centro exacto).
* `zona_sobrefermentada` (Tuple[int, int]): Rango del track donde la masa colapsa automáticamente.
* `puntos_baja` (Integer): Puntos de Maestría otorgados si se hornea en la zona baja.
* `puntos_optimos` (Integer): Puntos de Maestría otorgados si se hornea en la zona óptima.
* `penalizacion_colapso` (Integer): Puntos de Maestría negativos aplicados en horneado de emergencia (o si se hornea manual en esa zona).
* `monedas_baja` / `monedas_optima` / `monedas_sobre` (Integer): Monedas cobradas al Hornear y Vender (Acción F) según la zona de horneado.
* `bono_sabor_pts` (Integer): Puntos de Maestría del Bono de Sabor, otorgados junto con +2 Monedas si el Cubo de Acidez estaba sellado (y el horneado no fue un colapso).
* `req_tecnologico` (String / None): Mejora de laboratorio estrictamente necesaria para iniciar la receta. **Es la única puerta tecnológica**: el grado ya no implica ninguna (una carta de harina especial sin `req_tecnologico` es jugable desde el Día 1).

---

## 2. Catálogo de Recetas (Dataset)

12 cartas: 4 Básicas + 4 Intermedias + 4 Avanzadas. Son 4 Básicas y no 3 porque el
setup reparte una Básica distinta por jugador (hasta 4) — con tres, el jugador 4
recibía una copia de la del jugador 1.

| ID Receta | Grado | Harinas (siempre 100% en total) | Agua — Tokens (Hidratación) | Acidez Diana (Bono) | Zona Baja | Zona Óptima | Zona Sobre | Puntos (Baja/Óptimo/Sobre) | Monedas (Baja/Óptima/Sobre) | Req. Tecnológico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pan de Campo** | Básica | Blanca 100% | 12 (60%) | [3] (+3) | 1 - 10 | 11 - 15 | 16 - 20 | 4 / 10 / -2 | 13 / 17 / 11 | Ninguno |
| **Pan de Molde** | Básica | Blanca 100% | 11 (55%) | [1, 2] (+2) | 1 - 8 | 9 - 14 | 15 - 20 | 3 / 9 / -2 | 12 / 16 / 10 | Ninguno |
| **Baguette** | Básica | Blanca 100% | 13 (65%) | [2] (+3) | 1 - 11 | 12 - 15 | 16 - 20 | 5 / 11 / -2 | 14 / 18 / 12 | Ninguno |
| **Focaccia** | Básica | Blanca 100% | 15 (75%) | [1, 2] (+2) | 1 - 9 | 10 - 14 | 15 - 20 | 3 / 12 / -3 | 15 / 19 / 13 | Ninguno |
| **Miche** | Intermedia | Blanca 50% + Integral 50% | 14 (70%) | [3, 4] (+4) | 1 - 11 | 12 - 16 | 17 - 20 | 5 / 13 / -4 | 16 / 20 / 13 | Ninguno |
| **Pizza Napolitana** | Intermedia | Blanca 50% + Integral 50% | 13 (62%) | [3] (+4) | 1 - 10 | 11 - 14 | 15 - 20 | 4 / 14 / -4 | 15 / 21 / 12 | Módulo Analítico |
| **Brioche** | Intermedia | Blanca 50% + Centeno 50% | 11 (52%) | [1] (+5) | 1 - 14 | 15 - 17 | 18 - 20 | 5 / 16 / -6 | 14 / 21 / 11 | Módulo Analítico |
| **Panettone** | Intermedia | Blanca 50% + Centeno 50% | 10 (47%) | [1] (+8) | 1 - 16 | 17 - 18 | 19 - 20 | 8 / 16 / -8 | 13 / 22 / 10 | Módulo Analítico |
| **Hogaza Centeno** | Avanzada | Centeno 100% | 14 (67%) | [4, 5] (+6) | 1 - 12 | 13 - 16 | 17 - 20 | 6 / 17 / -5 | 20 / 27 / 17 | Módulo Analítico |
| **Pan Semillas** | Avanzada | Integral 100% | 16 (78%) | [3, 4] (+7) | 1 - 13 | 14 - 16 | 17 - 20 | 6 / 17 / -5 | 19 / 26 / 16 | Módulo Analítico |
| **Pan Graham** | Avanzada | Integral 100% | 16 (80%) | [4, 5] (+6) | 1 - 13 | 14 - 17 | 18 - 20 | 6 / 19 / -6 | 18 / 26 / 15 | Módulo Analítico |
| **Pumpernickel** | Avanzada | Centeno 100% | 17 (85%) | [5, 6] (+8) | 1 - 15 | 16 - 18 | 19 - 20 | 8 / 20 / -8 | 16 / 28 / 12 | Módulo Analítico |

---

## 3. Reglas de Validación para la Simulación
* **Inicio Condicional:** Un agente no puede ejecutar la acción "Iniciar Receta" si no posee en su reserva **todas** las harinas que la carta imprime (`requisito_harina`, 100% en total: una bolsa entera de un tipo, o media bolsa de cada uno de dos tipos) y la cantidad exacta de `tokens_agua`. Si la carta declara un `req_tecnologico`, esa mejora debe estar instalada — se comprueba contra el campo de la carta, **no** contra su grado.
* **Sello de Acidez:** Al iniciar la receta, el agente compara el nivel de Acidez actual de su cultivo base con la lista `acidez_diana`. Si el valor actual está dentro de la lista, la receta se marca internamente con un booleano `bono_sabor = True`. Si no, `bono_sabor = False`.
* **Gatillo de Colapso:** Durante la Fase III, si la posición de la masa entra en el rango definido por `zona_sobrefermentada`, el agente invoca automáticamente la función de horneado aplicando la `penalizacion_colapso`.

---

## 4. Grados: qué imprime cada uno, y qué paga

El grado de una receta **es** su reparto de harinas. No es una etiqueta editorial que
acompaña a la carta: `_grado_desde_harinas` (models.py) lo deriva, y una carta cuyo
campo `grado` no coincida no llega a construirse.

| Grado | Imprime | Coste en la Bolsa (posición 1 → 5) |
| :--- | :--- | :--- |
| **Básica** | Blanca 100% | 2 – 6 Monedas |
| **Intermedia** | 50% + 50% de dos harinas distintas | 3 – 7 (Blanca+Integral) … 5 – 9 (Integral+Centeno) |
| **Avanzada** | 100% de una harina **especial** (Centeno o Integral) | 4 – 8 (Integral) / 6 – 10 (Centeno) |

**Harina especial** = Centeno o Integral. La Blanca es el producto común, la pista más
barata de las tres, y es precisamente lo que impide que una Básica sea una Avanzada.

La escalera de coste no está escrita en ninguna tabla nueva: sale de `PRECIOS_HARINA`
(engine.py) más la media bolsa, que cuesta `⌈compra/2⌉`. Por eso la media bolsa no es
un descuento — a precio impar es estrictamente peor por token — y una Intermedia paga
por la liquidez de necesitar dos pistas a la vez.

### Bandas de puntuación (sin solape)

`puntos_optimos` está bandeado por grado, de modo que subir de escalón signifique algo
en el marcador y no solo en la lista de la compra:

| Grado | `puntos_optimos` |
| :--- | :--- |
| Básica | 9 – 12 |
| Intermedia | 13 – 16 |
| Avanzada | 17 – 20 |

Las **Monedas y el ancho de las zonas NO están bandeados**: siguen siendo el eje que
distingue, dentro de un mismo grado, una carta de puntos baratos de una carta caja
fuerte (compárense Hogaza Centeno, 17 pts / 27 Monedas, y Pumpernickel, 20 / 28 con una
ventana óptima de 3 espacios y un colapso de -8). Igual que el Bono de Sabor: Panettone
es Intermedia y aun así tiene el mayor bono del juego (+8) — no es la carta de más
puntos, es la de más sabor.

`tests/test_recetas_grado.py` fija estas bandas y la composición 4/4/4; añadir una carta
fuera de banda rompe la suite, que es el punto.

### Dónde aparece cada grado

* **Reparto del Día 1** (`bootstrap.create_game`): una **Básica** distinta por jugador. Por eso
  hay cuatro y no tres — con tres, el jugador 4 recibía una copia de la del jugador 1.
* **Mazo del mercado** (`Market.crear_inicial`): 36 cartas físicas — cada protocolo entra con sus
  copias (`models.COPIAS_POR_GRADO`: 4 por Básica, 3 por Intermedia, 2 por Avanzada, ver
  `expandir_copias`/`build_recipe_deck`, calcados de `build_climate_deck`). Avanzadas e
  Intermedias **mezcladas entre sí** arriba, Básicas barajadas al fondo. Las copias van por
  **grado y no por carta** (a diferencia de `ClimateCard.cantidad`, que es un campo por carta)
  porque el grado ya lo derivan las harinas: una tabla por carta serían 12 números derivables que
  podrían desmentir al reglamento. La escasez de las Avanzadas (8 cartas de 36) es una barrera
  independiente de su precio.
  `bootstrap.create_game` retira después **una copia** por jugador de la Básica repartida — una
  copia, no el protocolo: con 4 por Básica, quitar las cuatro vaciaría el estrato de reserva en
  una partida a 4. Las Intermedias no van en un tercer estrato por debajo de
  las Avanzadas: el escalón medio existe para escalarse durante la partida, y una escalera
  estricta lo haría aparecer justo cuando ya sobra. Las Básicas están al fondo porque cada
  jugador ya empieza con una: en el mercado son la reserva, no la oferta.

Un grado que no se nombre en `crear_inicial` es sencillamente invisible aunque esté en el
catálogo — le pasó a las Intermedias al introducirlas. La suite lo verifica.
