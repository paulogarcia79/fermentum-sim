<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'

const recientes = computed(() => store.eventos.slice(-12).reverse())

function jugadorNombre(idx: number | null): string {
  if (idx === null || !store.estado) return ''
  return store.estado.players[idx]?.nombre ?? ''
}

const ICONOS: Record<string, string> = {
  jefe_asignado: '👑',
  clima_revelado: '⛅',
  tendencia_anunciada: '📣',
  tendencia_mercado: '📈',
  mercado_refrescado: '🔄',
  receta_descartada: '🗑',
  masa_avanzo: '📈',
  horneado: '🍞',
  desgaste: '💧',
  contaminacion: '☣',
  fin_de_partida: '🏁',
}
</script>

<template>
  <section class="panel eventos">
    <h3>Registro</h3>
    <ul>
      <li v-for="(ev, i) in recientes" :key="i" class="fila-evento">
        <span class="icono">{{ ICONOS[ev.tipo] ?? '•' }}</span>
        <span class="texto">
          <span v-if="ev.jugador_idx !== null" class="quien">{{ jugadorNombre(ev.jugador_idx) }}:</span>
          {{ ev.mensaje }}
        </span>
      </li>
      <li v-if="recientes.length === 0" class="vacio">Sin eventos todavía.</li>
    </ul>
  </section>
</template>

<style scoped>
.eventos h3 {
  margin-top: 0;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  max-height: 320px;
  overflow-y: auto;
}

.fila-evento {
  display: flex;
  gap: var(--e2);
  font-size: var(--t-s);
  align-items: flex-start;
}

.quien {
  font-weight: 600;
}

.vacio {
  color: var(--tinta-tenue);
  font-style: italic;
}
</style>
