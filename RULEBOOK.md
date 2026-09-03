<!--
  MANTENIMIENTO — leer antes de editar.

  Este fichero tiene un GEMELO: RULEBOOK.html, la misma reglamentación como página
  autónoma con estilos. NO hay ningún script que genere uno a partir del otro: se
  mantienen a mano en paralelo, así que editar solo uno deja el trabajo a medias.

  Todo cambio de regla debe tocar, en el MISMO commit, los cuatro sitios:
    1. el código (models.py / engine.py / actions.py / ...)
    2. context/*.md          — la especificación de implementación
    3. RULEBOOK.md           — este fichero
    4. RULEBOOK.html         — el gemelo

  Ya se olvidó dos veces en silencio (ver CLAUDE.md, "Every rules change MUST update
  the rulebooks"). Ningún test lee estos ficheros.

  Fermentum_ GDDv0.0.2.pdf es LEGADO y NO es autoritativo. No es fuente de verdad.
-->

# Fermentum — Reglamento Completo

*Versión del reglamento correspondiente a la revisión de reglas GDD v0.0.2. Este documento es la
referencia canónica y legible del juego: cualquier cambio de regla futuro debe editarse aquí
directamente, en esta misma estructura.*

## Índice

1. [Introducción y Objetivo](#1-introducción-y-objetivo)
2. [Componentes](#2-componentes)
3. [Preparación de la Partida](#3-preparación-de-la-partida)
4. [Estructura del Día de Laboratorio](#4-estructura-del-día-de-laboratorio)
5. [Fase I: Ambiente](#5-fase-i-ambiente)
6. [Fase II: Acción](#6-fase-ii-acción)
7. [Catálogo de Acciones](#7-catálogo-de-acciones)
8. [Catálogo de Recetas](#8-catálogo-de-recetas)
9. [Fase III: Fermentación](#9-fase-iii-fermentación)
10. [Tecnologías de Laboratorio](#10-tecnologías-de-laboratorio)
11. [Fin del Juego y Puntuación](#11-fin-del-juego-y-puntuación)
12. [Anexo: Resumen de Mazos](#12-anexo-resumen-de-mazos)

---

## 1. Introducción y Objetivo

Fermentum es una simulación competitiva de gestión de recursos y construcción de motores
("engine-building") para 1 a 4 jugadores, ambientada en un laboratorio de panadería científica.
Cada jugador dirige un investigador que cultiva y mantiene una masa madre viva, la utiliza para
producir distintas recetas de panificación, y comercia con harina, agua y monedas para sostener su
operación.

Los jugadores compiten por acumular la mayor cantidad de **Puntos de Maestría**. Estos se obtienen
principalmente:

- Horneando recetas con éxito, especialmente en su Zona Óptima de fermentación.
- Horneando recetas **variadas**: cada tipo nuevo de pan vale más que el anterior.
- Equipando el laboratorio con **Tecnologías**: cada mejora instalada puntúa al final, y también
  con una curva creciente.
- Manteniendo una masa madre con alta Vitalidad y un buen equilibrio de Acidez hasta el final de
  la partida.
- Gestionando con cuidado la economía del laboratorio: insumos, Datos de Investigación y Monedas.

El final se desencadena en cuanto se agota el mazo de Clima, o en cuanto algún jugador hornea con
éxito su quinta receta — lo que ocurra primero. La partida no se corta ahí: se juega el Día de
Laboratorio en curso hasta el final, de modo que todos los jugadores disputan el mismo número de
días.

---

## 2. Componentes

- **Tablero Central (El Laboratorio):** controla el estado global — termómetro/Ábaco de
  Fermentación, mercado de recetas, Bolsa de Harinas y Suministro Hídrico Global, y el Track de
  Orden de Turno.
- **Tableros Individuales:** uno por jugador, dividido en zonas — Cultivo Base (Vitalidad y
  Acidez), Estaciones de Fermentación (3, la tercera bloqueada al inicio), Tecnologías de
  Laboratorio, y Carpeta de Proyectos (recetas investigadas pero no iniciadas).
- **Cartas de Receta:** 36 en total — **12 protocolos distintos** (4 Básicas, 4 Intermedias, 4
  Avanzadas) con distinto número de copias cada uno: las Básicas son comunes y las Avanzadas
  escasas. Definen el protocolo de horneado de cada pan — ver
  [Catálogo de Recetas](#8-catálogo-de-recetas).
- **Cartas de Clima:** 30 cartas que regulan la temperatura y los eventos biológicos del
  laboratorio — ver [Anexo](#12-anexo-resumen-de-mazos).
- **Cartas de Tendencias de Mercado:** 21 cartas que mueven el precio de la harina. Cada una se
  anuncia al inicio de un día y se aplica al final de ese mismo día, fijando los precios del
  siguiente.
- **Cartas de Patrocinio:** 8 cartas usadas una sola vez, al preparar la partida, para repartir el
  orden de turno inicial y los recursos de arranque.
- **Dados de Inóculo:** 3 por jugador, sellan la velocidad de fermentación de cada masa iniciada.
- **Cubos de Laboratorio:** 9 por jugador, marcan acciones usadas, acidez sellada y tecnologías
  instaladas.
- **Tokens de Recursos:** harina (Blanca, Integral, Centeno) y agua — ver [Las dos unidades de
  insumo](#las-dos-unidades-de-insumo) justo abajo.
- **Fichas de Monedas** y **Tokens de Datos de Investigación:** las dos divisas del juego (ver más
  abajo).

### Las dos unidades de insumo

Los dos insumos físicos se cuentan en **tokens**. Lo único que cambia entre ellos es cuánto vale
un token:

| Insumo | 1 token equivale a | Unidad de compra habitual |
|:---|:---|:---|
| **Harina** | **10%** | 1 bolsa = 100% = **10 tokens**; media bolsa = **5 (50%)** |
| **Agua** | **5%** de hidratación | lote del 100% = **20 tokens** |

En todo este reglamento las cantidades se escriben **`N (P%)`** — primero el número de tokens,
después su porcentaje. Así, `10 (100%)` es una bolsa entera de harina y `20 (100%)` es un lote
completo de agua.

Ambos tipos de token cuentan **1:1** en la Penalización por Desperdicio del final de la partida
(ver [Fin del Juego](#11-fin-del-juego-y-puntuación)): un token de harina del 10% y uno de agua
del 5% valen exactamente lo mismo a esos efectos. Esa es la razón de que la unidad atómica de la
harina sea el 10% y no la bolsa entera.

### Las dos divisas del juego

Fermentum usa dos recursos económicos independientes, que no se convierten entre sí:

- **Monedas:** la divisa comercial. Se ganan de dos formas: el pago inmediato al Hornear y
  Vender, y los **Ingresos de Panadería**, la renta que cada pan ya horneado sigue produciendo
  todas las noches (ver [9.4](#94-ingresos-de-panadería)). Se gastan comprando harina y agua en el
  Mercado, adquiriendo recetas y pagando Pliegues.
- **Datos de Investigación:** la divisa técnica del laboratorio. Se ganan **reclamando la
  Jefatura** (1 por día, y solo se la lleva un jugador de la mesa), horneando en Zona Óptima y
  sacrificando un pan del Archivo en el Simposio Técnico; algunos Patrocinios reparten alguno al
  empezar. Se gastan en instalar Tecnologías, en Horas Extras, en el Pedido de Urgencia y en el
  Inóculo de Emergencia.

> **La panadería es un motor, no una caja registradora.** Un pan horneado no se cobra y se olvida:
> se queda en tu Archivo produciendo Monedas cada noche. Por eso hornear pronto vale más que
> hornear tarde, aunque el pan sea el mismo.

---

## 3. Preparación de la Partida

> **Todos los mazos se barajan al preparar la partida, antes de repartir o revelar ninguna carta:**
> el de Recetas, el de Clima, el de Tendencias de Mercado y el de Patrocinio. Los pasos de abajo lo
> repiten módulo por módulo; ninguno de ellos es una excepción.

1. Colocar el Tablero Central con la temperatura en **20°C** y el Track de Orden de Turno al
   lado.
2. Repartir a cada jugador un Tablero Individual, sus marcadores, 3 Dados de Inóculo y 9 Cubos de
   Laboratorio. El track de Vitalidad inicia en **Nivel 2** y el de Acidez en **Nivel 1**. Colocar una Ficha de
   Bloqueo sobre la tercera ranura de fermentación (se libera al instalar la tecnología Cámara B).
3. **Asignación de Patrocinios:** barajar el mazo de 8 Cartas de Patrocinio y repartir una carta
   boca abajo a cada jugador sentado (de 1 a 4 jugadores). Revelar todas las cartas
   simultáneamente.
   - El jugador con el número de **Iniciativa más bajo** en su carta recibe el token de
     Investigador Jefe y actúa primero en el Día 1. Los demás se ordenan de forma ascendente según
     su número de Iniciativa.
   - **Despliegue de Insumos:** cada jugador toma de la reserva general la harina, el lote de agua,
     las monedas y los Datos de Investigación indicados en su carta (tabla completa abajo). Hecho esto, todas las cartas de
     Patrocinio vuelven a la caja — no se usan de nuevo en la partida.

   | Iniciativa | Harina — Tokens (%) | Agua — Tokens (%) | Monedas Iniciales | Datos Iniciales |
   |:---:|:---|:---|:---:|:---:|
   | 1 | 10 (100%) de Blanca | 2 (10%) | 9 | — |
   | 2 | 10 (100%) de Blanca | 6 (30%) | 8 | — |
   | 3 | 10 (100%) de Blanca | 12 (60%) | 6 | 1 |
   | 4 | 10 (100%) de Integral | 6 (30%) | 8 | — |
   | 5 | 10 (100%) de Integral | 12 (60%) | 6 | 1 |
   | 6 | 10 (100%) de Centeno | 6 (30%) | 8 | — |
   | 7 | 10 (100%) de Centeno | 12 (60%) | 6 | 1 |
   | 8 | 20 (200%) de Blanca | 20 (100%) | 4 | 2 |

   Los jugadores con Iniciativa alta (actúan más tarde en la primera ronda) reciben un capital de
   insumos de mayor valor, para compensar la ventaja temporal del Investigador Jefe. Los **Datos
   Iniciales** van en sentido inverso a las Monedas: el patrocinador que menos dinero da compensa
   con conocimiento. Existen porque los Datos son escasos hasta el primer horneado en Zona Óptima
   — el Simposio Técnico exige sacrificar un pan ya horneado, y al empezar nadie tiene ninguno.

4. **Carpeta de Proyectos inicial:** separar **un ejemplar de cada protocolo Básico** (son 4),
   barajar esos cuatro y entregar a cada jugador 1 al azar — de un **protocolo distinto**, de modo
   que una partida a 4 jugadores los reparte todos. Se coloca boca arriba en su Carpeta de
   Proyectos, en estado inactivo: deberá usarse la acción Iniciar Receta durante la partida para
   activarla.
5. **Mazo de mercado:** retirar del mazo general **una copia** de cada Básica repartida en el paso
   anterior — una copia, no el protocolo entero: cada Básica tiene 4 ejemplares y quitarlos todos
   dejaría ese pan fuera del mercado. Devolver al mazo el resto de las Básicas y **barajarlo
   entero, todas las cartas juntas**. No hay estratos: una Básica puede asomar en el mercado igual
   que una Avanzada. Lo que hace raras a las Avanzadas es que solo hay 2 copias de cada una frente
   a 4 de cada Básica (ver [Resumen de Mazos](#12-anexo-resumen-de-mazos)), no el sitio que ocupan.
6. **Mercado inicial:** revelar las primeras 4 cartas de ese mazo — pueden ser de cualquier grado.
   Colocar los 3 visores de la Bolsa de Harinas en la posición central (**3 de 5**) para Blanca,
   Integral y Centeno.
7. **Mazos del día:** barajar el **mazo de Clima** (30 cartas) y el **mazo de Tendencias de
   Mercado** (21 cartas) por separado y colocarlos boca abajo junto al Tablero Central, cada uno
   con su espacio de descarte al lado. No se revela ninguna carta en la preparación: la primera de
   cada mazo sale en la Fase I del Día 1.

Cada jugador arranca, sin importar su carta de Patrocinio, con: **Vitalidad 2**, Acidez 1, 3 Dados
de Inóculo, 0 Puntos de Acción, todas las Tecnologías desactivadas, y 1 receta Básica aleatoria en
su Carpeta de Proyectos. Los Datos de Investigación iniciales sí dependen de la carta (ver tabla).

> **Por qué la Vitalidad empieza en 2.** El Desgaste Metabólico resta 1 cada noche y Alimentar el
> Cultivo repone 1 una vez al día, así que quien alimenta a diario **se mantiene en el nivel con
> el que empezó**. Si ese nivel fuera 1, la carta de clima «Aletargamiento Invernal» (−2 de
> Vitalidad) provocaría una contaminación imposible de evitar jugando bien. Empezando en 2, esa
> carta te deja en 1: duele, pero se sobrevive. La contaminación castiga descuidar el cultivo, no
> tener mala suerte con el mazo.

A partir de la Ronda 2, el orden de turno vuelve a calcularse cada Fase I según la regla estándar
de Jerarquía (ver más abajo) — la Iniciativa de las Cartas de Patrocinio solo determina el Día 1.

---

## 4. Estructura del Día de Laboratorio

Cada ronda de juego se llama un **Día de Laboratorio** y consta de tres fases secuenciales y
estrictas, siempre en este orden:

1. **Fase I: Ambiente** — se preparan las variables globales del día.
2. **Fase II: Acción** — los jugadores usan sus Puntos de Acción.
3. **Fase III: Fermentación** — resolución automática de las masas, desgaste del cultivo base,
   **cobro de los Ingresos de Panadería** (cada pan del Archivo rinde Monedas), rotación del
   Mercado de Recetas (se descarta la más antigua) y aplicación de la Tendencia de Mercado
   anunciada esa mañana, que fija los precios del día siguiente.

---

## 5. Fase I: Ambiente

Liderada por el Investigador Jefe, esta fase se resuelve en el siguiente orden:

### 5.1 Actualización de Jerarquía

El token de Investigador Jefe pasa a quien **reclamó la Jefatura** ayer, ocupando su espacio de
acción (1 PA — ver [Reclamar la Jefatura](#7-catálogo-de-acciones)).

- **Si nadie la reclamó, la ficha se queda donde está:** el Jefe de ayer sigue siéndolo hoy. No hay
  rotación automática.
- La reclamación **vale para un día y se consume**: quien reclamó el Día 3 abre el Día 4, y para
  abrir también el Día 5 tiene que volver a reclamarla.
- El Investigador Jefe actúa primero en la Fase II y tiene prioridad en la elección de recetas e
  insumos.
- *Excepción:* en el Día 1, el orden lo determina la Iniciativa de las Cartas de Patrocinio (ver
  [Preparación de la Partida](#3-preparación-de-la-partida)) — nadie ha podido reclamar todavía.

> **La Jefatura ya no se hereda: se compra.** Antes la recibía automáticamente quien tuviera más
> Vitalidad, lo que significaba que el orden de turno no lo decidía nadie: se leía del tablero. Ir
> primero es ahora una jugada que cuesta un Punto de Acción entero, y quien la paga se lleva además
> un Dato de Investigación — la única fuente de Datos de toda la partida que no depende de hornear
> bien.

### 5.2 Resolución del Clima

1. Se revela la carta superior del mazo de Clima — es el "Reporte Meteorológico" del día, y
   permanece visible hasta la siguiente Fase I.
2. El termómetro se **reinicia a la base de 20°C** y luego se le suma o resta el Modificador
   Térmico de la carta (el resultado del día anterior no se arrastra).
3. Se sincroniza el **Ábaco de Fermentación** con la nueva temperatura: 20°C = 4 pasos de avance,
   25°C = 5 pasos, 30°C = 6 pasos (en general, temperatura ÷ 5).
4. Si la carta tiene un Efecto Biológico Inmediato (por ejemplo, ganancia de Vitalidad o Acidez
   para todos), se aplica instantáneamente a todos los jugadores antes de empezar la Fase II.
5. Si la carta tiene un Efecto Pasivo (por ejemplo, Alta Humedad o Aletargamiento Invernal),
   queda vigente durante el resto del día — ver el catálogo completo en el
   [Anexo](#12-anexo-resumen-de-mazos).

### 5.3 Anuncio de la Tendencia de Mercado

Se revela la carta superior del mazo de Tendencias de Mercado (21 cartas) y se deja **a la vista de
todos** durante el resto del día.

**Este paso no mueve ningún visor.** La carta es un pronóstico: se aplica al final de este mismo
día (§9.7) y, por tanto, fija los precios de la Bolsa de Harinas del **día siguiente**. Los precios
que rigen hoy son los que dejó la tendencia anunciada ayer, de modo que cualquiera que compre o
venda harina hoy (Acción C) lo hace conociendo ya hacia dónde se moverá el mercado esta noche.

### 5.4 Protocolo de Refresco del Mercado de Recetas

Este paso **reabastece**, no descarta (el descarte de la carta más antigua ocurre al final de la
Fase III del día anterior — ver §9). Las cartas supervivientes se desplazan hacia la derecha para
cubrir los espacios vacíos (los huecos dejados por jugadores con la Acción G y el hueco que dejó
el descarte de fin de día), y se revelan cartas nuevas del mazo por el extremo izquierdo hasta
completar de nuevo las 4 estaciones. Si el mazo de recetas se agota, se baraja su descarte como
mazo nuevo; si mazo y descarte quedan vacíos, el mercado puede quedar temporalmente por debajo de
4 cartas.

---

## 6. Fase II: Acción

Cada jugador dispone de **2 Puntos de Acción (PA)** por Día de Laboratorio.

- **Turno intercalado:** empezando por el Investigador Jefe y siguiendo el orden de turno, cada
  jugador ejecuta **una sola acción** por visita y luego el turno pasa al siguiente jugador. Este
  ciclo se repite hasta que ningún jugador tenga PA disponibles ni una acción gratuita pendiente
  por usar.
- **Registro:** al ejecutar una acción de costo, el jugador desplaza un Cubo de Laboratorio a su
  Checklist de Protocolo para marcar el gasto del punto.
- **Acciones que no terminan el turno:** Alimentar el Cultivo, Técnica (Pliegues), Descarte, Horas
  Extras y Pedido de Urgencia son gratuitas en PA y **no** cierran la visita del jugador — un
  jugador que ya gastó sus 2 PA en otras acciones sigue recibiendo visitas mientras le quede alguna
  de estas cinco acciones sin usar ese día (en el caso de Pliegues y Descarte, mientras conserve su
  espacio libre y con qué pagarlo: Monedas para Pliegues, y Monedas **o** agua para Descarte, que
  cobra un recurso distinto en cada sentido). Cualquier acción de costo en PA, o un **Pasar**
  explícito, sí cierra la visita; **Pasar** además renuncia de inmediato a cualquier acción gratuita
  pendiente por el resto del día.
- **Un espacio de acción, una visita por día:** cada espacio de acción (B a G, Simposio Técnico,
  H, I y también **E** y **Descarte**, que no cuestan PA pero sí ocupan espacio) solo puede visitarse **una vez por
  Día de Laboratorio, por jugador** — el investigador marca el espacio con su color en cuanto lo
  visita, bloqueándolo para él (no para el resto de jugadores) hasta el día siguiente. Con 2-3 PA
  (Horas Extras incluida) esto significa como máximo un uso de cada espacio distinto por día, nunca
  el mismo espacio dos veces. El tope es una propiedad **del espacio**, no del coste. Hay dos
  excepciones, y van en direcciones opuestas: **Reclamar la Jefatura** se agota para TODA la mesa en
  cuanto un jugador la visita, no solo para él; y el **Turno de Mostrador** no se agota nunca —
  cuesta PA pero no ocupa espacio, así que puedes repetirlo mientras te queden Puntos de Acción (es
  el suelo del tablero: ver su entrada en el Catálogo de Acciones). Alimentar el
  Cultivo y Horas Extras se limitan con su propio marcador de "ya usada", y ni Pedido de Urgencia ni
  Estasis Biológica ni Incubadora tienen límite alguno — las dos últimas porque son **ajustes y no
  consumos**: diales de dos sentidos que puedes accionar las veces que quieras y que, por lo mismo,
  tampoco te mantienen en la rotación de visitas (ver sus entradas en el Catálogo de Acciones).
- **Sin escasez de insumos:** a diferencia de las recetas del mercado (que sí ocupan un espacio
  limitado), la harina y el agua ya no se agotan por turno — son un precio compartido (Bolsa de
  Harinas) y una tabla de precio por temperatura (Suministro Hídrico Global) que cualquier jugador
  puede usar en su visita al Mercado sin quitarle el cupo a los demás.

---

## 7. Catálogo de Acciones

### Acciones principales (Costo: 1 PA)

#### B. Iniciar Receta

**Costo:** 1 PA + **10 tokens de harina — 10 (100%), una bolsa entera en total** + los **tokens de
agua** exactos que la receta imprima (cada token = 5% de hidratación). **Límite:** 1 vez por día
(por espacio de acción).

Entre cuántos tipos se reparte esa bolsa lo dice el **grado** de la receta (ver
[Catálogo de Recetas](#8-catálogo-de-recetas)):

| Grado | Se paga con |
|:---|:---|
| **Básica** | 10 tokens — 10 (100%) de Harina Blanca |
| **Intermedia** | 5 tokens — 5 (50%), media bolsa, de **cada una** de las dos harinas que imprima |
| **Avanzada** | 10 tokens — 10 (100%) de la harina **especial** que imprima (Centeno o Integral) |

Hay que tener **todas** las harinas impresas: con una Intermedia, disponer de una de las dos
mitades no basta.

**Ninguna receta exige tecnología.** Una Avanzada de centeno puro puede iniciarse el primer día si
se paga: lo que la hace difícil es su precio de adquisición y su bolsa entera de harina cara, no
una mejora de laboratorio que haya que comprar antes.

Al iniciar la masa, se sella su **Memoria Biológica**: el Dado de Inóculo guarda la Vitalidad
actual del cultivo base (determina la velocidad de fermentación de esa masa específica durante
toda su vida), y el Cubo de Laboratorio guarda la Acidez actual — pero **solo si** esa Acidez cae
dentro del rango de Acidez Diana impreso en la carta. Si el cubo queda sellado, la masa obtendrá el
Bono de Sabor al hornearse con éxito.

Requiere una estación de fermentación libre (la tercera solo si Cámara B está instalada) y al
menos 1 Dado de Inóculo disponible.

#### C. Visitar el Mercado

**Costo:** 1 PA por visita, sin importar cuántas transacciones incluya. **Límite:** 1 vez por día
(por espacio de acción) — todas las transacciones de la visita se resuelven en esa única visita.

El Mercado de Insumos es donde se comercian los recursos del juego:

- **Comprar Harina:** pagar el coste de Compra visible (en Monedas, según la posición actual del
  visor de ese tipo en la Bolsa de Harinas) y recibir **10 tokens — 10 (100%)**, una bolsa entera.
  El visor se mueve 1 casilla hacia el extremo caro (tope en posición 5).
- **Vender Harina:** entregar **10 tokens — 10 (100%)** de esa harina y cobrar el valor de Venta
  visible en Monedas. El visor se mueve 1 casilla hacia el extremo barato (tope en posición 1).
- **Media Bolsa:** tanto la compra como la venta admiten **media bolsa — 5 tokens, 5 (50%)**. El
  precio es la mitad del visible, **redondeando hacia arriba al comprar y hacia abajo al vender**
  (⌈Compra/2⌉ y ⌊Venta/2⌋), así que con precios impares media bolsa nunca sale a mejor precio por
  token que una entera: es una facilidad de liquidez, no un descuento. Una venta que redondee a
  **0 Monedas** (Blanca en la posición 1) es legal — se entrega la media bolsa a cambio de mover
  el visor. **El visor se mueve 1 casilla igual que con una bolsa entera:** una transacción es una
  señal de mercado, sin importar su tamaño. Por debajo de la media bolsa el mercado no opera: no
  se compran ni venden tokens sueltos de harina.
- **Comprar Lote de Agua:** pagar el coste en Monedas según la fila de temperatura actual y el
  lote elegido, y recibir el lote completo en tokens de agua (1 token = 5% de hidratación). Los
  cuatro lotes son **2 (10%)**, **6 (30%)**, **12 (60%)** y **20 (100%)**.
- **Contratar el Molino:** pagar **una sola vez** el precio del tipo de harina elegido y quedarse
  con el **Contrato con el Molino** de esa harina. Desde esa misma noche, en cada Fase III, el
  molino entrega **2 tokens — 2 (20%)** de esa harina, para siempre ([§9.5](#95-entrega-del-molino)).
  **No mueve el visor:** el molino produce fuera de la Bolsa. Un contrato por jugador y por
  partida — no se cambia de harina, no se cancela y no se revende.

**Regla de Exclusividad:** una misma visita puede combinar varias transacciones, pero como máximo
**una por tipo de recurso** — se puede comprar Blanca, vender Centeno y comprar un lote de agua en
la misma visita, pero no comprar y vender la misma harina, ni comprar el mismo tipo dos veces. **El
Molino cuenta como su propio recurso**, así que firmar el contrato de Centeno y comprar Centeno en
esa misma visita sí es legal — el molino no entrega hasta la noche, y hoy todavía necesitas harina.

**Bolsa de Harinas** (Monedas según la posición del visor, 1 a 5). Entre paréntesis, el precio de
la **media bolsa**, que se deriva del entero con ⌈Compra/2⌉ y ⌊Venta/2⌋:

| Harina | Posición 1 | Posición 2 | Posición 3 | Posición 4 | Posición 5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Blanca — Compra / Venta | 2 (1) / 1 (0) | 3 (2) / 2 (1) | 4 (2) / 3 (1) | 5 (3) / 4 (2) | 6 (3) / 5 (2) |
| Integral — Compra / Venta | 4 (2) / 2 (1) | 5 (3) / 3 (1) | 6 (3) / 4 (2) | 7 (4) / 5 (2) | 8 (4) / 6 (3) |
| Centeno — Compra / Venta | 6 (3) / 3 (1) | 7 (4) / 4 (2) | 8 (4) / 5 (2) | 9 (5) / 6 (3) | 10 (5) / 7 (3) |

**Contrato con el Molino** (pago único en Monedas; la entrega nocturna es la misma para los tres):

| Harina | Contrato | Entrega cada noche |
|:---|:---:|:---:|
| Blanca | 3 | 2 (20%) |
| Integral | 4 | 2 (20%) |
| Centeno | 6 | 2 (20%) |

> **Los tres se amortizan la misma noche: la cuarta.** Valorando la entrega al precio de Compra de
> la posición 3 (donde arrancan los tres visores), el Molino de Blanca produce 0,8 Monedas por
> noche, el de Integral 1,2 y el de Centeno 1,6 — y a las cuatro noches los tres han cubierto su
> precio, mientras que a las tres no lo cubre ninguno. Que el horizonte sea idéntico es lo que
> mantiene la elección en «qué harina necesito» y no en «cuál se recupera antes». Es una noche más
> lento que los Ingresos de Panadería a propósito: la renta se cobra por haber horneado, que ya es
> la jugada difícil, mientras que el Contrato solo pide Monedas.

**Suministro Hídrico Global** (Monedas según temperatura y tamaño de lote):

| Temperatura | 2 (10%) | 6 (30%) | 12 (60%) | 20 (100%) |
|:---:|:---:|:---:|:---:|:---:|
| 30°C | 3 | 6 | 10 | 14 |
| 25°C | 2 | 5 | 8 | 12 |
| 20°C | 2 | 4 | 7 | 10 |
| 15°C | 1 | 3 | 6 | 9 |
| 10°C | 1 | 2 | 4 | 7 |

> **Con la tecnología [Comerciante](#10-tecnologías-de-laboratorio) instalada**, cada transacción
> de **compra** de tu visita — harina (bolsa o media), lote de agua y la firma del Molino — cuesta
> **1 Moneda menos**, con un mínimo de 1: los precios de las tablas de arriba son los de la mesa, y
> tú pagas uno menos por cada compra. **Ninguna venta mejora**, y tu compra **mueve el visor igual
> que la de cualquiera**.
>
> Sí: con el descuento, comprar Blanca un día y venderla al siguiente te deja **+1 Moneda**
> (comprar sube el visor, así que la venta cobra la casilla siguiente, y en Blanca eso empata justo
> con la horquilla). No es un agujero, es una mala jugada: como no puedes comprar y vender la misma
> harina en la misma visita y el espacio C se agota una vez al día, ese +1 te cuesta **dos días
> enteros** de acceso al mercado. Vender una bolsa que te regaló el Molino paga 5 en un solo Punto
> de Acción.

#### D. Implementar Mejora de Laboratorio

**Costo:** 1 PA + Datos de Investigación, según la mejora — ver [Tecnologías de
Laboratorio](#10-tecnologías-de-laboratorio). El beneficio se activa de inmediato. Cada mejora
individual solo puede instalarse **una vez** por partida, pero un jugador puede llegar a instalar
varias mejoras distintas a lo largo de la partida — no existe un tope global de "una sola mejora
en total". **Límite adicional:** el espacio D en sí solo puede visitarse 1 vez por día — instalar
CUALQUIER mejora agota el espacio para el resto del día, así que dos mejoras distintas nunca pueden
instalarse el mismo día; como muy pronto, la segunda espera al día siguiente.

#### F. Hornear y Vender (Finalización de Protocolo)

**Costo:** 1 PA. **Límite:** 1 vez por día (por espacio de acción) — no aplica al colapso
automático de Fase III, que no pasa por este espacio ni consume PA. Finaliza el protocolo de una
masa y la vende de inmediato: se obtienen Puntos de
Maestría, Monedas y (en Zona Óptima) Datos de Investigación, según la zona del track donde se
encuentre el marcador:

| Zona | Puntos de Maestría | Monedas | Datos de Investigación |
|:---|:---|:---|:---:|
| **Crecimiento** (la masa aún no es pan) | — | — | — |
| **Pre-fermento** (masa cruda) | Puntos reducidos de la carta | Venta con margen reducido | No |
| **Óptima** | Puntos íntegros de la carta | Ingreso completo de la carta | Sí (+1, +1 extra con Módulo Analítico, +1 más en el centro exacto) |
| **Colapso** (resuelto automáticamente en Fase III) | Penalización negativa de la carta | Recuperación del coste base, sin margen | No |

**No se puede hornear una masa en Crecimiento.** Todavía no es pan: la Acción F la rechaza, y el
espacio aparece deshabilitado. Toda masa nace en Crecimiento al iniciarse la receta y sale de él
en cuanto la fermentación la lleva al Pre-fermento.

**Y tampoco puedes deshacerte de ella.** Iniciar una receta es un compromiso irreversible: no
existe ninguna acción que abandone una masa. Una masa que ya no quieres seguirá avanzando cada
noche hasta que la hornees o hasta que colapse sola. Nunca se queda atascada ocupando la estación
— la Fase III la mueve siempre — pero el precio de haberte equivocado de día es que vas a pagar
su penalización de colapso.

**Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado desde que se inició la receta
(y el horneado **no** fue un colapso), se suman los puntos de sabor impresos en la carta **y**
+2 Monedas adicionales al ingreso de la venta. El Bono de Sabor nunca se aplica en un colapso.

#### G. Investigar Protocolo

**Costo:** 1 PA + **Monedas según el grado de la carta** — Básica **1**, Intermedia **2**,
Avanzada **3**. El precio es *aditivo*: el Punto de Acción y el espacio siguen siendo el límite
real, y las Monedas hacen del mercado una economía en lugar de una cola.
**Límites:** máximo 3 cartas en la Carpeta de Proyectos (si está llena, hay que
descartar una antes de investigar la nueva); además, 1 vez por día (por espacio de acción).
Selecciona una carta de receta de cualquiera de las 4 estaciones visibles del Mercado Central y la
coloca boca arriba, en estado inactivo, en la Carpeta de Proyectos propia. El espacio del mercado
que se libera queda vacío hasta el reabastecimiento del Protocolo de Refresco al inicio del día
siguiente.

#### Simposio Técnico

**Costo:** 1 PA + **un pan horneado con éxito de tu Archivo**. **Límite:** 1 vez por día (por
espacio de acción).

Presentas uno de tus panes en el simposio: retiras su registro del **Archivo de Horneados
Exitosos** y ganas Datos de Investigación **según el grado de la carta** — Básica **1**,
Intermedia **2**, Avanzada **3**. La carta vuelve al descarte del mazo de recetas y puede
reaparecer al rebarajar.

Es la **única forma de sacar un pan del Archivo**, y hacerlo cuesta, todo a la vez:

- los **Puntos de Maestría** de ese horneado;
- su **renta** de [Ingresos de Panadería](#94-ingresos-de-panadería), para el resto de la partida;
- un escalón de **Variedad de Recetas**, si era el único pan de ese tipo que tenías;
- un paso del contador **X/5** que termina la partida.

> **No es una jugada eficiente, y no pretende serlo.** Ningún puñado de Datos compensa ese precio:
> el Simposio es una **palanca de emergencia** — quemar un éxito pasado para salvar el presente —
> y en la práctica se sacrifica siempre el pan más barato que se tenga. Un jugador con 4 panes en
> el Archivo puede además sacrificar uno para *retrasar* el final de la partida; es carísimo, y
> por eso es legítimo. Lo que no puede es deshacer un final ya desencadenado.

**Ojo, cambió respecto a versiones anteriores:** el Simposio ya **no** descarta de la Carpeta de
Proyectos ni de una estación de fermentación. Para descartar de la Carpeta está la propia acción
Investigar Protocolo cuando la carpeta está llena; y **abandonar una masa ya no es posible en
absoluto** (ver [9.2](#92-colapso-estructural-sobre-fermentación)).

#### Reclamar la Jefatura

**Costo:** 1 PA. Ganas **1 Dato de Investigación** en el acto y abres la Fase II **de mañana** como
Investigador Jefe.

**Límite: uno por día en toda la mesa.** Este es el único espacio del tablero que no se agota por
jugador sino para todos a la vez: en cuanto alguien coloca su peón aquí, nadie más puede reclamarla
ese día. Ocuparlo no es solo usarlo — es quitárselo a los demás.

El efecto llega mañana porque el orden de turno se fija una sola vez, en la Fase I, y no se
rebaraja a media jornada: lo que compras es la salida de mañana, no la de hoy. **Reclamarla siendo
ya el Jefe es legal** y cuesta lo mismo — es la única manera de retenerla, porque aunque sin
reclamación la ficha se queda donde está, cualquiera puede venir a comprarla.

> **Un Punto de Acción entero por salir primero es caro, y debe serlo.** A cambio te llevas el
> Dato, y ahí está la otra mitad del asunto: es la única fuente de Datos de Investigación de la
> partida que no pasa por hornear en Zona Óptima. Antes, quien horneaba bien primero acumulaba
> también la divisa técnica y el resto de la mesa se quedaba sin combustible para Horas Extras y
> Pedidos de Urgencia. Aquí entra **1 Dato por día en total**, repartido por rotación y no por
> riqueza: lo limita la competencia, no el precio.

#### Turno de Mostrador

**Costo:** 1 PA. Ganas **1 Moneda**. No hay nada que elegir ni nada que pagar.

**Sin límite: es el único espacio con costo de PA que no se agota.** Todos los demás se marcan con
tu peón al visitarlos y quedan cerrados para ti hasta el día siguiente; este no. Puedes atender el
mostrador tantas veces como Puntos de Acción te queden.

Es el **suelo del tablero**: la acción que existe para que un turno nunca esté vacío. Si te
encuentras con Puntos de Acción y ninguna jugada que te sirva — sin recetas en la Carpeta, con la
masa todavía en Crecimiento, sin Monedas para el Mercado, sin Datos para una mejora y con la
Jefatura ya reclamada por otro — dejas la investigación, bajas a la panadería y despachas lo que
haya en el mostrador.

> **Una Moneda es poco a propósito.** Es exactamente lo que valía la vieja acción de Pliegues que
> costaba 1 PA, la que nadie tomaba nunca: ese es el listón que se busca. Cualquier otra acción del
> tablero rinde más que atender el mostrador, así que esto no es nunca una estrategia — es lo que
> haces cuando no hay nada que hacer. Y no se puede ganar la partida a base de mostrador: el día
> tiene 2 Puntos de Acción, y gastarlos aquí es no haber horneado, ni comprado, ni investigado.

> **Por qué no está condicionada a «no tener nada mejor que hacer».** Sería la regla natural y es
> impracticable: nadie en la mesa puede juzgar si a otro jugador le conviene o no una compra. Un
> permiso así habría que discutirlo cada vez. El Mostrador se limita solo, siendo flojo: no hace
> falta cerrarlo porque nunca compensa.

**Ojo:** pasar turno **no** es lo mismo. Pasar renuncia a todo el resto del día, incluidas tus
acciones gratuitas (Alimentar el Cultivo, Pliegues, Descarte, Horas Extras, Pedido de Urgencia).
Atender el mostrador solo gasta un Punto de Acción y te deja en la rotación.

### Acciones auxiliares y de emergencia (Costo: 0 PA)

#### A. Alimentar el Cultivo (Mantenimiento)

**Límite:** una vez por Día de Laboratorio. Se gasta **1 token de harina — 1 (10%)** (de cualquier
tipo) por **+1 Vitalidad** (máximo Nivel 6). Repone exactamente el -1 que el Metabolismo resta cada
Fase III, así que quien alimenta a diario orbita su Vitalidad inicial.

Esta acción **no toca la Acidez**. Todo el control voluntario de la Acidez vive en la acción
**Descarte**, que la mueve en los dos sentidos.

#### Descarte (Refresco del Cultivo)

**Costo:** 0 PA, pero **ocupa su espacio de acción**: una vez por Día de Laboratorio, como
cualquier otro espacio. No termina tu turno.

Es el único control voluntario de la Acidez, y funciona en **los dos sentidos** — pero cada uno se
paga con un recurso distinto, y eso no es arbitrario: subir la acidez es sólo añadir agua, mientras
que bajarla es descartar parte del cultivo y refrescarlo con harina nueva, es decir **tirar
producto**. Elige un solo sentido por visita.

| Mover la Acidez | +1 | +2 | +3 |
|:---|:---:|:---:|:---:|
| **Subir** — cuesta tokens de agua | 2 | 5 | 9 |

| Mover la Acidez | -1 | -2 | -3 |
|:---|:---:|:---:|:---:|
| **Bajar** — cuesta Monedas | 1 | 3 | 6 |

Ambas escaleras son **crecientes al margen** (2, 3 y 4 tokens; 1, 2 y 3 Monedas): comprar más nunca
sale más barato por unidad. La Acidez sigue acotada entre los Niveles 0 y 6, y el escalón se cobra
entero aunque el ajuste tope contra un extremo.

**Para qué sirve.** Para caer dentro de la **Acidez Diana** de una receta antes de iniciarla y
sellar así su Bono de Sabor (§7). Pero no lo uses a ciegas: la **Madurez del Cultivo** del recuento
final (§11.2) premia el *equilibrio*, no la acidez bruta — su pico está en el **Nivel 3** y los
extremos 0 y 6 no puntúan. Perseguir la diana de un Panettone (Nivel 1) o de un Pumpernickel
(Niveles 5-6) cuesta puntos finales mientras la sostienes, y por eso esas cartas son justamente las
que más Bono de Sabor pagan.

#### E. Técnica (Pliegues)

**Costo:** Monedas, no PA. Se compran entre 1 y 3 espacios de avance del marcador de Inóculo y se
reparten entre las masas activas: **1 espacio = 1 Moneda, 2 = 3 Monedas, 3 = 6 Monedas**. El precio
es creciente al margen a propósito — comprar más nunca sale más barato por espacio. El precio
depende del **total** comprado, no de cuántas masas se afecten. **No termina el turno:** se puede
encadenar con otra acción en la misma visita. **Límite:** 1 vez por Día de Laboratorio — es la
única acción de 0 PA que ocupa un espacio de acción, y se limita por ese espacio y no por su
precio (las Monedas son renovables, así que el coste por sí solo no bastaría como freno).

Con la tecnología **Cámara B** instalada, el jugador **no compra más espacios**, sino que puede
repartirlos entre **dos masas distintas** en lugar de concentrarlos en una. La Cámara B desbloquea
además una variante alternativa: recuperar **+1 de Vitalidad** en el cultivo base por **6 Monedas**,
sin comprar ningún espacio de avance.

**Riesgo:** el avance no tiene tope. Comprar 3 espacios puede empujar una masa más allá de su zona
óptima hasta la zona de colapso, que la Fase III hornea automáticamente en colapso y con
penalización. Ese riesgo es el contrapeso del escalón caro: el juego avisa, pero no lo impide.

#### Horas Extras

**Costo:** 1 Dato de Investigación. Otorga de inmediato +1 Punto de Acción adicional para usar ese
mismo día. Solo puede activarse **una vez por Día de Laboratorio** por jugador.

#### Estasis Biológica

**Costo:** ninguno. **Requiere la tecnología Criopreservación.** No ocupa espacio de acción, no
termina tu turno y no tiene límite de usos.

Tu Criopreservación mantiene el cultivo en estasis: ignora el desgaste metabólico cada noche. Esta
acción decide si, **sólo por esta noche**, lo dejas desgastarse con normalidad (−1 Vitalidad, −2 con
Aletargamiento Invernal vigente). Es un interruptor de dos sentidos: puedes suspender la Estasis y
volver a activarla cuantas veces quieras mientras sea tu turno. La Fase III **la reactiva sola**, así
que la suspensión nunca dura más de una noche y un ajuste olvidado no puede contaminarte.

Se decide en la Fase II, con la carta de clima ya sobre la mesa: eliges sabiendo la temperatura del
día y si hay Aletargamiento.

> **Por qué querrías desgastar tu propio cultivo.** Iniciar Receta sella el **Dado de Inóculo** con
> tu Vitalidad de ese día, y ese número se suma al avance de esa masa **todas las noches**. Nada más
> en el juego baja la Vitalidad a propósito — el Descarte sólo mueve la Acidez —, así que quien tiene
> Criopreservación y alimenta a diario sube hasta 6 y se queda ahí clavado: sus masas avanzan de 9 a
> 11 casillas por noche, y las recetas Avanzadas tienen zonas óptimas de 2 o 3 casillas. Pasarse de
> largo dejaba de ser un error de cálculo para ser una certeza, precisamente para quien había pagado
> la mejora. Con la suspensión, la Vitalidad vuelve a ser un dial de dos sentidos, como la Acidez.

**Ojo:** suspender la Estasis con Vitalidad 1 (o 2 bajo Aletargamiento) te lleva a **0**, es decir a
Contaminación: −3 Puntos de Maestría y no puedes iniciar recetas hasta ejecutar un Protocolo de
Emergencia. El juego te enseña la cifra resultante antes de confirmar, pero no te lo impide.

#### Incubadora

**Costo:** ninguno. **Requiere la tecnología Incubadora** y al menos una masa fermentando. No ocupa
espacio de acción, no termina tu turno y no tiene límite de usos.

Fija, **masa por masa**, cuánto avanzará cada una **esta noche**: −1 la frena una casilla, +1 la
acelera una, 0 la deja con su cinética limpia. Con varias estaciones ocupadas puedes frenar una
mientras empujas otra — el dial es de cada masa, no del laboratorio.

Se decide en la Fase II, con la carta de clima ya sobre la mesa: eliges sabiendo la temperatura del
día, es decir sabiendo cuánto va a correr cada masa. El ajuste **dura una sola noche**: la Fase III
lo aplica y devuelve el dial a 0, así que un ajuste olvidado no puede seguir empujando una masa
noche tras noche.

> **Por qué el dial no se elige al iniciar la receta.** Antes se fijaba al mezclar y quedaba clavado
> en la masa para siempre. Quien compraba la Incubadora con una masa ya fermentando descubría que no
> podía tocarla: veía cómo se pasaba de la Zona Óptima sin poder frenarla, con la mejora recién
> pagada delante. Ahora el ajuste es de cada noche, así que instalar la Incubadora rescata lo que ya
> tienes en marcha — igual que hace el Módulo Analítico con la Zona Óptima.

**Ojo:** un +1 puede meter la masa en **Colapso**, y entonces se hornea sola esta noche con la
penalización de esa zona. El juego te enseña dónde caerá la masa antes de confirmar, pero no te lo
impide: a veces adelantar un colapso es la jugada.

#### Pedido de Urgencia

**Costo:** 1 Dato de Investigación. Ignora el Mercado por completo — sin importar el precio
vigente — y entrega de la reserva general **una** parcela fija a elección: **media bolsa — 5
(50%)** de un tipo de harina, o **6 (30%)** de agua. Eliges el recurso, nunca la cantidad.

Media bolsa, y no una entera, porque el Pedido era también el mejor arbitraje de la partida:
1 Dato entregaba una bolsa completa de cualquier harina, y una bolsa de Centeno en posición 5 se
revende en el acto por 7 Monedas. La emergencia se conserva (dos Pedidos completan una bolsa, y una
receta Intermedia sólo pide media de cada harina), pero la reventa se hunde — la venta de media
bolsa redondea hacia **abajo**, así que ese mismo Centeno pasa a pagar 3.

El agua también es una cantidad fija, y por un motivo paralelo: una receta pide entre 10 y 17
tokens y un lote del 100% cuesta de 7 a 14 Monedas, así que pedir «los que quieras» convertía 1
Dato en toda el agua de la partida. El agua no se revende, de modo que no había arbitraje en
Monedas, pero el único freno era la penalización por desperdicio del recuento final (−1 punto por
cada 3 tokens sin usar), un precio ridículo por saltarse el Suministro Hídrico durante toda la
partida. Se entrega el equivalente al lote del 30%, que cuesta entre 2 y 6 Monedas según la
temperatura: lo mismo, más o menos, que la media bolsa de harina, de modo que el Dato compra el
mismo valor elijas lo que elijas. Y sostiene la misma historia — igual que dos Pedidos completan
una bolsa, dos Pedidos cubren aproximadamente el agua de una receta.

A diferencia de Horas Extras, no tiene límite de usos por día — se autolimita únicamente por los
Datos de Investigación disponibles. Al no costar PA, queda exento de la regla "1 vez por día por
espacio de acción" de la [Fase II](#6-fase-ii-acción) — es intencional, no un descuido.

#### Protocolos de Emergencia (Rescate de Cultivo)

Solo pueden ejecutarse si la Vitalidad del cultivo base ha llegado a 0 (ver [Fase
III](#9-fase-iii-fermentación)):

- **H. Re-cultivo Manual:** Costo 1 PA + **3 tokens de harina — 3 (30%)** (de cualquier tipo, sin costo de agua).
  Retira la Contaminación y sitúa Vitalidad y Acidez en Nivel 1. **Límite:** 1 vez por día (por
  espacio de acción), además de requerir Contaminación activa.
- **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira la Contaminación y
  sitúa Vitalidad y Acidez en Nivel 2 (resultado superior al Re-cultivo Manual). **Límite:** 1 vez
  por día (por espacio de acción), además de requerir Contaminación activa.

---

## 8. Catálogo de Recetas

Hay **12 protocolos distintos: 4 Básicas, 4 Intermedias y 4 Avanzadas.** El mazo físico son 36
cartas, porque cada protocolo lleva un número distinto de copias — 4 por Básica, 3 por Intermedia,
2 por Avanzada (ver [Anexo](#12-anexo-resumen-de-mazos)). La escasez es, por sí sola, una segunda
barrera para las Avanzadas: no basta con poder pagarlas, tienen que salir. Los tracks de
fermentación de todas las recetas corren de 1 a 20 casillas.

### Los tres grados

El grado de una receta **es** la harina que imprime — no es una etiqueta aparte:

| Grado | Imprime | Coste en la Bolsa (visor en 1 → 5) |
|:---|:---|:---|
| **Básica** | Harina Blanca 100% (una bolsa entera) | 2 – 6 Monedas |
| **Intermedia** | 50% + 50% de **dos harinas distintas** (dos medias bolsas) | 3 – 7 … 5 – 9 Monedas |
| **Avanzada** | 100% de **una harina especial** — Centeno o Integral | 4 – 8 (Integral) / 6 – 10 (Centeno) |

**Harina especial** = Centeno o Integral. La Blanca es el producto común y la pista más barata de
las tres; es precisamente lo que impide que una Básica sea una Avanzada.

Solo existen esas dos formas de pago —una bolsa entera, o dos medias— y no es una restricción
arbitraria: la Bolsa de Harinas únicamente vende bolsa entera y media bolsa
(ver [Acción C](#7-catálogo-de-acciones)), nunca tokens sueltos. Por eso una Intermedia no sale
más cara por el peso de la harina, sino por la **liquidez**: obliga a tener dos pistas surtidas a
la vez, y cada media bolsa se compra redondeando hacia arriba.

Las zonas de la tabla son las **impresas**. Con el **Módulo Analítico** instalado, tu Zona Óptima
corre una casilla en cada dirección y el umbral de colapso se retrasa con ella (ver
[Colapso Estructural](#9-fase-iii-fermentación) y [Tecnologías](#10-tecnologías-de-laboratorio)).

**Ninguna carta exige tecnología.** El grado dice qué harina cuesta y cuántos puntos paga, nada
más. Adquirir la carta cuesta Monedas según su grado (Básica 1, Intermedia 2, Avanzada 3 — ver
[Acción G](#7-catálogo-de-acciones)), y el resto del freno es la harina que hay que reunir.

### Puntuación por grado

Los Puntos de Maestría de la Zona Óptima están escalonados por grado y **no se solapan**:

| Grado | Puntos en Zona Óptima |
|:---|:---:|
| Básica | 9 – 12 |
| Intermedia | 13 – 16 |
| Avanzada | 17 – 20 |

Las **Monedas y el ancho de las zonas no** están escalonados: son el eje que distingue, dentro de
un mismo grado, una carta de puntos baratos de una carta caja fuerte. Compárense Hogaza Centeno
(17 puntos, 18 Monedas, zona óptima de 4 casillas) y Pumpernickel (20 puntos, 19 Monedas, pero
solo 3 casillas de zona óptima y un colapso de −8). El Bono de Sabor va por libre igual: Panettone
es Intermedia y aun así tiene el mayor bono del juego (+8) — no es la carta de más puntos, es la
de más sabor.

| Receta | Grado | Coste (Monedas) | Harina (siempre 10 tokens / 100% en total) | Agua — Tokens (Hidratación) | Acidez Diana (Bono de Sabor) | Crecimiento | Pre-fermento | Óptima | Colapso | Puntos (Pre-f. / Óptima / Colapso) | Monedas al hornear (Pre-f. / Óptima / Colapso) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Pan de Campo | Básica | 1 | Blanca 100% | 12 (60%) | Nivel 3 (+1) | 1–5 | 6–10 | 11–15 | 16–20 | 4 / 10 / −2 | 10 / 14 / 8 |
| Pan de Molde | Básica | 1 | Blanca 100% | 11 (55%) | Nivel 1–2 (+2) | 1–3 | 4–8 | 9–14 | 15–20 | 3 / 9 / −2 | 9 / 13 / 7 |
| Baguette | Básica | 1 | Blanca 100% | 13 (65%) | Nivel 2 (+2) | 1–5 | 6–11 | 12–15 | 16–20 | 5 / 11 / −2 | 11 / 15 / 9 |
| Focaccia | Básica | 1 | Blanca 100% | 15 (75%) | Nivel 1–2 (+2) | 1–4 | 5–9 | 10–14 | 15–20 | 3 / 12 / −3 | 12 / 16 / 10 |
| Miche | Intermedia | 2 | Blanca 50% + Integral 50% | 14 (70%) | Nivel 3–4 (+2) | 1–5 | 6–11 | 12–16 | 17–20 | 5 / 13 / −4 | 10 / 14 / 7 |
| Pizza Napolitana | Intermedia | 2 | Blanca 50% + Integral 50% | 13 (62%) | Nivel 3 (+2) | 1–5 | 6–10 | 11–14 | 15–20 | 4 / 14 / −4 | 9 / 15 / 6 |
| Brioche | Intermedia | 2 | Blanca 50% + Centeno 50% | 11 (52%) | Nivel 1 (+3) | 1–7 | 8–14 | 15–17 | 18–20 | 5 / 16 / −6 | 8 / 15 / 5 |
| Panettone | Intermedia | 2 | Blanca 50% + Centeno 50% | 10 (47%) | Nivel 1 (+3) | 1–10 | 11–16 | 17–18 | 19–20 | 8 / 16 / −8 | 7 / 16 / 4 |
| Hogaza Centeno | Avanzada | 3 | Centeno 100% | 14 (67%) | Nivel 4–5 (+4) | 1–6 | 7–12 | 13–16 | 17–20 | 6 / 17 / −5 | 11 / 18 / 8 |
| Pan Semillas | Avanzada | 3 | Integral 100% | 16 (78%) | Nivel 3–4 (+3) | 1–6 | 7–13 | 14–16 | 17–20 | 6 / 17 / −5 | 10 / 17 / 7 |
| Pan Graham | Avanzada | 3 | Integral 100% | 16 (80%) | Nivel 4–5 (+4) | 1–6 | 7–13 | 14–17 | 18–20 | 6 / 19 / −6 | 9 / 17 / 6 |
| Pumpernickel | Avanzada | 3 | Centeno 100% | 17 (85%) | Nivel 5–6 (+4) | 1–9 | 10–15 | 16–18 | 19–20 | 8 / 20 / −8 | 7 / 19 / 3 |

*El track de fermentación de cada carta se divide en **cuatro** zonas. **Crecimiento** no tiene
columna de pago porque **no se puede hornear ahí**: la masa todavía no es pan y la
[Acción F](#7-catálogo-de-acciones) la rechaza. Tampoco se puede abandonar: iniciar una receta es
un compromiso, y una masa que ya no quieres fermentará hasta hornearse o colapsar. Las otras tres
zonas sí pagan, y sus valores son las columnas de Puntos y Monedas.*

> **La columna de Monedas es solo el pago del momento de hornear.** Cada pan que entra en tu
> Archivo sigue produciendo Monedas **todas las noches** mientras siga allí — Básica 1, Intermedia
> 2, Avanzada 3 (ver [9.4 Ingresos de Panadería](#94-ingresos-de-panadería)). Los números de la
> tabla ya están ajustados a la baja para dejarle sitio a esa renta: **cualquier carta recupera al
> tercer día lo que pagaba antes de golpe**, y a partir de ahí gana más. Por eso hornear pronto
> vale más que hornear tarde, y por eso el pan barato horneado el Día 3 puede rendir más que el
> pan caro horneado el Día 8.*

*La columna **Coste** es lo que cuesta llevarse la carta del Mercado Central con la
[Acción G](#7-catálogo-de-acciones); va impresa en la carta. No confundir con la harina y el agua,
que son lo que cuesta **iniciarla** después con la Acción B.*

*El número entre paréntesis junto a la Acidez Diana es el bono de Puntos de Maestría del Bono de
Sabor (ver [Acción F](#7-catálogo-de-acciones)); el Bono de Sabor también otorga siempre +2
Monedas adicionales, sin importar la receta.*

---

## 9. Fase III: Fermentación

Ocurre de forma automática y simultánea para todos los jugadores, una vez que la Fase II termina
(ningún jugador tiene PA ni una acción gratuita pendiente).

### 9.1 Cinética Biológica (Avance de Masas)

Cada masa activa en una estación de fermentación avanza en su track según:

> **Avance Final = (Temperatura Ambiental ÷ 5) + Valor del Dado de Inóculo + Modificador de
> Incubadora**

- La inercia térmica (temperatura ÷ 5) es igual para todas las masas del laboratorio ese día.
- El Dado de Inóculo es el valor que quedó **sellado** al iniciar esa masa concreta — no cambia
  aunque la Vitalidad actual del cultivo base cambie después.
- El Modificador de Incubadora (−1, 0 o +1) solo está disponible si el jugador tiene esa
  tecnología instalada. **Lo fija su dueño durante la Fase II**, masa por masa, con la acción
  gratuita «Incubadora» (§7), y esta fase lo **devuelve a 0** después de aplicarlo: el ajuste dura
  una sola noche. A diferencia del Dado de Inóculo, no queda sellado al iniciar la receta, así que
  instalar la Incubadora sirve también para las masas que ya tenías fermentando.

**Principio de Memoria Biológica:** una vez iniciada, una masa es un ecosistema independiente. Si
el cultivo base del jugador llega a Vitalidad 0 o se contamina después de haber iniciado la
receta, esa masa en curso **no se ve afectada** — sigue avanzando con el valor de dado que quedó
sellado en el momento de la mezcla original. Lo sellado es el **Dado de Inóculo**; el Modificador de
Incubadora no lo está, y por eso puedes moverlo cada noche.

### 9.2 Colapso Estructural (Sobre-fermentación)

Las cuatro zonas del track, de menos a más fermentada: **Crecimiento** (la masa aún no es pan, no
se puede hornear), **Pre-fermento** (cruda, hornea con puntos y Monedas reducidos), **Óptima**
(puntos completos y +1 Dato) y **Colapso** (horneado automático con penalización).

Si, tras aplicar el Avance Final, la posición de una masa entra en su Zona de Colapso, la
masa colapsa de inmediato: se hornea automáticamente con costo 0 PA, aplicando la penalización de
puntos y el ingreso de Monedas de recuperación de coste de esa zona (ver [Catálogo de
Recetas](#8-catálogo-de-recetas)). El Dado de Inóculo se recupera y la estación de fermentación
queda libre para el día siguiente. Un colapso nunca otorga el Bono de Sabor, aunque el Cubo de
Acidez estuviera sellado.

**Las zonas que cuentan son las tuyas, no las impresas.** Si tienes el **Módulo Analítico**
instalado, tu Zona Óptima corre una casilla más en cada dirección, de modo que el umbral de
colapso está una casilla más arriba que lo que dice la carta. Es un efecto **vivo**: instalar el
Módulo hoy salva esta noche una masa que ya estaba fermentando, y no hace falta que estuviera
instalado al iniciarla. Ensanchar no mueve el centro exacto — la zona perdona más, pero clavar el
centro cuesta lo mismo.

### 9.3 Desgaste Metabólico

Al final de la Fase III, todos los cultivos base sufren desgaste:

- **Estándar:** −1 Vitalidad.
- **Con Aletargamiento Invernal vigente:** −2 Vitalidad.
- **Con la tecnología Criopreservación instalada:** el jugador ignora el desgaste por completo
  ese día (Estasis Biológica) — ni −1 ni −2, sin importar el clima.
- **Con la Estasis suspendida esta noche:** ese mismo jugador sufre el desgaste normal que le
  tocaría sin la mejora (−1, o −2 con Aletargamiento). Es una decisión suya, tomada en la Fase II
  con la acción gratuita «Estasis Biológica» (§7); la Fase III reactiva la Estasis al terminar.

> **La cuenta que conviene tener presente.** El desgaste resta 1 y Alimentar el Cultivo repone 1
> una vez al día, así que **quien alimenta a diario se queda donde empezó**: en Vitalidad 2. Desde
> ahí, un Aletargamiento Invernal (−2) te deja en 1 y sobrevives. Si te saltas la alimentación un
> solo día y cae esa carta, llegas a 0. Eso es exactamente lo que la Contaminación castiga.

La Vitalidad nunca desciende por debajo de 0. Si un jugador llega a Vitalidad 0 en cualquier
momento (por desgaste, por un evento, o al inicio del turno), sufre una penalización inmediata de
**−3 Puntos de Maestría** y entra en estado de **Contaminación**: no puede iniciar nuevas recetas
hasta ejecutar un Protocolo de Emergencia (H o I). Cada episodio de Contaminación aplica su propia
penalización de −3 puntos — si un jugador cae en Contaminación más de una vez durante la partida,
las penalizaciones se acumulan.

### 9.4 Ingresos de Panadería

Cada jugador cobra Monedas de la reserva general **por cada pan de su Archivo de Horneados
Exitosos**, según el grado de cada carta:

| Grado del pan archivado | Monedas por noche |
|:---|:---:|
| Básica | 1 |
| Intermedia | 2 |
| Avanzada | 3 |

Se cobra por **todos** los panes del Archivo, todas las noches, sin límite de días. Un jugador con
una Focaccia y un Pumpernickel archivados cobra 1 + 3 = 4 Monedas cada Fase III.

Tres precisiones que deciden partidas:

- **Un pan horneado hoy cobra esta misma noche.** No hay que esperar al día siguiente.
- **Los colapsos no rinden nada.** Solo paga el Archivo de Horneados *Exitosos*; el Archivo de
  Colapsos no produce Monedas. Provocar un colapso es fácil y barato, así que pagarlo sería
  regalar la renta sin haber horneado bien nada.
- **Si un pan sale del Archivo, su renta se va con él.** La única forma de que eso ocurra es el
  [Simposio Técnico](#7-catálogo-de-acciones).

> **Este es el motor de la partida.** Hornear no es solo puntuar: es montar una fuente de ingresos
> que trabaja para ti el resto del juego. Un pan horneado el Día 3 cobra seis o siete noches; el
> mismo pan horneado el Día 9 cobra una o dos. Pero la partida termina cuando alguien hornea su
> **quinto** pan, así que correr para montar la renta es también correr para cerrar tu propia
> ventana. Esa tensión es deliberada.

### 9.5 Entrega del Molino

Cada jugador que tenga firmado un **Contrato con el Molino** (Acción C, §7) recibe de la reserva
general **2 tokens — 2 (20%)** de la harina que contrató. Todas las noches, para siempre, sin
límite de días y sin volver a pagar nada.

La entrega es **la misma para los tres tipos de harina**: lo que cambia entre ellos es el precio
del contrato, no lo que produce. Así solo hay un número de producción que recordar, y elegir qué
harina contratar es una pregunta sobre qué necesita tu panadería, no sobre qué contrato rinde más.

> **Por qué existe este paso.** Antes, la única forma de tener harina era comprarla en la Bolsa — y
> comprar empuja el visor hacia el extremo caro. Eso dejaba muerto el lado de *venta* del mercado:
> una ida y vuelta comprar→vender pierde siempre el diferencial y mueve el visor dos veces en tu
> contra, y como la Tendencia desplaza los tres visores a la vez, tampoco había especulación
> posible. El Molino es la única harina que no compras, y por eso la única que puedes vender sin
> haberla pagado antes al precio de la Bolsa.

### 9.6 Rotación del Mercado de Recetas

Al cerrar el día, se descarta la carta de receta situada en la estación más a la derecha del
Mercado Central (la más antigua). Si esa estación ya estaba vacía por una Acción G, se descarta la
siguiente carta real hacia la izquierda. El hueco que deja se rellena en el Protocolo de Refresco
del día siguiente (§5.4).

### 9.7 Aplicación de la Tendencia de Mercado

Ahora se cobra la carta de Tendencia anunciada esta mañana (§5.3). Su modificador desplaza
**simultáneamente** los 3 visores de la Bolsa de Harinas (Blanca, Integral y Centeno). Cada visor
tiene su propio tope independiente entre la posición 1 (más barata) y la posición 5 (más cara): si
el desplazamiento lo llevaría más allá del límite, simplemente se detiene en ese límite, sin
arrastre ni efecto acumulado.

Los precios que quedan tras este paso son los que regirán durante **todo el día siguiente**. La
carta pasa entonces al descarte de Tendencias; si el mazo se agota, se reutiliza ese descarte,
barajado de nuevo, como mazo nuevo.

> El Día 1 se juega con los precios de inicio de partida (los 3 visores en la posición 3), ya que
> la primera tendencia no se aplica hasta el final de ese día.

---

## 10. Tecnologías de Laboratorio

Cada jugador puede instalar hasta 5 mejoras permanentes a lo largo de la partida (Acción D). Cada
una solo puede instalarse una vez, pero un jugador puede llegar a tener varias distintas.

Además de su efecto en partida, **cada mejora instalada puntúa al final**, en curva creciente y sin
importar lo que costó: ver [Desarrollo Tecnológico](#112-cálculo-de-puntos-de-maestría-finales) en
§11.2. Una mejora no se desinstala nunca, así que esos puntos, una vez ganados, no se pierden.

| Tecnología | Costo | Efecto |
|:---|:---:|:---|
| **Incubadora** | 3 Datos | Permite ajustar la temperatura local ±5°C (±1 casilla de avance en Fase III) para una masa específica, mitigando el clima. El dial se fija **cada noche y masa por masa** con la acción gratuita del mismo nombre (§7), así que también sirve en masas que ya estaban fermentando cuando la instalaste. |
| **Cámara B** | 4 Datos | Desbloquea la tercera estación de fermentación y mejora la Acción E (Pliegues): permite repartir los espacios comprados entre dos masas (no compra más), y habilita la variante de recuperar +1 Vitalidad por 6 Monedas. |
| **Módulo Analítico** | 4 Datos | **Ensancha la Zona Óptima 1 casilla por cada lado** — se come una casilla del Pre-fermento por abajo y una del Colapso por arriba, así que **también retrasa el colapso**. Además sube el rendimiento del horneado: **2 Datos** en cualquier punto de la Zona Óptima y **3** en el centro exacto. |
| **Criopreservación** | 2 Datos | Estasis Biológica: el cultivo base ignora por completo el desgaste metabólico normal de la Fase III. Puedes **suspenderla noche a noche** con la acción gratuita del mismo nombre (§7) para dejar bajar tu Vitalidad cuando te convenga un Dado de Inóculo más bajo. |
| **Comerciante** | 3 Datos | Mejores condiciones de compra: **cada transacción de compra** de tu Acción C — bolsa o media bolsa de harina, lote de agua y la firma del Contrato con el Molino — te cuesta **1 Moneda menos**, con un mínimo de 1. **No mejora ninguna venta** y **no altera el movimiento del visor**: tu compra lo desplaza igual que la de cualquiera. |

---

## 11. Fin del Juego y Puntuación

### 11.1 Gatillos de Finalización

El final de la partida se **desencadena** de inmediato en cuanto ocurre cualquiera de estas dos
condiciones:

1. El mazo de Clima se agota por completo (se detecta al revelar la carta de Clima de la Fase I).
2. Algún jugador hornea con éxito su **quinta receta** (las recetas colapsadas con valor negativo
   no cuentan para este conteo).

**Disparar el final no detiene el juego: la partida termina al concluir el Día de Laboratorio en
curso.** Ese día se juega entero — todas las visitas de Fase II que queden y la Fase III completa
(avance de masas, colapsos, ingresos de panadería, desgaste metabólico y tendencia de mercado) —
y solo entonces se calcula la puntuación. Así todos los jugadores disputan exactamente el mismo
número de días, sin importar en qué momento del día saltó el gatillo.

El gatillo, una vez disparado, no se revierte: si el jugador que horneó su quinta receta la
sacrifica después con un Simposio Técnico, la partida termina igualmente esta noche.

### 11.2 Cálculo de Puntos de Maestría Finales

1. **Puntos Base:** suma de los puntos de todas las recetas horneadas, tanto positivas como
   negativas (colapsos incluidos).
2. **Puntos de Sabor:** suma de los bonos de Bono de Sabor de cada carta horneada con el Cubo de
   Acidez sellado.
3. **Madurez del Cultivo:** **Vitalidad actual + equilibrio de Acidez**, donde el equilibrio vale
   **3 − |Acidez − 3|**. Es decir, la Vitalidad puntúa entera y la Acidez puntúa por lo *centrada*
   que esté, no por lo alta que sea:

   | Acidez | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
   |:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
   | Puntos de equilibrio | 0 | +1 | +2 | **+3** | +2 | +1 | 0 |

   Un cultivo maduro es uno **compensado**, no uno maximalmente ácido. Esta es la contrapartida de
   que la Acidez sea un dial que puedes mover en ambos sentidos (Descarte): mientras sólo subía,
   premiar el nivel bruto no tenía coste alguno y empujaba a todo el mundo al mismo extremo.
4. **Variedad de Recetas:** puntos por la amplitud de tu repertorio — cuenta cuántas recetas
   **distintas** (por protocolo, no por copia) hay en tu Archivo de Horneados Exitosos:

   | Recetas distintas | 0 | 1 | 2 | 3 | 4 | 5 |
   |:---|:---:|:---:|:---:|:---:|:---:|:---:|
   | Puntos de Maestría | 0 | +1 | +3 | +6 | +10 | +15 |

   Solo cuenta el Archivo de horneados **exitosos**: un colapso nunca aporta variedad. Como el
   mazo trae varias copias de cada protocolo, hornear dos veces el mismo pan cuenta como **una**
   clase, y repetir renuncia al mayor incremento de la curva. Un pan sacrificado en el Simposio
   Técnico deja de contar aquí.
5. **Desarrollo Tecnológico:** puntos por la amplitud del laboratorio que construiste — cuenta
   cuántas **Tecnologías** tienes instaladas (§10), con la **misma curva** que Variedad de Recetas:

   | Mejoras instaladas | 0 | 1 | 2 | 3 | 4 | 5 |
   |:---|:---:|:---:|:---:|:---:|:---:|:---:|
   | Puntos de Maestría | 0 | +1 | +3 | +6 | +10 | +15 |

   Los dos términos de amplitud llegan al mismo tope, +15, por motivos distintos: aquí porque hay
   cinco mejoras, arriba porque la partida termina al quinto horneado. Equiparte del todo cuesta
   16 Datos, así que es una partida entera dedicada a ello y no un extra. **Lo que cuenta es
   cuántas tienes, no lo que pagaste:** la Criopreservación (2 Datos) puntúa igual que la Cámara B
   (4 Datos), del mismo modo que un pan Básico y uno Avanzado cuentan un tipo cada uno más arriba.
   Y como una mejora no se desinstala jamás, este término nunca baja — a diferencia de Variedad,
   que sí pierde un escalón si sacrificas un pan en el Simposio Técnico.

6. **Penalización por Desperdicio:** −1 punto por cada 3 **tokens de insumo** sin utilizar en la
   reserva final. Un token de harina (10%) y uno de agua (5%) cuentan **1:1** aquí pese a
   representar porcentajes distintos: se suman en un único total y de ahí sale la división. Es la
   única regla que mezcla los dos insumos — ver [Las dos unidades de
   insumo](#las-dos-unidades-de-insumo).
7. **Penalización por Contaminación:** −3 puntos por cada vez que la Vitalidad del jugador llegó a
   0 durante la partida.
8. **Conversión de Riqueza:** +1 punto por cada 5 Monedas restantes en la reserva final (división
   entera).

> **Los Ingresos de Panadería no son un término de puntuación.** La renta se cobra en Monedas
> durante la partida; lo que llegue al final sin gastar puntúa por Conversión de Riqueza como
> cualquier otra Moneda. Su valor real es lo que te dejó comprar mientras jugabas.

### 11.3 Desempate

En caso de empate en Puntos de Maestría:

1. Gana el investigador con más recetas **distintas** horneadas con éxito (el mismo recuento que
   alimenta Variedad de Recetas).
2. Si persiste el empate, gana quien tenga el mayor Nivel de Vitalidad en su cultivo base.
3. Si persiste el empate, gana quien tenga más Datos de Investigación.
4. Si persiste el empate, los investigadores empatados **comparten el puesto**: si es el
   primero, comparten la victoria y el siguiente ocupa el tercer puesto.

---

## 12. Anexo: Resumen de Mazos

### Mazo de Clima (30 cartas)

| Evento | Cantidad | Modificador Térmico | Efecto Biológico Inmediato | Efecto Pasivo (resto del día) |
|:---|:---:|:---:|:---|:---|
| Estabilidad Térmica | 10 | 0°C | Ninguno | Ninguno — avance normal. |
| Fallo de Refrigeración | 4 | +5°C | Ninguno | Acelera el avance base en +1 casilla. |
| Ola de Calor | 2 | +10°C | Ninguno | Acelera el avance base en +2 casillas. |
| Corriente de Aire | 4 | −5°C | Ninguno | Ralentiza el avance base en −1 casilla. |
| Fallo de Calefacción | 2 | −10°C | Ninguno | Ralentiza el avance base en −2 casillas. |
| Alta Humedad | 2 | 0°C | Ninguno | Iniciar Receta cuesta 1 token de agua menos ese día (−5% de hidratación). |
| Explosión de Levaduras | 2 | 0°C | Todos ganan +1 Vitalidad (máx. 6). | Ninguno. |
| Acidificación Acelerada | 2 | 0°C | Todos ganan +1 Acidez (máx. 6). | Ninguno. |
| Aletargamiento Invernal | 2 | −5°C | Ninguno | Desgaste metabólico de −2 Vitalidad en vez de −1. |

### Mazo de Tendencias de Mercado (21 cartas)

| Modificador | Cantidad | Efecto |
|:---:|:---:|:---|
| −2 | 1 | Los 3 visores de harina se mueven 2 casillas hacia abajo (más baratos). |
| −1 | 7 | Los 3 visores se mueven 1 casilla hacia abajo. |
| 0 | 5 | Los visores no se mueven. |
| +1 | 7 | Los 3 visores se mueven 1 casilla hacia arriba (más caros). |
| +2 | 1 | Los 3 visores se mueven 2 casillas hacia arriba. |

### Mazo de Recetas (36 cartas)

12 protocolos distintos, con distinto número de copias según el grado:

| Grado | Protocolos | Copias de cada uno | Cartas |
|:---|:---:|:---:|:---:|
| Básica | 4 | 4 | 16 |
| Intermedia | 4 | 3 | 12 |
| Avanzada | 4 | 2 | 8 |
| **Total** | **12** | — | **36** |

Las Básicas son comunes y las Avanzadas escasas: la rareza es una barrera independiente del
precio, y es la **única** barrera de posición que hay — el mazo se baraja entero, sin estratos, así
que los tres grados se mezclan y una Básica puede salir en el mercado igual que una Avanzada. Antes
de barajarlo se retira una copia de cada Básica repartida a las Carpetas de Proyectos iniciales
(ver [Preparación](#3-preparación-de-la-partida)).

Todos los valores de cada protocolo, en el [Catálogo de Recetas](#8-catálogo-de-recetas).

### Mazo de Patrocinios (8 cartas)

Se usa una única vez, en la preparación de la partida — ver la tabla completa en [Preparación de
la Partida](#3-preparación-de-la-partida). No vuelve a barajarse ni a jugarse durante la partida.
