# RECIPE_DATABASE (Fermentum)
**Descripción General:** Este archivo contiene el catálogo maestro de los protocolos de panificación (recetas). Define los parámetros matemáticos, requerimientos de insumos y los rangos de las zonas de fermentación para el cálculo de colapsos y puntuaciones.
**Nota Aclaratoria** Inicio Condicional: Al iniciar una receta, el sistema debe comprobar que el jugador tiene al menos 100 en el valor del diccionario reserva_harina[tipo_requerido] y restarlos.

## 1. Esquema de Datos (Data Schema)
Para la simulación, cada entidad de tipo `Receta` debe contener los siguientes atributos lógicos:
* `id` (String): Identificador único de la receta.
* `grado` (String): "Básica" o "Avanzada". (Las avanzadas suelen requerir tecnologías específicas).
* `harina_base` (String): Tipo de token de harina requerido (ej. "Blanca", "Centeno", "Integral").
* `hidratacion_pct` (Integer): Porcentaje total de hidratación.
* `tokens_agua` (Integer): Cantidad de tokens de agua del 5% requeridos (ej. 60% / 5% = 12 tokens).
* `acidez_diana` (List[int]): Rango de niveles de Acidez que otorgan el Bono de Sabor al iniciar la receta.
* `zona_baja` (Tuple[int, int]): Rango del track donde la masa está cruda (otorga pocos puntos y 0 Datos).
* `zona_optima` (Tuple[int, int]): Rango del track objetivo (otorga puntos máximos, Datos extra en el centro exacto).
* `zona_sobrefermentada` (Tuple[int, int]): Rango del track donde la masa colapsa automáticamente.
* `puntos_optimos` (Integer): Puntos de Maestría otorgados si se hornea en la zona óptima.
* `penalizacion_colapso` (Integer): Puntos de Maestría negativos aplicados en horneado de emergencia (o si se hornea manual en esa zona).
* `req_tecnologico` (String / None): Mejora de laboratorio estrictamente necesaria para iniciar u hornear la receta con bonos.

---

## 2. Catálogo de Recetas (Dataset)

| ID Receta | Grado | Harina | Hidratación (Tokens) | Acidez Diana | Zona Baja | Zona Óptima | Zona Sobre | Puntos (Óptimo) | Penalización | Req. Tecnológico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pan de Campo** | Básica | Blanca | 60% (12 tokens) | [3] | 1 - 11 | 12 - 14 | 15 - 20 | 10 pts | -2 pts | Ninguno |
| **Focaccia** | Básica | Blanca | 75% (15 tokens) | [1, 2] | 1 - 9 | 10 - 14 | 15 - 20 | 12 pts | -3 pts | Ninguno |
| **Baguette** | Básica | Blanca | 65% (13 tokens) | [2] | 1 - 13 | 14 - 15 | 16 - 20 | 11 pts | -2 pts | Ninguno |
| **Pizza Napolitana** | Avanzada | Blanca | 62% (13 tokens) | [3] | 1 - 10 | 11 - 13 | 14 - 20 | 14 pts | -4 pts | Módulo Analítico |
| **Brioche** | Avanzada | Blanca | 52% (11 tokens) | [1] | 1 - 16 | 17 - 18 | 19 - 20 | 16 pts | -6 pts | Módulo Analítico |
| **Hogaza Centeno**| Avanzada | Centeno | 67% (14 tokens) | [4, 5] | 1 - 14 | 15 - 18 | 19 - 20 | 15 pts | -5 pts | Módulo Analítico |
| **Pan Semillas** | Avanzada | Integral | 78% (16 tokens) | [3, 4] | 1 - 12 | 13 - 15 | 16 - 20 | 17 pts | -5 pts | Módulo Analítico |
| **Panettone** | Avanzada | Blanca | 47% (10 tokens) | [1] | 1 - 17 | 18 - 19 | 20 | 20 pts | -8 pts | Módulo Analítico |

---

## 3. Reglas de Validación para la Simulación
* **Inicio Condicional:** Un agente no puede ejecutar la acción "Iniciar Receta" si no posee en su reserva el token de harina especificado y la cantidad exacta de `tokens_agua`. Si la receta es "Avanzada", el agente también debe verificar si la variable `tecnologia_modulo_analitico` es verdadera en su estado.
* **Sello de Acidez:** Al iniciar la receta, el agente compara el nivel de Acidez actual de su cultivo base con la lista `acidez_diana`. Si el valor actual está dentro de la lista, la receta se marca internamente con un booleano `bono_sabor = True`. Si no, `bono_sabor = False`.
* **Gatillo de Colapso:** Durante la Fase III, si la posición de la masa entra en el rango definido por `zona_sobrefermentada`, el agente invoca automáticamente la función de horneado aplicando la `penalizacion_colapso`.
