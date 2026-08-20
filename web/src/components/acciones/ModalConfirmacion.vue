<script setup lang="ts">
// Compartido por H (Re-cultivo Manual), I (Inóculo de Emergencia) y Horas
// Extras: las tres son acciones sin parámetros propios, solo una
// confirmación de costo -- a diferencia de las otras 8 acciones, que sí
// tienen forms bien distintos y viven en su propio componente.
import { ref } from 'vue'
import { despacharAccion } from '../../store'
import ModalShell from '../ModalShell.vue'

const props = defineProps<{ titulo: string; descripcion: string; accion: string }>()
const emit = defineEmits<{ cerrar: [] }>()

const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion(props.accion, {})
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar la acción.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell :titulo="titulo" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">{{ descripcion }}</p>
    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
