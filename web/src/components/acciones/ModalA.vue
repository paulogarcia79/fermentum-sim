<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { fmtHarina } from '../../data/unidades'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const tiposConHarina = computed(
  () => (Object.keys(yo.value.reserva_harina) as TipoHarina[]).filter((t) => yo.value.reserva_harina[t] >= 10),
)

const tipoHarina = ref<TipoHarina | ''>(tiposConHarina.value[0] ?? '')
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  if (!tipoHarina.value) {
    error.value = 'No tienes ningún tipo de harina con al menos 10%.'
    return
  }
  enviando.value = true
  try {
    await despacharAccion('A', { tipo_harina: tipoHarina.value })
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
    <p class="info-linea">
      +1 Vitalidad por 1 token de Harina (10%). Una vez por día — repone exactamente el -1 que el
      desgaste metabólico quita cada noche.
    </p>
    <p class="info-nota">
      La Acidez se ajusta en la acción «Descarte», no aquí.
    </p>

    <label class="campo">
      Tipo de harina
      <select v-model="tipoHarina">
        <option v-for="t in tiposConHarina" :key="t" :value="t">{{ t }} — {{ fmtHarina(yo.reserva_harina[t]) }}</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !tipoHarina" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>

<style scoped>
.info-nota {
  margin: calc(var(--e1) * -1) 0 var(--e3);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}
</style>
