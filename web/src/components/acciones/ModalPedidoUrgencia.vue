<script setup lang="ts">
// Pedido de Urgencia (GDD v0.0.2) -- accion auxiliar gratuita (0 PA, sin
// limite por ronda, autolimitada por Datos de Investigacion disponibles).
// Antes vivia como el modo "urgencia" de la Accion C; ahora es su propia
// accion independiente (accion_auxiliar_pedido_urgencia en actions.py),
// desacoplada de Visitar el Mercado.
//
// Las DOS cantidades son fijas y vienen de pedidoUrgencia.ts: el jugador solo
// elige cual de los dos recursos quiere. El agua tuvo aqui un <input number>
// sin tope, y con el 1 Dato compraba toda el agua de la partida.
import { ref } from 'vue'
import { despacharAccion } from '../../store'
import ModalShell from '../ModalShell.vue'
import { fmtAgua, fmtHarina } from '../../data/unidades'
import { AGUA_PEDIDO_URGENCIA_TOKENS, HARINA_PEDIDO_URGENCIA_PCT } from '../../data/pedidoUrgencia'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const recurso = ref<'harina' | 'agua'>('harina')
const harina = ref<TipoHarina>('Blanca')
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('pedido_urgencia', {
      recurso: recurso.value,
      harina: recurso.value === 'harina' ? harina.value : null,
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
    <p class="info-linea">
      Ignora el mercado por completo. Elige un solo recurso; la cantidad es fija.
    </p>
    <div class="opciones-radio">
      <label
        ><input type="radio" value="harina" v-model="recurso" /> Harina
        <span class="dato">+{{ fmtHarina(HARINA_PEDIDO_URGENCIA_PCT) }}</span> media bolsa</label
      >
      <label
        ><input type="radio" value="agua" v-model="recurso" /> Agua
        <span class="dato">+{{ fmtAgua(AGUA_PEDIDO_URGENCIA_TOKENS) }}</span></label
      >
    </div>
    <label v-if="recurso === 'harina'" class="campo">
      Tipo
      <select v-model="harina">
        <option value="Blanca">Blanca</option>
        <option value="Centeno">Centeno</option>
        <option value="Integral">Integral</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
