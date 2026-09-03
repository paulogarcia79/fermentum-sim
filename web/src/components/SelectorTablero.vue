<script setup lang="ts">
// Selector del tablero a la vista -- una ficha por jugador, en el orden de
// turno del dia. Sustituye al rotulo «Mi Tablero» de la region: el titulo
// pasaria a repetir lo que la ficha seleccionada ya dice.
//
// Toda la informacion de este juego es publica (ver server/views.py: la vista
// es la misma para cualquier solicitante), asi que ver el tablero completo de
// un oponente no revela nada; lo unico que hacia falta era un sitio donde
// mirarlo. La otra puerta de entrada son las filas de TablerosOponentes.vue.
//
// El color: cobre = tuyo / el turno activo (App.vue). Por eso la ficha
// SELECCIONADA se rellena en tinta neutra y solo la del jugador en turno
// lleva el aro de cobre -- si la seleccion fuera cobre, mirar el tablero de
// alguien lo pintaria como si fuera el tuyo.
import { computed } from 'vue'
import { observarJugador, store } from '../store'
import { hexDeColor } from '../data/coloresJugador'
import IconoPeon from './IconoPeon.vue'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)

// Mismo criterio que OrdenTurnoPanel.vue: turno_orden puede venir vacio antes
// del primer dia, y entonces se usa el orden de inscripcion.
const orden = computed(() =>
  estado.value.turno_orden.length > 0
    ? estado.value.turno_orden
    : estado.value.players.map((_, i) => i),
)

const seleccionado = computed(() => store.jugadorObservado ?? miIndice.value)

function esTurno(idx: number): boolean {
  return idx === estado.value.jugador_en_turno_idx
}

/** Flechas ←/→ para moverse entre fichas, como pide role="tablist". */
function mover(paso: number): void {
  const pos = orden.value.indexOf(seleccionado.value)
  if (pos === -1) return
  const destino = orden.value[(pos + paso + orden.value.length) % orden.value.length]
  observarJugador(destino)
}
</script>

<template>
  <!-- En solitario no hay nada que elegir: se mantiene el rotulo de siempre. -->
  <h2 v-if="estado.players.length === 1" class="eyebrow rotulo-region">Mi Tablero</h2>

  <div
    v-else
    class="selector-tablero"
    role="tablist"
    aria-label="Tablero a la vista"
    @keydown.left.prevent="mover(-1)"
    @keydown.right.prevent="mover(1)"
  >
    <button
      v-for="idx in orden"
      :key="idx"
      type="button"
      role="tab"
      class="ficha"
      :class="{ seleccionada: idx === seleccionado, 'en-turno': esTurno(idx) }"
      :aria-selected="idx === seleccionado"
      :title="
        idx === miIndice
          ? 'Ver mi tablero'
          : `Ver el tablero de ${estado.players[idx].nombre}`
      "
      @click="observarJugador(idx)"
    >
      <span class="ico-xs"><IconoPeon :color="hexDeColor(estado.players[idx].color)" /></span>
      <span class="nombre">{{ estado.players[idx].nombre }}</span>
      <span v-if="idx === miIndice" class="tu">(tú)</span>
    </button>
  </div>
</template>

<style scoped>
.selector-tablero {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e1);
  flex: 0 0 auto;
}

.ficha {
  display: inline-flex;
  align-items: center;
  gap: var(--e1);
  padding: 2px var(--e2);
  background: transparent;
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  color: var(--tinta-tenue);
  font: inherit;
  font-size: var(--t-xs);
  line-height: 1.4;
  cursor: pointer;
  transition:
    border-color var(--transicion),
    background var(--transicion),
    color var(--transicion);
}

.ficha:hover {
  border-color: var(--borde-fuerte);
  color: var(--tinta);
}

.ficha.seleccionada {
  background: var(--carta);
  border-color: var(--borde-fuerte);
  color: var(--tinta);
  font-weight: 600;
}

/* El aro de cobre marca a quien le toca jugar, igual que la fila activa de
   OrdenTurnoPanel.vue -- es estado de partida, no la seleccion de vista. */
.ficha.en-turno {
  border-color: var(--cobre);
}

.ficha.seleccionada.en-turno {
  box-shadow: inset 0 0 0 1px var(--cobre);
}

.nombre {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tu {
  color: var(--tinta-tenue);
  font-weight: 400;
  font-size: var(--t-micro);
}
</style>
