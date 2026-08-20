<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const estacionesActivas = computed(
  () => yo.value.estaciones_fermentacion.map((s, i) => ({ s, i })).filter(({ s }) => s !== null),
)

const opcion = ref<'avanzar' | 'recuperar_vitalidad' | 'doble_masa'>('avanzar')
const slotIndex = ref(estacionesActivas.value[0]?.i ?? 0)
const slotIndex2 = ref(estacionesActivas.value[1]?.i ?? estacionesActivas.value[0]?.i ?? 0)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('E', {
      slot_index: slotIndex.value,
      opcion_camara_b: opcion.value,
      slot_index_2: opcion.value === 'doble_masa' ? slotIndex2.value : null,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo aplicar el pliegue.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Técnica — Pliegues (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <div v-if="yo.tecnologias.camara_b" class="opciones-radio">
      <label><input type="radio" value="avanzar" v-model="opcion" /> Avanzar +1 casilla</label>
      <label><input type="radio" value="recuperar_vitalidad" v-model="opcion" /> Recuperar +1 Vitalidad</label>
      <label><input type="radio" value="doble_masa" v-model="opcion" /> Avanzar +1 en dos masas</label>
    </div>
    <p v-else class="info-linea">Avanza +1 casilla el marcador de inóculo de la masa elegida.</p>

    <label v-if="opcion !== 'recuperar_vitalidad'" class="campo">
      Masa
      <select v-model.number="slotIndex">
        <option v-for="{ s, i } in estacionesActivas" :key="i" :value="i">Est-{{ i + 1 }}: {{ s!.recipe.nombre }} (pos {{ s!.posicion_track }})</option>
      </select>
    </label>
    <label v-if="opcion === 'doble_masa'" class="campo">
      Segunda masa
      <select v-model.number="slotIndex2">
        <option v-for="{ s, i } in estacionesActivas" :key="i" :value="i">Est-{{ i + 1 }}: {{ s!.recipe.nombre }} (pos {{ s!.posicion_track }})</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || estacionesActivas.length === 0" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
