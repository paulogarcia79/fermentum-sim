<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { PRECIO_RECETA, PRECIO_RECETA_MAZO } from '../../data/preciosReceta'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const mercado = computed(() => store.estado!.market)
const recetasDisponibles = computed(
  () => mercado.value.recetas_visibles.map((r, i) => ({ r, i })).filter(({ r }) => r !== null),
)
const carpetaLlena = computed(() => yo.value.carpeta_proyectos.length >= 3)

const indiceMercado = ref(recetasDisponibles.value[0]?.i ?? 0)

// Precio de la receta seleccionada. Espejo del servidor: evita enviar una accion
// que ActionManager va a rechazar, sin ser la autoridad.
const precioSeleccionado = computed(() => {
  const receta = mercado.value.recetas_visibles[indiceMercado.value]
  return receta ? PRECIO_RECETA[receta.grado] : 0
})
const puedePagar = computed(() => yo.value.monedas >= precioSeleccionado.value)

// El mazo sigue teniendo carta mientras quede descarte: robar lo rebaraja antes.
const cartasEnMazo = computed(() => mercado.value.mazo_recetas_restantes)
const cartasEnDescarte = computed(() => mercado.value.descarte_recetas.length)
const mazoDisponible = computed(() => cartasEnMazo.value > 0 || cartasEnDescarte.value > 0)
const puedePagarMazo = computed(() => yo.value.monedas >= PRECIO_RECETA_MAZO)

// Valor INICIAL, no computed: una vez abierto el modal manda lo que elija el
// jugador. Se arranca en el mazo solo cuando la mesa no ofrece nada pagable y la
// ciega si, que es exactamente el hueco que esta accion vino a tapar.
const hayVisiblePagable = recetasDisponibles.value.some(
  ({ r }) => yo.value.monedas >= PRECIO_RECETA[r!.grado],
)
const origen = ref<'mercado' | 'mazo'>(
  !hayVisiblePagable && mazoDisponible.value && puedePagarMazo.value ? 'mazo' : 'mercado',
)

const puedeConfirmar = computed(() =>
  origen.value === 'mercado'
    ? recetasDisponibles.value.length > 0 && puedePagar.value
    : mazoDisponible.value && puedePagarMazo.value,
)

const indiceDescartar = ref(0)
const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    // Solo viajan los parametros del origen elegido: el servidor rechaza las
    // combinaciones cruzadas, asi que mandar el indice "por si acaso" seria un error.
    await despacharAccion('G', {
      origen: origen.value,
      ...(origen.value === 'mercado' ? { indice_mercado: indiceMercado.value } : {}),
      indice_descartar: carpetaLlena.value ? indiceDescartar.value : null,
    })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo investigar el protocolo.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Investigar Protocolo (1 PA + Monedas)" :error="error" @cerrar="emit('cerrar')">
    <div class="opciones-radio">
      <label
        ><input type="radio" value="mercado" v-model="origen" /> Del mercado
        <span class="dato">1–3 Monedas</span></label
      >
      <label :class="{ inerte: !mazoDisponible }"
        ><input type="radio" value="mazo" v-model="origen" :disabled="!mazoDisponible" /> Del mazo,
        a ciegas <span class="dato">{{ PRECIO_RECETA_MAZO }} Monedas</span></label
      >
    </div>

    <template v-if="origen === 'mercado'">
      <label class="campo">
        Receta del mercado
        <select v-model.number="indiceMercado">
          <option v-for="{ r, i } in recetasDisponibles" :key="i" :value="i">
            {{ r!.nombre }} ({{ r!.grado }}) — {{ PRECIO_RECETA[r!.grado] }} Monedas
          </option>
        </select>
      </label>

      <p class="info-linea" :class="{ falta: !puedePagar }">
        Cuesta {{ precioSeleccionado }} Monedas · tienes {{ yo.monedas }}.
      </p>
    </template>

    <template v-else>
      <p class="a-ciegas">
        Te llevas la carta de arriba del mazo, del grado que salga. Es la que se revelaría
        mañana en el Protocolo de Refresco; las cartas expuestas no se mueven.
      </p>
      <p class="info-linea">
        Quedan <span class="dato">{{ cartasEnMazo }}</span> cartas en el mazo<template
          v-if="cartasEnMazo === 0 && cartasEnDescarte > 0"
        >
          — se barajará el descarte (<span class="dato">{{ cartasEnDescarte }}</span
          >)</template
        >.
      </p>
      <p class="info-linea" :class="{ falta: !puedePagarMazo }">
        Cuesta {{ PRECIO_RECETA_MAZO }} Monedas · tienes {{ yo.monedas }}.
      </p>
    </template>

    <label v-if="carpetaLlena" class="campo">
      Tu carpeta está llena (3/3) — receta a descartar
      <select v-model.number="indiceDescartar">
        <option v-for="(r, i) in yo.carpeta_proyectos" :key="i" :value="i">{{ r.nombre }}</option>
      </select>
    </label>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !puedeConfirmar" @click="confirmar">
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.falta {
  color: var(--riesgo);
}

.inerte {
  color: var(--tinta-tenue);
}

.a-ciegas {
  margin: 0 0 var(--e2);
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}
</style>
