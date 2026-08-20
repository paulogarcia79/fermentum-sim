<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const mercado = computed(() => store.estado!.market)
const slotsDisponibles = computed(
  () => mercado.value.suministros.map((s, i) => ({ s, i })).filter(({ s }) => s !== null),
)

const modo = ref<'normal' | 'urgencia'>('normal')
const indiceSlot = ref(slotsDisponibles.value[0]?.i ?? 0)
const recursoUrgencia = ref<'harina' | 'agua'>('harina')
const harinaUrgencia = ref<TipoHarina>('Blanca')
const aguaTokensUrgencia = ref(2)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    if (modo.value === 'normal') {
      await despacharAccion('C', { indice_slot: indiceSlot.value })
    } else {
      await despacharAccion('C', {
        urgencia: true,
        harina_urgencia: recursoUrgencia.value === 'harina' ? harinaUrgencia.value : null,
        agua_tokens_urgencia: recursoUrgencia.value === 'agua' ? aguaTokensUrgencia.value : 0,
      })
    }
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudieron adquirir los insumos.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Adquirir Insumos (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <div class="opciones-radio">
      <label><input type="radio" value="normal" v-model="modo" :disabled="slotsDisponibles.length === 0" /> Del mercado</label>
      <label><input type="radio" value="urgencia" v-model="modo" /> Pedido de Urgencia (+1 Dato)</label>
    </div>

    <label v-if="modo === 'normal'" class="campo">
      Lote
      <select v-model.number="indiceSlot">
        <option v-for="{ s, i } in slotsDisponibles" :key="i" :value="i">
          Lote {{ i + 1 }} — B:{{ s!.recursos.Blanca }}% C:{{ s!.recursos.Centeno }}% I:{{ s!.recursos.Integral }}% A:{{ s!.recursos.agua }}%
        </option>
      </select>
    </label>

    <template v-else>
      <div class="opciones-radio">
        <label><input type="radio" value="harina" v-model="recursoUrgencia" /> Harina (+100%)</label>
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
      </label>
    </template>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>
