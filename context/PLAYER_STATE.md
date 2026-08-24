# PLAYER_STATE (Fermentum)
**Descripción General:** Este archivo define la estructura de datos, el inventario y los límites físicos del tablero individual de cada jugador. Representa el estado del laboratorio y de la biomasa bajo el control del investigador.

## 1. Esquema de Datos (Data Schema de la Clase Player)
Para la simulación, cada instancia de `Jugador` debe inicializarse y gestionar los siguientes atributos de estado:

### Atributos Biológicos (Zona 1: Cultivo Base / Masa Madre)
* `vitalidad` (Integer): Nivel de actividad de la levadura. Límite: Mínimo 0, Máximo 6.
* `acidez` (Integer): Perfil de ácido láctico/acético. Límite: Mínimo 0, Máximo 6.

### Atributos Operativos y Económicos
* `puntos_accion` (Integer): PA disponibles en el turno actual. (Máximo 2, se reinician en cada Fase II. Puede subir a 3 temporalmente usando "Horas Extras").
* `datos_investigacion` (Integer): Moneda técnica para comprar mejoras de laboratorio, PA extra (Horas Extras) y Pedidos de Urgencia. Distinta de `monedas` (la divisa comercial).
* `monedas` (Integer): Divisa comercial del juego (GDD v0.0.2). Se gana al hornear y vender (Acción F) y se gasta en Visitar el Mercado (Acción C) para comprar harina/agua.
* `reserva_harina` (Dict[String, Integer]): Inventario de harinas representadas en porcentajes (múltiplos de 10%). Ej: `{"Blanca": 100, "Centeno": 20, "Integral": 0}`.
* `reserva_agua` (Integer): Suma total de los tokens de hidratación disponibles (en múltiplos de 5%).
* `accion_alimentar_usada` (Boolean): Bandera que se reinicia a `False` al inicio de cada Fase II para limitar el mantenimiento a 1 vez por ronda.
* `horas_extras_usadas` (Boolean): Bandera que se reinicia a `False` al inicio de cada Fase II (junto con `puntos_accion`) para limitar la acción auxiliar "Horas Extras" a 1 vez por día.
* `acciones_pa_usadas_hoy` (List[String]): Ids de espacios de acción con costo de PA (B, C, D, E, F, G, H, I, "simposio") ya visitados este Día de Laboratorio por este jugador — cada espacio solo puede visitarse una vez por día (ACTIONS_REGISTRY.md §1). Se llena al gastar el PA de la acción y se reinicia a `[]` al inicio de cada Fase II, junto con `accion_alimentar_usada`. Pedido de Urgencia (0 PA) y las acciones gratuitas (Alimentar, Horas Extras) no participan de esta lista — tienen sus propias banderas dedicadas.

### Atributos de Infraestructura
* `tecnologias_activas` (Dict[String, Boolean]): Registro de módulos de la Zona 4.
    * `incubadora`: True/False.
    * `camara_B`: True/False.
    * `modulo_analitico`: True/False.
    * `criopreservacion`: True/False.
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

* **Reglas base para todos:** `vitalidad` = 1, `acidez` = 1, `dados_inoculo` = 3, `puntos_accion` = 0, `datos_investigacion` = 0, se entrega 1 Receta "Básica" aleatoria, y `tecnologias_activas` inician en `False`.
* **Asignación según Carta de Patrocinio** (`reserva_harina`, `reserva_agua` y `monedas` provienen íntegramente de la carta repartida a ese jugador; tras el despliegue de insumos las cartas vuelven a la caja):

  | Iniciativa | Harina | Lote de Agua | Monedas Iniciales |
  |---|---|---|---|
  | 1 | 1x Blanca | 2x (10%) | 9 |
  | 2 | 1x Blanca | 6x (30%) | 8 |
  | 3 | 1x Blanca | 12x (60%) | 6 |
  | 4 | 1x Integral | 6x (30%) | 8 |
  | 5 | 1x Integral | 12x (60%) | 6 |
  | 6 | 1x Centeno | 6x (30%) | 8 |
  | 7 | 1x Centeno | 12x (60%) | 6 |
  | 8 | 2x Blanca | 20x (100%) | 4 |

  Los jugadores que reciben números de Iniciativa altos (actúan más tarde en la primera ronda) son compensados con un capital de insumos de mayor valor para equilibrar la ventaja temporal del Investigador Jefe.

---

## 3. Reglas de Validación de Estado (Validations)
El sistema debe comprobar constantemente estas restricciones antes de permitir que un agente ejecute una acción:

* **Límites Biológicos:** Al sumar o restar `vitalidad` o `acidez`, el sistema debe aplicar `max(0, min(6, nuevo_valor))`.
* **Penalización por Vitalidad 0:** Si al inicio o durante el turno de un jugador, su `vitalidad` llega a 0, se le marca una penalización de -3 Puntos de Maestría al final del juego y queda en estado de "Contaminación" hasta que ejecute un Protocolo de Emergencia (Recultivo Manual o Inóculo de Emergencia).
* **Bloqueo de Estación:** Si un agente intenta usar la Acción B (Iniciar Receta) y las estaciones 01 y 02 están ocupadas, la acción debe ser rechazada (False) a menos que la `camara_B` sea True.
* **Gatillo de Fin de Partida:** Al finalizar la Acción F (Hornear y Vender) de cualquier jugador, el entorno debe evaluar: `if len(archivo_horneado_exitoso) >= 5: trigger_endgame()`. 
    * *Nota:* El tamaño de `archivo_colapsos` no afecta el gatillo de fin de juego.