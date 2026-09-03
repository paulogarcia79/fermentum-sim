<script setup lang="ts">
import { computed } from 'vue'
import { observarJugador, store } from '../store'
import { hexDeColor } from '../data/coloresJugador'

// No hay informacion oculta entre jugadores en Fermentum (la Carpeta de
// Proyectos es boca arriba, ACTIONS_REGISTRY.md SS2G), asi que mostrar
// filas compactas del resto de jugadores es solo una decision de espacio
// en pantalla, no una restriccion de reglas.
//
// Cada fila es ademas la puerta de entrada al tablero COMPLETO de ese
// jugador: al pulsarla, la region Tablero pasa a dibujar su tablero (ver
// SelectorTablero.vue, que es el otro camino y el unico siempre visible).
const oponentes = computed(() =>
  store.estado!.players
    .map((p, i) => ({ p, i }))
    .filter(({ i }) => i !== store.sesion!.playerIndex),
)

function esJefe(i: number): boolean {
  return store.estado!.jefe_investigador_idx === i
}

function esTurno(i: number): boolean {
  return store.estado!.jugador_en_turno_idx === i
}

function esObservado(i: number): boolean {
  return store.jugadorObservado === i
}
</script>

<template>
  <section class="panel oponentes">
    <h3>Otros investigadores</h3>
    <button
      v-for="{ p, i } in oponentes"
      :key="i"
      type="button"
      class="fila"
      :class="{ turno: esTurno(i), observada: esObservado(i) }"
      :aria-pressed="esObservado(i)"
      :title="`Ver el tablero de ${p.nombre}`"
      @click="observarJugador(i)"
    >
      <span class="nombre-fila">
        <span class="punto-color" :style="{ background: hexDeColor(p.color) }" />
        {{ p.nombre }}
        <span v-if="esJefe(i)" title="Investigador Jefe">👑</span>
        <span v-if="p.en_estado_contaminacion" class="badge-contaminado">◉</span>
      </span>
      <span class="stats">
        <span>Vit {{ p.vitalidad }}/6</span>
        <span>Acidez {{ p.acidez }}/6</span>
        <span>PA {{ p.puntos_accion }}</span>
        <span>Datos {{ p.datos_investigacion }}</span>
        <span>Monedas {{ p.monedas }}</span>
        <span :title="`${p.archivo_horneado_exitoso.length} horneados exitosos de los 5 que terminan la partida · ${p.archivo_colapsos.length} colapsos`">
          🍞 {{ p.archivo_horneado_exitoso.length }}/5
          <template v-if="p.archivo_colapsos.length"> · {{ p.archivo_colapsos.length }}⚠</template>
        </span>
        <span :title="`${p.puntos_horneados} pts horneados · proyección final ${p.puntos_maestria_final} PM`">
          Maestría {{ p.puntos_maestria_final }}
        </span>
      </span>
      <span class="masas" v-if="p.estaciones_fermentacion.some((s) => s)">
        <span v-for="(slot, idx) in p.estaciones_fermentacion" :key="idx">
          <template v-if="slot">Est-{{ idx + 1 }}: {{ slot.recipe.nombre }} (pos {{ slot.posicion_track }})</template>
        </span>
      </span>
    </button>
  </section>
</template>

<style scoped>
.oponentes h3 {
  margin-top: 0;
}

/* La fila es un <button> de verdad y no un div con @click: asi trae gratis
   el foco por teclado, Enter/Espacio y el anillo de foco global de App.vue.
   Todo lo de abajo es solo quitarle el cromado nativo. */
.fila {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  border-top: 1px solid var(--borde);
  border-radius: var(--r-control);
  padding: var(--e2) 0;
  font: inherit;
  font-size: var(--t-s);
  color: inherit;
  cursor: pointer;
  transition: background var(--transicion);
}

.fila:hover {
  background: var(--carta);
}

/* El tablero de este jugador es el que se esta viendo ahora mismo en la
   region Tablero. Marca neutra a proposito: el cobre ya significa «tuyo /
   en turno» en la misma lista. */
.fila.observada {
  background: var(--carta);
  box-shadow: inset 3px 0 0 var(--borde-fuerte);
}

.fila:first-of-type {
  border-top: none;
}

.fila.turno {
  color: var(--cobre);
}

.nombre-fila {
  font-weight: 600;
  display: flex;
  gap: var(--e2);
  align-items: center;
}

.badge-contaminado {
  color: var(--riesgo);
}

.punto-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  color: var(--tinta-tenue);
  margin-top: var(--e1);
}

.masas {
  display: flex;
  flex-direction: column;
  color: var(--tinta-tenue);
  margin-top: var(--e1);
}
</style>
