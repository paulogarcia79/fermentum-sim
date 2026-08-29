# RECIPE_DATABASE (Fermentum)
**Descripción General:** Este archivo contiene el catálogo maestro de los protocolos de panificación (recetas). Define los parámetros matemáticos, requerimientos de insumos y los rangos de las zonas de fermentación para el cálculo de colapsos y puntuaciones.
**Nota Aclaratoria** Inicio Condicional: Al iniciar una receta, el sistema debe comprobar que el jugador tiene al menos 100 en el valor del diccionario reserva_harina[tipo_requerido] — es decir **10 Tokens de Harina, 10 (100%)** — y restarlos.

## 1. Esquema de Datos (Data Schema)
Para la simulación, cada entidad de tipo `Receta` debe contener los siguientes atributos lógicos:
* `id` (String): Identificador único de la receta.
* `grado` (String): "Básica" o "Avanzada". (Las avanzadas suelen requerir tecnologías específicas).
* `harina_base` (String): Tipo de harina requerido (ej. "Blanca", "Centeno", "Integral"). Toda receta cuesta **10 Tokens — 10 (100%)** de ese tipo, sea cual sea; lo único que varía entre recetas es el agua.
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
* `req_tecnologico` (String / None): Mejora de laboratorio estrictamente necesaria para iniciar u hornear la receta con bonos.

---

## 2. Catálogo de Recetas (Dataset)

| ID Receta | Grado | Harina (siempre 10 tokens / 100%) | Agua — Tokens (Hidratación) | Acidez Diana (Bono) | Zona Baja | Zona Óptima | Zona Sobre | Puntos (Baja/Óptimo/Sobre) | Monedas (Baja/Óptima/Sobre) |Req. Tecnológico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pan de Campo** | Básica | Blanca | 12 (60%) | [3] (+3) | 1 - 10 | 11 - 15 | 16 - 20 | 4 / 10 / -2 | 13 / 17 / 11 | Ninguno |
| **Focaccia** | Básica | Blanca | 15 (75%) | [1, 2] (+2) | 1 - 9 | 10 - 14 | 15 - 20 | 3 / 12 / -3 | 15 / 19 / 13 | Ninguno |
| **Baguette** | Básica | Blanca | 13 (65%) | [2] (+3) | 1 - 11 | 12 - 15 | 16 - 20 | 5 / 11 / -2 | 14 / 18 / 12 | Ninguno |
| **Pizza Napolitana** | Avanzada | Blanca | 13 (62%) | [3] (+4) | 1 - 10 | 11 - 14 | 15 - 20 | 4 / 14 / -4 | 15 / 21 / 12 | Módulo Analítico |
| **Brioche** | Avanzada | Blanca | 11 (52%) | [1] (+5) | 1 - 14 | 15 - 17 | 18 - 20 | 5 / 16 / -6 | 14 / 21 / 11 | Módulo Analítico |
| **Hogaza Centeno**| Avanzada | Centeno | 14 (67%) | [4, 5] (+6) | 1 - 12 | 13 - 16 | 17 - 20 | 6 / 15 / -5 | 20 / 27 / 17 | Módulo Analítico |
| **Pan Semillas** | Avanzada | Integral | 16 (78%) | [3, 4] (+7) | 1 - 13 | 14 - 16 | 17 - 20 | 6 / 17 / -5 | 19 / 26 / 16 | Módulo Analítico |
| **Panettone** | Avanzada | Blanca | 10 (47%) | [1] (+8) | 1 - 16 | 17 - 18 | 19 - 20 | 8 / 20 / -8 | 13 / 22 / 10 | Módulo Analítico |

---

## 3. Reglas de Validación para la Simulación
* **Inicio Condicional:** Un agente no puede ejecutar la acción "Iniciar Receta" si no posee en su reserva **10 Tokens — 10 (100%)** de la harina especificada y la cantidad exacta de `tokens_agua`. Si la receta es "Avanzada", el agente también debe verificar si la variable `tecnologia_modulo_analitico` es verdadera en su estado.
* **Sello de Acidez:** Al iniciar la receta, el agente compara el nivel de Acidez actual de su cultivo base con la lista `acidez_diana`. Si el valor actual está dentro de la lista, la receta se marca internamente con un booleano `bono_sabor = True`. Si no, `bono_sabor = False`.
* **Gatillo de Colapso:** Durante la Fase III, si la posición de la masa entra en el rango definido por `zona_sobrefermentada`, el agente invoca automáticamente la función de horneado aplicando la `penalizacion_colapso`.
