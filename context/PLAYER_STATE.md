# PLAYER_STATE (Fermentum)
**Descripción General:** Este archivo define la estructura de datos, el inventario y los límites físicos del tablero individual de cada jugador. Representa el estado del laboratorio y de la biomasa bajo el control del investigador.

## 1. Esquema de Datos (Data Schema de la Clase Player)
Para la simulación, cada instancia de `Jugador` debe inicializarse y gestionar los siguientes atributos de estado:

### Atributos Biológicos (Zona 1: Cultivo Base / Masa Madre)
* `vitalidad` (Integer): Nivel de actividad de la levadura. Límite: Mínimo 0, Máximo 6.
* `acidez` (Integer): Perfil de ácido láctico/acético. Límite: Mínimo 0, Máximo 6. Es **bidireccional**: la única forma voluntaria de moverla, en cualquiera de los dos sentidos, es la acción **Descarte** (0 PA, ocupa espacio, 1 vez por día — ver ACTIONS_REGISTRY.md). La Acción A ya no la toca. Las otras dos fuentes son la carta de clima «Acidificación Acelerada» (+1 a todos) y los Protocolos H/I, que la fijan en 1 y 2 respectivamente pero exigen Contaminación activa.

### Unidades de Insumo (Tokens)

Los dos insumos físicos del juego se cuentan en **tokens**. Lo único que cambia entre ellos es cuánto vale un token:

| Insumo | 1 token equivale a | Unidad de compra habitual |
|---|---|---|
| **Harina** | **10%** | 1 bolsa = 100% = **10 tokens**; media bolsa = **5 (50%)** |
| **Agua** | **5%** de hidratación | lote del 100% = **20 tokens** |

**Notación canónica** en estos documentos y en la interfaz: **`N (P%)`** — primero el número de tokens, después su porcentaje. Ej.: `10 (100%)` de harina, `20 (100%)` de agua, `2 (10%)` de agua.

Ambos tipos de token cuentan **1:1** en la penalización por desperdicio del final de partida (-1 Punto de Maestría por cada 3 tokens de insumo sin usar — CORE_MECHANICS.md §3.4): un token de harina del 10% y uno de agua del 5% valen exactamente lo mismo a esos efectos. Esa regla es la razón de que la unidad atómica de la harina sea el 10% y no la bolsa entera.

*Nota de implementación:* el código guarda cada insumo en la unidad que le resultó cómoda — `reserva_agua` ya es un conteo de tokens, mientras que `reserva_harina` son porcentajes en múltiplos de 10. La conversión es exacta en ambos sentidos y no hay pérdida de información.

### Atributos Operativos y Económicos
* `puntos_accion` (Integer): PA disponibles en el turno actual. (Máximo 2, se reinician en cada Fase II. Puede subir a 3 temporalmente usando "Horas Extras").
* `datos_investigacion` (Integer): Moneda técnica para comprar mejoras de laboratorio, PA extra (Horas Extras) y Pedidos de Urgencia. Distinta de `monedas` (la divisa comercial).
* `monedas` (Integer): Divisa comercial del juego (GDD v0.0.2). Se gana al hornear y vender (Acción F) y se gasta en Visitar el Mercado (Acción C) para comprar harina/agua.
* `reserva_harina` (Dict[String, Integer]): Inventario de harinas. Se almacena en porcentajes (múltiplos de 10%), donde **cada 10% es 1 Token de Harina**: 100% = 10 tokens = una bolsa entera. Ej: `{"Blanca": 100, "Centeno": 20, "Integral": 0}` = 10 (100%) de Blanca, 2 (20%) de Centeno, 0 de Integral.
* `contrato_molino` (Optional[String]): Tipo de harina del **Contrato con el Molino** firmado por este jugador (`"Blanca"`, `"Centeno"` o `"Integral"`), o `None` si no ha firmado ninguno. Uno por partida, permanente, sin cambio ni cancelación: se firma en la Acción C y entrega **2 (20%)** de esa harina en cada Fase III. Usa deliberadamente las mismas claves que `reserva_harina`, para que la entrega nocturna sea `reserva_harina[contrato_molino] += 20` sin traducción de por medio. Es un campo y no un derivado: el contrato es una decisión del jugador que nada más en el estado permite reconstruir.
* `reserva_agua` (Integer): Conteo total de **Tokens de Agua** disponibles. **Cada token = 5% de hidratación**, así que 20 tokens = 100%. A diferencia de `reserva_harina`, este campo ya está expresado en tokens, no en porcentaje.
* `accion_alimentar_usada` (Boolean): Bandera que se reinicia a `False` al inicio de cada Fase II para limitar el mantenimiento a 1 vez por ronda.
* `horas_extras_usadas` (Boolean): Bandera que se reinicia a `False` al inicio de cada Fase II (junto con `puntos_accion`) para limitar la acción auxiliar "Horas Extras" a 1 vez por día.
* `acciones_pa_usadas_hoy` (List[String]): Ids de espacios de acción con costo de PA (B, C, D, E, F, G, H, I, "simposio") ya visitados este Día de Laboratorio por este jugador — cada espacio solo puede visitarse una vez por día (ACTIONS_REGISTRY.md §1). Se llena al gastar el PA de la acción y se reinicia a `[]` al inicio de cada Fase II, junto con `accion_alimentar_usada`. Pedido de Urgencia (0 PA) y las acciones gratuitas (Alimentar, Horas Extras) no participan de esta lista — tienen sus propias banderas dedicadas. `"jefatura"` sí entra en la lista (gasta PA y ocupa el espacio del jugador), pero su límite real es **global** y vive en el motor (`GameEngine.jefatura_reclamada_por`): un solo jugador de la mesa puede reclamarla cada día.

### Atributos de Infraestructura
* `tecnologias_activas` (Dict[String, Boolean]): Registro de módulos de la Zona 4.
    * `incubadora`: True/False.
    * `camara_B`: True/False.
    * `modulo_analitico`: True/False.
    * `criopreservacion`: True/False.
    * `comerciante`: True/False.
* `estaciones_fermentacion` (List[Dict o None]): Representa las 3 ranuras de la Zona 2. 
    * El índice 0 y 1 están siempre disponibles. 
    * El índice 2 (Estación 03) está bloqueado por defecto y requiere `camara_B == True` para utilizarse.
* `dados_inoculo` (Integer): Cantidad de dados físicos disponibles para iniciar masas. (Máximo 3).

### Atributos de Archivo (Cartas)
* `carpeta_proyectos` (List[Receta]): Recetas investigadas pendientes de iniciar. Límite estricto: Máximo 3 cartas.
* `archivo_horneado_exitoso` (List[Receta]): Recetas completadas con puntaje positivo. (Gatillo de fin de juego).
* `archivo_colapsos` (List[Receta]): Recetas sobre-fermentadas retiradas por emergencia con puntaje negativo.

---

## 2. Preparación Inicial del Jugador (Cartas de Patrocinio)
Al iniciar la simulación (Día 1), el setup baraja el mazo de 8 Cartas de Patrocinio (GDD v0.0.2, Módulo I §6.4 / Anexo B) y reparte 1 carta a cada jugador sentado (1 a 4 jugadores), reveladas simultáneamente. El jugador con el número de Iniciativa más bajo en su carta recibe el token de Investigador Jefe y actúa primero en el Día 1; los demás se ordenan ascendentemente según su número.

* **Reglas base para todos:** `vitalidad` = **2** (`models.VITALIDAD_INICIAL`), `acidez` = 1, `dados_inoculo` = 3, `puntos_accion` = 0, se entrega 1 Receta "Básica" aleatoria, y `tecnologias_activas` inician en `False`. `datos_investigacion` **ya no es 0 para todos**: lo fija la Carta de Patrocinio (ver tabla abajo).

  La Vitalidad inicial es 2 y no 1 por una razón concreta: el desgaste de la Fase III resta -1 y la Acción A repone +1 una vez al día, así que un jugador que alimenta a diario **orbita en su valor inicial**. Partiendo de 1, la carta «Aletargamiento Invernal» (-2, dos copias en un mazo de 30) lo dejaba en 0 → contaminación inevitable, sin jugada posible que la evitara: no era una decisión mal tomada, era el barajado. Partiendo de 2 la misma carta lo deja en 1, y la contaminación vuelve a castigar lo que debe castigar, que es descuidar el mantenimiento. Ver CLIMATE_LOGIC.md.
* **Asignación según Carta de Patrocinio** (`reserva_harina`, `reserva_agua`, `monedas` y `datos_investigacion` provienen íntegramente de la carta repartida a ese jugador; tras el despliegue de insumos las cartas vuelven a la caja):

  | Iniciativa | Harina — Tokens (%) | Agua — Tokens (%) | Monedas Iniciales | Datos Iniciales |
  |---|---|---|---|---|
  | 1 | 10 (100%) Blanca | 2 (10%) | 9 | 0 |
  | 2 | 10 (100%) Blanca | 6 (30%) | 8 | 0 |
  | 3 | 10 (100%) Blanca | 12 (60%) | 6 | 1 |
  | 4 | 10 (100%) Integral | 6 (30%) | 8 | 0 |
  | 5 | 10 (100%) Integral | 12 (60%) | 6 | 1 |
  | 6 | 10 (100%) Centeno | 6 (30%) | 8 | 0 |
  | 7 | 10 (100%) Centeno | 12 (60%) | 6 | 1 |
  | 8 | 20 (200%) Blanca | 20 (100%) | 4 | 2 |

  Los jugadores que reciben números de Iniciativa altos (actúan más tarde en la primera ronda) son compensados con un capital de insumos de mayor valor para equilibrar la ventaja temporal del Investigador Jefe.

  Los **Datos Iniciales** van en sentido inverso a las Monedas de la carta (el patrocinador tacaño compensa con conocimiento). Existen porque el Simposio Técnico dejó de ser una fuente barata de Datos: ahora exige sacrificar un horneado del Archivo (ver ACTIONS_REGISTRY.md §Simposio), así que sin ellos no habría ningún Dato en la mesa hasta el primer horneado en Zona Óptima — y con ello ni Horas Extras, ni Pedido de Urgencia, ni mejoras de laboratorio, ni Protocolo I.

---

## 3. Reglas de Validación de Estado (Validations)
El sistema debe comprobar constantemente estas restricciones antes de permitir que un agente ejecute una acción:

* **Límites Biológicos:** Al sumar o restar `vitalidad` o `acidez`, el sistema debe aplicar `max(0, min(6, nuevo_valor))`.
* **Penalización por Vitalidad 0:** Si al inicio o durante el turno de un jugador, su `vitalidad` llega a 0, se le marca una penalización de -3 Puntos de Maestría al final del juego y queda en estado de "Contaminación" hasta que ejecute un Protocolo de Emergencia (Recultivo Manual o Inóculo de Emergencia).
* **Bloqueo de Estación:** Si un agente intenta usar la Acción B (Iniciar Receta) y las estaciones 01 y 02 están ocupadas, la acción debe ser rechazada (False) a menos que la `camara_B` sea True.
* **Gatillo de Fin de Partida:** Al finalizar la Acción F (Hornear y Vender) de cualquier jugador, el entorno debe evaluar: `if len(archivo_horneado_exitoso) >= 5: trigger_endgame()`. 
    * *Nota:* El tamaño de `archivo_colapsos` no afecta el gatillo de fin de juego.