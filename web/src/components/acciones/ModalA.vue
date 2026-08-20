<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const tiposConHarina = computed(
  () => (Object.keys(yo.value.reserva_harina) as TipoHarina[]).filter((t) => yo.value.reserva_harina[t] >= 10),
)

const usarHarina = ref(tiposConHarina.value.length > 0)
const tipoHarina = ref<TipoHarina | ''>(tiposConHarina.value[0] ?? '')
const usarAgua = ref(yo.value.reserva_agua >= 2)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  if (!usarHarina.value && !usarAgua.value) {
    error.value = 'Elige al menos harina o agua.'
    return
  }
  enviando.value = true
  try {
    await despacharAccion('A', {
      usar_harina: usarHarina.value,
      tipo_harina: usarHarina.value ? tipoHarina.value : null,
      usar_agua: usarAgua.value,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo alimentar el cultivo.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Alimentar Cultivo (0 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">+1 Vitalidad por 10% de harina, +1 Acidez por 2 tokens de agua. Una vez por día.</p>

    <label class="campo-checkbox">
      <input type="checkbox" v-model="usarHarina" :disabled="tiposConHarina.length === 0" />
      Usar harina (+1 Vitalidad)
    </label>
    <label v-if="usarHarina" class="campo">
      Tipo de harina
      <select v-model="tipoHarina">
        <option v-for="t in tiposConHarina" :key="t" :value="t">{{ t }} ({{ yo.reserva_harina[t] }}%)</option>
      </select>
    </label>

    <label class="campo-checkbox">
      <input type="checkbox" v-model="usarAgua" :disabled="yo.reserva_agua < 2" />
      Usar agua (+1 Acidez) — {{ yo.reserva_agua }} tokens disponibles
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
