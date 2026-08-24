<script setup lang="ts">
import { computed, ref } from 'vue'
import { cerrarSesion, crearSalaNueva, store } from '../store'

const estado = computed(() => store.estado!)
const filas = computed(() =>
  estado.value.ranking.map((r) => ({ ...r, jugador: estado.value.players[r.player_idx] })),
)

const creandoSala = ref(false)
async function onCrearSalaNueva() {
  creandoSala.value = true
  try {
    await crearSalaNueva()
  } finally {
    creandoSala.value = false
  }
}
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
          <th>Monedas</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="fila in filas" :key="fila.player_idx" :class="{ ganador: fila.posicion === 1 }">
          <td>{{ fila.posicion }}</td>
          <td>{{ fila.jugador.nombre }}</td>
          <td>{{ fila.jugador.puntos_maestria_final }}</td>
          <td>{{ fila.jugador.vitalidad }}</td>
          <td>{{ fila.jugador.datos_investigacion }}</td>
          <td>{{ fila.jugador.monedas }}</td>
        </tr>
      </tbody>
    </table>

    <div class="acciones-fin">
      <button class="primario" :disabled="creandoSala" @click="onCrearSalaNueva">Crear sala nueva</button>
      <button :disabled="creandoSala" @click="cerrarSesion">Ir al lobby</button>
    </div>
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

.acciones-fin {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.acciones-fin button {
  flex: 1;
  padding: 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: var(--color-panel);
  color: var(--color-texto);
}

.primario {
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}
</style>
