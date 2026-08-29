# CORE_MECHANICS (Fermentum)
**Descripción General:** Fermentum es un Eurogame de gestión de recursos y "engine-building" para 1-4 jugadores. El objetivo central es acumular Puntos de Maestría controlando variables biológicas y térmicas.

## 1. Bucle de Juego (Día de Laboratorio)
El juego se divide en rondas llamadas "Días de Laboratorio". Cada ronda consta de tres fases secuenciales y estrictas:
1. **Fase I: Ambiente** 
2. **Fase II: Acción** 
3. **Fase III: Fermentación** 

---

## 2. Resolución de Fases

### FASE I: Ambiente (Preparación y Clima)
Liderada por el Investigador Jefe, esta fase configura las variables globales del turno:
* **Actualización de Jerarquía:** El token de Investigador Jefe se asigna al jugador con el nivel de Vitalidad más alto en su frasco (cultivo base). 
    * *Desempate:* Mayor cantidad de Datos de Investigación.
    * *Ventaja:* El Investigador Jefe actúa primero en la Fase II y tiene prioridad en los mercados.
    * *Excepción Día 1:* En la primera ronda, el orden se determina por la Iniciativa de la Carta de Patrocinio de cada jugador (ver PLAYER_STATE.md §2), no por Vitalidad — a partir del Día 2 rige la regla estándar de este párrafo.
* **Resolución del Clima:** Se revela una carta del mazo de Clima. **(CRÍTICO PARA LA CLI: El sistema debe anunciar/imprimir en pantalla claramente el nombre de la carta, su modificador térmico y su efecto pasivo para que los jugadores puedan tomar decisiones).**
    * Se ajusta el termómetro en el tablero sumando o restando el Modificador Térmico a la base de 20°C.
    * Se sincroniza el "Ábaco de Fermentación" (20°C = 4 Pasos; 25°C = 5 Pasos; 30°C = 6 Pasos).
    * Se aplican Anomalías Biológicas instantáneamente (ej. +1 Vitalidad para todos) o Efectos Pasivos.
* **Mercado de Tendencias (anuncio):** Se revela una carta del mazo de Tendencias de Mercado (21 cartas: -2×1, -1×7, 0×5, +1×7, +2×1) y queda a la vista de todos durante el día. **Este paso no mueve ningún visor:** la carta es un pronóstico y se aplica al final de este mismo día (ver Fase III), por lo que rige los precios del día SIGUIENTE. Los precios de hoy son los que dejó la tendencia de ayer, ya conocidos cuando los jugadores deciden comprar o vender.
* **Protocolo de Refresco (reabastecimiento):** Recetas — se compactan las cartas supervivientes conservando su orden (más nueva → más antigua) y se revelan cartas nuevas a la izquierda hasta volver a tener 4 recetas visibles, rellenando tanto los huecos dejados por la Acción G del día anterior como el que dejó el descarte de fin de día (ver Fase III). Si el mazo se agota, se baraja el descarte como nuevo mazo. **Este paso ya no descarta ninguna carta** — el descarte de la más antigua se movió al final de la Fase III.

### FASE II: Acción (Operatividad)
Fase donde los jugadores intervienen en su laboratorio mediante un sistema de "Round-Robin" (turnos alternos).
* **Capacidad:** Cada jugador dispone de 2 PA.
* **Flujo Intercalado:** Empezando por el Investigador Jefe, el jugador activo ejecuta **solo 1 acción** (o pasa). Luego el control pasa al siguiente jugador. El ciclo (while loop) continúa hasta que la suma de PA de todos los jugadores sea 0 y nadie quiera usar "Horas Extras".
* **Registro:** Se marca el uso de PA moviendo Cubos de Laboratorio en la Zona 5 (Checklist) del tablero personal.
* **Un espacio, una visita por día:** cada espacio de acción con costo de PA (Acciones B a G, Simposio Técnico, H, I — ver ACTIONS_REGISTRY.md §1) solo puede ser visitado UNA vez por Día de Laboratorio por cada jugador; visitarlo lo marca con el color de ese jugador (bloqueado para él, no para el resto) hasta el reinicio del siguiente Día de Laboratorio. Pedido de Urgencia (0 PA) queda exento.
* **Escasez de Mercado:** Durante esta fase, si un jugador investiga una receta (Acción G), el espacio del mercado queda vacío hasta la próxima Fase I. La harina y el agua, en cambio, ya no son un slot consumible — son un track de precio compartido (Bolsa de Harinas) y una matriz de precio por temperatura (Suministro Hídrico Global) que cualquier jugador puede usar en Visitar el Mercado (Acción C) sin agotar un cupo.

### FASE III: Fermentación (Resolución Automática)
Ocurre simultáneamente para todos una vez terminada la Fase II.
* **Cinética Biológica (Avance de Masas):** Las masas en la Zona 2 avanzan en sus tracks según la siguiente ecuación:
    > `Avance Final = (Temperatura Ambiental / 5) + (Valor del Dado de Inóculo) + (Modificadores de Tecnología)` 
* **Colapso Estructural:** Si el avance hace que una masa supere la zona óptima de horneado (llegando a sobre-fermentación), la masa colapsa. 
    * *Resolución:* Se hornea automáticamente (Costo: 0 PA), aplicando los puntos negativos de la carta.
* **Metabolismo (Desgaste):** La Vitalidad del cultivo base (Zona 1) se reduce automáticamente en -1 punto. (Nota: Los valores de Vitalidad y Acidez nunca pueden bajar de 0 ).
* **Rotación del Mercado (fin de día):** Se descarta la receta visible más antigua del Mercado Central (la carta real más a la derecha; si ese extremo ya está vacío por una Acción G, se descarta la siguiente carta real hacia la izquierda). El hueco resultante lo rellena el Protocolo de Refresco de la Fase I del día siguiente.
* **Mercado de Tendencias (aplicación):** Se cobra ahora la carta anunciada esta mañana (ver Fase I): su modificador desplaza simultáneamente los 3 visores de la Bolsa de Harinas (Blanca/Integral/Centeno), cada uno con tope independiente en [1, 5] (sin arrastre más allá del límite). Los precios resultantes son los que regirán el día siguiente. La carta pasa entonces al descarte de Tendencias; si el mazo se agota, se baraja ese descarte como mazo nuevo.

---

## 3. Fin del Juego y Puntuación

### Gatillos de Finalización
El final del juego se desencadena de inmediato si ocurre una de estas dos condiciones:
1. El mazo de Clima se agota por completo.
2. Un jugador hornea exitosamente su **quinta (5ta) receta** (las recetas colapsadas con valor negativo no cuentan).
*Una vez desencadenado, se termina el Día de Laboratorio en curso y se puntúa.*

### Cálculo de Puntos de Maestría Finales
1. **Puntos Base:** Suma de los puntos de todas las recetas horneadas (positivos y negativos).
2. **Puntos de Sabor:** Suma de los bonos de Acidez impresos en las cartas que tengan un Cubo de Laboratorio sellado.
3. **Madurez del Cultivo:** `(Vitalidad Actual + Acidez Actual) / 2` (redondeando hacia arriba).
4. **Desperdicio (Penalización):** -1 punto de Maestría por cada 3 **tokens de insumo** sin utilizar en la reserva. Un **Token de Harina (10%)** y un **Token de Agua (5%)** cuentan **1:1** aquí, pese a representar porcentajes distintos: se suman en un único total (`sum(reserva_harina) / 10 + reserva_agua`) y de ahí sale la división entera por 3. Esta es la única regla del juego que suma los dos insumos, y es la que fija el 10% como unidad atómica de la harina — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)".
5. **Conversión de Riqueza:** +1 punto de Maestría por cada 5 Monedas restantes en la reserva final (división entera).

### Desempate
En caso de empate en Puntos de Maestría, el ganador se determina por:
1. El investigador con el mayor Nivel de Vitalidad en su cultivo base.
2. Si persiste el empate, el jugador con más Datos de Investigación.