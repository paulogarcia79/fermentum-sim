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
- Manteniendo una masa madre con alta Vitalidad y un buen equilibrio de Acidez hasta el final de
  la partida.
- Gestionando con cuidado la economía del laboratorio: insumos, Datos de Investigación y Monedas.

La partida termina en cuanto se agota el mazo de Clima, o en cuanto algún jugador hornea con éxito
su quinta receta — lo que ocurra primero.

---

## 2. Componentes

- **Tablero Central (El Laboratorio):** controla el estado global — termómetro/Ábaco de
  Fermentación, mercado de recetas, Bolsa de Harinas y Suministro Hídrico Global, y el Track de
  Orden de Turno.
- **Tableros Individuales:** uno por jugador, dividido en zonas — Cultivo Base (Vitalidad y
  Acidez), Estaciones de Fermentación (3, la tercera bloqueada al inicio), Tecnologías de
  Laboratorio, y Carpeta de Proyectos (recetas investigadas pero no iniciadas).
- **Cartas de Receta:** 36 en total (18 Básicas, 18 Avanzadas), definen el protocolo de horneado de
  cada pan — ver [Catálogo de Recetas](#8-catálogo-de-recetas).
- **Cartas de Clima:** 30 cartas que regulan la temperatura y los eventos biológicos del
  laboratorio — ver [Anexo](#12-anexo-resumen-de-mazos).
- **Cartas de Tendencias de Mercado:** 21 cartas que mueven el precio de la harina. Cada una se
  anuncia al inicio de un día y se aplica al final de ese mismo día, fijando los precios del
  siguiente.
- **Cartas de Patrocinio:** 8 cartas usadas una sola vez, al preparar la partida, para repartir el
  orden de turno inicial y los recursos de arranque.
- **Dados de Inóculo:** 3 por jugador, sellan la velocidad de fermentación de cada masa iniciada.
- **Cubos de Laboratorio:** 8 por jugador, marcan acciones usadas, acidez sellada y tecnologías
  instaladas.
- **Tokens de Recursos:** harina (Blanca, Integral, Centeno) y agua (múltiplos de 5% de
  hidratación).
- **Fichas de Monedas** y **Tokens de Datos de Investigación:** las dos divisas del juego (ver más
  abajo).

### Las dos divisas del juego

Fermentum usa dos recursos económicos independientes, que no se convierten entre sí:

- **Monedas:** la divisa comercial. Se ganan vendiendo pan al Hornear y Vender, y se gastan
  comprando harina y agua en el Mercado.
- **Datos de Investigación:** la divisa técnica del laboratorio. Se ganan horneando en Zona
  Óptima, mediante el Simposio Técnico, o pasivamente por mantener el cultivo maduro. Se gastan en
  instalar Tecnologías, en Horas Extras y en el Pedido de Urgencia.

---

## 3. Preparación de la Partida

1. Colocar el Tablero Central con la temperatura en **20°C** y el Track de Orden de Turno al
   lado.
2. Repartir a cada jugador un Tablero Individual, sus marcadores, 3 Dados de Inóculo y 8 Cubos de
   Laboratorio. Los tracks de Vitalidad y Acidez inician en **Nivel 1**. Colocar una Ficha de
   Bloqueo sobre la tercera ranura de fermentación (se libera al instalar la tecnología Cámara B).
3. **Asignación de Patrocinios:** barajar el mazo de 8 Cartas de Patrocinio y repartir una carta
   boca abajo a cada jugador sentado (de 1 a 4 jugadores). Revelar todas las cartas
   simultáneamente.
   - El jugador con el número de **Iniciativa más bajo** en su carta recibe el token de
     Investigador Jefe y actúa primero en el Día 1. Los demás se ordenan de forma ascendente según
     su número de Iniciativa.
   - **Despliegue de Insumos:** cada jugador toma de la reserva general la harina, el lote de agua
     y las monedas indicadas en su carta (tabla completa abajo). Hecho esto, todas las cartas de
     Patrocinio vuelven a la caja — no se usan de nuevo en la partida.

   | Iniciativa | Harina | Lote de Agua | Monedas Iniciales |
   |:---:|:---|:---|:---:|
   | 1 | 1 bolsa de Blanca | 2 tokens (10%) | 9 |
   | 2 | 1 bolsa de Blanca | 6 tokens (30%) | 8 |
   | 3 | 1 bolsa de Blanca | 12 tokens (60%) | 6 |
   | 4 | 1 bolsa de Integral | 6 tokens (30%) | 8 |
   | 5 | 1 bolsa de Integral | 12 tokens (60%) | 6 |
   | 6 | 1 bolsa de Centeno | 6 tokens (30%) | 8 |
   | 7 | 1 bolsa de Centeno | 12 tokens (60%) | 6 |
   | 8 | 2 bolsas de Blanca | 20 tokens (100%) | 4 |

   Los jugadores con Iniciativa alta (actúan más tarde en la primera ronda) reciben un capital de
   insumos de mayor valor, para compensar la ventaja temporal del Investigador Jefe.

4. **Carpeta de Proyectos inicial:** separar todas las recetas de grado Básica del mazo general,
   barajarlas, y entregar 1 al azar a cada jugador — se coloca boca arriba en su Carpeta de
   Proyectos, en estado inactivo. Deberá usarse la acción Iniciar Receta durante la partida para
   activarla. Las recetas básicas restantes se remezclan de vuelta en el mazo general.
5. **Mercado inicial:** revelar las primeras 4 cartas del mazo general de recetas (la distribución
   de grados es aleatoria, ya que las básicas de arranque ya se separaron). Colocar los 3 visores
   de la Bolsa de Harinas en la posición central (**3 de 5**) para Blanca, Integral y Centeno.

Cada jugador arranca, sin importar su carta de Patrocinio, con: Vitalidad 1, Acidez 1, 3 Dados de
Inóculo, 0 Puntos de Acción, 0 Datos de Investigación, todas las Tecnologías desactivadas, y 1
receta Básica aleatoria en su Carpeta de Proyectos.

A partir de la Ronda 2, el orden de turno vuelve a calcularse cada Fase I según la regla estándar
de Jerarquía (ver más abajo) — la Iniciativa de las Cartas de Patrocinio solo determina el Día 1.

---

## 4. Estructura del Día de Laboratorio

Cada ronda de juego se llama un **Día de Laboratorio** y consta de tres fases secuenciales y
estrictas, siempre en este orden:

1. **Fase I: Ambiente** — se preparan las variables globales del día.
2. **Fase II: Acción** — los jugadores usan sus Puntos de Acción.
3. **Fase III: Fermentación** — resolución automática de las masas, desgaste del cultivo base,
   rotación del Mercado de Recetas (se descarta la más antigua) y aplicación de la Tendencia de
   Mercado anunciada esa mañana, que fija los precios del día siguiente.

---

## 5. Fase I: Ambiente

Liderada por el Investigador Jefe, esta fase se resuelve en el siguiente orden:

### 5.1 Actualización de Jerarquía

El token de Investigador Jefe se reasigna al jugador con el nivel de **Vitalidad más alto** en su
cultivo base.

- **Desempate:** mayor cantidad de Datos de Investigación.
- **Empate persistente:** se mantiene el orden de turno del día anterior.
- El Investigador Jefe actúa primero en la Fase II y tiene prioridad en la elección de recetas e
  insumos.
- *Excepción:* en el Día 1, el orden lo determina la Iniciativa de las Cartas de Patrocinio (ver
  [Preparación de la Partida](#3-preparación-de-la-partida)), no la Vitalidad.

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
día (§9.5) y, por tanto, fija los precios de la Bolsa de Harinas del **día siguiente**. Los precios
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
- **Acciones que no terminan el turno:** Alimentar el Cultivo, Horas Extras y Pedido de Urgencia
  son gratuitas (0 PA) y **no** cierran la visita del jugador — un jugador que ya gastó sus 2 PA en
  otras acciones sigue recibiendo visitas mientras le quede alguna de estas tres acciones
  gratuitas sin usar ese día. Cualquier acción de costo en PA, o un **Pasar** explícito, sí cierra
  la visita; **Pasar** además renuncia de inmediato a cualquier acción gratuita pendiente por el
  resto del día.
- **Un espacio de acción, una visita por día:** cada espacio de acción con costo de PA (B a G,
  Simposio Técnico, H, I) solo puede visitarse **una vez por Día de Laboratorio, por jugador** —
  el investigador marca el espacio con su color en cuanto lo visita, bloqueándolo para él (no para
  el resto de jugadores) hasta el día siguiente. Con 2-3 PA (Horas Extras incluida) esto significa
  como máximo un uso de cada espacio distinto por día, nunca el mismo espacio dos veces. Pedido de
  Urgencia queda exento (no cuesta PA — ver su entrada en el Catálogo de Acciones).
- **Sin escasez de insumos:** a diferencia de las recetas del mercado (que sí ocupan un espacio
  limitado), la harina y el agua ya no se agotan por turno — son un precio compartido (Bolsa de
  Harinas) y una tabla de precio por temperatura (Suministro Hídrico Global) que cualquier jugador
  puede usar en su visita al Mercado sin quitarle el cupo a los demás.

---

## 7. Catálogo de Acciones

### Acciones principales (Costo: 1 PA)

#### B. Iniciar Receta

**Costo:** 1 PA + 1 token de harina (100% del tipo que pida la receta) + los tokens de agua
exactos según la hidratación de la receta. **Límite:** 1 vez por día (por espacio de acción).

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
  visor de ese tipo en la Bolsa de Harinas) y recibir 1 bolsa (100%) de esa harina. El visor se
  mueve 1 casilla hacia el extremo caro (tope en posición 5).
- **Vender Harina:** entregar 1 bolsa (100%) de esa harina y cobrar el valor de Venta visible en
  Monedas. El visor se mueve 1 casilla hacia el extremo barato (tope en posición 1).
- **Comprar Lote de Agua:** pagar el coste en Monedas según la fila de temperatura actual y el
  tamaño de lote elegido (10%, 30%, 60% o 100%), y recibir los tokens de agua correspondientes (1
  token = 5% de hidratación).

**Regla de Exclusividad:** una misma visita puede combinar varias transacciones, pero como máximo
**una por tipo de recurso** — se puede comprar Blanca, vender Centeno y comprar un lote de agua en
la misma visita, pero no comprar y vender la misma harina, ni comprar el mismo tipo dos veces.

**Bolsa de Harinas** (Monedas según la posición del visor, 1 a 5):

| Harina | Posición 1 | Posición 2 | Posición 3 | Posición 4 | Posición 5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Blanca — Compra / Venta | 2 / 1 | 3 / 2 | 4 / 3 | 5 / 4 | 6 / 5 |
| Integral — Compra / Venta | 4 / 2 | 5 / 3 | 6 / 4 | 7 / 5 | 8 / 6 |
| Centeno — Compra / Venta | 6 / 3 | 7 / 4 | 8 / 5 | 9 / 6 | 10 / 7 |

**Suministro Hídrico Global** (Monedas según temperatura y tamaño de lote):

| Temperatura | 10% | 30% | 60% | 100% |
|:---:|:---:|:---:|:---:|:---:|
| 30°C | 3 | 6 | 10 | 14 |
| 25°C | 2 | 5 | 8 | 12 |
| 20°C | 2 | 4 | 7 | 10 |
| 15°C | 1 | 3 | 6 | 9 |
| 10°C | 1 | 2 | 4 | 7 |

#### D. Implementar Mejora de Laboratorio

**Costo:** 1 PA + Datos de Investigación, según la mejora — ver [Tecnologías de
Laboratorio](#10-tecnologías-de-laboratorio). El beneficio se activa de inmediato. Cada mejora
individual solo puede instalarse **una vez** por partida, pero un jugador puede llegar a instalar
varias mejoras distintas a lo largo de la partida — no existe un tope global de "una sola mejora
en total". **Límite adicional:** el espacio D en sí solo puede visitarse 1 vez por día — instalar
CUALQUIER mejora agota el espacio para el resto del día, así que dos mejoras distintas nunca pueden
instalarse el mismo día; como muy pronto, la segunda espera al día siguiente.

#### E. Técnica (Pliegues)

**Costo:** 1 PA. Avanza el marcador de una masa en fermentación 1 casilla adicional. Con la
tecnología Cámara B instalada, el jugador puede optar en su lugar por recuperar +1 de Vitalidad en
su cultivo base, o por afectar a dos masas simultáneamente (+1 casilla a cada una). **Límite:** 1
vez por día (por espacio de acción) — cualquiera de las variantes agota el espacio.

#### F. Hornear y Vender (Finalización de Protocolo)

**Costo:** 1 PA. **Límite:** 1 vez por día (por espacio de acción) — no aplica al colapso
automático de Fase III, que no pasa por este espacio ni consume PA. Finaliza el protocolo de una
masa y la vende de inmediato: se obtienen Puntos de
Maestría, Monedas y (en Zona Óptima) Datos de Investigación, según la zona del track donde se
encuentre el marcador:

| Zona | Puntos de Maestría | Monedas | Datos de Investigación |
|:---|:---|:---|:---:|
| **Óptima** | Puntos íntegros de la carta | Ingreso completo de la carta | Sí (+1, +1 extra si se hornea en el centro exacto con Módulo Analítico) |
| **Baja** (masa cruda) | Puntos reducidos de la carta | Venta con margen reducido | No |
| **Sobre-fermentada** (colapso, resuelto automáticamente en Fase III) | Penalización negativa de la carta | Recuperación del coste base, sin margen | No |

**Bono de Sabor:** si la carta conserva el Cubo de Acidez sellado desde que se inició la receta
(y el horneado **no** fue un colapso), se suman los puntos de sabor impresos en la carta **y**
+2 Monedas adicionales al ingreso de la venta. El Bono de Sabor nunca se aplica en un colapso.

#### G. Investigar Protocolo

**Costo:** 1 PA. **Límites:** máximo 3 cartas en la Carpeta de Proyectos (si está llena, hay que
descartar una antes de investigar la nueva); además, 1 vez por día (por espacio de acción).
Selecciona una carta de receta de cualquiera de las 4 estaciones visibles del Mercado Central y la
coloca boca arriba, en estado inactivo, en la Carpeta de Proyectos propia. El espacio del mercado
que se libera queda vacío hasta el reabastecimiento del Protocolo de Refresco al inicio del día
siguiente.

#### Simposio Técnico

**Costo:** 1 PA. **Límite:** 1 vez por día (por espacio de acción), sin importar si se descarta
desde la carpeta o desde una estación. Descarta una carta de receta de la Carpeta de Proyectos o de
una estación de fermentación activa (perdiendo esa masa sin puntuación ni penalización, pero
recuperando el Dado de Inóculo) a cambio de +1 Dato de Investigación inmediato.

### Acciones auxiliares y de emergencia (Costo: 0 PA)

#### A. Alimentar el Cultivo (Mantenimiento)

**Límite:** una vez por Día de Laboratorio. Se puede gastar 10% de harina (de cualquier tipo) por
+1 Vitalidad, y/o 10% de agua por +1 Acidez (máximo Nivel 6 en ambos) — uno, otro, o ambos en la
misma acción.

#### Horas Extras

**Costo:** 1 Dato de Investigación. Otorga de inmediato +1 Punto de Acción adicional para usar ese
mismo día. Solo puede activarse **una vez por Día de Laboratorio** por jugador.

#### Pedido de Urgencia

**Costo:** 1 Dato de Investigación. Ignora el Mercado por completo — sin importar el precio
vigente — y obtiene directamente de la reserva general **un** tipo de recurso a elección: 100% de
un tipo de harina, o los tokens de agua que el jugador desee (5% cada uno). A diferencia de Horas
Extras, no tiene límite de usos por día — se autolimita únicamente por los Datos de Investigación
disponibles. Al no costar PA, queda exento de la regla "1 vez por día por espacio de acción" de la
[Fase II](#6-fase-ii-acción) — es intencional, no un descuido.

#### Protocolos de Emergencia (Rescate de Cultivo)

Solo pueden ejecutarse si la Vitalidad del cultivo base ha llegado a 0 (ver [Fase
III](#9-fase-iii-fermentación)):

- **H. Re-cultivo Manual:** Costo 1 PA + 50% de harina (de cualquier tipo, sin costo de agua).
  Retira la Contaminación y sitúa Vitalidad y Acidez en Nivel 1. **Límite:** 1 vez por día (por
  espacio de acción), además de requerir Contaminación activa.
- **I. Inóculo de Emergencia:** Costo 1 PA + 1 Dato de Investigación. Retira la Contaminación y
  sitúa Vitalidad y Acidez en Nivel 2 (resultado superior al Re-cultivo Manual). **Límite:** 1 vez
  por día (por espacio de acción), además de requerir Contaminación activa.

---

## 8. Catálogo de Recetas

El mazo oficial de recetas contiene 36 cartas — 18 de grado Básica y 18 de grado Avanzada, con
distintas cantidades de copias según el tipo. Todas las Avanzadas requieren la tecnología Módulo
Analítico para poder iniciarse. Los tracks de fermentación de todas las recetas corren de 1 a 20
casillas.

| Receta | Grado | Harina | Hidratación | Acidez Diana (Bono de Sabor) | Zona Baja | Zona Óptima | Zona Sobre-fermentada | Puntos (Baja / Óptima / Sobre) | Monedas (Baja / Óptima / Sobre) | Requiere |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| Pan de Campo | Básica | Blanca | 60% (12 tokens) | Nivel 3 (+3) | 1–10 | 11–15 | 16–20 | 4 / 10 / −2 | 13 / 17 / 11 | — |
| Focaccia | Básica | Blanca | 75% (15 tokens) | Nivel 1–2 (+2) | 1–9 | 10–14 | 15–20 | 3 / 12 / −3 | 15 / 19 / 13 | — |
| Baguette | Básica | Blanca | 65% (13 tokens) | Nivel 2 (+3) | 1–11 | 12–15 | 16–20 | 5 / 11 / −2 | 14 / 18 / 12 | — |
| Pizza Napolitana | Avanzada | Blanca | 62% (13 tokens) | Nivel 3 (+4) | 1–10 | 11–14 | 15–20 | 4 / 14 / −4 | 15 / 21 / 12 | Módulo Analítico |
| Brioche | Avanzada | Blanca | 52% (11 tokens) | Nivel 1 (+5) | 1–14 | 15–17 | 18–20 | 5 / 16 / −6 | 14 / 21 / 11 | Módulo Analítico |
| Hogaza Centeno | Avanzada | Centeno | 67% (14 tokens) | Nivel 4–5 (+6) | 1–12 | 13–16 | 17–20 | 6 / 15 / −5 | 20 / 27 / 17 | Módulo Analítico |
| Pan de Semillas | Avanzada | Integral | 78% (16 tokens) | Nivel 3–4 (+7) | 1–13 | 14–16 | 17–20 | 6 / 17 / −5 | 19 / 26 / 16 | Módulo Analítico |
| Panettone | Avanzada | Blanca | 47% (10 tokens) | Nivel 1 (+8) | 1–16 | 17–18 | 19–20 | 8 / 20 / −8 | 13 / 22 / 10 | Módulo Analítico |

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
  tecnología instalada, y se aplica masa por masa.

**Principio de Memoria Biológica:** una vez iniciada, una masa es un ecosistema independiente. Si
el cultivo base del jugador llega a Vitalidad 0 o se contamina después de haber iniciado la
receta, esa masa en curso **no se ve afectada** — sigue avanzando con el valor de dado que quedó
sellado en el momento de la mezcla original.

### 9.2 Colapso Estructural (Sobre-fermentación)

Si, tras aplicar el Avance Final, la posición de una masa entra en su Zona Sobre-fermentada, la
masa colapsa de inmediato: se hornea automáticamente con costo 0 PA, aplicando la penalización de
puntos y el ingreso de Monedas de recuperación de coste de esa zona (ver [Catálogo de
Recetas](#8-catálogo-de-recetas)). El Dado de Inóculo se recupera y la estación de fermentación
queda libre para el día siguiente. Un colapso nunca otorga el Bono de Sabor, aunque el Cubo de
Acidez estuviera sellado.

### 9.3 Desgaste Metabólico

Al final de la Fase III, todos los cultivos base sufren desgaste:

- **Estándar:** −1 Vitalidad.
- **Con Aletargamiento Invernal vigente:** −2 Vitalidad.
- **Con la tecnología Criopreservación instalada:** el jugador ignora el desgaste por completo
  ese día (Estasis Biológica) — ni −1 ni −2, sin importar el clima.

La Vitalidad nunca desciende por debajo de 0. Si un jugador llega a Vitalidad 0 en cualquier
momento (por desgaste, por un evento, o al inicio del turno), sufre una penalización inmediata de
**−3 Puntos de Maestría** y entra en estado de **Contaminación**: no puede iniciar nuevas recetas
hasta ejecutar un Protocolo de Emergencia (H o I). Cada episodio de Contaminación aplica su propia
penalización de −3 puntos — si un jugador cae en Contaminación más de una vez durante la partida,
las penalizaciones se acumulan.

### 9.4 Rotación del Mercado de Recetas

Al cerrar el día, se descarta la carta de receta situada en la estación más a la derecha del
Mercado Central (la más antigua). Si esa estación ya estaba vacía por una Acción G, se descarta la
siguiente carta real hacia la izquierda. El hueco que deja se rellena en el Protocolo de Refresco
del día siguiente (§5.4).

### 9.5 Aplicación de la Tendencia de Mercado

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

Cada jugador puede instalar hasta 4 mejoras permanentes a lo largo de la partida (Acción D). Cada
una solo puede instalarse una vez, pero un jugador puede llegar a tener varias distintas.

| Tecnología | Costo | Efecto |
|:---|:---:|:---|
| **Incubadora** | 3 Datos | Permite ajustar la temperatura local ±5°C (±1 casilla de avance en Fase III) para una masa específica, mitigando el clima. |
| **Cámara B** | 4 Datos | Desbloquea la tercera estación de fermentación y mejora la Acción E (Pliegues): recuperar +1 Vitalidad, o afectar dos masas a la vez. |
| **Módulo Analítico** | 3 Datos | Otorga +1 Dato de Investigación extra al hornear exactamente en el centro de la Zona Óptima, y habilita el inicio de recetas de grado Avanzada. |
| **Criopreservación** | 2 Datos | Estasis Biológica: el cultivo base ignora por completo el desgaste metabólico normal de la Fase III. |

---

## 11. Fin del Juego y Puntuación

### 11.1 Gatillos de Finalización

La partida termina de inmediato en cuanto ocurre cualquiera de estas dos condiciones:

1. El mazo de Clima se agota por completo.
2. Algún jugador hornea con éxito su **quinta receta** (las recetas colapsadas con valor negativo
   no cuentan para este conteo).

Una vez desencadenado el final, se completa el Día de Laboratorio en curso y se calcula la
puntuación.

### 11.2 Cálculo de Puntos de Maestría Finales

1. **Puntos Base:** suma de los puntos de todas las recetas horneadas, tanto positivas como
   negativas (colapsos incluidos).
2. **Puntos de Sabor:** suma de los bonos de Bono de Sabor de cada carta horneada con el Cubo de
   Acidez sellado.
3. **Madurez del Cultivo:** (Vitalidad actual + Acidez actual) ÷ 2, redondeando hacia arriba.
4. **Penalización por Desperdicio:** −1 punto por cada 3 tokens de harina o agua sin utilizar en
   la reserva final.
5. **Penalización por Contaminación:** −3 puntos por cada vez que la Vitalidad del jugador llegó a
   0 durante la partida.
6. **Conversión de Riqueza:** +1 punto por cada 5 Monedas restantes en la reserva final (división
   entera).

### 11.3 Desempate

En caso de empate en Puntos de Maestría:

1. Gana el investigador con el mayor Nivel de Vitalidad en su cultivo base.
2. Si persiste el empate, gana quien tenga más Datos de Investigación.

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
| Alta Humedad | 2 | 0°C | Ninguno | Iniciar Receta cuesta 1 token de agua menos ese día. |
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

18 Básicas + 18 Avanzadas — ver la composición exacta y todos los valores en el [Catálogo de
Recetas](#8-catálogo-de-recetas).

### Mazo de Patrocinios (8 cartas)

Se usa una única vez, en la preparación de la partida — ver la tabla completa en [Preparación de
la Partida](#3-preparación-de-la-partida). No vuelve a barajarse ni a jugarse durante la partida.
