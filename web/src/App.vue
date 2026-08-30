<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import LobbyView from './components/LobbyView.vue'
import GameView from './components/GameView.vue'
import { intentarReconectar, store } from './store'
import { habilitarAudio } from './sonido'

const reconectando = ref(true)

// Si cerraste el navegador a mitad de partida, la sesión (sala + tu token)
// sigue en localStorage -- se intenta recuperar una sola vez al arrancar,
// antes de decidir si mostrar el lobby o el tablero directamente.
onMounted(async () => {
  await intentarReconectar()
  reconectando.value = false
})

// Los navegadores exigen un gesto del usuario antes de permitir audio -- se
// habilita el AudioContext en la primera interaccion de toda la pestaña
// (crear/unirse a una sala ya cuenta), bien antes de que un cambio de turno
// real necesite sonar (ver sonido.ts / store.ts:aplicarEstado).
document.addEventListener('pointerdown', habilitarAudio, { once: true })

const enPartida = computed(() => store.sesion !== null && store.estado !== null)
</script>

<template>
  <!-- El lobby/ranking se leen como documento (columna centrada); la partida
       es un tablero y ocupa la ventana entera -- ver GameView.vue. -->
  <main class="app-shell" :class="{ centrado: !enPartida }">
    <p v-if="reconectando" class="reconectando">Cargando…</p>
    <template v-else>
      <GameView v-if="enPartida" />
      <LobbyView v-else />
    </template>
  </main>
</template>

<style>
/* ---------------------------------------------------------------------------
   CAPA DE TOKENS -- fuente unica de verdad del sistema visual.
   Ningun componente deberia volver a escribir un hex, un tamaño de fuente ni
   un espaciado a mano: todo sale de aqui.

   Tres SUPERFICIES, como en un juego de mesa fisico: la mesa (el suelo de
   todo), la zona impresa (las regiones del tablero) y la carta (lo que se
   levanta de la mesa). Antes todo era el mismo rectangulo plano sobre el
   mismo fondo, que es justo por lo que la pantalla parecia una lista de
   widgets en vez de un tablero.

   Dos ACENTOS con significado: cobre = tuyo / interactivo / turno activo;
   verdin = estado compartido del mercado. El resto de colores son estado de
   juego (vitalidad, riesgo, temperatura) y no se usan para decorar.
--------------------------------------------------------------------------- */
:root {
  /* Superficies */
  --mesa: #100d0b;
  --zona: #191411;
  --carta: #241c17;
  --borde: #3a322a;
  --borde-fuerte: #4d4238;

  /* Tinta */
  --tinta: #efe6d9;
  --tinta-tenue: #a2917c;
  --tinta-sobre-acento: #1a1410;

  /* Acentos */
  --cobre: #e0a343;
  --verdin: #4e9b8f;

  /* Estado de juego */
  --vital: #7bb662;
  --riesgo: #d0553f;
  --calido: #d9612f;
  --frio: #6fa8d9;

  /* Lavados: un unico alfa por color (antes convivian 0.08/0.10/0.12 del
     mismo rojo y 0.14/0.15/0.16 del mismo ambar). */
  --lavado-cobre: rgba(224, 163, 67, 0.15);
  --lavado-verdin: rgba(78, 155, 143, 0.15);
  --lavado-riesgo: rgba(208, 85, 63, 0.12);
  --lavado-vital: rgba(123, 182, 98, 0.12);
  --velo-modal: rgba(0, 0, 0, 0.72);

  /* Elevacion: las cartas son lo unico que se levanta de la mesa. */
  --sombra-carta: 0 2px 6px rgba(0, 0, 0, 0.4);
  --sombra-flotante: 0 6px 18px rgba(0, 0, 0, 0.45);

  /* Tipografia */
  --fuente-titulo: 'Bricolage Grotesque', 'Segoe UI', system-ui, sans-serif;
  --fuente: 'IBM Plex Sans', 'Segoe UI', system-ui, -apple-system, sans-serif;
  --fuente-dato: 'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace;

  /* Escala tipografica: 7 pasos. Sustituye a los 30 tamaños distintos que
     habia, doce de ellos dentro de la franja 0.62-0.82rem. */
  --t-micro: 0.6875rem; /* 11px -- eyebrows, ticks, unidades */
  --t-xs: 0.75rem; /*   12px -- celdas de tabla, tooltips */
  --t-s: 0.8125rem; /*  13px -- texto secundario, stats */
  --t-m: 0.9375rem; /*  15px -- cuerpo */
  --t-l: 1.1875rem; /*  19px -- titulos de panel */
  --t-xl: 1.625rem; /*  26px -- titulos de region, lecturas grandes */
  --t-display: 2.125rem; /* 34px -- numeros de carta */

  /* Espaciado: todo padding/margin/gap sale de estos seis. */
  --e1: 0.25rem;
  --e2: 0.5rem;
  --e3: 0.75rem;
  --e4: 1rem;
  --e5: 1.5rem;
  --e6: 2rem;

  /* Radios: control / carta / zona. */
  --r-control: 4px;
  --r-carta: 8px;
  --r-zona: 12px;

  --transicion: 140ms ease;

  /* Alias de compatibilidad: los componentes se migran uno a uno, y hasta
     entonces siguen leyendo los nombres viejos. Se borran al final. */
  --color-fondo: var(--mesa);
  --color-panel: var(--zona);
  --color-borde: var(--borde);
  --color-texto: var(--tinta);
  --color-texto-tenue: var(--tinta-tenue);
  --color-acento: var(--cobre);
  --color-bien: var(--vital);
  --color-mal: var(--riesgo);
  --color-calido: var(--calido);
  --color-frio: var(--frio);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--mesa);
  color: var(--tinta);
  font-family: var(--fuente);
  font-size: var(--t-m);
  line-height: 1.45;
}

/* Los titulos son la voz de Bricolage; el cuerpo es Plex Sans. Sin este
   reset, siete <h3> de la app se dibujaban al 1.17em por defecto del
   navegador porque nadie los estilaba. */
h1,
h2,
h3,
h4 {
  font-family: var(--fuente-titulo);
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
}

h1 {
  font-size: var(--t-xl);
}

h2 {
  font-size: var(--t-l);
}

h3 {
  font-size: var(--t-m);
}

h4 {
  font-size: var(--t-s);
}

/* Cualquier numero que viva sobre una escala (vitalidad, acidez,
   fermentacion, precio, PA, hidratacion) se compone en Plex Mono: es lo que
   hace que las distintas pistas se lean como el mismo instrumento. */
.dato {
  font-family: var(--fuente-dato);
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'zero' 1;
}

/* Etiqueta de seccion. Antes existian cinco variantes de esto mismo
   (.sub-titulo, .titulo-mesa, .etiqueta-pila, .seccion-titulo,
   .cabecera-zona h4) con cinco juegos de valores distintos. */
.eyebrow {
  font-family: var(--fuente);
  font-size: var(--t-micro);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
  margin: 0;
}

/* Tamaños de icono. Los ocho Icono*.vue ya declaran width/height 100%, asi
   que quien los usa solo tiene que elegir una caja de esta escala en vez de
   inventarse un px (habia ocho valores distintos: 14/16/18/20/22/26/30/42). */
.ico-xs,
.ico-s,
.ico-m,
.ico-l {
  display: inline-block;
  flex: 0 0 auto;
  line-height: 0;
}

.ico-xs {
  width: 14px;
  height: 14px;
}

.ico-s {
  width: 18px;
  height: 18px;
}

.ico-m {
  width: 24px;
  height: 24px;
}

.ico-l {
  width: 40px;
  height: 40px;
}

button {
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* No habia ningun estilo de foco en toda la app. */
:focus-visible {
  outline: 2px solid var(--cobre);
  outline-offset: 2px;
  border-radius: var(--r-control);
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

.app-shell {
  min-height: 100vh;
}

/* El lobby y el ranking son documentos: se leen en una columna centrada. La
   partida es un tablero y ocupa toda la pantalla (ver GameView.vue). */
.app-shell.centrado {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--e4);
}

.reconectando {
  text-align: center;
  color: var(--tinta-tenue);
  margin-top: 4rem;
}

/* Superficie de panel. La "zona impresa" del tablero; las cartas van encima
   con .carta-superficie. */
.panel {
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
  padding: var(--e4);
}

/* Superficie de modal. Un modal NO es una zona impresa del tablero: es lo que
   se levanta por encima de todo, asi que le toca el tier --carta con sombra
   flotante. Por eso tampoco lleva .panel -- ademas de ser el tier equivocado,
   GameView aplana todo .panel que caiga dentro de una region. */
.modal {
  background: var(--carta);
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-zona);
  padding: var(--e4);
  box-shadow: var(--sombra-flotante);
}

/* Estilos compartidos por los 11 modales de accion (BarraAcciones.vue) */
.campo {
  display: block;
  margin-bottom: var(--e3);
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.campo select,
.campo input {
  display: block;
  width: 100%;
  margin-top: var(--e1);
  padding: var(--e2);
  background: var(--mesa);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  color: var(--tinta);
  font-family: inherit;
  font-size: var(--t-m);
}

.campo-checkbox {
  display: flex;
  align-items: center;
  gap: var(--e1);
  margin-bottom: var(--e2);
  font-size: var(--t-s);
}

.campo-checkbox input {
  width: auto;
}

.opciones-radio {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  margin-bottom: var(--e3);
  font-size: var(--t-s);
}

.opciones-radio label {
  display: flex;
  align-items: center;
  gap: var(--e1);
}

button.confirmar {
  flex: 1;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--cobre);
  background: var(--cobre);
  color: var(--tinta-sobre-acento);
  font-weight: 600;
  transition: filter var(--transicion);
}

button.confirmar:hover:not(:disabled) {
  filter: brightness(1.08);
}

button.secundario {
  flex: 1;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: var(--carta);
  color: var(--tinta);
  transition: border-color var(--transicion);
}

button.secundario:hover:not(:disabled) {
  border-color: var(--borde-fuerte);
}

.info-linea {
  font-size: var(--t-s);
  color: var(--tinta-tenue);
  margin-bottom: var(--e2);
}

/* Unidad equivalente entre parentesis (token <-> porcentaje). Ver
   data/unidades.ts: cada insumo se guarda en una unidad distinta, asi que en
   todas partes se imprime la primaria de ese sitio y esta al lado, atenuada. */
.unidad-secundaria {
  color: var(--tinta-tenue);
  font-size: 0.85em;
  font-weight: 400;
  white-space: nowrap;
}
</style>
