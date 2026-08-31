<script setup lang="ts">
// Pedido de Urgencia (GDD v0.0.2) -- accion auxiliar gratuita (0 PA, sin
// limite por ronda, autolimitada por Datos de Investigacion disponibles).
// Antes vivia como el modo "urgencia" de la Accion C; ahora es su propia
// accion independiente (accion_auxiliar_pedido_urgencia en actions.py),
// desacoplada de Visitar el Mercado.
import { ref } from 'vue'
import { despacharAccion } from '../../store'
import ModalShell from '../ModalShell.vue'
import { fmtTokensHarina, pctAgua } from '../../data/unidades'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const recursoUrgencia = ref<'harina' | 'agua'>('harina')
const harinaUrgencia = ref<TipoHarina>('Blanca')
const aguaTokensUrgencia = ref(2)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('pedido_urgencia', {
      harina_urgencia: recursoUrgencia.value === 'harina' ? harinaUrgencia.value : null,
      agua_tokens_urgencia: recursoUrgencia.value === 'agua' ? aguaTokensUrgencia.value : 0,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar el Pedido de Urgencia.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Pedido de Urgencia (0 PA, 1 Dato)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">Ignora el mercado por completo. Elige un solo tipo de recurso.</p>
    <div class="opciones-radio">
      <label
        ><input type="radio" value="harina" v-model="recursoUrgencia" /> Harina (+{{ fmtTokensHarina(50) }} ·
        50%, media bolsa)</label
      >
      <label><input type="radio" value="agua" v-model="recursoUrgencia" /> Agua</label>
    </div>
    <label v-if="recursoUrgencia === 'harina'" class="campo">
      Tipo
      <select v-model="harinaUrgencia">
        <option value="Blanca">Blanca</option>
        <option value="Centeno">Centeno</option>
        <option value="Integral">Integral</option>
      </select>
    </label>
    <label v-else class="campo">
      Tokens de agua
      <input type="number" v-model.number="aguaTokensUrgencia" min="1" step="1" />
      <span class="unidad-secundaria">= {{ pctAgua(aguaTokensUrgencia || 0) }}% de hidratación</span>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
