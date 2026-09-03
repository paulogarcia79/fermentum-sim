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
* **Actualización de Jerarquía:** El token de Investigador Jefe pasa a quien **reclamó la Jefatura** el día anterior ocupando su espacio de acción (1 PA; ver ACTIONS_REGISTRY.md §Jefatura). La reclamación se consume al aplicarse: vale para un día, no se acumula.
    * *Si nadie la reclamó:* la ficha **se queda donde está** — el Jefe de ayer sigue siéndolo. Es semántica de ficha física, sin una segunda regla de rotación que recordar, y deja la Jefatura sin dueño nuevo mientras a nadie le compense pagar 1 PA por ella.
    * *Ventaja:* El Investigador Jefe actúa primero en la Fase II y tiene prioridad en los mercados.
    * *Excepción Día 1:* En la primera ronda, el orden se determina por la Iniciativa de la Carta de Patrocinio de cada jugador (ver PLAYER_STATE.md §2) — nadie ha podido reclamar todavía.
    * *Regla retirada:* hasta la versión anterior la Jefatura se asignaba automáticamente a la mayor Vitalidad, con los Datos como desempate. Eso no era una decisión de nadie — el orden de turno se deducía del estado — y dejaba al rol sin más contenido que salir primero. Ahora ir primero se paga, y quien paga se lleva además el Dato que hace de esta la única fuente **renovable** de Datos de Investigación de la partida.
* **Resolución del Clima:** Se revela una carta del mazo de Clima. **(CRÍTICO PARA EL CLIENTE: el sistema debe anunciar claramente el nombre de la carta, su modificador térmico y su efecto pasivo para que los jugadores puedan tomar decisiones — hoy lo cumple `InicioDiaModal.vue`, de descarte obligatorio).**
    * Se ajusta el termómetro en el tablero sumando o restando el Modificador Térmico a la base de 20°C.
    * Se sincroniza el "Ábaco de Fermentación" (20°C = 4 Pasos; 25°C = 5 Pasos; 30°C = 6 Pasos).
    * Se aplican Anomalías Biológicas instantáneamente (ej. +1 Vitalidad para todos) o Efectos Pasivos.
* **Mercado de Tendencias (anuncio):** Se revela una carta del mazo de Tendencias de Mercado (21 cartas: -2×1, -1×7, 0×5, +1×7, +2×1) y queda a la vista de todos durante el día. **Este paso no mueve ningún visor:** la carta es un pronóstico y se aplica al final de este mismo día (ver Fase III), por lo que rige los precios del día SIGUIENTE. Los precios de hoy son los que dejó la tendencia de ayer, ya conocidos cuando los jugadores deciden comprar o vender.
* **Protocolo de Refresco (reabastecimiento):** Recetas — se compactan las cartas supervivientes conservando su orden (más nueva → más antigua) y se revelan cartas nuevas a la izquierda hasta volver a tener 4 recetas visibles, rellenando tanto los huecos dejados por la Acción G del día anterior como el que dejó el descarte de fin de día (ver Fase III). Si el mazo se agota, se baraja el descarte como nuevo mazo. **Este paso ya no descarta ninguna carta** — el descarte de la más antigua se movió al final de la Fase III.

### FASE II: Acción (Operatividad)
Fase donde los jugadores intervienen en su laboratorio mediante un sistema de "Round-Robin" (turnos alternos).
* **Capacidad:** Cada jugador dispone de 2 PA.
* **Flujo Intercalado:** Empezando por el Investigador Jefe, el jugador activo ejecuta **solo 1 acción** (o pasa). Luego el control pasa al siguiente jugador. El ciclo (while loop) continúa hasta que la suma de PA de todos los jugadores sea 0 y nadie conserve una acción gratuita pendiente (Acción A, Horas Extras, Pedido de Urgencia o el espacio de Pliegues sin usar y con Monedas para pagarlo).
* **Registro:** Se marca el uso de PA moviendo Cubos de Laboratorio en la Zona 5 (Checklist) del tablero personal.
* **Un espacio, una visita por día:** cada espacio de acción (Acciones B a G, Simposio Técnico, H, I y también E — ver ACTIONS_REGISTRY.md §1) solo puede ser visitado UNA vez por Día de Laboratorio por cada jugador; visitarlo lo marca con el color de ese jugador (bloqueado para él, no para el resto) hasta el reinicio del siguiente Día de Laboratorio. El tope es propiedad del espacio, no del coste: la **Acción E (Pliegues)** se paga en Monedas y no gasta PA, pero ocupa su espacio igual. Pedido de Urgencia queda exento (sin límite), y Acción A y Horas Extras se limitan con su propio marcador de "ya usada". Hay **dos excepciones con costo de PA, y son simétricas**: **Reclamar la Jefatura** es el único espacio **global** — se agota para toda la mesa en cuanto un jugador lo visita, no solo para él — y el **Turno de Mostrador** no se agota nunca, porque cuesta PA pero no ocupa espacio alguno, de modo que se repite mientras queden Puntos de Acción (ACTIONS_REGISTRY.md §2 «Mostrador»). Esta última existe para que un jugador con PA y sin ninguna jugada útil no tenga que renunciar al resto del día pasando turno: los PA sobrantes no se convierten en nada al llegar la Fase III.
* **Escasez de Mercado:** Durante esta fase, si un jugador investiga una receta (Acción G), el espacio del mercado queda vacío hasta la próxima Fase I. La harina y el agua, en cambio, ya no son un slot consumible — son un track de precio compartido (Bolsa de Harinas) y una matriz de precio por temperatura (Suministro Hídrico Global) que cualquier jugador puede usar en Visitar el Mercado (Acción C) sin agotar un cupo.

### FASE III: Fermentación (Resolución Automática)
Ocurre simultáneamente para todos una vez terminada la Fase II.
* **Cinética Biológica (Avance de Masas):** Las masas en la Zona 2 avanzan en sus tracks según la siguiente ecuación:
    > `Avance Final = (Temperatura Ambiental / 5) + (Valor del Dado de Inóculo) + (Modificadores de Tecnología)` 

    El único modificador de tecnología es el **dial de la Incubadora** (`-1/0/+1`), que su dueño fija en la Fase II sobre cada masa por separado y que esta misma fase devuelve a 0 tras aplicarlo (ACTIONS_REGISTRY.md §3 «Incubadora»). El Dado de Inóculo, en cambio, sí queda sellado desde la Acción B.
* **Cuatro zonas del track:** de menos a más fermentada — **Crecimiento** (la masa aún no es pan: la Acción F la rechaza, no hay pago posible), **Pre-fermento** (cruda, hornea con puntos y Monedas reducidos), **Óptima** (puntos completos y Datos) y **Colapso**. Toda masa nace en la casilla 0, que cuenta como Crecimiento: `Recipe.esta_en_crecimiento` es el caso por DEFECTO y no un rango cerrado, precisamente para que ninguna posición quede sin zona y pagando por accidente.
* **Colapso Estructural:** Si el avance hace que una masa supere la zona óptima de horneado (llegando al Colapso), la masa colapsa. 
    * *Resolución:* Se hornea automáticamente (Costo: 0 PA), aplicando los puntos negativos de la carta.
    * *Zona efectiva, no impresa:* el umbral se lee contra las zonas **del propietario de la masa**, no contra las de la carta. El Módulo Analítico ensancha la zona óptima 1 casilla por lado y con ella empuja el umbral de colapso una casilla más arriba (`Recipe.zonas_efectivas`, ver RECIPE_DATABASE.md §1). Es un efecto en vivo: instalar el Módulo salva una masa que ya está fermentando.
* **Metabolismo (Desgaste):** La Vitalidad del cultivo base (Zona 1) se reduce automáticamente en -1 punto. La tecnología Criopreservación lo ignora por completo, salvo que su dueño haya **suspendido la Estasis** para esta noche con la acción gratuita del mismo nombre (ACTIONS_REGISTRY.md §3), que es la única forma de bajar la Vitalidad a propósito y con ella el Dado de Inóculo que sella la Acción B; la bandera se limpia en esta misma fase. (Nota: Los valores de Vitalidad y Acidez nunca pueden bajar de 0 ). Como la Acción A repone +1 una vez al día, un jugador que alimenta a diario **orbita en su Vitalidad inicial**, que es 2 (ver PLAYER_STATE.md §2) — de ahí que «Aletargamiento Invernal» (-2) lo deje en 1 y no en 0.
* **Ingresos de Panadería:** Cada horneado **exitoso** del Archivo de cada jugador le paga Monedas, todas las noches, mientras siga en el archivo: **Básica 1, Intermedia 2, Avanzada 3** (`engine.PRECIO_RENTA`). Una receta horneada con éxito deja de ser historial y pasa a ser una fuente de ingresos — la panadería acumula clientela — de modo que hornear pronto rinde más que hornear tarde. No es dinero nuevo: los pagos por zona de las 12 cartas se recortaron en `renta × 3` sobre las tres zonas, así que el total se conserva y lo que cambia es *cuándo* se cobra; ese 3 es un **horizonte de amortización común a todos los grados**, para que la presión temporal sea idéntica se juegue la carta que se juegue. Un horneado hecho en la Fase II de hoy ya está en el archivo, así que **cobra esa misma noche**. Los **colapsos no rinden nada** (`archivo_colapsos`): provocar un colapso es gratis, así que pagarlo regalaría la renta sin hornear bien nada — el mismo argumento de incentivos que rige «Variedad de Recetas». La renta se **deriva del archivo vivo y no se cachea en ninguna parte**, y por eso sacrificar un horneado en el Simposio Técnico (ver ACTIONS_REGISTRY.md) corta su ingreso sin que ninguna regla tenga que coordinarlo.
* **Entrega del Molino:** Cada jugador con un **Contrato con el Molino** firmado (Acción C, ver ACTIONS_REGISTRY.md §C) recibe **2 Tokens — 2 (20%)** de la harina contratada, todas las noches, para siempre (`engine.RENDIMIENTO_MOLINO_PCT`). Es la **única fuente de harina que no pasa por la Bolsa**, y existe porque sin ella vender harina no era una línea económica: la única forma de tener harina era comprarla, y comprar mueve el visor en tu contra antes de que puedas vender. La entrega es la misma para los tres tipos — lo que escala es el precio del contrato — y se **deriva del contrato vivo**, sin ningún campo de producción diaria cacheado, igual que la renta se deriva del archivo vivo. Va detrás de los Ingresos de Panadería solo por relato (primero el dinero, luego la harina): son estrictamente independientes, el molino no cobra nada por entregar.
* **Rotación del Mercado (fin de día):** Se descarta la receta visible más antigua del Mercado Central (la carta real más a la derecha; si ese extremo ya está vacío por una Acción G, se descarta la siguiente carta real hacia la izquierda). El hueco resultante lo rellena el Protocolo de Refresco de la Fase I del día siguiente.
* **Mercado de Tendencias (aplicación):** Se cobra ahora la carta anunciada esta mañana (ver Fase I): su modificador desplaza simultáneamente los 3 visores de la Bolsa de Harinas (Blanca/Integral/Centeno), cada uno con tope independiente en [1, 5] (sin arrastre más allá del límite). Los precios resultantes son los que regirán el día siguiente. La carta pasa entonces al descarte de Tendencias; si el mazo se agota, se baraja ese descarte como mazo nuevo.

---

## 3. Fin del Juego y Puntuación

### Gatillos de Finalización
El final del juego se desencadena de inmediato si ocurre una de estas dos condiciones:
1. El mazo de Clima se agota por completo (detectado en `_robar_carta_clima`, durante la Fase I).
2. Un jugador hornea exitosamente su **quinta (5ta) receta** (las recetas colapsadas con valor negativo no cuentan).

*Desencadenar el final no detiene el juego: se termina el Día de Laboratorio en curso —Fase II
entera y Fase III completa— y solo entonces se puntúa, de modo que todos los jugadores disputan el
mismo número de días.* En el motor esto es exactamente lo que significa `partida_terminada`: un
**pestillo de gatillo**, no «la partida acabó». Ningún camino de la Fase II lo lee; el único que lo
consulta es `iniciar_dia`, que impide abrir un día de más. Quien necesite saber si la partida
terminó de verdad debe mirar `fase_actual == Fase.TERMINADA`, que solo se alcanza tras el
`resolver_fase_III` de esa última jornada (o de inmediato con el fin anticipado por voto unánime,
`forzar_fin_de_partida`, que es la única forma de cortar la última jornada). El pestillo no se
revierte: sacrificar el 5º horneado con un Simposio Técnico después del gatillo no cancela el
final.

### Cálculo de Puntos de Maestría Finales
1. **Puntos Base:** Suma de los puntos de todas las recetas horneadas (positivos y negativos).
2. **Puntos de Sabor:** Suma de los bonos de Acidez impresos en las cartas que tengan un Cubo de Laboratorio sellado.
3. **Madurez del Cultivo:** `vitalidad + (PUNTOS_EQUILIBRIO_MAX - |acidez - ACIDEZ_EQUILIBRIO_CENTRO|)`, es decir `vitalidad + (3 - |acidez - 3|)` (`models.Player.puntos_equilibrio_acidez`). La Vitalidad puntúa entera; la Acidez puntúa por lo **centrada** que esté, no por lo alta que sea: 0, +1, +2, **+3**, +2, +1, 0 para los niveles 0 a 6. No necesita `max(0, ...)` porque el centro está a distancia 3 de ambos bordes y `acidez` ya vive acotada en [0, 6].

   Premiaba antes la acidez **cruda** (`ceil((vitalidad + acidez) / 2)`), lo que no tenía coste alguno mientras la Acidez sólo sabía subir — el juego empujaba a todo el mundo al mismo extremo y luego castigaba haberlo seguido. Con la Acidez convertida en un dial bidireccional (acción Descarte, ACTIONS_REGISTRY.md), premiar el equilibrio es lo que le da un precio a perseguir una diana extrema; es el reverso exacto de cómo se derivan los `bono_sabor_pts` del catálogo (RECIPE_DATABASE.md).
4. **Variedad de Recetas:** puntos por la amplitud del repertorio horneado — el número de recetas **distintas** (por carta, no por copia) en el archivo de horneados exitosos, en la curva triangular `models.puntos_triangulares` (`n*(n+1)/2`):

   | Recetas distintas | 0 | 1 | 2 | 3 | 4 | 5 |
   |---|---|---|---|---|---|---|
   | Puntos de Maestría | 0 | +1 | +3 | +6 | +10 | +15 |

   Sólo cuenta el archivo de horneados **exitosos**: un colapso nunca aporta variedad, ni siquiera de una carta que no se haya horneado bien nunca. La razón es de incentivos — provocar un colapso es gratis (iniciar una masa y dejar que la Fase III la hornee sola al sobrefermentar), así que contarlo permitiría cosechar el bono sin hornear bien nada. El mazo reparte varias copias de cada carta (ver RECIPE_DATABASE.md), de modo que hornear dos veces el mismo pan cuenta como **una** clase. Como la partida termina al quinto horneado exitoso, el tope real del término es +15, y repetir una sola carta renuncia al incremento más grande de la curva.
5. **Desarrollo Tecnológico:** puntos por la amplitud del laboratorio construido — el número de mejoras **instaladas** (`Technologies.cantidad_instaladas`), en la **misma** curva triangular que «Variedad de Recetas» (`models.puntos_triangulares`, una sola derivación para las dos tablas):

   | Mejoras instaladas | 0 | 1 | 2 | 3 | 4 | 5 |
   |---|---|---|---|---|---|---|
   | Puntos de Maestría | 0 | +1 | +3 | +6 | +10 | +15 |

   Desde que existe Comerciante (la quinta mejora) los dos términos de amplitud llegan al mismo tope, +15, por motivos distintos: aquí porque hay cinco mejoras, en Variedad porque la partida termina al quinto horneado. La curva **no se topa a mano** en ninguno de los dos — se acaba donde se acaba el recuento, que es precisamente lo que permitió añadir una quinta mejora sin tocar la puntuación ni el snapshot dorado. Equiparse del todo cuesta 16 Datos, así que es una línea de partida entera y no un extra. La intención es de **simetría**, no de reequilibrio — la puntuación premiaba *qué horneas* y era indiferente al **motor que construyes**, así que «amplitud del laboratorio» acompaña a «amplitud del repertorio». Se acepta con los ojos abiertos que las tecnologías pasan a cobrar por **tercera** vez, encima de sus dos beneficios en partida (el Módulo ensancha la óptima, la Criopreservación esquiva el desgaste, la Cámara B abre la Estación 03, la Incubadora pone un dial de ±1 casilla sobre cada masa y cada noche, el Comerciante abarata cada compra).

   **No se pondera por coste**: Criopreservación (2 Datos) cuenta igual que Cámara B (4), exactamente como una Básica y una Avanzada cuentan una clase cada una en Variedad pese a costar 1 y 3 Monedas. Una tabla de tramos sobre los Datos invertidos se descartó por dos razones: sería una segunda tabla que no se deriva de ninguna carta, y se desviaría en silencio el día que se reequilibre `COSTOS_TECNOLOGIA`. La consecuencia — comprar primero lo barato es estrictamente correcto — está aceptada: es un empujón de **orden**, no una línea dominante, porque el incremento más grande sigue exigiendo las cinco y la mejora que te saltes es justo la que querías.

   A diferencia de Variedad, este término **nunca baja**. El Simposio Técnico saca un horneado del archivo y hace caer un escalón de Variedad; nada desinstala una mejora, porque `Technologies.activar` no tiene inversa. La asimetría es **deliberada**: hacerlo reversible exigiría una acción nueva con sus reglas de disponibilidad, su modal, su sonido y su sección de reglamento — otra funcionalidad, no ésta. No es un descuido pendiente de arreglar.

   El término **no toca el desempate**: el recuento de tecnologías correlaciona con los Datos, que ya son el cuarto criterio, así que sería un escalón redundante.

6. **Desperdicio (Penalización):** -1 punto de Maestría por cada 3 **tokens de insumo** sin utilizar en la reserva. Un **Token de Harina (10%)** y un **Token de Agua (5%)** cuentan **1:1** aquí, pese a representar porcentajes distintos: se suman en un único total (`sum(reserva_harina) / 10 + reserva_agua`) y de ahí sale la división entera por 3. Esta es la única regla del juego que suma los dos insumos, y es la que fija el 10% como unidad atómica de la harina — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)".
7. **Contaminación (Penalización):** -3 puntos de Maestría por cada episodio de contaminación sufrido (cada vez que la Vitalidad llegó a 0), acumulativo.
8. **Conversión de Riqueza:** +1 punto de Maestría por cada 5 Monedas restantes en la reserva final (división entera).

### Desempate
En caso de empate en Puntos de Maestría, el ganador se determina por:
1. El investigador con más recetas **distintas** horneadas con éxito (el mismo recuento que alimenta «Variedad de Recetas»).
2. Si persiste el empate, el investigador con el mayor Nivel de Vitalidad en su cultivo base.
3. Si persiste el empate, el jugador con más Datos de Investigación.
4. Si persiste el empate, los investigadores empatados **comparten el puesto**: si es el primero, comparten la victoria y el siguiente jugador ocupa el tercer puesto. No hay un quinto criterio — el orden de inscripción no decide nada, porque no es una decisión de nadie.