<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import type { TecnologiaID } from '../../types'
import { TECNOLOGIAS } from '../../data/tecnologias'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])

// Preselección: la primera mejora pendiente que además se pueda PAGAR, para que
// abrir el modal no aterrice de entrada en un Confirmar apagado. Si no hay
// ninguna asequible se cae a la primera pendiente (el modal se abre igualmente
// para poder leer las descripciones) y, en último término, a la Incubadora.
const pendientes = TECNOLOGIAS.filter((t) => !yo.value.tecnologias[t.id])
const tecnologia = ref<TecnologiaID>(
  pendientes.find((t) => t.costo <= yo.value.datos_investigacion)?.id ??
    pendientes[0]?.id ??
    'incubadora',
)
const enviando = ref(false)
const error = ref<string | null>(null)

const costoSeleccionado = computed(
  () => TECNOLOGIAS.find((t) => t.id === tecnologia.value)?.costo ?? 0,
)
const puedePagar = computed(() => yo.value.datos_investigacion >= costoSeleccionado.value)

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
    <!-- Las mejoras pendientes que no puedes pagar siguen siendo seleccionables a
         propósito: así se puede leer su descripción y decidir para qué ahorrar.
         Lo que se bloquea es Confirmar. -->
    <div class="opciones-radio">
      <label v-for="t in TECNOLOGIAS" :key="t.id">
        <input type="radio" :value="t.id" v-model="tecnologia" :disabled="yo.tecnologias[t.id]" />
        {{ t.nombre }} — {{ t.costo }} Datos
        <span v-if="yo.tecnologias[t.id]" class="ya-instalada">(ya instalada)</span>
      </label>
    </div>
    <p class="info-linea" :class="{ falta: !puedePagar }">
      Cuesta {{ costoSeleccionado }} Datos · tienes {{ yo.datos_investigacion }}.
    </p>
    <p class="info-linea">{{ TECNOLOGIAS.find((t) => t.id === tecnologia)?.descripcion }}</p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || yo.tecnologias[tecnologia] || !puedePagar"
        @click="confirmar"
      >
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.ya-instalada {
  color: var(--tinta-tenue);
  font-size: var(--t-xs);
}

.falta {
  color: var(--riesgo);
}
</style>
