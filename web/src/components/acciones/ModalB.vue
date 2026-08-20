<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const carpetaIndex = ref(0)
const modificadorIncubadora = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

const recetaSeleccionada = computed(() => yo.value.carpeta_proyectos[carpetaIndex.value])

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('B', {
      carpeta_index: carpetaIndex.value,
      receta_id: recetaSeleccionada.value?.id,
      modificador_incubadora: yo.value.tecnologias.incubadora ? modificadorIncubadora.value : 0,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo iniciar la receta.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Iniciar Receta (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <label class="campo">
      Receta de la Carpeta de Proyectos
      <select v-model.number="carpetaIndex">
        <option v-for="(r, i) in yo.carpeta_proyectos" :key="i" :value="i">{{ r.nombre }} ({{ r.grado }})</option>
      </select>
    </label>

    <p v-if="recetaSeleccionada" class="info-linea">
      Requiere: 1 Harina {{ recetaSeleccionada.harina_base }} (100%) + {{ recetaSeleccionada.tokens_agua }} tokens de
      agua. Bono de sabor si tu Acidez ∈ {{ recetaSeleccionada.acidez_diana.join(', ') }} (actual: {{ yo.acidez }}).
    </p>

    <label v-if="yo.tecnologias.incubadora" class="campo">
      Modificador Incubadora
      <select v-model.number="modificadorIncubadora">
        <option :value="-1">-1</option>
        <option :value="0">0</option>
        <option :value="1">+1</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !recetaSeleccionada" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
