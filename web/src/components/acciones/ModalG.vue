<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { PRECIO_RECETA } from '../../data/preciosReceta'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const recetasDisponibles = computed(
  () => store.estado!.market.recetas_visibles.map((r, i) => ({ r, i })).filter(({ r }) => r !== null),
)
const carpetaLlena = computed(() => yo.value.carpeta_proyectos.length >= 3)

const indiceMercado = ref(recetasDisponibles.value[0]?.i ?? 0)

// Precio de la receta seleccionada. Espejo del servidor: evita enviar una accion
// que ActionManager va a rechazar, sin ser la autoridad.
const precioSeleccionado = computed(() => {
  const receta = store.estado!.market.recetas_visibles[indiceMercado.value]
  return receta ? PRECIO_RECETA[receta.grado] : 0
})
const puedePagar = computed(() => yo.value.monedas >= precioSeleccionado.value)
const indiceDescartar = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('G', {
      indice_mercado: indiceMercado.value,
      indice_descartar: carpetaLlena.value ? indiceDescartar.value : null,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo investigar el protocolo.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Investigar Protocolo (1 PA + Monedas)" :error="error" @cerrar="emit('cerrar')">
    <label class="campo">
      Receta del mercado
      <select v-model.number="indiceMercado">
        <option v-for="{ r, i } in recetasDisponibles" :key="i" :value="i">
          {{ r!.nombre }} ({{ r!.grado }}) — {{ PRECIO_RECETA[r!.grado] }} Monedas
        </option>
      </select>
    </label>

    <p class="info-linea" :class="{ falta: !puedePagar }">
      Cuesta {{ precioSeleccionado }} Monedas · tienes {{ yo.monedas }}.
    </p>

    <label v-if="carpetaLlena" class="campo">
      Tu carpeta está llena (3/3) — receta a descartar
      <select v-model.number="indiceDescartar">
        <option v-for="(r, i) in yo.carpeta_proyectos" :key="i" :value="i">{{ r.nombre }}</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || recetasDisponibles.length === 0 || !puedePagar"
        @click="confirmar"
      >
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.falta {
  color: var(--riesgo);
}
</style>
