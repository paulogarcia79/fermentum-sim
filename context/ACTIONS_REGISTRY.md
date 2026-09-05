# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación. **Un Token de Harina = 10%; un Token de Agua = 5% de hidratación** — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)" para la notación `N (P%)` usada en todo este registro.
* **Un espacio de acción, una visita por día:** cada espacio de acción (B a G, Simposio Técnico, H, I y también E y Descarte, que no cuestan PA pero sí ocupan espacio) solo puede visitarse UNA vez por Día de Laboratorio, por jugador — un peón de investigador marca el espacio con su color en cuanto lo visita, bloqueándolo para él (no para el resto de jugadores) hasta el día siguiente. Con 2 PA esto significa: como máximo un uso de cada espacio distinto por día, nunca el mismo espacio dos veces. La **única** forma de repetir un espacio es el **marcador neutral de las Horas Extras** (§3), que se entrega junto al 3er PA y permite volver una vez a uno de los ocho espacios por jugador con costo de PA (B, C, D, F, G, Simposio, H, I). Es un marcador que no es de nadie: se coloca sobre el espacio junto al peón de color, y por eso no lo desbloquea para los demás ni lo desbloquea dos veces para ti. El tope es una propiedad **del espacio**, no del coste: la Acción E y el Descarte lo conservan aunque se paguen en Monedas o en agua. Las excepciones son Acción A y Horas Extras (que se limitan con su propio marcador de "ya usada", no con un espacio), Pedido de Urgencia, sin límite alguno (se autolimita por Datos de Investigación), **Estasis Biológica** e **Incubadora**, que no tienen límite ni marcador porque son **ajustes y no consumos** — diales de dos sentidos que pueden accionarse cuantas veces se quiera y que por eso tampoco mantienen al jugador en la rotación de visitas (§3), **Reclamar la Jefatura, que va justo al revés**: es el único espacio **global** del tablero, se agota para toda la mesa en cuanto un jugador lo visita, y por eso su marca vive en el motor y no en `acciones_pa_usadas_hoy`; y el **Turno de Mostrador**, que va al revés en el otro sentido: cuesta PA pero **no ocupa espacio ninguno**, así que se repite mientras queden PA (§2 «Mostrador»). Las dos excepciones con costo de PA son por tanto simétricas — una se agota para todos, la otra no se agota nunca.

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
    * *Contratar el Molino:* Pagar **una sola vez** el precio del tipo de harina elegido (Blanca 3, Integral 4, Centeno 6 Monedas) y quedarse con el **Contrato con el Molino** de esa harina. Desde esa misma noche, en **cada Fase III**, el molino entrega **2 Tokens — 2 (20%)** de esa harina, para siempre. **No mueve el visor** (el molino produce fuera de la Bolsa). Un contrato por jugador y por partida: no se cambia de harina, no se cancela y no se revende.
* **Regla de Exclusividad:** una visita (1 PA) puede incluir como máximo UNA transacción por tipo de recurso — comprar Blanca y vender Centeno y comprar un lote de agua en la misma visita está permitido; comprar o vender el mismo tipo dos veces en la misma visita no lo está. **El Molino cuenta como su propio tipo de recurso**, así que firmar el contrato de Centeno y comprar Centeno en la misma visita sí es legal — el molino no entrega hasta la noche, y ese día todavía necesitas harina.
* **Por qué existe el Contrato con el Molino:** hasta ahora la única forma de tener harina era comprarla en la Bolsa, y comprar mueve el visor hacia el extremo caro — de modo que el lado de **venta** del mercado era funcionalidad muerta. Una ida y vuelta comprar→vender pierde el diferencial (1/2/3 Monedas) y mueve el visor dos veces en tu contra, y el Mercado de Tendencias desplaza los tres visores a la vez con un mazo simétrico, así que tampoco había especulación posible. El Contrato es la única fuente de harina que no pasa por el mercado; con él, un jugador produce harina que nunca compró y vender por fin significa algo.
* **Cómo se derivaron los tres precios — horizonte de amortización común: la 4ª noche.** Valorando la entrega diaria al precio de Compra de la posición 3 (la inicial de los tres visores): Blanca 4×20% = 0,8/noche, Integral 6×20% = 1,2, Centeno 8×20% = 1,6. A las 4 noches los tres cubren su precio (3,2 ≥ 3; 4,8 ≥ 4; 6,4 ≥ 6) y a las 3 ninguno llega (2,4; 3,6; 4,8). Que el horizonte sea **el mismo** en los tres es lo que hace que elegir tipo siga siendo una pregunta sobre qué harina necesitas y no sobre cuál se recupera antes — el mismo principio que reparte el horizonte de los Ingresos de Panadería entre los tres grados. El horizonte es una noche más largo que el de la renta (4 frente a 3) a propósito: la renta se cobra por haber horneado, que ya es la jugada difícil, mientras que el Contrato solo pide Monedas, y firmar el primer día no debe ser automáticamente la apertura correcta.
* **Tablas de precio** (posición del visor 1-5 → Monedas). Cada celda es `Compra/Venta`, y entre paréntesis el precio de la media bolsa, derivado de la entera con ⌈compra/2⌉ y ⌊venta/2⌋:

  | | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | Blanca (Compra/Venta) | 2(1)/1(0) | 3(2)/2(1) | 4(2)/3(1) | 5(3)/4(2) | 6(3)/5(2) |
  | Integral (Compra/Venta) | 4(2)/2(1) | 5(3)/3(1) | 6(3)/4(2) | 7(4)/5(2) | 8(4)/6(3) |
  | Centeno (Compra/Venta) | 6(3)/3(1) | 7(4)/4(2) | 8(4)/5(2) | 9(5)/6(3) | 10(5)/7(3) |

  Contrato con el Molino (pago único en Monedas; la entrega es la misma para los tres):

  | Harina | Contrato | Entrega cada Fase III |
  |---|---|---|
  | Blanca | 3 | 2 (20%) |
  | Integral | 4 | 2 (20%) |
  | Centeno | 6 | 2 (20%) |

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
    * *Incubadora:* 3 Datos. Permite ajustar la temperatura local en +/- 5°C (±1 casilla de avance en la Fase III) sobre **una masa concreta y para una sola noche**, con la acción gratuita del mismo nombre (§3). Es un efecto **en vivo**, como el del Módulo Analítico: se decide cada noche en la Fase II, así que instalarla rescata masas que ya estaban fermentando.
    * *Cámara B:* 4 Datos. Desbloquea Estación 03 y mejora la acción de Pliegue.
    * *Módulo Analítico:* 4 Datos. **Ensancha la zona óptima 1 casilla por cada lado** — a costa del pre-fermento por abajo y del colapso por arriba, así que también **retrasa el umbral de colapso** — y sube los Datos del horneado: 2 en cualquier punto de la zona óptima, 3 en el centro exacto. Es un efecto **en vivo**: instalarlo salva una masa que ya está fermentando. El dial de la Incubadora llegó al mismo sitio por otro camino — lo fija su dueño noche a noche en vez de recalcularse solo —, de modo que ninguna de las dos mejoras deja ya fuera a una masa que empezó antes de comprarlas. Ensanchar simétricamente **no mueve el centro exacto**, así que la precisión sigue costando lo mismo.
    * *Criopreservación:* 2 Datos. Efecto Pasivo "Estasis Biológica" — durante la Fase III, el cultivo base ignora el desgaste metabólico normal (no resta Vitalidad). La Estasis es el estado **por defecto** y su dueño puede **suspenderla noche a noche** con la acción gratuita del mismo nombre (§3), que es lo que le devuelve el control sobre su Vitalidad — y con ella sobre el Dado de Inóculo que la Acción B sella.
    * *Comerciante:* 3 Datos. **Sólo toca la Acción C** — en particular, **no descuenta la ponencia del Simposio Técnico**, cuyos 5 Monedas por Dato los paga toda la mesa por igual. Cada transacción de **compra** de la Acción C — bolsa y media bolsa de harina, lote de agua y la firma del Contrato con el Molino — cuesta `DESCUENTO_COMERCIANTE` (1) Moneda menos, con **suelo de 1**. **No toca el lado de venta** y **no altera el movimiento del visor** (una transacción es una señal de mercado con independencia de su precio, igual que media bolsa). Se aplica en los dos bucles de `accion_C_visitar_mercado` a través de un único helper, `_precio_compra_efectivo`, para que simular saldos y aplicar no puedan cobrar distinto. Consecuencia medida y aceptada: como comprar sube el visor una casilla y la horquilla de la Blanca es de 1 Moneda, el ciclo comprar→vender de Blanca ya era de saldo **cero** sin tecnología y con el descuento pasa a **+1**; lo acota el espacio de acción (Regla de Exclusividad + espacio C único por día ⇒ dos días para ganar 1 Moneda), no el precio. Ver la docstring de `actions.DESCUENTO_COMERCIANTE`.
* **Límites:** Cada mejora individual solo puede adquirirse UNA vez por partida, pero un jugador puede llegar a instalar varias mejoras distintas a lo largo de la partida (no hay tope global de "una mejora total"). Además, el espacio D en sí solo puede visitarse 1 vez por día (§1): instalar CUALQUIER mejora agota el espacio para el resto del día, así que dos mejoras distintas nunca pueden instalarse el mismo día — como muy pronto, la segunda espera al día siguiente.
* **Reglas:** El beneficio se activa inmediatamente y se marca con un Cubo de Laboratorio en la Zona 4.

### F. Hornear y Vender (Finalización de Protocolo)
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1). No aplica al colapso automático de Fase III (sobrefermentación), que no pasa por este espacio ni consume PA.
* **Efecto:** El jugador obtiene Puntos de Maestría según la zona en la que se encuentre el marcador. Al hornear, además cobra ingresos en Monedas, y si está en Zona Óptima también recibe Datos de Investigación.
* **Prohibición:** una masa en **Crecimiento** no se puede hornear — todavía no es pan. `ActionManager.accion_F_hornear` lanza `RuleViolationError` y `disponibilidad.py` apaga el espacio con el motivo "La masa aún está creciendo". Se comprueba contra las zonas **efectivas** del jugador, aunque el crecimiento nunca se amplía, de modo que esa frontera no se mueve al instalar el Módulo Analítico. **No hay forma de abandonar una masa**: iniciar una receta es un compromiso irreversible, y una masa que no se quiere fermentará hasta hornearse o colapsar (el Simposio Técnico ya no descarta de una estación). No queda nunca atascada — la Fase III la hace avanzar todas las noches — así que lo que se pierde es la posibilidad de esquivar `penalizacion_colapso`, no el uso de la estación. Esto es lo que cierra el agujero de iniciar una receta y hornearla el mismo día desde la casilla 0, que pagaba como pre-fermento.
* **Resolución por zona:**
    * *Crecimiento:* no se hornea (ver arriba). Sin puntos, sin Monedas, sin Datos.
    * *Zona Óptima:* Ingreso completo en Monedas (`monedas_optima`) + Puntos de Maestría íntegros (`puntos_optimos`) + Datos de Investigación (1; **2 con Módulo Analítico**, y **3** si además es el centro exacto). Las zonas se leen ya ensanchadas por el Módulo del jugador: una posición que sin la mejora sería pre-fermento puede pagar como óptima con ella.
    * *Pre-fermento:* Venta con margen reducido en Monedas (`monedas_pre_fermento`) + Puntos de Maestría reducidos (`puntos_pre_fermento`), sin Datos.
    * *Colapso (Fase III):* Recuperación del coste base en Monedas (`monedas_colapso`) + Puntos de Maestría negativos (`penalizacion_colapso`), sin Datos.
* **Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado (y el horneado no fue un colapso), se suma el bono de Puntos de Maestría impreso en la carta (`bono_sabor_pts`) **y** +2 Monedas adicionales al ingreso de la venta.

### G. Investigar Protocolo
* **Costo:** 1 PA + **Monedas según el grado de la receta** (`engine.PRECIO_RECETA`: Básica 1, Intermedia 2, Avanzada 3). El precio es **aditivo** sobre el PA: el punto de acción y el espacio siguen siendo la escasez real. El precio se indexa por grado, que a su vez lo derivan las harinas impresas, así que no puede contradecir a la carta.
* **Origen `"mazo"` — Investigación a ciegas:** en lugar de una carta expuesta, roba la **carta superior de `Market.mazo_recetas`** (índice 0, la que revelaría el refresco de mañana) por `engine.PRECIO_RECETA_MAZO` = **2 Monedas planas**, sin verla antes de pagar. Las 4 estaciones no se tocan. `PRECIO_RECETA_MAZO` vale lo mismo que `PRECIO_RECETA[INTERMEDIA]` pero es una **constante separada a propósito** (precedente `DATOS_SIMPOSIO` vs `PRECIO_RENTA`): reajustar la tabla visible no debe reajustar la apuesta. El 2 está elegido contra el precio esperado de la carta de arriba comprada visible, (16·1 + 12·2 + 8·3)/36 ≈ 1,78, de modo que la ciega es una apuesta ligeramente cara y no un descuento.
* **Mazo agotado:** si `mazo_recetas` está vacío pero queda descarte, `Market.robar_receta_del_mazo` baraja el descarte como mazo nuevo **en el momento de robar** (`Market._rebarajar_descarte_si_agotado`, el mismo helper que usa el Protocolo de Refresco). Solo con mazo **y** descarte vacíos la opción desaparece: `RecipeDeckEmptyError`, y `disponibilidad.py` apaga el espacio.
* **Orden de validación (fail-fast):** las Monedas se comprueban **antes** de tocar ninguna carta, en los dos orígenes y por motivos distintos. En `"mercado"`, `Market.tomar_receta` quita la carta de la mesa, de modo que cobrar después haría que cada intento de un jugador sin dinero destruyera una carta para todos. En `"mazo"` hay **dos** pasos irreversibles: el `pop(0)` se lleva la carta de arriba y el rebarajado consume el RNG global, así que un intento rechazado tampoco puede barajar el mazo de nadie.
* **Forma de la llamada:** `origen` discrimina los dos modos (precedente del `modo` del Simposio y del `recurso` del Pedido de Urgencia), pero **con valor por defecto `"mercado"`** — ningún parámetro cambia de significado, así que la forma antigua sigue queriendo decir lo mismo y el modo nuevo hay que pedirlo a propósito. `origen="mazo"` con `indice_mercado`, o `"mercado"` sin él, son `InvalidActionError`: la carta ciega no se elige.
* **Límites:** Máximo 3 recetas inactivas (si está llena, debe descartar una previa); además, 1 vez por día (por espacio de acción — ver §1). Idénticos en ambos orígenes: el espacio es uno, así que es una cosa **o** la otra por día.
* **Efecto:** Selecciona 1 Carta de Receta del Mercado Central (o roba la superior del mazo) y la coloca boca arriba en la "Carpeta de Proyectos" (estado inactivo).
* **Mercado:** Tomando de las estaciones, el espacio central queda vacío hasta que el "Protocolo de Refresco" del inicio del día siguiente reabastezca el Mercado Central a 4 recetas. Robando del mazo no se libera ningún espacio: la exposición queda como estaba.

### Simposio Técnico (Generación de Datos)
* **Costo:** 1 PA + **uno de dos pagos, a elegir con el parámetro `modo`**:
    * `sacrificar`: **un horneado exitoso del Archivo**.
    * `ponencia`: **`PRECIO_DATO_SIMPOSIO` (5) Monedas por cada Dato**, de 1 a `MAX_DATOS_PONENCIA` (3) Datos por visita.

  El PA es aditivo sobre ese pago en los dos casos, igual que el precio en Monedas de la Acción G lo es sobre su PA: el punto de acción sigue siendo la escasez real, y la acción termina el turno como cualquier otra Principal.
* **Límite:** 1 vez por día (por espacio de acción — ver §1). Como el espacio es único, **una visita elige un modo y sólo uno**: la exclusividad no necesita regla propia, la da el espacio.
* **Los DOS modos exigen `archivo_horneado_exitoso` no vacío.** Se presenta un pan en el simposio; el modo decide si además se sacrifica. Esa puerta compartida es lo que impide que las Monedas del Patrocinio sean un grifo de Datos el Día 1 (sigue sin haber ningún Dato en la mesa hasta el primer horneado — ver PLAYER_STATE.md §Patrocinio) y lo que permite que `disponibilidad.py` no cambie ni una línea: su condición (archivo no vacío + PA + espacio libre) ya vale para ambos.
* **Efecto (`sacrificar`):** Retira un registro de `archivo_horneado_exitoso` y otorga Datos de Investigación **según el grado de la carta**: **Básica 1, Intermedia 2, Avanzada 3** (`engine.DATOS_SIMPOSIO`). La carta física vuelve al descarte de recetas y puede reaparecer al rebarajar.
* **Efecto (`ponencia`):** Acredita los Datos comprados y cobra `datos * PRECIO_DATO_SIMPOSIO` Monedas. **El Archivo no se toca**: ni el registro, ni sus puntos, ni su renta, ni el contador X/5.
* **El modo `sacrificar` es la única forma de sacar un registro del Archivo**, y por tanto la única forma de perder la renta de Ingresos de Panadería (ver CORE_MECHANICS.md §Fase III). Sacrificar un horneado cuesta a la vez:
    * sus Puntos de Maestría base (9-20 según la carta),
    * su renta diaria para el resto de la partida,
    * un escalón entero de «Variedad de Recetas» si era el único de su tipo (hasta -5 PM),
    * y un paso del contador X/5 que dispara el fin de partida.
* **Nada de esto necesita código que lo coordine:** `puntos_horneados`, `puntos_variedad` y `recetas_distintas_horneadas` se derivan todos de esa misma lista.
* **El sacrificio no es una jugada eficiente y no pretende serlo.** Ningún rendimiento en Datos compensa ese precio: es una **palanca de emergencia** — quemar un éxito pasado para salvar el presente — y en la práctica se sacrifica siempre la carta más barata que se tenga. Consecuencia emergente que se documenta y no se corrige: un jugador en 4/5 puede sacrificar un horneado para bajar a 3/5 y retrasar el final. Es carísimo, así que es legítimo. Lo que no puede es revertir un final ya disparado.
* **La ponencia, y por qué 5 y 3.** El sacrificio es tan caro que casi nadie lo tocaba, mientras que «Ingresos de Panadería» hace que al final de la partida sobren Monedas sin más destino que la harina y los Datos entren de uno en uno. La ponencia conecta las dos puntas, y sus dos cifras son de equilibrio:
    * **5 Monedas por Dato es la tasa de «Conversión de Riqueza»** (+1 PM por cada 5 Monedas sobrantes, ver CORE_MECHANICS.md §3), así que un Dato comprado cuesta exactamente el Punto de Maestría que ese dinero habría puntuado. Es un trueque a la par y sólo compensa si el Dato se invierte en algo que rinda más de 1 PM.
    * **5 está además por encima de 3**, lo máximo que revende la media bolsa que entrega un Pedido de Urgencia (Centeno en posición 5 se vende a 7, y la media redondea a la baja). Eso cierra el bucle Monedas → Dato → media bolsa → Monedas, que a cualquier precio menor de 4 habría sido una máquina de imprimir dinero con dos acciones ya existentes.
    * **El tope de 3 iguala `DATOS_SIMPOSIO[Avanzada]`**, el mejor pago del sacrificio: por mucha renta acumulada, una bolsa nunca rinde en una visita más Datos que sacrificar una Avanzada, de modo que el sacrificio conserva un papel propio aunque su tabla no haya cambiado.
    * **El tope también protege el primer escalón**: la Jefatura da 1 Dato por 1 PA y sin pagar Monedas, así que comprar un solo Dato es estrictamente peor que reclamarla. La ponencia sólo compensa a 2 o 3 de golpe, o cuando otro ya se llevó la Jefatura de hoy.
    * **Ninguna de las dos se deriva de otra constante** (ni del `// 5` de `desglose_maestria`, ni de `DATOS_SIMPOSIO`): mismo criterio que `DATOS_SIMPOSIO` frente a `PRECIO_RENTA` y que `AGUA_PEDIDO_URGENCIA` frente a `AGUA_TOKENS_POR_LOTE[30]` — reequilibrar la puntuación final no debe reajustar en silencio el precio de una acción.
    * **La tecnología Comerciante no descuenta la ponencia.** Sólo abarata las compras de la Acción C.
    * **El cable lleva un discriminador, no una bolsa de campos opcionales**: `{modo: "sacrificar", indice}` o `{modo: "ponencia", datos}`, y el parámetro del modo contrario es un error. Mismo patrón que el `recurso` del Pedido de Urgencia: el estado ilegal es irrepresentable en vez de validado.
* **Ya NO descarta de la carpeta ni de una estación.** Descartar de la carpeta lo cubre la propia Acción G (parámetro `indice_descartar` cuando la carpeta está llena). Abandonar una masa **ya no es posible en absoluto**: ver §F.

### Reclamar la Jefatura
* **Costo:** 1 PA. Termina el turno como cualquier acción Principal.
* **Límite: UNO POR DÍA EN TODA LA MESA.** Es el único espacio **global** del tablero: el resto se limitan por jugador (`acciones_pa_usadas_hoy`), este se limita para todos a la vez, y por eso su marca vive en el motor (`GameEngine.jefatura_reclamada_por`) y no en el jugador. Reclamarla no solo la usa: se la quita a los demás.
* **Efecto:** `DATOS_JEFATURA` (= 1) Dato de Investigación **inmediato**, y el jugador abre la Fase II **de mañana** como Investigador Jefe (ver CORE_MECHANICS.md §Fase I).
* **El efecto es diferido a propósito.** El orden de turno se calcula una sola vez, en la Fase I, y no se rebaraja a media jornada: lo que se compra es la salida de mañana, no la de hoy.
* **Reclamar siendo ya Jefe es legal** y cuesta lo mismo — es la única forma de retener la Jefatura, ya que sin reclamación la ficha se queda donde está pero cualquiera puede comprarla.
* **Sustituye a la asignación automática por Vitalidad**, que no era una decisión de nadie y dejaba al Investigador Jefe sin más contenido que salir primero.
* **Es la fuente renovable de Datos que faltaba.** Los Datos salían de hornear en Zona Óptima, del Módulo Analítico (que es a su vez una compra en Datos) y del Simposio — casi todo de la misma jugada, de modo que quien horneaba bien primero acumulaba también la divisa técnica, y las dos acciones que se pagan en Datos (Horas Extras y Pedido de Urgencia) se quedaban sin combustible en la mesa de los demás. Aquí entra 1 Dato por día **en total**, repartido por rotación y no por riqueza: está limitado por competencia, no por precio, que es lo que impide que se convierta en un grifo.
* **La ponencia del Simposio es hoy la otra vía renovable** (Monedas → Datos), pero cuesta 1 PA **más** 5 Monedas por Dato y exige tener ya un pan en el Archivo. La Jefatura sigue dominando el primer escalón: es el único Dato que no cuesta nada más que el punto de acción.

### Turno de Mostrador
* **Costo:** 1 PA. Termina el turno como cualquier acción Principal.
* **Límite: NINGUNO.** Es la única acción con costo de PA que **no ocupa espacio**: llama a `Player.consumir_punto_accion("mostrador", ocupa_espacio=False)`, de modo que `"mostrador"` nunca entra en `acciones_pa_usadas_hoy` y la acción puede repetirse mientras queden PA. Es la excepción inversa a la Jefatura (§1): aquella se agota para toda la mesa, esta no se agota nunca.
* **Efecto:** `MONEDAS_MOSTRADOR` (= 1) Moneda. Sin parámetros y sin requisitos: teniendo PA está siempre disponible.
* **Por qué existe: el turno hueco.** Un jugador podía tener PA y ninguna jugada útil — carpeta vacía, masa aún en Crecimiento, 0 Monedas, 0 Datos y la Jefatura ya reclamada por otro — y su única salida era `pasar_turno`, que además **renuncia a las acciones gratuitas del resto del día**. Los PA sobrantes se perdían en silencio: `resolver_fase_III` nunca lee `puntos_accion`, y la penalización de «Desperdicio» del recuento final sólo cuenta harina y agua.
* **Por qué NO ocupa espacio.** Un jugador tiene 2 PA (3 con Horas Extras) y el hueco puede darse dos veces el mismo día. Un espacio de una visita por día resolvería la mitad del problema y dejaría el segundo PA tan hueco como antes. Ese es el motivo de que `consumir_punto_accion` ganara el parámetro `ocupa_espacio` — es el caso simétrico e inverso de `ocupar_espacio_accion`, que marca espacio sin gastar PA (Acción E, Descarte).
* **Por qué se paga en Monedas.** En Datos formaría un bucle con Horas Extras (1 Dato → +1 PA → 1 Dato) y pisaría a la Jefatura, que ya paga 1 Dato por 1 PA *y además* el orden de turno. En Vitalidad pisaría a la Acción A, que da +1 por 10% de harina y encima cuesta 0 PA. Las Monedas son la divisa más líquida y no cierran ningún ciclo.
* **Por qué 1 y no más.** Es exactamente lo que valía la Acción E retirada (1 PA por 1 casilla de avance), la acción que nadie tomaba: ese es el listón buscado. Cualquier acción real domina al Mostrador, así que nunca es una línea de juego.
* **Por qué NO está condicionada a «no tener nada mejor que hacer».** Esa condición no es observable: `disponibilidad.py` reporta la Acción C habilitada siempre que haya PA y no se haya usado el espacio, aunque el jugador no tenga Monedas ni harina que vender. Un guardia así se apagaría casi siempre y el suelo no estaría cuando hace falta. Se autolimita **siendo débil, no estando cerrado**.
* **Por qué sí otorga visitas:** las otorga el propio PA (`GameEngine._jugador_elegible` ya devuelve `True` con `puntos_accion > 0`), así que no hizo falta cláusula nueva — al contrario que Estasis e Incubadora, que son ajustes sin coste y por eso están deliberadamente fuera de esa condición.

---

## 3. Acciones Auxiliares y de Emergencia (Costo: 0 PA)

### A. Mantenimiento del Cultivo (Alimentación)
* **Costo:** 0 PA.
* **Límite:** 1 vez por ronda (valida `accion_alimentar_usada == False`). En esa única acción el jugador elige el escalón; elegir +1 renuncia al +2 por ese día.
* **Efecto:** escalera `models.HARINA_ALIMENTAR = {1: 10, 2: 30}` (Vitalidad ganada → harina gastada, en %), siempre con tope 6:
  * **10%** (1 token) **de un mismo tipo** = **+1 Vitalidad**. Repone exactamente el -1 del desgaste metabólico de Fase III, de modo que quien alimenta a diario orbita su Vitalidad inicial.
  * **30%** (3 tokens), **de un tipo o mezclados** = **+2 Vitalidad**. Creciente al margen (el segundo punto cuesta 20): es lo que contrarresta el -2 de «Aletargamiento Invernal», o compra +1 neto al día pagando la prima; el freno es el precio.
* **Wire / firma:** `accion_A_alimentar(player, harina={tipo: pct})`. La harina viaja como un reparto en múltiplos de 10; los puntos se **derivan** de la suma (el escalón cuyo precio coincide) y una suma que no sea escalón (p. ej. 20) se rechaza con `InvalidActionError`. No hay un `pasos` aparte: sería un segundo número libre de contradecir al reparto (el argumento de `PRECIO_PLIEGUES`, invertido). Un faltante nombra **todos** los tipos que faltan.
* **Disponibilidad:** `Player.puede_alimentar` (≥10% de un mismo tipo) es lo que consultan `disponibilidad.py` y `engine._jugador_elegible`; 5% + 5% en dos tipos no vale, y el agua no participa (hubo un `or reserva_agua >= 2` heredado de la mitad de agua retirada que encendía la casilla sin harina).
* **Ya NO toca la Acidez.** Tuvo una mitad de agua que daba +1 Acidez, pero mientras la Acidez sólo sabía subir esa mitad era un trinquete — y encima uno que convenía accionar siempre, porque la Madurez premiaba el nivel bruto. Todo el control voluntario de la Acidez vive ahora en la acción **Descarte**, abajo; la Acción A quedó reducida a lo único que hacía sin ambigüedad.

### Descarte (Refresco del Cultivo)
* **Costo:** 0 PA, pero **ocupa su espacio de acción** (ver §1). No termina el turno del jugador: se puede encadenar con otra acción en la misma visita.
* **Límite:** 1 vez por día (por espacio de acción — ver §1). Es, junto a la Acción E, una de las dos acciones de 0 PA que ocupan espacio: el mismo argumento se aplica aquí, ya que las Monedas son renovables y el precio por sí solo no limitaría nada.
* **Efecto:** ajusta la Acidez del cultivo base en **uno de los dos sentidos** (uno solo por visita), con el clamp habitual [0, 6]:

  | Niveles | +1 / -1 | +2 / -2 | +3 / -3 |
  |:---|:---:|:---:|:---:|
  | **Subir** — Tokens de Agua (`COSTE_REFRESCO_AGUA`) | 2 | 5 | 9 |
  | **Bajar** — Monedas (`PRECIO_DESCARTE`) | 1 | 3 | 6 |

* **Por qué cada sentido cobra un recurso distinto:** subir la acidez es sólo añadir agua; bajarla es descartar parte del cultivo y refrescarlo con harina nueva, es decir tirar producto, y por eso se paga en la moneda del juego. La asimetría además protege al jugador arruinado, que conserva un sentido del dial sin una sola Moneda — y es lo que hace que `_jugador_elegible` tenga que comprobar **ambos** recursos, no sólo Monedas.
* **Ambas escaleras son crecientes al margen** (2, 3 y 4 tokens; 1, 2 y 3 Monedas): el volumen nunca es un descuento, la misma regla que `PRECIO_PLIEGUES`. El escalón se cobra entero aunque el ajuste tope contra 0 o 6.
* **No emite ningún `GameEvent`**, pese a cambiar estado visible. Al ser 0 PA ocurre dentro de la ventana de deshacer, y `GameSession.restaurar_checkpoint` repone el motor desde un pickle: un evento suyo haría *encoger* `engine.eventos` al deshacer y dejaría los punteros `since` / `Last-Event-ID` de los clientes por delante del servidor.
* **Interacción con el recuento final:** sirve para caer dentro de la `acidez_diana` de una receta antes de iniciarla (Bono de Sabor, ver §2B), pero la **Madurez del Cultivo** premia el equilibrio y no el nivel bruto (CORE_MECHANICS.md §3.3), con el pico en Acidez 3 y 0 puntos en los extremos. Perseguir una diana extrema cuesta puntos finales mientras se sostiene — y es exactamente por eso que esas cartas pagan más `bono_sabor_pts`.

### E. Técnica (Pliegues)
* **Costo:** Monedas, según la cantidad de avance que se compre — **1 espacio = 1 Moneda, 2 espacios = 3 Monedas, 3 espacios = 6 Monedas**. El precio es creciente al margen a propósito: comprar más nunca es un descuento por volumen. La variante de Vitalidad (ver Sinergia) cuesta **6 Monedas** fijas.
* **Tipo:** Acción Gratuita (0 PA). No termina el turno del jugador: se puede encadenar con otra acción en la misma visita.
* **Límite:** 1 vez por día (por espacio de acción — ver §1) — incluye todas sus variantes: usar cualquiera de ellas agota el espacio E para el resto del día. Es la única acción de 0 PA que ocupa un espacio de acción; se autolimita por el espacio, no por su coste (las Monedas son un recurso renovable, así que el precio por sí solo no bastaría).
* **Efecto:** Compra entre 1 y 3 espacios de avance del marcador de Inóculo y los reparte entre las masas activas del jugador. El precio depende del TOTAL comprado, no del número de masas afectadas.
* **Sinergia:** La mejora Cámara B **no aumenta cuántos espacios se pueden comprar**, sino que permite repartirlos entre **dos masas distintas** en lugar de concentrarlos en una sola. Además desbloquea una variante alternativa: recuperar **+1 de Vitalidad** en el cultivo base por 6 Monedas, en cuyo caso no se compra ningún espacio de avance.
* **Riesgo (deliberado):** el avance **no tiene tope**. Comprar 3 espacios puede empujar una masa más allá de su zona óptima hasta la zona de colapso, que la Fase III hornea automáticamente y con penalización. Ese riesgo es el freno del escalón caro; el sistema avisa pero no lo impide.

### Horas Extras
* **Costo:** 1 Token de Datos de Investigación (`models.DATOS_HORAS_EXTRAS`).
* **Tipo:** Acción Gratuita (0 PA).
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II.
* **Efecto:** Otorga inmediatamente +1 Punto de Acción (PA) adicional **y un marcador neutral**: una de las acciones con costo de PA de ese jugador ese día podrá ejecutarse en un espacio que él ya haya visitado (§1). Los espacios que lo admiten son los ocho **por jugador y con costo de PA**: B, C, D, F, G, Simposio Técnico, H e I (`actions.ESPACIOS_CON_MARCADOR_NEUTRAL`).
* **Límite:** Solo una (1) vez por ronda, por investigador; el marcador es, por tanto, uno por día como máximo.

* **Por qué existe el marcador.** El 3er PA valía menos que los dos primeros, y era una consecuencia directa de §1: sólo podía comprar un espacio **distinto y sin usar**, que muchos días era el Mostrador (1 Moneda) o nada. Enfrente, el juego valora 1 Dato en 1 Punto de Maestría (`engine.PRECIO_DATO_SIMPOSIO` = 5 Monedas = la tasa de Conversión de Riqueza), y **Reclamar la Jefatura es el trueque inverso** — 1 PA por 1 Dato *más* el orden de turno. Es decir, quien compraba Horas Extras estaba en el lado malo de un intercambio que la mesa ya ofrecía. Lo que estaba mal no era el precio, sino lo que compraba: **el precio no se tocó.**
* **Se gasta sólo al repetir, y por eso el orden da igual.** Si el PA extra cae en un espacio libre, el jugador pone su color como siempre y **conserva** el marcador para más tarde ese mismo día. Así activar las Horas Extras pronto (para asegurar el Dato) nunca castiga, que es justo lo que haría una regla del tipo "la siguiente acción puede repetir".
* **Por qué la Jefatura queda fuera.** Su bloqueo es de la mesa entera, no de tu color: un marcador que sólo sabe cubrir tu propia marca no tiene ahí nada que cubrir. Y pagaría un segundo Dato para cobrar uno — el bucle que la entrada del Mostrador (§2) ya documenta.
* **Por qué Pliegues y Descarte quedan fuera.** Cuestan 0 PA, y el marcador viaja con una acción de PA: no hay dónde gastarlo. Dejarlos entrar convertiría 1 Dato en una segunda escalera de Pliegues (hasta 6 casillas más de pista) el mismo día.
* **Dónde vive.** No hay campo nuevo: la repetición se guarda como la **única entrada duplicada** posible de `acciones_pa_usadas_hoy`, y `Player.espacio_repetido_hoy` / `Player.marcador_neutral_disponible` la leen (PLAYER_STATE.md §1). Esto es lo que evita tocar el formato persistido, igual que en los Pliegues y el Mostrador.
* **Fail-fast:** el marcador se comprueba al validar el espacio pero se consume al registrar la visita, de modo que un intento de repetir que falle más tarde (sin harina para la receta, sin masa horneable) deja el marcador intacto.

### Estasis Biológica
* **Costo:** Ninguno.
* **Tipo:** Acción Gratuita (0 PA). **No ocupa espacio de acción.**
* **Requisito:** Tecnología Criopreservación instalada.
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II — es decir, con la carta de clima del día ya revelada, así que la decisión se toma sabiendo la temperatura y el desgaste que traerá la noche.
* **Efecto:** Fija `Player.estasis_suspendida`. Con la Estasis **suspendida**, el cultivo base sufre esta noche el desgaste metabólico normal (−1, o −2 con Aletargamiento Invernal) pese a la Criopreservación; **reactivada**, lo ignora como siempre.
* **Límite:** Ninguno. Es un interruptor de dos sentidos, accionable cuantas veces se quiera dentro de las visitas que el jugador ya tenga.
* **Duración:** Una sola noche. La propia Fase III limpia la bandera tras aplicar el desgaste (`GameEngine._aplicar_desgaste_metabolico`), de modo que la Estasis **se reactiva sola cada día**.
* **Por qué existe:** la Acción B sella el Dado de Inóculo con la Vitalidad del día y **nada en el juego baja la Vitalidad a propósito** — el Descarte solo mueve la Acidez. Quien tenía Criopreservación y alimentaba a diario subía 2→6 y se quedaba clavado en 6: sus masas avanzaban 9–11 casillas por noche contra las 2–3 casillas de zona óptima de una receta Avanzada, así que la mejora que había pagado en Datos le inhabilitaba el tramo alto del catálogo. La suspensión es la válvula que faltaba.
* **Por qué no otorga visitas:** un ajuste no es un recurso. No aparece en `GameEngine._jugador_elegible`, a diferencia de Acción A y Horas Extras: se acciona dentro de una visita que ya se tenía, nunca la crea. Si lo hiciera, todo dueño de la Criopreservación cobraría una visita extra al día quisiera o no.
* **Por qué el estado por defecto es la Estasis ACTIVA:** quien ignore la acción juega exactamente como antes, y como la suspensión dura una sola noche un ajuste olvidado no puede contaminar a nadie.
* **Por qué no emite `GameEvent`:** es una acción de 0 PA, o sea que ocurre dentro de la ventana de deshacer, y restaurar un checkpoint reconstruye el motor entero — un evento aquí encogería `engine.eventos` al deshacer. El rastro permanente lo deja el evento `DESGASTE` de la Fase III, que informa de `estasis_suspendida`.

### Incubadora
* **Costo:** Ninguno.
* **Tipo:** Acción Gratuita (0 PA). **No ocupa espacio de acción.**
* **Requisito:** Tecnología Incubadora instalada y al menos una masa en fermentación.
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II — es decir, con la carta de clima del día ya revelada, así que el dial se mueve sabiendo la temperatura que traerá la noche.
* **Efecto:** Fija `FermentationSlot.modificador_incubadora` de UNA masa concreta: `-1` la frena una casilla esta noche, `+1` la acelera una, `0` deja la cinética limpia. Se acciona masa por masa, así que con varias estaciones ocupadas se puede frenar una mientras se empuja otra.
* **Límite:** Ninguno. Es un dial de dos sentidos, accionable cuantas veces se quiera dentro de las visitas que el jugador ya tenga.
* **Duración:** Una sola noche. La propia Fase III limpia el dial tras aplicarlo (`GameEngine._avanzar_masas_jugador`), de modo que **vuelve a 0 cada día**.
* **Por qué existe:** el modificador se elegía en la Acción B y quedaba **sellado** en la masa para siempre. Quien instalaba la Incubadora con una masa ya fermentando no podía tocar su dial — era un 0 que ninguna acción del juego alcanzaba —, así que veía colapsar esa masa sin poder frenarla, con la mejora recién pagada en Datos encima de la mesa. El reglamento ya prometía un ajuste «masa por masa» en la Fase III; esta acción es lo que lo cumple.
* **Por qué no otorga visitas:** un ajuste no es un recurso. No aparece en `GameEngine._jugador_elegible`, a diferencia de Acción A y Horas Extras: se acciona dentro de una visita que ya se tenía, nunca la crea. Mismo criterio que la Estasis Biológica.
* **Por qué el dial vuelve a 0 cada noche:** una masa nace sin ajuste y la Fase III lo restablece, así que quien ignore la acción juega exactamente como antes y un `+1` olvidado no puede seguir empujando una masa hacia el colapso noche tras noche.
* **Por qué el sobrepaso es legal:** un `+1` puede meter la masa en Colapso, y no se impide — el riesgo es el freno del dial, igual que en la Acción E. El cliente enseña dónde caerá la masa antes de confirmar.
* **Por qué no emite `GameEvent`:** es una acción de 0 PA, o sea que ocurre dentro de la ventana de deshacer, y restaurar un checkpoint reconstruye el motor entero — un evento aquí encogería `engine.eventos` al deshacer. El rastro permanente lo deja el evento `MASA_AVANZO` de la Fase III, que informa del modificador aplicado.

### Pedido de Urgencia
* **Costo:** 1 Token de Datos de Investigación.
* **Tipo:** Acción Gratuita (0 PA).
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II.
* **Efecto:** Ignora el Mercado por completo (y su precio vigente) y obtiene directamente de la reserva general UNA parcela **fija**, a elección del jugador: **media bolsa de Harina — 5 (50%)** de un tipo elegido O **6 Tokens de Agua — 6 (30%)**. El jugador elige el recurso, nunca la cantidad.
* **Por qué el agua también es una cantidad fija:** era la única cifra del juego que escribía el jugador y nada la acotaba. Una receta pide entre 10 y 17 tokens y un lote del 100% cuesta de 7 a 14 Monedas, así que 1 Dato compraba toda el agua de la partida entera. El agua no se revende, de modo que no había arbitraje en Monedas como con la harina, pero el único freno era la penalización por desperdicio del final (−1 PM por cada 3 tokens sin usar), un precio ridículo por saltarse el Suministro Hídrico durante toda la partida. Se fija en **6 (30%)** porque es el lote del 30% del mercado (2 a 6 Monedas según temperatura), el mismo orden de magnitud que la media bolsa de harina (1 a 3 Monedas): el Dato compra lo mismo elijas lo que elijas. Y conserva la historia que ya cuenta la harina — igual que dos Pedidos completan una bolsa, dos Pedidos cubren aproximadamente el agua de una receta. Coincide con `AGUA_TOKENS_POR_LOTE[30]` pero **no se deriva de él**: redimensionar los lotes del mercado no debe rebalancear en silencio una acción de rescate.
* **Por qué media bolsa y no una entera:** el Pedido era, además de un rescate logístico, el mejor arbitraje de la partida — 1 Dato compraba una bolsa entera de *cualquier* harina, y una bolsa de Centeno en posición 5 se revende en el acto por 7 Monedas. Con el Contrato con el Molino (§C) convirtiendo la venta de harina en una línea económica real, ese bucle habría escalado antes que ninguna otra cosa. Media bolsa conserva la función de emergencia (2 Pedidos completan una bolsa entera, y una receta Intermedia sólo pide 50% de cada harina, o sea un Pedido exacto por mitad) y parte el arbitraje por más de la mitad, porque la venta de media bolsa redondea hacia **abajo**: el Centeno en posición 5 baja de 7 a 3 Monedas por Dato.
* **Límite:** Ninguno — a diferencia de Horas Extras, no hay tope de usos por ronda; se autolimita por los Datos de Investigación disponibles. A diferencia de las Acciones B a I y Simposio Técnico, Pedido de Urgencia no cuesta PA y por lo tanto queda exento de la regla "1 vez por día por espacio de acción" (§1) — es intencional, no un descuido.

### Protocolos de Emergencia (Rescate de Cultivo)
*Solo pueden ejecutarse si la Vitalidad del cultivo base llega a 0, momento en el cual el jugador recibe una penalización de -3 Puntos de Maestría.*
* **H. Re-cultivo Manual:** Costo 1 PA + **3 Tokens de Harina — 3 (30%)** (de cualquier tipo). Bajó de 50% a 30% al endurecerse el juego alrededor de la contaminación: los Datos ahora sólo salen de hornear bien o de sacrificar un horneado, así que un jugador contaminado temprano puede no tener ninguno para el Protocolo I, y H es la vía comprable y tiene que seguir siéndolo. A 30% cabe en la bolsa inicial de Patrocinio incluso tras varias Acciones A, de modo que rescatarse nunca obliga a gastar antes una visita entera en el mercado. Sigue siendo el peor de los dos rescates (Nivel 1 frente al Nivel 2 del Protocolo I). Sin costo de Agua. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 1. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.
* **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 2. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.