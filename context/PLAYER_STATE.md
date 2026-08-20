# PLAYER_STATE (Fermentum)
**Descripción General:** Este archivo define la estructura de datos, el inventario y los límites físicos del tablero individual de cada jugador. Representa el estado del laboratorio y de la biomasa bajo el control del investigador.

## 1. Esquema de Datos (Data Schema de la Clase Player)
Para la simulación, cada instancia de `Jugador` debe inicializarse y gestionar los siguientes atributos de estado:

### Atributos Biológicos (Zona 1: Cultivo Base / Masa Madre)
* `vitalidad` (Integer): Nivel de actividad de la levadura. Límite: Mínimo 0, Máximo 6.
* `acidez` (Integer): Perfil de ácido láctico/acético. Límite: Mínimo 0, Máximo 6.

### Atributos Operativos y Económicos
* `puntos_accion` (Integer): PA disponibles en el turno actual. (Máximo 2, se reinician en cada Fase II. Puede subir a 3 temporalmente usando "Horas Extras").
* `datos_investigacion` (Integer): Moneda virtual para comprar mejoras y PA extra.
* `reserva_harina` (Dict[String, Integer]): Inventario de harinas representadas en porcentajes (múltiplos de 10%). Ej: `{"Blanca": 100, "Centeno": 20, "Integral": 0}`.
* `reserva_agua` (Integer): Suma total de los tokens de hidratación disponibles (en múltiplos de 5%).
* `accion_alimentar_usada` (Boolean): Bandera que se reinicia a `False` al inicio de cada Fase II para limitar el mantenimiento a 1 vez por ronda.

### Atributos de Infraestructura
* `tecnologias_activas` (Dict[String, Boolean]): Registro de módulos de la Zona 4.
    * `incubadora`: True/False.
    * `camara_B`: True/False.
    * `modulo_analitico`: True/False.
* `estaciones_fermentacion` (List[Dict o None]): Representa las 3 ranuras de la Zona 2. 
    * El índice 0 y 1 están siempre disponibles. 
    * El índice 2 (Estación 03) está bloqueado por defecto y requiere `camara_B == True` para utilizarse.
* `dados_inoculo` (Integer): Cantidad de dados físicos disponibles para iniciar masas. (Máximo 3).

### Atributos de Archivo (Cartas)
* `carpeta_proyectos` (List[Receta]): Recetas investigadas pendientes de iniciar. Límite estricto: Máximo 3 cartas.
* `archivo_horneado_exitoso` (List[Receta]): Recetas completadas con puntaje positivo. (Gatillo de fin de juego).
* `archivo_colapsos` (List[Receta]): Recetas sobre-fermentadas retiradas por emergencia con puntaje negativo.

---

## 2. Preparación Inicial del Jugador (Setup Asimétrico)
Al iniciar la simulación (Día 1), la función de inicialización debe recibir el índice del jugador (orden de turno, de 1 a 4) y asignar los recursos iniciales de forma asimétrica para balancear la ventaja del jugador inicial:

* **Reglas base para todos:** `vitalidad` = 1, `acidez` = 1, `dados_inoculo` = 3, `puntos_accion` = 0, se entrega 1 Receta "Básica" aleatoria, y `tecnologias_activas` inician en `False`.
* **Asignación Asimétrica según Índice:**
    * **Jugador 1 (Índice 0):** `reserva_harina` = {"Blanca": 100, "Centeno": 0, "Integral": 0}, `reserva_agua` = 0 (0%), `datos_investigacion` = 1.
    * **Jugador 2 (Índice 1):** `reserva_harina` = {"Blanca": 100, "Centeno": 0, "Integral": 0}, `reserva_agua` = 10 (50%), `datos_investigacion` = 1.
    * **Jugador 3 (Índice 2):** `reserva_harina` = {"Blanca": 100, "Centeno": 0, "Integral": 0}, `reserva_agua` = 20 (100%), `datos_investigacion` = 1.
    * **Jugador 4 (Índice 3):** `reserva_harina` = {"Blanca": 100, "Centeno": 0, "Integral": 0}, `reserva_agua` = 20 (100%), `datos_investigacion` = 2.

---

## 3. Reglas de Validación de Estado (Validations)
El sistema debe comprobar constantemente estas restricciones antes de permitir que un agente ejecute una acción:

* **Límites Biológicos:** Al sumar o restar `vitalidad` o `acidez`, el sistema debe aplicar `max(0, min(6, nuevo_valor))`.
* **Penalización por Vitalidad 0:** Si al inicio o durante el turno de un jugador, su `vitalidad` llega a 0, se le marca una penalización de -3 Puntos de Maestría al final del juego y queda en estado de "Contaminación" hasta que ejecute un Protocolo de Emergencia (Recultivo Manual o Inóculo de Emergencia).
* **Bloqueo de Estación:** Si un agente intenta usar la Acción B (Iniciar Receta) y las estaciones 01 y 02 están ocupadas, la acción debe ser rechazada (False) a menos que la `camara_B` sea True.
* **Gatillo de Fin de Partida:** Al finalizar la Acción F (Hornear) de cualquier jugador, el entorno debe evaluar: `if len(archivo_horneado_exitoso) >= 5: trigger_endgame()`. 
    * *Nota:* El tamaño de `archivo_colapsos` no afecta el gatillo de fin de juego.