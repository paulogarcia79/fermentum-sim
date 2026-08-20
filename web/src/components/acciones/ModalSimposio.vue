<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const estacionesActivas = computed(
  () => yo.value.estaciones_fermentacion.map((s, i) => ({ s, i })).filter(({ s }) => s !== null),
)

const origen = ref<'carpeta' | 'estacion'>(yo.value.carpeta_proyectos.length > 0 ? 'carpeta' : 'estacion')
const indice = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

watch(origen, () => {
  indice.value = origen.value === 'estacion' ? (estacionesActivas.value[0]?.i ?? 0) : 0
})

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('simposio', { origen: origen.value, indice: indice.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar el Simposio Técnico.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Simposio Técnico (1 PA → +1 Dato)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">Descarta una receta de la Carpeta o una masa activa a cambio de +1 Dato de Investigación.</p>

    <div class="opciones-radio">
      <label><input type="radio" value="carpeta" v-model="origen" :disabled="yo.carpeta_proyectos.length === 0" /> De la Carpeta de Proyectos</label>
      <label><input type="radio" value="estacion" v-model="origen" :disabled="estacionesActivas.length === 0" /> De una estación (pierde la masa)</label>
    </div>

    <label v-if="origen === 'carpeta'" class="campo">
      Receta
      <select v-model.number="indice">
        <option v-for="(r, i) in yo.carpeta_proyectos" :key="i" :value="i">{{ r.nombre }}</option>
      </select>
    </label>
    <label v-else class="campo">
      Estación
      <select v-model.number="indice">
        <option v-for="{ s, i } in estacionesActivas" :key="i" :value="i">Est-{{ i + 1 }}: {{ s!.recipe.nombre }}</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
