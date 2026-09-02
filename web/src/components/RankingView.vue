<script setup lang="ts">
import { computed, ref } from 'vue'
import { cerrarSesion, crearSalaNueva, store } from '../store'
import ConfetiPanes from './ConfetiPanes.vue'

const estado = computed(() => store.estado!)
const filas = computed(() =>
  estado.value.ranking.map((r) => ({ ...r, jugador: estado.value.players[r.player_idx] })),
)

const miIndice = computed(() => store.sesion!.playerIndex)

// Puede haber mas de un ganador: un empate en los cuatro criterios comparte la
// posicion 1 (engine.calcular_ranking_final, CORE_MECHANICS.md §Desempate).
const ganadores = computed(() => filas.value.filter((f) => f.posicion === 1))
const soyGanador = computed(() => ganadores.value.some((f) => f.player_idx === miIndice.value))
const nombresGanadores = computed(() => ganadores.value.map((f) => f.jugador.nombre))

// El confeti vive aqui y no en el store a proposito: es parte de la pantalla de
// resultados, no del instante en que la partida termina, asi que recargar la
// pestaña vuelve a mostrarlo. Los sonidos hacen lo contrario -- suenan una sola
// vez, en la transicion en vivo (ver `finDePartidaSonado` en store.ts).

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
    <ConfetiPanes v-if="soyGanador" />

    <h2>🏁 Resultados Finales</h2>

    <p class="veredicto" :class="{ mio: soyGanador }">
      <template v-if="soyGanador && ganadores.length > 1">
        ¡Victoria compartida! Empatas en lo más alto con
        {{ nombresGanadores.filter((n) => n !== store.estado!.players[miIndice].nombre).join(', ') }}.
      </template>
      <template v-else-if="soyGanador">¡Has ganado la partida!</template>
      <template v-else-if="ganadores.length > 1">
        Victoria compartida: {{ nombresGanadores.join(' y ') }}.
      </template>
      <template v-else>Gana {{ nombresGanadores[0] }}.</template>
    </p>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Investigador</th>
          <th>Puntos de Maestría</th>
          <th title="Recetas distintas horneadas con éxito">Tipos</th>
          <th>Vitalidad</th>
          <th>Datos</th>
          <th>Monedas</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="fila in filas" :key="fila.player_idx" :class="{ ganador: fila.posicion === 1 }">
          <td>{{ fila.posicion }}</td>
          <td>{{ fila.jugador.nombre }}</td>
          <td class="dato">{{ fila.jugador.puntos_maestria_final }}</td>
          <td class="dato">{{ fila.jugador.recetas_distintas_horneadas }}</td>
          <td>{{ fila.jugador.vitalidad }}</td>
          <td>{{ fila.jugador.datos_investigacion }}</td>
          <td>{{ fila.jugador.monedas }}</td>
        </tr>
      </tbody>
    </table>

    <section class="desglose">
      <h3 class="eyebrow">Desglose de puntuación</h3>
      <div class="bloques">
        <article v-for="fila in filas" :key="fila.player_idx" class="bloque-jugador">
          <h4>{{ fila.jugador.nombre }}</h4>
          <dl>
            <template v-for="(puntos, termino) in fila.jugador.desglose_maestria" :key="termino">
              <dt>{{ termino }}</dt>
              <dd class="dato" :class="{ negativo: puntos < 0 }">
                {{ puntos > 0 ? '+' : '' }}{{ puntos }}
              </dd>
            </template>
            <dt class="total">Total</dt>
            <dd class="total dato">{{ fila.jugador.puntos_maestria_final }}</dd>
          </dl>
        </article>
      </div>
    </section>

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
  padding: var(--e2);
  border-bottom: 1px solid var(--borde);
}

th {
  color: var(--tinta-tenue);
  font-size: var(--t-xs);
  text-transform: uppercase;
}

tr.ganador td {
  color: var(--cobre);
  font-weight: 600;
}

.veredicto {
  margin: 0 0 var(--e4);
  color: var(--tinta-tenue);
}

.veredicto.mio {
  color: var(--cobre);
  font-family: var(--fuente-titulo);
  font-size: var(--t-l);
}

.desglose {
  margin-top: var(--e5);
}

.desglose h3 {
  margin: 0 0 var(--e3);
}

.bloques {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--e3);
}

.bloque-jugador {
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
  padding: var(--e3);
}

.bloque-jugador h4 {
  margin: 0 0 var(--e2);
  font-size: var(--t-s);
}

.bloque-jugador dl {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--e1) var(--e2);
  margin: 0;
  font-size: var(--t-xs);
}

.bloque-jugador dt {
  color: var(--tinta-tenue);
}

.bloque-jugador dd {
  margin: 0;
  text-align: right;
}

.bloque-jugador dd.negativo {
  color: var(--riesgo);
}

.bloque-jugador .total {
  margin-top: var(--e1);
  padding-top: var(--e1);
  border-top: 1px solid var(--borde);
  color: var(--tinta);
  font-weight: 600;
}

.acciones-fin {
  display: flex;
  gap: var(--e2);
  margin-top: var(--e4);
}

.acciones-fin button {
  flex: 1;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: var(--zona);
  color: var(--tinta);
}

.primario {
  border: 1px solid var(--cobre);
  background: var(--cobre);
  color: var(--tinta-sobre-acento);
  font-weight: 600;
}
</style>
