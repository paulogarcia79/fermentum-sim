# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación. **Un Token de Harina = 10%; un Token de Agua = 5% de hidratación** — ver PLAYER_STATE.md §"Unidades de Insumo (Tokens)" para la notación `N (P%)` usada en todo este registro.
* **Un espacio de acción, una visita por día:** cada espacio de acción con costo de PA (B a G, Simposio Técnico, H, I) solo puede visitarse UNA vez por Día de Laboratorio, por jugador — un peón de investigador marca el espacio con su color en cuanto lo visita, bloqueándolo para él (no para el resto de jugadores) hasta el día siguiente. Con 2-3 PA (Horas Extras incluida) esto significa: como máximo un uso de cada espacio distinto por día, nunca el mismo espacio dos veces. Pedido de Urgencia queda exento (ver su entrada en §3): no cuesta PA y se autolimita por Datos de Investigación.

---

## 2. Catálogo de Acciones Principales (Costo: 1 PA)
*(Nota: La Acción A original se mueve a auxiliares. La Acción B ahora requiere restar 100 unidades — es decir 10 Tokens de Harina, el 100% — de la harina específica en el diccionario).*

### B. Iniciar Receta
* **Costo:** 1 PA + **10 Tokens de Harina — 10 (100%), una bolsa entera** del tipo que pida la receta + los **Tokens de Agua** exactos que la receta imprima (ver RECIPE_DATABASE.md; cada token = 5% de hidratación).
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
    * *Módulo Analítico:* 3 Datos. Genera +1 Dato extra al hornear en centro exacto y habilita recetas avanzadas.
    * *Criopreservación:* 2 Datos. Efecto Pasivo "Estasis Biológica" — durante la Fase III, el cultivo base ignora el desgaste metabólico normal (no resta Vitalidad).
* **Límites:** Cada mejora individual solo puede adquirirse UNA vez por partida, pero un jugador puede llegar a instalar varias mejoras distintas a lo largo de la partida (no hay tope global de "una mejora total"). Además, el espacio D en sí solo puede visitarse 1 vez por día (§1): instalar CUALQUIER mejora agota el espacio para el resto del día, así que dos mejoras distintas nunca pueden instalarse el mismo día — como muy pronto, la segunda espera al día siguiente.
* **Reglas:** El beneficio se activa inmediatamente y se marca con un Cubo de Laboratorio en la Zona 4.

### E. Técnica (Pliegues)
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1) — incluye todas sus variantes (avanzar, recuperar vitalidad, doble masa): usar cualquiera de ellas agota el espacio E para el resto del día.
* **Efecto:** Avanza el marcador de Inóculo de una masa 1 casilla.
* **Sinergia:** Con la mejora Cámara B, el jugador puede optar por recuperar +1 de Vitalidad en su cultivo base o afectar a dos masas simultáneamente.

### F. Hornear y Vender (Finalización de Protocolo)
* **Costo:** 1 PA.
* **Límite:** 1 vez por día (por espacio de acción — ver §1). No aplica al colapso automático de Fase III (sobrefermentación), que no pasa por este espacio ni consume PA.
* **Efecto:** El jugador obtiene Puntos de Maestría según la zona en la que se encuentre el marcador. Al hornear, además cobra ingresos en Monedas, y si está en Zona Óptima también recibe Datos de Investigación.
* **Resolución por zona:**
    * *Zona Óptima:* Ingreso completo en Monedas (`monedas_optima`) + Puntos de Maestría íntegros (`puntos_optimos`) + Datos de Investigación.
    * *Zona Baja:* Venta con margen reducido en Monedas (`monedas_baja`) + Puntos de Maestría reducidos (`puntos_baja`), sin Datos.
    * *Zona Sobre-fermentada (colapso, Fase III):* Recuperación del coste base en Monedas (`monedas_sobre`) + Puntos de Maestría negativos (`penalizacion_colapso`), sin Datos.
* **Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado (y el horneado no fue un colapso), se suma el bono de Puntos de Maestría impreso en la carta (`bono_sabor_pts`) **y** +2 Monedas adicionales al ingreso de la venta.

### G. Investigar Protocolo
* **Costo:** 1 PA.
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