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
* `zona_crecimiento` (Tuple[int, int]): Rango donde la masa **todavía no es pan**: la Acción F la rechaza, así que no tiene pago asociado. Es además el CASO POR DEFECTO — `Recipe.esta_en_crecimiento` no comprueba un rango cerrado sino "ninguna de las otras tres" —, de modo que la casilla 0, donde nace toda masa y que ninguna carta imprime, cae aquí en vez de quedarse sin zona.
* `zona_pre_fermento` (Tuple[int, int]): Rango del track donde la masa está cruda pero ya hornea (otorga pocos puntos, `puntos_pre_fermento`, y 0 Datos).
* `zona_optima` (Tuple[int, int]): Rango del track objetivo (otorga puntos máximos, Datos extra en el centro exacto).
* `zona_colapso` (Tuple[int, int]): Rango del track donde la masa colapsa automáticamente.
* **Las cuatro zonas impresas no son necesariamente las vigentes.** El Módulo Analítico ensancha la zona óptima una casilla por lado, a costa del pre-fermento por abajo y del colapso por arriba — es decir, **también retrasa el umbral de colapso**. El **crecimiento nunca se amplía**, así que la frontera de "ya se puede hornear" no se mueve bajo los pies del jugador. `Recipe.zonas_efectivas(ampliacion)` es el único sitio donde vive esa aritmética; toda consulta de zona (`esta_en_crecimiento`, `esta_en_pre_fermento`, `esta_en_zona_optima`, `esta_en_colapso`) acepta el mismo parámetro. Un pre-fermento más estrecho que `ANCHO_MINIMO_PRE_FERMENTO` se vaciaría al ampliarse, y `__post_init__` lo rechaza. Es un efecto **en vivo** del propietario, no un valor sellado en la masa: instalar el Módulo salva una masa que ya está fermentando. `es_centro_exacto` **no** acepta ampliación porque ensanchar simétricamente no mueve el centro (`(a-n + b+n)//2 == (a+b)//2`).
* `puntos_pre_fermento` (Integer): Puntos de Maestría otorgados si se hornea en el pre-fermento.
* `puntos_optimos` (Integer): Puntos de Maestría otorgados si se hornea en la zona óptima.
* `penalizacion_colapso` (Integer): Puntos de Maestría negativos aplicados en horneado de emergencia (o si se hornea manual en esa zona).
* `monedas_pre_fermento` / `monedas_optima` / `monedas_colapso` (Integer): Monedas cobradas al Hornear y Vender (Acción F) según la zona de horneado. El crecimiento no tiene campo: no se hornea ahí.
* `bono_sabor_pts` (Integer): Puntos de Maestría del Bono de Sabor, otorgados junto con +2 Monedas si el Cubo de Acidez estaba sellado (y el horneado no fue un colapso).

  Los 12 valores del catálogo **se derivan, no se autoran a mano**: `base(grado) + (1 si la diana está fuera del centro, si no 0)`, con `base` = Básica 1 / Intermedia 2 / Avanzada 3, y la distancia medida como la **mínima** de `acidez_diana` a `ACIDEZ_EQUILIBRIO_CENTRO` (= 3) — mínima porque con un dial de acidez el jugador elige el extremo más cercano del rango. Es el reverso exacto de «Madurez del Cultivo» (CORE_MECHANICS.md §3.3), que premia el equilibrio: la carta paga justo por el sitio de la pista que la Madurez cobra. `tests/test_acidez_descarte.py` verifica la regla sobre el catálogo entero, así que una carta nueva no puede salirse de ella.
*(El campo `req_tecnologico` ya no existe: **ninguna receta está restringida por tecnología**. La regla es estructural — `Recipe` no tiene dónde escribir una puerta tecnológica —, así que no puede reintroducirse editando una carta. El freno de una receta cara es su precio de adquisición y su coste en insumos, no una mejora de laboratorio.)

---

## 2. Catálogo de Recetas (Dataset)

12 cartas: 4 Básicas + 4 Intermedias + 4 Avanzadas. Son 4 Básicas y no 3 porque el
setup reparte una Básica distinta por jugador (hasta 4) — con tres, el jugador 4
recibía una copia de la del jugador 1.

| ID Receta | Grado | Coste (Monedas) | Harinas (siempre 100% en total) | Agua — Tokens (Hidratación) | Acidez Diana (Bono) | Crecimiento | Pre-fermento | Óptima | Colapso | Puntos (Pre-f./Óptimo/Colapso) | Monedas al hornear (Pre-f./Óptima/Colapso) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pan de Campo** | Básica | 1 | Blanca 100% | 12 (60%) | [3] (+1) | 1 - 5 | 6 - 10 | 11 - 15 | 16 - 20 | 4 / 10 / -2 | 10 / 14 / 8 |
| **Pan de Molde** | Básica | 1 | Blanca 100% | 11 (55%) | [1, 2] (+2) | 1 - 3 | 4 - 8 | 9 - 14 | 15 - 20 | 3 / 9 / -2 | 9 / 13 / 7 |
| **Baguette** | Básica | 1 | Blanca 100% | 13 (65%) | [2] (+2) | 1 - 5 | 6 - 11 | 12 - 15 | 16 - 20 | 5 / 11 / -2 | 11 / 15 / 9 |
| **Focaccia** | Básica | 1 | Blanca 100% | 15 (75%) | [1, 2] (+2) | 1 - 4 | 5 - 9 | 10 - 14 | 15 - 20 | 3 / 12 / -3 | 12 / 16 / 10 |
| **Miche** | Intermedia | 2 | Blanca 50% + Integral 50% | 14 (70%) | [3, 4] (+2) | 1 - 5 | 6 - 11 | 12 - 16 | 17 - 20 | 5 / 13 / -4 | 10 / 14 / 7 |
| **Pizza Napolitana** | Intermedia | 2 | Blanca 50% + Integral 50% | 13 (62%) | [3] (+2) | 1 - 5 | 6 - 10 | 11 - 14 | 15 - 20 | 4 / 14 / -4 | 9 / 15 / 6 |
| **Brioche** | Intermedia | 2 | Blanca 50% + Centeno 50% | 11 (52%) | [1] (+3) | 1 - 7 | 8 - 14 | 15 - 17 | 18 - 20 | 5 / 16 / -6 | 8 / 15 / 5 |
| **Panettone** | Intermedia | 2 | Blanca 50% + Centeno 50% | 10 (47%) | [1] (+3) | 1 - 10 | 11 - 16 | 17 - 18 | 19 - 20 | 8 / 16 / -8 | 7 / 16 / 4 |
| **Hogaza Centeno** | Avanzada | 3 | Centeno 100% | 14 (67%) | [4, 5] (+4) | 1 - 6 | 7 - 12 | 13 - 16 | 17 - 20 | 6 / 17 / -5 | 11 / 18 / 8 |
| **Pan Semillas** | Avanzada | 3 | Integral 100% | 16 (78%) | [3, 4] (+3) | 1 - 6 | 7 - 13 | 14 - 16 | 17 - 20 | 6 / 17 / -5 | 10 / 17 / 7 |
| **Pan Graham** | Avanzada | 3 | Integral 100% | 16 (80%) | [4, 5] (+4) | 1 - 6 | 7 - 13 | 14 - 17 | 18 - 20 | 6 / 19 / -6 | 9 / 17 / 6 |
| **Pumpernickel** | Avanzada | 3 | Centeno 100% | 17 (85%) | [5, 6] (+4) | 1 - 9 | 10 - 15 | 16 - 18 | 19 - 20 | 8 / 20 / -8 | 7 / 19 / 3 |

---

## 3. Reglas de Validación para la Simulación
* **Inicio Condicional:** Un agente no puede ejecutar la acción "Iniciar Receta" si no posee en su reserva **todas** las harinas que la carta imprime (`requisito_harina`, 100% en total: una bolsa entera de un tipo, o media bolsa de cada uno de dos tipos) y la cantidad exacta de `tokens_agua`. **Ninguna comprobación tecnológica**: no existe receta que exija una mejora de laboratorio.
* **Sello de Acidez:** Al iniciar la receta, el agente compara el nivel de Acidez actual de su cultivo base con la lista `acidez_diana`. Si el valor actual está dentro de la lista, la receta se marca internamente con un booleano `bono_sabor = True`. Si no, `bono_sabor = False`.
* **Gatillo de Colapso:** Durante la Fase III, si la posición de la masa entra en el rango sobrefermentado **efectivo de su propietario** (`zonas_efectivas`, ver §1), el agente invoca automáticamente la función de horneado aplicando la `penalizacion_colapso`. Leerlo contra la zona impresa en vez de la efectiva es el error que haría colapsar una masa pese a tener el Módulo Analítico instalado.
### Renta: los pagos de la tabla son el pago ÚNICO, no todo lo que rinde la carta

Un horneado exitoso sigue rindiendo **cada noche** mientras permanezca en el Archivo
(CORE_MECHANICS.md §Fase III, `engine.PRECIO_RENTA`):

| Grado | Renta por Fase III |
|---|---|
| Básica | 1 Moneda |
| Intermedia | 2 Monedas |
| Avanzada | 3 Monedas |

Los números de Monedas de la tabla de arriba **ya están recortados** en `renta × 3`
respecto a los originales (Básica -3, Intermedia -6, Avanzada -9), sobre las **tres**
zonas. Dos cosas se siguen de ahí y conviene no reabrirlas por descuido:

* **El recorte es uniforme dentro de cada carta**, así que el orden interno
  Óptima > Pre-fermento > Colapso se conserva en las 12. Recortar sólo la Óptima
  invertía Miche y Hogaza Centeno (la venta cruda pagaría más que clavar el punto);
  no tocar el Colapso lo invertía al revés en las 12 (fallar pagaría más que vender
  pronto). Sólo el recorte a las tres zonas deja la tabla coherente.
* **El 3 es un horizonte de amortización común**, no un número suelto: cualquier
  horneado recupera su pago antiguo al tercer día, sea del grado que sea, de modo que
  la presión por hornear pronto es idéntica para todas las cartas y elegir receta sigue
  siendo una cuestión de puntos y harina, no de velocidad de retorno. Está fijado en
  `tests/test_renta_panaderia.py::test_amortizacion_al_tercer_dia` para los tres grados.

Efecto secundario aceptado: **la escalera de grados se invierte en el pago único**
(Panettone paga 7 en Pre-fermento frente a los 9 de Pan de Molde), porque el grado alto
cede más al flujo. Se restaura en valor total al tercer día, que es justamente el
principio elegido.

Un **colapso no rinde renta**: va a `archivo_colapsos`, y provocarlo es gratis.

* **Adquisición (Acción G):** Tomar una receta del mercado cuesta 1 PA **más Monedas según su grado** (`engine.PRECIO_RECETA`: Básica 1, Intermedia 2, Avanzada 3). El precio se valida **antes** de retirar la carta del mercado: `Market.tomar_receta` la quita, así que cobrar después significaría que un jugador sin Monedas destruye una carta al fallar.

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
fuerte (compárense Hogaza Centeno, 17 pts / 18 Monedas, y Pumpernickel, 20 / 19 con una
ventana óptima de 3 espacios y un colapso de -8).

El **Bono de Sabor sí está bandeado**, y a propósito: desde que se deriva de
`grado × distancia al centro` (ver arriba) cae en 1-2 para Básica, 2-3 para Intermedia y
3-4 para Avanzada. Antes no lo estaba — Panettone era Intermedia y tenía el mayor bono
del juego (+8) — pero ese diseño daba por supuesto que la Acidez era un trinquete de un
solo sentido, de modo que una diana baja era un premio *inalcanzable* y podía valer
cualquier cosa. Con el dial de Descarte toda diana es alcanzable, así que lo que
diferencia a una carta ya no es si puedes llegar, sino **cuánta Madurez te cuesta
quedarte allí** — y eso es exactamente lo que mide la distancia al centro.

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
