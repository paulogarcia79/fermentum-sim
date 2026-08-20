<script setup lang="ts">
// Vista previa de puntos: replica solo la lectura de zona (no una decision
// de reglas) usando las mismas constantes que ya viajan en el snapshot --
// PUNTOS_ZONA_BAJA_DIVISOR=3 es el unico numero "mágico" duplicado de
// engine.py, puramente para mostrar una estimacion antes de confirmar
// (ver engine.py:_calcular_puntos_zona). El servidor sigue siendo quien
// calcula el resultado real al recibir la accion.
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'

const PUNTOS_ZONA_BAJA_DIVISOR = 3

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const estacionesActivas = computed(
  () => yo.value.estaciones_fermentacion.map((s, i) => ({ s, i })).filter(({ s }) => s !== null),
)

const slotIndex = ref(estacionesActivas.value[0]?.i ?? 0)
const enviando = ref(false)
const error = ref<string | null>(null)

const slotSeleccionado = computed(() => yo.value.estaciones_fermentacion[slotIndex.value])

const previa = computed(() => {
  const slot = slotSeleccionado.value
  if (!slot) return null
  const r = slot.recipe
  const pos = slot.posicion_track
  if (pos >= r.zona_sobrefermentada[0]) return { zona: 'Sobrefermentada', puntos: r.penalizacion_colapso }
  if (pos >= r.zona_optima[0] && pos <= r.zona_optima[1]) {
    const bono = slot.bono_sabor ? r.bono_sabor_pts : 0
    return { zona: 'Óptima', puntos: r.puntos_optimos + bono }
  }
  const bono = slot.bono_sabor ? r.bono_sabor_pts : 0
  return { zona: 'Baja', puntos: Math.max(1, Math.floor(r.puntos_optimos / PUNTOS_ZONA_BAJA_DIVISOR)) + bono }
})

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('F', { slot_index: slotIndex.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo hornear.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Hornear (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <label class="campo">
      Masa
      <select v-model.number="slotIndex">
        <option v-for="{ s, i } in estacionesActivas" :key="i" :value="i">Est-{{ i + 1 }}: {{ s!.recipe.nombre }} (pos {{ s!.posicion_track }})</option>
      </select>
    </label>

    <p v-if="previa" class="info-linea">
      Zona {{ previa.zona }} — resultado estimado: <strong>{{ previa.puntos }} pts</strong>
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || estacionesActivas.length === 0" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
