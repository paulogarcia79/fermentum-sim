<script setup lang="ts">
import { ref } from 'vue'
import { despacharAccion } from '../../store'
import ModalShell from '../ModalShell.vue'
import type { TecnologiaID } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const TECNOLOGIAS: { id: TecnologiaID; nombre: string; costo: number; descripcion: string }[] = [
  { id: 'incubadora', nombre: 'Incubadora', costo: 3, descripcion: 'Ajuste ±5°C local (±1 en Fase III) por masa.' },
  { id: 'camara_b', nombre: 'Cámara B', costo: 4, descripcion: 'Desbloquea Estación 03 y mejora la Acción E.' },
  { id: 'modulo_analitico', nombre: 'Módulo Analítico', costo: 3, descripcion: '+1 Dato en centro exacto; habilita recetas Avanzadas.' },
]

const tecnologia = ref<TecnologiaID>('incubadora')
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
    <p class="info-linea">Solo se puede instalar una mejora por partida.</p>
    <div class="opciones-radio">
      <label v-for="t in TECNOLOGIAS" :key="t.id">
        <input type="radio" :value="t.id" v-model="tecnologia" />
        {{ t.nombre }} — {{ t.costo }} Datos
      </label>
    </div>
    <p class="info-linea">{{ TECNOLOGIAS.find((t) => t.id === tecnologia)?.descripcion }}</p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
