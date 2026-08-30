<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import { DATOS_SIMPOSIO, RENTA_POR_GRADO } from '../../data/datosSimposio'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const archivo = computed(() => yo.value.archivo_horneado_exitoso)

const indice = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

/** Lo que cuesta cada fila, calculado por registro para que el jugador compare
 * antes de elegir. Los puntos y la renta salen del registro; el escalón de
 * Variedad hay que derivarlo porque sólo se pierde si era la ÚLTIMA copia de
 * esa receta en el archivo. */
const opciones = computed(() =>
  archivo.value.map((record, i) => {
    const grado = record.recipe.grado
    const otrasCopias = archivo.value.some((r, j) => j !== i && r.recipe.id === record.recipe.id)
    return {
      i,
      nombre: record.recipe.nombre,
      grado,
      datos: DATOS_SIMPOSIO[grado],
      puntos: record.puntos_totales,
      renta: RENTA_POR_GRADO[grado],
      pierdeVariedad: !otrasCopias,
    }
  }),
)

const elegida = computed(() => opciones.value.find((o) => o.i === indice.value) ?? null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('simposio', { indice: indice.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar el Simposio Técnico.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Simposio Técnico (1 PA + un horneado)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Publica uno de tus horneados exitosos a cambio de Datos de Investigación.
      El registro <strong>sale del archivo para siempre</strong>: pierdes sus Puntos
      de Maestría, su renta diaria y su paso hacia el 5/5 que termina la partida.
    </p>

    <p v-if="archivo.length === 0" class="aviso-vacio">
      Todavía no tienes ningún horneado exitoso que sacrificar.
    </p>

    <template v-else>
      <label class="campo">
        Horneado a sacrificar
        <select v-model.number="indice">
          <option v-for="o in opciones" :key="o.i" :value="o.i">
            {{ o.nombre }} ({{ o.grado }}) → +{{ o.datos }} Datos
          </option>
        </select>
      </label>

      <div v-if="elegida" class="balance">
        <div class="ganas">
          <span class="eyebrow">Ganas</span>
          <p class="dato">+{{ elegida.datos }} Datos de Investigación</p>
        </div>
        <div class="pierdes">
          <span class="eyebrow">Pierdes</span>
          <ul>
            <li class="dato">−{{ elegida.puntos }} Puntos de Maestría</li>
            <li class="dato">−{{ elegida.renta }} Monedas cada noche</li>
            <li>Un paso del Archivo ({{ archivo.length }}/5 → {{ archivo.length - 1 }}/5)</li>
            <li v-if="elegida.pierdeVariedad" class="grave">
              Un escalón de Variedad de Recetas ({{ yo.recetas_distintas_horneadas }} →
              {{ yo.recetas_distintas_horneadas - 1 }} tipos)
            </li>
          </ul>
        </div>
      </div>
    </template>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || archivo.length === 0"
        @click="confirmar"
      >
        Sacrificar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.aviso-vacio {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  padding: var(--e3) 0;
}

.balance {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--e3);
  margin-top: var(--e3);
  padding: var(--e3);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--zona);
}

.ganas p {
  color: var(--vital);
  margin: var(--e1) 0 0;
}

.pierdes ul {
  list-style: none;
  margin: var(--e1) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
}

.pierdes li {
  color: var(--riesgo);
  font-size: var(--t-s);
}

.pierdes li.grave {
  font-weight: 600;
}

@media (max-width: 720px) {
  .balance {
    grid-template-columns: 1fr;
  }
}
</style>
