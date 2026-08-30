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

// Una fila por harina impresa: con una Intermedia (media bolsa de dos tipos)
// saber que "falta harina" no dice cual comprar, asi que cada tipo lleva su
// propio tienes/necesitas. La autoridad sigue siendo ActionManager -- esto solo
// evita mandar una accion que se sabe que va a fallar.
const requisitosHarina = computed(() =>
  (recetaSeleccionada.value?.harinas ?? []).map(([tipo, pct]) => ({
    tipo,
    pct,
    disponible: yo.value.reserva_harina[tipo] ?? 0,
    suficiente: (yo.value.reserva_harina[tipo] ?? 0) >= pct,
  })),
)

const aguaSuficiente = computed(
  () => !recetaSeleccionada.value || yo.value.reserva_agua >= recetaSeleccionada.value.tokens_agua,
)

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

    <template v-if="recetaSeleccionada">
      <div class="eyebrow">Insumos requeridos</div>
      <ul class="requisitos">
        <li v-for="req in requisitosHarina" :key="req.tipo" :class="{ falta: !req.suficiente }">
          <span class="marca">{{ req.suficiente ? '✓' : '✗' }}</span>
          {{ fmtTokensHarina(req.pct) }} de Harina {{ req.tipo }}
          <span class="unidad-secundaria">({{ req.pct }}%)</span>
          <span class="tienes">tienes {{ fmtHarina(req.disponible) }}</span>
        </li>
        <li :class="{ falta: !aguaSuficiente }">
          <span class="marca">{{ aguaSuficiente ? '✓' : '✗' }}</span>
          {{ recetaSeleccionada.tokens_agua }} tokens de Agua
          <span class="unidad-secundaria">({{ recetaSeleccionada.hidratacion_pct }}% de hidratación)</span>
          <span class="tienes">tienes {{ fmtAgua(yo.reserva_agua) }}</span>
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

.tienes {
  margin-left: auto;
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
}
</style>
