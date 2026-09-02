<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { fmtAgua, fmtHarina, fmtTokensHarina } from '../../data/unidades'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const carpetaIndex = ref(0)
const modificadorIncubadora = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

const recetaSeleccionada = computed(() => yo.value.carpeta_proyectos[carpetaIndex.value])

// La cuenta la hace el servidor (`disponibilidad.insumos_receta`) y viaja en la
// carta. Antes se calculaba aqui, y se calculaba MAL: leia `receta.tokens_agua`
// tal cual, sin el descuento de un token de Alta Humedad que la Accion B si
// aplica, asi que en un dia humedo esta lista tachaba con una cruz un agua que
// el servidor aceptaba. Una regla de CLIMATE_LOGIC.md no se reimplementa en
// TypeScript; aqui solo se dibuja lo que llega.
const insumos = computed(() => recetaSeleccionada.value?.insumos)

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
        <option v-for="(r, i) in yo.carpeta_proyectos" :key="i" :value="i">
          {{ r.insumos?.completos ? '✓' : '✗' }} {{ r.nombre }} ({{ r.grado }})
        </option>
      </select>
    </label>

    <template v-if="recetaSeleccionada && insumos">
      <div class="eyebrow">Insumos requeridos</div>
      <ul class="requisitos">
        <li v-for="req in insumos.harinas" :key="req.tipo" :class="{ falta: req.falta }">
          <span class="marca">{{ req.falta ? '✗' : '✓' }}</span>
          {{ fmtTokensHarina(req.necesita) }} de Harina {{ req.tipo }}
          <span class="unidad-secundaria">({{ req.necesita }}%)</span>
          <span class="tienes">tienes {{ fmtHarina(req.tiene) }}</span>
        </li>
        <li :class="{ falta: insumos.agua.falta }">
          <span class="marca">{{ insumos.agua.falta ? '✗' : '✓' }}</span>
          {{ insumos.agua.necesita }} tokens de Agua
          <span class="unidad-secundaria">({{ recetaSeleccionada.hidratacion_pct }}% de hidratación)</span>
          <span class="tienes">tienes {{ fmtAgua(yo.reserva_agua) }}</span>
        </li>
        <li v-if="insumos.agua.necesita < recetaSeleccionada.tokens_agua" class="descuento">
          Alta Humedad: 1 token de Agua menos que los
          {{ recetaSeleccionada.tokens_agua }} impresos en la carta.
        </li>
      </ul>
      <p class="info-linea">
        Bono de sabor si tu Acidez ∈ {{ recetaSeleccionada.acidez_diana.join(', ') }} (actual: {{ yo.acidez }}).
      </p>
    </template>

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

<style scoped>
.requisitos {
  list-style: none;
  margin: 0 0 var(--e2);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  font-size: var(--t-s);
}

.requisitos li {
  display: flex;
  align-items: baseline;
  gap: var(--e1);
}

.marca {
  color: var(--vital);
  font-weight: 700;
}

.falta .marca {
  color: var(--riesgo);
}

.falta {
  color: var(--riesgo);
}

.descuento {
  color: var(--verdin);
  font-size: var(--t-micro);
}

.tienes {
  margin-left: auto;
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
}
</style>
