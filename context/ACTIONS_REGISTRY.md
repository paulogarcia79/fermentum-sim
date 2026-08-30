# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación. **Un Token de Harina = 10%; un Token de Agua = 5% de hidratación** — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)" para la notación `N (P%)` usada en todo este registro.
* **Un espacio de acción, una visita por día:** cada espacio de acción (B a G, Simposio Técnico, H, I y también E, que no cuesta PA pero sí ocupa espacio) solo puede visitarse UNA vez por Día de Laboratorio, por jugador — un peón de investigador marca el espacio con su color en cuanto lo visita, bloqueándolo para él (no para el resto de jugadores) hasta el día siguiente. Con 2-3 PA (Horas Extras incluida) esto significa: como máximo un uso de cada espacio distinto por día, nunca el mismo espacio dos veces. El tope es una propiedad **del espacio**, no del coste: la Acción E lo conserva aunque se pague en Monedas. Las excepciones son Acción A y Horas Extras (que se limitan con su propio marcador de "ya usada", no con un espacio) y Pedido de Urgencia, sin límite alguno: se autolimita por Datos de Investigación.

---

## 2. Catálogo de Acciones Principales (Costo: 1 PA)
*(Nota: La Acción A original se mueve a auxiliares. La Acción B resta 100 unidades en total — es decir 10 Tokens de Harina, el 100%, una bolsa entera — repartidas entre las harinas que la carta imprima).*

### B. Iniciar Receta
* **Costo:** 1 PA + **10 Tokens de Harina — 10 (100%) en total, una bolsa entera** + los **Tokens de Agua** exactos que la receta imprima (ver RECIPE_DATABASE.md; cada token = 5% de hidratación).
    * El reparto de esa bolsa lo dicta el **grado** de la receta, que a su vez lo dicta lo que la carta imprime (RECIPE_DATABASE.md §4): **Básica** = 10 Tokens de Blanca; **Intermedia** = 5 Tokens — 5 (50%), media bolsa — de cada una de dos harinas distintas; **Avanzada** = 10 Tokens de una harina especial (Centeno o Integral).
    * Se exigen **todas** las harinas impresas: con una Intermedia, tener una de las dos mitades no basta y el rechazo nombra las dos.
* **Requisito tecnológico:** Ninguno. **Ninguna receta está restringida por tecnología** — una Avanzada de centeno puro es iniciable desde el Día 1 si se paga. El freno es el precio de adquisición (Acción G) más el coste en insumos, no una mejora de laboratorio.
* **Límite:** 1 vez por día (por espacio de acción — ver §1).
* **Memoria Biológica:** Se sella el Dado de Inóculo (con la Vitalidad actual) y el Cubo de Laboratorio (con la Acidez actual) en la carta de receta.
* **Condición:** El Cubo de Acidez solo se sella si la acidez del cultivo base se encuentra dentro del rango con bonificación de sabor exigido por la receta.

### C. Visitar el Mercado
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1); todas las transacciones de la visita (compras y ventas) se resuelven en una sola visita.
* **Efecto:** El Mercado de Insumos donde se comercian los diferentes insumos del juego: comprar o vender harina, y adquirir agua para completar los insumos requeridos por las recetas.
    * *Comprar Harina:* Pagar el coste visible de Compra (en Monedas, según la posición actual del visor en la Bolsa de Harinas), recibir **10 Tokens — 10 (100%), una bolsa entera** y mover el visor 1 casilla a la derecha (tope en posición 5).
    * *Vender Harina:* Entregar **10 Tokens — 10 (100%), una bolsa entera**, cobrar el valor visible de Venta en Monedas y mover el visor 1 casilla a la izquierda (tope en posición 1).
    * *Media Bolsa:* Tanto comprar como vender admiten media bolsa — **5 Tokens — 5 (50%)**. El precio es la mitad del visible, **redondeando hacia ARRIBA al comprar y hacia ABAJO al vender** (⌈compra/2⌉, ⌊venta/2⌋), de modo que con precios impares media bolsa nunca sale a mejor precio por token que una entera: es liquidez, no descuento. Una venta que redondea a 0 Monedas (Blanca en posición 1) es legal — se entrega media bolsa a cambio de mover el visor. **El visor se mueve 1 casilla igual que con una bolsa entera**: una transacción es una señal de mercado, sin importar su tamaño. No se opera por debajo de la media bolsa: no se pueden comprar ni vender tokens sueltos.
    * *Comprar Lote de Agua:* Pagar el coste en Monedas según la fila de temperatura actual y recibir el lote completo en Tokens de Agua (1 token = 5% de hidratación). Los cuatro lotes son **2 (10%), 6 (30%), 12 (60%) y 20 (100%)**.
* **Regla de Exclusividad:** una visita (1 PA) puede incluir como máximo UNA transacción por tipo de recurso — comprar Blanca y vender Centeno y comprar un lote de agua en la misma visita está permitido; comprar o vender el mismo tipo dos veces en la misma visita no lo está.
* **Tablas de precio** (posición del visor 1-5 → Monedas). Cada celda es `Compra/Venta`, y entre paréntesis el precio de la media bolsa, derivado de la entera con ⌈compra/2⌉ y ⌊venta/2⌋:

  | | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | Blanca (Compra/Venta) | 2(1)/1(0) | 3(2)/2(1) | 4(2)/3(1) | 5(3)/4(2) | 6(3)/5(2) |
  | Integral (Compra/Venta) | 4(2)/2(1) | 5(3)/3(1) | 6(3)/4(2) | 7(4)/5(2) | 8(4)/6(3) |
  | Centeno (Compra/Venta) | 6(3)/3(1) | 7(4)/4(2) | 8(4)/5(2) | 9(5)/6(3) | 10(5)/7(3) |

  Agua (Monedas por temperatura °C × tamaño de lote, en Tokens de Agua del 5%):

  | °C \ Lote | 2 (10%) | 6 (30%) | 12 (60%) | 20 (100%) |
  |---|---|---|---|---|
  | 30 | 3 | 6 | 10 | 14 |
  | 25 | 2 | 5 | 8 | 12 |
  | 20 | 2 | 4 | 7 | 10 |
  | 15 | 1 | 3 | 6 | 9 |
  | 10 | 1 | 2 | 4 | 7 |

### D. Implementar Mejora de Laboratorio
* **Costo:** 1 PA + Datos de Investigación.
    * *Incubadora:* 3 Datos. Permite ajustar temperatura local en +/- 5°C.
    * *Cámara B:* 4 Datos. Desbloquea Estación 03 y mejora la acción de Pliegue.
    * *Módulo Analítico:* 4 Datos. **Ensancha la zona óptima 1 casilla por cada lado** — a costa de la zona baja por abajo y de la sobrefermentada por arriba, así que también **retrasa el umbral de colapso** — y sube los Datos del horneado: 2 en cualquier punto de la zona óptima, 3 en el centro exacto. Es un efecto **en vivo**, no sellado en la masa como el modificador de la Incubadora: instalarlo salva una masa que ya está fermentando. Ensanchar simétricamente **no mueve el centro exacto**, así que la precisión sigue costando lo mismo.
    * *Criopreservación:* 2 Datos. Efecto Pasivo "Estasis Biológica" — durante la Fase III, el cultivo base ignora el desgaste metabólico normal (no resta Vitalidad).
* **Límites:** Cada mejora individual solo puede adquirirse UNA vez por partida, pero un jugador puede llegar a instalar varias mejoras distintas a lo largo de la partida (no hay tope global de "una mejora total"). Además, el espacio D en sí solo puede visitarse 1 vez por día (§1): instalar CUALQUIER mejora agota el espacio para el resto del día, así que dos mejoras distintas nunca pueden instalarse el mismo día — como muy pronto, la segunda espera al día siguiente.
* **Reglas:** El beneficio se activa inmediatamente y se marca con un Cubo de Laboratorio en la Zona 4.

### F. Hornear y Vender (Finalización de Protocolo)
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1). No aplica al colapso automático de Fase III (sobrefermentación), que no pasa por este espacio ni consume PA.
* **Efecto:** El jugador obtiene Puntos de Maestría según la zona en la que se encuentre el marcador. Al hornear, además cobra ingresos en Monedas, y si está en Zona Óptima también recibe Datos de Investigación.
* **Resolución por zona:**
    * *Zona Óptima:* Ingreso completo en Monedas (`monedas_optima`) + Puntos de Maestría íntegros (`puntos_optimos`) + Datos de Investigación (1; **2 con Módulo Analítico**, y **3** si además es el centro exacto). Las zonas se leen ya ensanchadas por el Módulo del jugador: una posición que sin la mejora sería zona baja puede pagar como óptima con ella.
    * *Zona Baja:* Venta con margen reducido en Monedas (`monedas_baja`) + Puntos de Maestría reducidos (`puntos_baja`), sin Datos.
    * *Zona Sobre-fermentada (colapso, Fase III):* Recuperación del coste base en Monedas (`monedas_sobre`) + Puntos de Maestría negativos (`penalizacion_colapso`), sin Datos.
* **Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado (y el horneado no fue un colapso), se suma el bono de Puntos de Maestría impreso en la carta (`bono_sabor_pts`) **y** +2 Monedas adicionales al ingreso de la venta.

### G. Investigar Protocolo
* **Costo:** 1 PA + **Monedas según el grado de la receta** (`engine.PRECIO_RECETA`: Básica 1, Intermedia 2, Avanzada 3). El precio es **aditivo** sobre el PA: el punto de acción y el espacio siguen siendo la escasez real. El precio se indexa por grado, que a su vez lo derivan las harinas impresas, así que no puede contradecir a la carta.
* **Orden de validación (fail-fast):** las Monedas se comprueban **antes** de retirar la carta del mercado. `Market.tomar_receta` la quita de la mesa, de modo que cobrar después haría que cada intento de un jugador sin dinero destruyera una carta para todos.
* **Límites:** Máximo 3 recetas inactivas (si está llena, debe descartar una previa); además, 1 vez por día (por espacio de acción — ver §1).
* **Efecto:** Selecciona 1 Carta de Receta del Mercado Central y la coloca boca arriba en la "Carpeta de Proyectos" (estado inactivo).
* **Mercado:** El espacio central queda vacío hasta que el "Protocolo de Refresco" del inicio del día siguiente reabastezca el Mercado Central a 4 recetas.

### Simposio Técnico (Generación de Datos)
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1), sin importar si se descarta desde la carpeta o desde una estación.
* **Efecto:** Descartar una Carta de Receta de la carpeta de proyectos o de la estación de fermentación para ganar 1 Dato de Investigación inmediatamente.

---

## 3. Acciones Auxiliares y de Emergencia (Costo: 0 PA)

### A. Mantenimiento del Cultivo (Alimentación)
* **Costo:** 0 PA.
* **Límite:** 1 vez por ronda (valida `accion_alimentar_usada == False`).
* **Efecto Modular:** * Restar **1 Token de Harina — 1 (10%)** (de cualquier tipo) = +1 Vitalidad (Máx 6).
    * Restar **2 Tokens de Agua — 2 (10%)** = +1 Acidez (Máx 6). Ojo: son 2 tokens, no 1, porque el token de agua es del 5%.
    * (Se puede hacer uno, otro, o ambos en la misma acción).

### E. Técnica (Pliegues)
* **Costo:** Monedas, según la cantidad de avance que se compre — **1 espacio = 1 Moneda, 2 espacios = 3 Monedas, 3 espacios = 6 Monedas**. El precio es creciente al margen a propósito: comprar más nunca es un descuento por volumen. La variante de Vitalidad (ver Sinergia) cuesta **6 Monedas** fijas.
* **Tipo:** Acción Gratuita (0 PA). No termina el turno del jugador: se puede encadenar con otra acción en la misma visita.
* **Límite:** 1 vez por día (por espacio de acción — ver §1) — incluye todas sus variantes: usar cualquiera de ellas agota el espacio E para el resto del día. Es la única acción de 0 PA que ocupa un espacio de acción; se autolimita por el espacio, no por su coste (las Monedas son un recurso renovable, así que el precio por sí solo no bastaría).
* **Efecto:** Compra entre 1 y 3 espacios de avance del marcador de Inóculo y los reparte entre las masas activas del jugador. El precio depende del TOTAL comprado, no del número de masas afectadas.
* **Sinergia:** La mejora Cámara B **no aumenta cuántos espacios se pueden comprar**, sino que permite repartirlos entre **dos masas distintas** en lugar de concentrarlos en una sola. Además desbloquea una variante alternativa: recuperar **+1 de Vitalidad** en el cultivo base por 6 Monedas, en cuyo caso no se compra ningún espacio de avance.
* **Riesgo (deliberado):** el avance **no tiene tope**. Comprar 3 espacios puede empujar una masa más allá de su zona óptima hasta la zona sobrefermentada, que la Fase III hornea automáticamente en colapso y con penalización. Ese riesgo es el freno del escalón caro; el sistema avisa pero no lo impide.

### Horas Extras
* **Costo:** 1 Token de Datos de Investigación.
* **Tipo:** Acción Gratuita (0 PA).
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II.
* **Efecto:** Otorga inmediatamente +1 Punto de Acción (PA) adicional.
* **Límite:** Solo una (1) vez por ronda, por investigador.

### Pedido de Urgencia
* **Costo:** 1 Token de Datos de Investigación.
* **Tipo:** Acción Gratuita (0 PA).
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II.
* **Efecto:** Ignora el Mercado por completo (y su precio vigente) y obtiene directamente de la reserva general UN tipo de recurso: **10 Tokens de Harina — 10 (100%)** de un tipo elegido O los **Tokens de Agua** que el jugador indique (5% c/u), a elección del jugador.
* **Límite:** Ninguno — a diferencia de Horas Extras, no hay tope de usos por ronda; se autolimita por los Datos de Investigación disponibles. A diferencia de las Acciones B a I y Simposio Técnico, Pedido de Urgencia no cuesta PA y por lo tanto queda exento de la regla "1 vez por día por espacio de acción" (§1) — es intencional, no un descuido.

### Protocolos de Emergencia (Rescate de Cultivo)
*Solo pueden ejecutarse si la Vitalidad del cultivo base llega a 0, momento en el cual el jugador recibe una penalización de -3 Puntos de Maestría.*
* **H. Re-cultivo Manual:** Costo 1 PA + **5 Tokens de Harina — 5 (50%)** (de cualquier tipo). Sin costo de Agua. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 1. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.
* **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 2. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.