<script setup lang="ts">
// Acción «Descarte»: el único control voluntario de la Acidez, y va en los dos
// sentidos. Es 0 PA pero ocupa su espacio de acción (una vez por día), igual
// que la Acción E -- las Monedas son renovables, así que el tope diario es lo
// que impide comprar visitas hasta vaciar la bolsa.
//
// Los dos sentidos cobran recursos DISTINTOS (subir = Agua, bajar = Monedas),
// así que el modal lee la escalera correspondiente de OPERACIONES_ACIDEZ en
// vez de tener dos ramas paralelas -- el mismo motivo por el que esa tabla
// existe del lado del servidor.
//
// La pista muestra el corchete sólido en la acidez actual y el discontinuo en
// la resultante, más la banda de equilibrio de la Madurez: perseguir una diana
// extrema tiene un precio en puntos finales, y el jugador debe poder verlo
// antes de confirmar, no descubrirlo en el recuento.
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import PistaMedida, { type BandaPista } from '../PistaMedida.vue'
import { fmtAgua } from '../../data/unidades'
import {
  ACIDEZ_EQUILIBRIO_CENTRO,
  NIVELES_ACIDEZ,
  OPERACIONES_ACIDEZ,
  puntosEquilibrio,
  type OperacionAcidez,
} from '../../data/preciosAcidez'

const emit = defineEmits<{ cerrar: [] }>()

const ACIDEZ_MAX = 6

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])

const operacion = ref<OperacionAcidez>('bajar')
const niveles = ref(1)
const enviando = ref(false)
const error = ref<string | null>(null)

const config = computed(() => OPERACIONES_ACIDEZ[operacion.value])
const precio = computed(() => config.value.escalera[niveles.value] ?? 0)
const saldo = computed(() =>
  config.value.recurso === 'agua' ? yo.value.reserva_agua : yo.value.monedas,
)
const puedePagar = computed(() => saldo.value >= precio.value)

/** El servidor recorta en [0, 6] (Player.ajustar_acidez), así que el modal
 *  proyecta lo mismo: prometer un 7 y entregar un 6 sería mentir sobre el
 *  resultado de una compra que sí se cobra entera. */
const resultante = computed(() =>
  Math.max(0, Math.min(ACIDEZ_MAX, yo.value.acidez + config.value.signo * niveles.value)),
)
const seDesperdicia = computed(
  () => Math.abs(resultante.value - yo.value.acidez) < niveles.value,
)

const equilibrioAhora = computed(() => puntosEquilibrio(yo.value.acidez))
const equilibrioDespues = computed(() => puntosEquilibrio(resultante.value))
const deltaEquilibrio = computed(() => equilibrioDespues.value - equilibrioAhora.value)

/** La banda del pico de Madurez. Se dibuja siempre, no sólo cuando conviene:
 *  es la regla que explica por qué las dianas extremas pagan más. */
const bandas = computed<BandaPista[]>(() => [
  { desde: -1, hasta: ACIDEZ_EQUILIBRIO_CENTRO - 1, tono: 'neutra' },
  {
    desde: ACIDEZ_EQUILIBRIO_CENTRO - 1,
    hasta: ACIDEZ_EQUILIBRIO_CENTRO,
    tono: 'optima',
    etiqueta: 'Pico Madurez',
    rango: String(ACIDEZ_EQUILIBRIO_CENTRO),
  },
  { desde: ACIDEZ_EQUILIBRIO_CENTRO, hasta: ACIDEZ_MAX, tono: 'neutra' },
])

function elegir(op: OperacionAcidez) {
  operacion.value = op
  niveles.value = 1
}

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('descarte', { operacion: operacion.value, niveles: niveles.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo ajustar la Acidez.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Descarte — ajustar Acidez (0 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Ocupa su espacio una vez por día y no termina tu turno. Tienes
      <span class="dato">{{ yo.monedas }}</span> Monedas y
      <span class="dato">{{ fmtAgua(yo.reserva_agua) }}</span> de agua.
    </p>

    <div class="opciones-radio">
      <label>
        <input type="radio" value="subir" :checked="operacion === 'subir'" @change="elegir('subir')" />
        Subir Acidez — se paga en Agua
      </label>
      <label>
        <input type="radio" value="bajar" :checked="operacion === 'bajar'" @change="elegir('bajar')" />
        Bajar Acidez — se paga en Monedas
      </label>
    </div>

    <p class="escalera">
      <span v-for="n in NIVELES_ACIDEZ" :key="n">
        <span class="dato">{{ operacion === 'subir' ? '+' : '−' }}{{ n }}</span> =
        <span class="dato">{{ config.escalera[n] }}</span>
        {{ config.recurso === 'agua' ? 'agua' : 'Monedas' }}
      </span>
    </p>

    <div class="stepper-fila">
      <span class="eyebrow">Niveles</span>
      <div class="stepper">
        <button type="button" :disabled="niveles <= NIVELES_ACIDEZ[0]" @click="niveles--">−</button>
        <span class="dato">{{ niveles }}</span>
        <button
          type="button"
          :disabled="niveles >= NIVELES_ACIDEZ[NIVELES_ACIDEZ.length - 1]"
          @click="niveles++"
        >
          +
        </button>
      </div>
    </div>

    <PistaMedida
      :valor="yo.acidez"
      :min="0"
      :max="ACIDEZ_MAX"
      :previsto="resultante"
      :bandas="bandas"
      etiqueta="Acidez"
      :lectura="`${yo.acidez} → ${resultante}`"
      tono="cobre"
      :tono-previsto="deltaEquilibrio < 0 ? 'riesgo' : 'vital'"
    />

    <p class="resumen">
      Coste <span class="dato">{{ precio }}</span>
      {{ config.recurso === 'agua' ? 'tokens de agua' : 'Monedas' }} ·
      Madurez <span class="dato">{{ equilibrioAhora }}</span> →
      <span class="dato">{{ equilibrioDespues }}</span>
      <span v-if="deltaEquilibrio !== 0" :class="deltaEquilibrio > 0 ? 'bien' : 'mal'">
        ({{ deltaEquilibrio > 0 ? '+' : '' }}{{ deltaEquilibrio }} pts finales)
      </span>
    </p>

    <p v-if="seDesperdicia" class="aviso">
      La Acidez se detiene en {{ resultante }} (la pista va de 0 a {{ ACIDEZ_MAX }}), pero el
      escalón se cobra entero. Baja los niveles para no pagar de más.
    </p>
    <p v-if="!puedePagar" class="aviso">
      No te alcanza: necesitas {{ precio }} y tienes {{ saldo }}.
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !puedePagar" @click="confirmar">
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.escalera {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2) var(--e4);
  margin: 0 0 var(--e3);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.stepper-fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--e3);
}

.stepper {
  display: flex;
  align-items: center;
  gap: var(--e2);
}

.stepper button {
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  line-height: 1;
}

.resumen {
  margin: var(--e3) 0 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.resumen .bien {
  color: var(--vital);
}

.resumen .mal {
  color: var(--riesgo);
}

.aviso {
  margin: var(--e2) 0 0;
  font-size: var(--t-micro);
  color: var(--riesgo);
}
</style>
