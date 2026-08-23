# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación.

---

## 2. Catálogo de Acciones Principales (Costo: 1 PA)
*(Nota: La Acción A original se mueve a auxiliares. La Acción B ahora requiere restar 100 unidades de la harina específica en el diccionario).*

### B. Iniciar Receta
* **Costo:** 1 PA + 1 Token de Harina (100% base) + Tokens de Agua (pago exacto según porcentaje de hidratación de la receta).
* **Memoria Biológica:** Se sella el Dado de Inóculo (con la Vitalidad actual) y el Cubo de Laboratorio (con la Acidez actual) en la carta de receta.
* **Condición:** El Cubo de Acidez solo se sella si la acidez del cultivo base se encuentra dentro del rango con bonificación de sabor exigido por la receta.

### C. Visitar el Mercado
* **Costo:** 1 PA.
* **Efecto:** El Mercado de Insumos donde se comercian los diferentes insumos del juego: comprar o vender harina, y adquirir agua para completar los insumos requeridos por las recetas.
    * *Comprar Harina:* Pagar el coste visible de Compra (en Monedas, según la posición actual del visor en la Bolsa de Harinas) y mover el visor 1 casilla a la derecha (tope en posición 5).
    * *Vender Harina:* Cobrar el valor visible de Venta en Monedas y mover el visor 1 casilla a la izquierda (tope en posición 1).
    * *Comprar Lote de Agua:* Pagar el coste en Monedas según la fila de temperatura actual (Lote 10%, 30%, 60% o 100%) y recibir los tokens correspondientes (1 token = 5% hidratación).
* **Regla de Exclusividad:** una visita (1 PA) puede incluir como máximo UNA transacción por tipo de recurso — comprar Blanca y vender Centeno y comprar un lote de agua en la misma visita está permitido; comprar o vender el mismo tipo dos veces en la misma visita no lo está.
* **Tablas de precio** (posición del visor 1-5 → Monedas):

  | | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | Blanca (Compra/Venta) | 2/1 | 3/2 | 4/3 | 5/4 | 6/5 |
  | Integral (Compra/Venta) | 4/2 | 5/3 | 6/4 | 7/5 | 8/6 |
  | Centeno (Compra/Venta) | 6/3 | 7/4 | 8/5 | 9/6 | 10/7 |

  Agua (Monedas por temperatura °C × tamaño de lote %):

  | °C \ Lote | 10% | 30% | 60% | 100% |
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
* **Reglas:** El beneficio se activa inmediatamente y se marca con un Cubo de Laboratorio en la Zona 4. Cada mejora individual solo puede adquirirse UNA vez por partida, pero un jugador puede llegar a instalar varias mejoras distintas a lo largo de la partida (no hay tope global de "una mejora total").

### E. Técnica (Pliegues)
* **Costo:** 1 PA.
* **Efecto:** Avanza el marcador de Inóculo de una masa 1 casilla.
* **Sinergia:** Con la mejora Cámara B, el jugador puede optar por recuperar +1 de Vitalidad en su cultivo base o afectar a dos masas simultáneamente.

### F. Hornear y Vender (Finalización de Protocolo)
* **Costo:** 1 PA.
* **Efecto:** El jugador obtiene Puntos de Maestría según la zona en la que se encuentre el marcador. Al hornear, además cobra ingresos en Monedas, y si está en Zona Óptima también recibe Datos de Investigación.
* **Resolución por zona:**
    * *Zona Óptima:* Ingreso completo en Monedas (`monedas_optima`) + Puntos de Maestría íntegros (`puntos_optimos`) + Datos de Investigación.
    * *Zona Baja:* Venta con margen reducido en Monedas (`monedas_baja`) + Puntos de Maestría reducidos (`puntos_baja`), sin Datos.
    * *Zona Sobre-fermentada (colapso, Fase III):* Recuperación del coste base en Monedas (`monedas_sobre`) + Puntos de Maestría negativos (`penalizacion_colapso`), sin Datos.
* **Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado (y el horneado no fue un colapso), se suma el bono de Puntos de Maestría impreso en la carta (`bono_sabor_pts`) **y** +2 Monedas adicionales al ingreso de la venta.

### G. Investigar Protocolo
* **Costo:** 1 PA.
* **Efecto:** Selecciona 1 Carta de Receta del Mercado Central y la coloca boca arriba en la "Carpeta de Proyectos" (estado inactivo).
* **Límites:** Máximo 3 recetas inactivas. Si está llena, debe descartar una previa.
* **Mercado:** El espacio central queda vacío hasta el "Protocolo de Refresco" del día siguiente.

### Simposio Técnico (Generación de Datos)
* **Costo:** 1 PA.
* **Efecto:** Descartar una Carta de Receta de la carpeta de proyectos o de la estación de fermentación para ganar 1 Dato de Investigación inmediatamente.

---

## 3. Acciones Auxiliares y de Emergencia (Costo: 0 PA)

### A. Mantenimiento del Cultivo (Alimentación)
* **Costo:** 0 PA.
* **Límite:** 1 vez por ronda (valida `accion_alimentar_usada == False`).
* **Efecto Modular:** * Restar 10% de Harina (cualquiera) = +1 Vitalidad (Máx 6).
    * Restar 10% de Agua = +1 Acidez (Máx 6).
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
* **Efecto:** Ignora el Mercado por completo (y su precio vigente) y obtiene directamente de la reserva general UN tipo de recurso: harina (100% de un tipo elegido) O tokens de agua (5% c/u), a elección del jugador.
* **Límite:** Ninguno — a diferencia de Horas Extras, no hay tope de usos por ronda; se autolimita por los Datos de Investigación disponibles.

### Protocolos de Emergencia (Rescate de Cultivo)
*Solo pueden ejecutarse si la Vitalidad del cultivo base llega a 0, momento en el cual el jugador recibe una penalización de -3 Puntos de Maestría.*
* **H. Re-cultivo Manual:** Costo 1 PA + 50% de Harina (cualquier tipo). Sin costo de Agua. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 1.
* **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 2.