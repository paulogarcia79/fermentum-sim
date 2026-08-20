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