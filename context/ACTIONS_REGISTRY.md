# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación. **Un Token de Harina = 10%; un Token de Agua = 5% de hidratación** — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)" para la notación `N (P%)` usada en todo este registro.
* **Un espacio de acción, una visita por día:** cada espacio de acción (B a G, Simposio Técnico, H, I y también E y Descarte, que no cuestan PA pero sí ocupan espacio) solo puede visitarse UNA vez por Día de Laboratorio, por jugador — un peón de investigador marca el espacio con su color en cuanto lo visita, bloqueándolo para él (no para el resto de jugadores) hasta el día siguiente. Con 2-3 PA (Horas Extras incluida) esto significa: como máximo un uso de cada espacio distinto por día, nunca el mismo espacio dos veces. El tope es una propiedad **del espacio**, no del coste: la Acción E y el Descarte lo conservan aunque se paguen en Monedas o en agua. Las excepciones son Acción A y Horas Extras (que se limitan con su propio marcador de "ya usada", no con un espacio), Pedido de Urgencia, sin límite alguno (se autolimita por Datos de Investigación), y **Reclamar la Jefatura, que va justo al revés**: es el único espacio **global** del tablero, se agota para toda la mesa en cuanto un jugador lo visita, y por eso su marca vive en el motor y no en `acciones_pa_usadas_hoy`.

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
* **Prohibición:** una masa en **Crecimiento** no se puede hornear — todavía no es pan. `ActionManager.accion_F_hornear` lanza `RuleViolationError` y `disponibilidad.py` apaga el espacio con el motivo "La masa aún está creciendo". Se comprueba contra las zonas **efectivas** del jugador, aunque el crecimiento nunca se amplía, de modo que esa frontera no se mueve al instalar el Módulo Analítico. **No hay forma de abandonar una masa**: iniciar una receta es un compromiso irreversible, y una masa que no se quiere fermentará hasta hornearse o colapsar (el Simposio Técnico ya no descarta de una estación). No queda nunca atascada — la Fase III la hace avanzar todas las noches — así que lo que se pierde es la posibilidad de esquivar `penalizacion_colapso`, no el uso de la estación. Esto es lo que cierra el agujero de iniciar una receta y hornearla el mismo día desde la casilla 0, que pagaba como zona baja.
* **Resolución por zona:**
    * *Crecimiento:* no se hornea (ver arriba). Sin puntos, sin Monedas, sin Datos.
    * *Zona Óptima:* Ingreso completo en Monedas (`monedas_optima`) + Puntos de Maestría íntegros (`puntos_optimos`) + Datos de Investigación (1; **2 con Módulo Analítico**, y **3** si además es el centro exacto). Las zonas se leen ya ensanchadas por el Módulo del jugador: una posición que sin la mejora sería zona baja puede pagar como óptima con ella.
    * *Pre-fermento:* Venta con margen reducido en Monedas (`monedas_pre_fermento`) + Puntos de Maestría reducidos (`puntos_pre_fermento`), sin Datos.
    * *Colapso (Fase III):* Recuperación del coste base en Monedas (`monedas_colapso`) + Puntos de Maestría negativos (`penalizacion_colapso`), sin Datos.
* **Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado (y el horneado no fue un colapso), se suma el bono de Puntos de Maestría impreso en la carta (`bono_sabor_pts`) **y** +2 Monedas adicionales al ingreso de la venta.

### G. Investigar Protocolo
* **Costo:** 1 PA + **Monedas según el grado de la receta** (`engine.PRECIO_RECETA`: Básica 1, Intermedia 2, Avanzada 3). El precio es **aditivo** sobre el PA: el punto de acción y el espacio siguen siendo la escasez real. El precio se indexa por grado, que a su vez lo derivan las harinas impresas, así que no puede contradecir a la carta.
* **Orden de validación (fail-fast):** las Monedas se comprueban **antes** de retirar la carta del mercado. `Market.tomar_receta` la quita de la mesa, de modo que cobrar después haría que cada intento de un jugador sin dinero destruyera una carta para todos.
* **Límites:** Máximo 3 recetas inactivas (si está llena, debe descartar una previa); además, 1 vez por día (por espacio de acción — ver §1).
* **Efecto:** Selecciona 1 Carta de Receta del Mercado Central y la coloca boca arriba en la "Carpeta de Proyectos" (estado inactivo).
* **Mercado:** El espacio central queda vacío hasta que el "Protocolo de Refresco" del inicio del día siguiente reabastezca el Mercado Central a 4 recetas.

### Simposio Técnico (Generación de Datos)
* **Costo:** 1 PA + **un horneado exitoso del Archivo**. El PA es aditivo sobre el sacrificio, igual que el precio en Monedas de la Acción G lo es sobre su PA: el punto de acción sigue siendo la escasez real, y la acción termina el turno como cualquier otra Principal.
* **Límite:** 1 vez por día (por espacio de acción — ver §1).
* **Efecto:** Retira un registro de `archivo_horneado_exitoso` y otorga Datos de Investigación **según el grado de la carta**: **Básica 1, Intermedia 2, Avanzada 3** (`engine.DATOS_SIMPOSIO`). La carta física vuelve al descarte de recetas y puede reaparecer al rebarajar.
* **Es la única forma de sacar un registro del Archivo**, y por tanto la única forma de perder la renta de Ingresos de Panadería (ver CORE_MECHANICS.md §Fase III). Sacrificar un horneado cuesta a la vez:
    * sus Puntos de Maestría base (9-20 según la carta),
    * su renta diaria para el resto de la partida,
    * un escalón entero de «Variedad de Recetas» si era el único de su tipo (hasta -5 PM),
    * y un paso del contador X/5 que dispara el fin de partida.
* **Nada de esto necesita código que lo coordine:** `puntos_horneados`, `puntos_variedad` y `recetas_distintas_horneadas` se derivan todos de esa misma lista.
* **No es una jugada eficiente y no pretende serlo.** Ningún rendimiento en Datos compensa ese precio: es una **palanca de emergencia** — quemar un éxito pasado para salvar el presente — y en la práctica se sacrifica siempre la carta más barata que se tenga. Consecuencia emergente que se documenta y no se corrige: un jugador en 4/5 puede sacrificar un horneado para bajar a 3/5 y retrasar el final. Es carísimo, así que es legítimo. Lo que no puede es revertir un final ya disparado.
* **Ya NO descarta de la carpeta ni de una estación.** Descartar de la carpeta lo cubre la propia Acción G (parámetro `indice_descartar` cuando la carpeta está llena). Abandonar una masa **ya no es posible en absoluto**: ver §F.

### Reclamar la Jefatura
* **Costo:** 1 PA. Termina el turno como cualquier acción Principal.
* **Límite: UNO POR DÍA EN TODA LA MESA.** Es el único espacio **global** del tablero: el resto se limitan por jugador (`acciones_pa_usadas_hoy`), este se limita para todos a la vez, y por eso su marca vive en el motor (`GameEngine.jefatura_reclamada_por`) y no en el jugador. Reclamarla no solo la usa: se la quita a los demás.
* **Efecto:** `DATOS_JEFATURA` (= 1) Dato de Investigación **inmediato**, y el jugador abre la Fase II **de mañana** como Investigador Jefe (ver CORE_MECHANICS.md §Fase I).
* **El efecto es diferido a propósito.** El orden de turno se calcula una sola vez, en la Fase I, y no se rebaraja a media jornada: lo que se compra es la salida de mañana, no la de hoy.
* **Reclamar siendo ya Jefe es legal** y cuesta lo mismo — es la única forma de retener la Jefatura, ya que sin reclamación la ficha se queda donde está pero cualquiera puede comprarla.
* **Sustituye a la asignación automática por Vitalidad**, que no era una decisión de nadie y dejaba al Investigador Jefe sin más contenido que salir primero.
* **Es la fuente renovable de Datos que faltaba.** Los Datos salían de hornear en Zona Óptima, del Módulo Analítico (que es a su vez una compra en Datos) y del Simposio — casi todo de la misma jugada, de modo que quien horneaba bien primero acumulaba también la divisa técnica, y las dos acciones que se pagan en Datos (Horas Extras y Pedido de Urgencia) se quedaban sin combustible en la mesa de los demás. Aquí entra 1 Dato por día **en total**, repartido por rotación y no por riqueza: está limitado por competencia, no por precio, que es lo que impide que se convierta en un grifo.

---

## 3. Acciones Auxiliares y de Emergencia (Costo: 0 PA)

### A. Mantenimiento del Cultivo (Alimentación)
* **Costo:** 0 PA.
* **Límite:** 1 vez por ronda (valida `accion_alimentar_usada == False`).
* **Efecto:** Restar **1 Token de Harina — 1 (10%)** (de cualquier tipo) = **+1 Vitalidad** (Máx 6). Repone exactamente el -1 del desgaste metabólico de Fase III, de modo que quien alimenta a diario orbita su Vitalidad inicial.
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
* **Efecto:** Ignora el Mercado por completo (y su precio vigente) y obtiene directamente de la reserva general UN tipo de recurso: **media bolsa de Harina — 5 (50%)** de un tipo elegido O los **Tokens de Agua** que el jugador indique (5% c/u), a elección del jugador.
* **Por qué media bolsa y no una entera:** el Pedido era, además de un rescate logístico, el mejor arbitraje de la partida — 1 Dato compraba una bolsa entera de *cualquier* harina, y una bolsa de Centeno en posición 5 se revende en el acto por 7 Monedas. Con el Contrato con el Molino (§C) convirtiendo la venta de harina en una línea económica real, ese bucle habría escalado antes que ninguna otra cosa. Media bolsa conserva la función de emergencia (2 Pedidos completan una bolsa entera, y una receta Intermedia sólo pide 50% de cada harina, o sea un Pedido exacto por mitad) y parte el arbitraje por más de la mitad, porque la venta de media bolsa redondea hacia **abajo**: el Centeno en posición 5 baja de 7 a 3 Monedas por Dato.
* **Límite:** Ninguno — a diferencia de Horas Extras, no hay tope de usos por ronda; se autolimita por los Datos de Investigación disponibles. A diferencia de las Acciones B a I y Simposio Técnico, Pedido de Urgencia no cuesta PA y por lo tanto queda exento de la regla "1 vez por día por espacio de acción" (§1) — es intencional, no un descuido.

### Protocolos de Emergencia (Rescate de Cultivo)
*Solo pueden ejecutarse si la Vitalidad del cultivo base llega a 0, momento en el cual el jugador recibe una penalización de -3 Puntos de Maestría.*
* **H. Re-cultivo Manual:** Costo 1 PA + **3 Tokens de Harina — 3 (30%)** (de cualquier tipo). Bajó de 50% a 30% al endurecerse el juego alrededor de la contaminación: los Datos ahora sólo salen de hornear bien o de sacrificar un horneado, así que un jugador contaminado temprano puede no tener ninguno para el Protocolo I, y H es la vía comprable y tiene que seguir siéndolo. A 30% cabe en la bolsa inicial de Patrocinio incluso tras varias Acciones A, de modo que rescatarse nunca obliga a gastar antes una visita entera en el mercado. Sigue siendo el peor de los dos rescates (Nivel 1 frente al Nivel 2 del Protocolo I). Sin costo de Agua. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 1. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.
* **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 2. Límite: 1 vez por día (por espacio de acción — ver §1), además de requerir contaminación activa.