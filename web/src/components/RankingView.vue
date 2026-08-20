<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'

const estado = computed(() => store.estado!)
const filas = computed(() =>
  estado.value.ranking.map((r) => ({ ...r, jugador: estado.value.players[r.player_idx] })),
)
</script>

<template>
  <section class="panel ranking">
    <h2>🏁 Resultados Finales</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Investigador</th>
          <th>Puntos de Maestría</th>
          <th>Vitalidad</th>
          <th>Datos</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="fila in filas" :key="fila.player_idx" :class="{ ganador: fila.posicion === 1 }">
          <td>{{ fila.posicion }}</td>
          <td>{{ fila.jugador.nombre }}</td>
          <td>{{ fila.jugador.puntos_maestria_final }}</td>
          <td>{{ fila.jugador.vitalidad }}</td>
          <td>{{ fila.jugador.datos_investigacion }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.ranking h2 {
  margin-top: 0;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid var(--color-borde);
}

th {
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
  text-transform: uppercase;
}

tr.ganador td {
  color: var(--color-acento);
  font-weight: 600;
}
</style>
