<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import type { TecnologiaID } from '../../types'
import { TECNOLOGIAS } from '../../data/tecnologias'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])

const tecnologia = ref<TecnologiaID>(
  TECNOLOGIAS.find((t) => !yo.value.tecnologias[t.id])?.id ?? 'incubadora',
)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('D', { tecnologia: tecnologia.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo instalar la mejora.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Implementar Mejora (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">Cada mejora solo puede instalarse una vez, pero puedes instalar varias distintas a lo largo de la partida.</p>
    <div class="opciones-radio">
      <label v-for="t in TECNOLOGIAS" :key="t.id">
        <input type="radio" :value="t.id" v-model="tecnologia" :disabled="yo.tecnologias[t.id]" />
        {{ t.nombre }} — {{ t.costo }} Datos
        <span v-if="yo.tecnologias[t.id]" class="ya-instalada">(ya instalada)</span>
      </label>
    </div>
    <p class="info-linea">{{ TECNOLOGIAS.find((t) => t.id === tecnologia)?.descripcion }}</p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || yo.tecnologias[tecnologia]" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>

<style scoped>
.ya-instalada {
  color: var(--color-texto-tenue);
  font-size: 0.78rem;
}
</style>
