# ARCHITECTURE & CODING STANDARDS (Fermentum Sim)
**Descripción General:** Este archivo define las reglas de arquitectura de software, patrones de diseño y estándares de código que el agente de IA debe seguir estrictamente al generar o modificar el código de la simulación en Python.

## 1. Patrones de Diseño Centrales
* **Separación de Responsabilidades (MVC/Arquitectura Limpia):** La lógica del juego (Reglas, Fases, Clima) debe estar completamente separada de los datos puros (Recetas, Eventos) y de la Interfaz/CLI.
* **Paradigma Orientado a Objetos (OOP):** Todo el sistema debe modelarse a través de clases bien definidas (`Player`, `Recipe`, `Environment`, `GameEngine`).
* **Inyección de Dependencias:** El motor principal (`GameEngine`) debe recibir a los jugadores y al entorno como parámetros o inicializarlos de forma modular, permitiendo pruebas unitarias (testing) aisladas.

## 2. Estructura de Datos y Tipado
* **Strict Type Hinting:** Todas las funciones, métodos y atributos de clase DEBEN incluir anotaciones de tipo de Python (ej. `List[str]`, `Optional[int]`, `Dict[str, bool]`).
* **Dataclasses / Pydantic:** Se recomienda encarecidamente el uso de `@dataclass` (o modelos de Pydantic) para representar entidades de datos puras e inmutables, como el catálogo de recetas (`Recipe`) o las cartas de clima (`ClimateCard`).
* **Inmutabilidad del Catálogo:** La base de datos de recetas (`RECIPE_DATABASE`) debe cargarse en memoria como una constante inmutable. Las instancias en las carpetas de los jugadores serán referencias o copias de estado.

## 3. Manejo de Errores y Validaciones
* **Excepciones Personalizadas:** No se deben usar `Exception` genéricas o simples retornos `False`. Se deben crear clases de error semánticas en un archivo `exceptions.py` (ej. `InvalidActionError`, `ResourceDeficitError`, `RuleViolationError`).
* **Validación Previa (Fail-Fast):** Todo método de acción (ej. `iniciar_receta()`) debe primero validar todas las precondiciones (PA suficientes, recursos suficientes, bloqueos de estación). Si falla, debe levantar una excepción antes de modificar cualquier estado interno.

## 4. Estructura del Proyecto Recomendada
* `models.py`: Definición de clases puras de datos (`Recipe`, `Player`, `Environment`).
* `engine.py`: Lógica de turnos, bucle de fases y validación de reglas.
* `actions.py`: Funciones o métodos de resolución para cada acción del Módulo III.
* `main.py`: Punto de entrada y CLI (Command Line Interface).
## 5. Documentación de Reglas (obligatorio en todo cambio de reglas)

Cambiar una regla del juego **no termina en el código**. Hay dos superficies documentales y las
dos son normativas:

* `context/*.md` — la **especificación**, para quien implementa.
* `RULEBOOK.md` **y** `RULEBOOK.html` (raíz del repo) — el **reglamento de jugador**, en español.
  Son las dos mitades de un mismo documento y **se mantienen a mano en paralelo: no hay ningún
  script que genere uno a partir del otro**, así que tocar solo uno deja el trabajo a medias.

**Un commit que cambia una regla y no toca los cuatro sitios está incompleto.** Cuenta como regla
cualquier cosa que un jugador notaría en la mesa: un paso de fase, el coste o efecto de una
acción, un valor de preparación, un término de puntuación, un criterio de desempate, los números
impresos de una carta, o una capacidad que desaparece. Un refactor o una tubería de servidor/web
no cuentan.

Está escrito aquí porque ya falló dos veces en silencio: el commit de «Variedad de Recetas» añadió
un séptimo término de puntuación y un criterio de desempate nuevo sin tocar el reglamento, y el de
«Ingresos de Panadería» repitió el olvido. Ningún test lee esos ficheros, y que `context/*.md` esté
al día hace que el hueco sea invisible desde el código.

Al hacerlo, no basta con las tablas: las reglas viejas sobreviven en la prosa (las fuentes de una
divisa, el resumen de fases, una referencia cruzada a una acción que ya no hace eso). Y conviene
**verificar en vez de mirar**: comparar celda a celda las 12 filas de recetas contra
`RECIPE_CATALOG` en los dos ficheros, buscar por texto la redacción de la regla superada, y en el
HTML comprobar el anidamiento de etiquetas y que cada tabla cuadre `<th>` con `<td>` (añadir una
columna en la cabecera y olvidarla en las filas es el fallo típico).

`Fermentum_ GDDv0.0.2.pdf` (raíz del repo) es **legado y NO es autoritativo**: es el documento de
diseño histórico del que salió la revisión GDD v0.0.2, es un binario que nadie puede editar y ya
contradice al código en varios puntos. Nunca se toma como fuente de verdad ni se "corrige" el
código para que encaje con él.
