<script setup lang="ts">
// Acción E (Pliegues): ya no cuesta PA, se paga en Monedas segun una escalera
// creciente (1/3/6 por 1/2/3 espacios). El input es un stepper por masa activa
// -- una traduccion directa del `reparto` {slot_index: espacios} que espera el
// servidor, sin capa intermedia que pueda desalinearse con el precio.
//
// La Camara B NO aumenta cuantos espacios se compran: permite repartirlos
// entre dos masas en vez de concentrarlos en una. Por eso el tope de espacios
// es el mismo para todos y lo unico que cambia es cuantos steppers se pueden
// tener a la vez por encima de cero.
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import PistaMedida, { type BandaPista } from '../PistaMedida.vue'
import {
  MAX_ESPACIOS_PLIEGUES,
  MAX_MASAS_CON_CAMARA_B,
  MAX_MASAS_SIN_CAMARA_B,
  PRECIO_PLIEGUES,
  PRECIO_PLIEGUES_VITALIDAD,
} from '../../data/preciosPliegues'

const emit = defineEmits<{ cerrar: [] }>()

const TRACK_MAX = 20

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const tieneCamaraB = computed(() => yo.value.tecnologias.camara_b)
const maxMasas = computed(() =>
  tieneCamaraB.value ? MAX_MASAS_CON_CAMARA_B : MAX_MASAS_SIN_CAMARA_B,
)
const estacionesActivas = computed(() =>
  yo.value.estaciones_fermentacion
    .map((s, i) => ({ s, i }))
    .filter((e): e is { s: NonNullable<typeof e.s>; i: number } => e.s !== null),
)

const opcion = ref<'avanzar' | 'recuperar_vitalidad'>('avanzar')
// slot_index -> espacios comprados para esa masa.
const reparto = ref<Record<number, number>>({})
const enviando = ref(false)
const error = ref<string | null>(null)

const totalEspacios = computed(() =>
  Object.values(reparto.value).reduce((a, b) => a + b, 0),
)
const masasElegidas = computed(() => Object.keys(reparto.value).length)

const precio = computed(() => {
  if (opcion.value === 'recuperar_vitalidad') return PRECIO_PLIEGUES_VITALIDAD
  return PRECIO_PLIEGUES[totalEspacios.value] ?? 0
})
const puedePagar = computed(() => yo.value.monedas >= precio.value)

/** Un stepper puede subir si queda presupuesto de espacios y, cuando esta masa
 *  aun no participa, si queda cupo de masas (la Camara B es lo unico que da
 *  cupo para una segunda). */
function puedeSumar(i: number): boolean {
  if (totalEspacios.value >= MAX_ESPACIOS_PLIEGUES) return false
  if (!reparto.value[i] && masasElegidas.value >= maxMasas.value) return false
  return true
}

function sumar(i: number) {
  if (!puedeSumar(i)) return
  reparto.value = { ...reparto.value, [i]: (reparto.value[i] ?? 0) + 1 }
}

function restar(i: number) {
  const actual = reparto.value[i] ?? 0
  if (actual <= 0) return
  const siguiente = { ...reparto.value }
  if (actual === 1) delete siguiente[i]
  else siguiente[i] = actual - 1
  reparto.value = siguiente
}

function bandasDe(indice: number): BandaPista[] {
  const r = estacionesActivas.value.find((e) => e.i === indice)?.s.recipe
  if (!r) return []
  return [
    { desde: r.zona_pre_fermento[0] - 1, hasta: r.zona_pre_fermento[1], tono: 'baja' },
    { desde: r.zona_optima[0] - 1, hasta: r.zona_optima[1], tono: 'optima' },
    { desde: r.zona_colapso[0] - 1, hasta: TRACK_MAX, tono: 'sobre' },
  ]
}

/** Posicion a la que quedaria la masa si se confirma este reparto. Es solo el
 *  efecto de la accion: NO incluye el avance de la Fase III de esta noche, que
 *  EstacionCard ya proyecta por su cuenta en el tablero. */
function posicionResultante(indice: number): number {
  const slot = estacionesActivas.value.find((e) => e.i === indice)?.s
  if (!slot) return 0
  return slot.posicion_track + (reparto.value[indice] ?? 0)
}

function tonoResultante(indice: number): 'riesgo' | 'vital' | 'cobre' {
  const r = estacionesActivas.value.find((e) => e.i === indice)?.s.recipe
  const p = posicionResultante(indice)
  if (!r) return 'cobre'
  if (p >= r.zona_colapso[0]) return 'riesgo'
  if (p >= r.zona_optima[0] && p <= r.zona_optima[1]) return 'vital'
  return 'cobre'
}

/** Masas que este reparto empujaria a la zona de colapso. Es legal a
 *  proposito (la Fase III las hornea en colapso): se avisa, no se bloquea. */
const masasEnRiesgo = computed(() =>
  estacionesActivas.value
    .filter((e) => (reparto.value[e.i] ?? 0) > 0 && tonoResultante(e.i) === 'riesgo')
    .map((e) => e.s.recipe.nombre),
)

const listo = computed(() => {
  if (!puedePagar.value) return false
  if (opcion.value === 'recuperar_vitalidad') return tieneCamaraB.value
  return totalEspacios.value > 0 && totalEspacios.value <= MAX_ESPACIOS_PLIEGUES
})

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion(
      'E',
      opcion.value === 'recuperar_vitalidad'
        ? { opcion: 'recuperar_vitalidad' }
        : { opcion: 'avanzar', reparto: reparto.value },
    )
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo aplicar el pliegue.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Técnica — Pliegues" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Se paga en Monedas, no en PA, y no termina tu turno. Tienes
      <span class="dato">{{ yo.monedas }}</span> Monedas.
    </p>

    <div v-if="tieneCamaraB" class="opciones-radio">
      <label><input type="radio" value="avanzar" v-model="opcion" /> Avanzar fermentación</label>
      <label>
        <input type="radio" value="recuperar_vitalidad" v-model="opcion" />
        Recuperar +1 Vitalidad ({{ PRECIO_PLIEGUES_VITALIDAD }} Monedas)
      </label>
    </div>

    <template v-if="opcion === 'avanzar'">
      <p class="escalera">
        <span v-for="(p, n) in PRECIO_PLIEGUES" :key="n">
          <span class="dato">{{ n }}</span> espacio{{ Number(n) > 1 ? 's' : '' }} =
          <span class="dato">{{ p }}</span> Monedas
        </span>
      </p>
      <p v-if="tieneCamaraB" class="info-linea">
        Con Cámara B puedes repartirlos entre dos masas (no compras más, los repartes).
      </p>

      <p v-if="estacionesActivas.length === 0" class="info-linea">
        No tienes masas activas que plegar.
      </p>

      <div v-for="{ s, i } in estacionesActivas" :key="i" class="masa">
        <div class="masa-cabecera">
          <span class="eyebrow">Est-{{ (i + 1).toString().padStart(2, '0') }} · {{ s.recipe.nombre }}</span>
          <div class="stepper">
            <button type="button" :disabled="!(reparto[i] ?? 0)" @click="restar(i)">−</button>
            <span class="dato">{{ reparto[i] ?? 0 }}</span>
            <button type="button" :disabled="!puedeSumar(i)" @click="sumar(i)">+</button>
          </div>
        </div>
        <PistaMedida
          :valor="s.posicion_track - 0.5"
          :min="0"
          :max="TRACK_MAX"
          :previsto="(reparto[i] ?? 0) > 0 ? posicionResultante(i) - 0.5 : null"
          :tono-previsto="tonoResultante(i)"
          :bandas="bandasDe(i)"
          modo="posicion"
          lectura=""
        />
        <div class="masa-pie">
          <span class="dato">{{ s.posicion_track }}</span>
          <template v-if="(reparto[i] ?? 0) > 0">
            → <span class="dato">{{ posicionResultante(i) }}</span>
          </template>
          <span class="tenue">/20</span>
        </div>
      </div>

      <p v-if="masasEnRiesgo.length" class="aviso-riesgo">
        ⚠ Este reparto empuja a zona de colapso:
        {{ masasEnRiesgo.join(', ') }}. La Fase III la horneará en colapso.
      </p>
    </template>

    <p class="total">
      Total:
      <template v-if="opcion === 'avanzar'">
        <span class="dato">{{ totalEspacios }}</span> espacio{{ totalEspacios === 1 ? '' : 's' }} —
      </template>
      <span class="dato">{{ precio }}</span> Monedas
      <span v-if="!puedePagar" class="sin-fondos">· no te alcanza</span>
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !listo" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>

<style scoped>
.escalera {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2) var(--e3);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  margin: 0 0 var(--e2);
}

.masa {
  border-top: 1px solid var(--borde);
  padding-top: var(--e2);
  margin-top: var(--e2);
}

.masa-cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e2);
  margin-bottom: var(--e1);
}

.stepper {
  display: flex;
  align-items: center;
  gap: var(--e2);
}

.stepper button {
  width: 1.75rem;
  height: 1.75rem;
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-control);
  background: var(--zona);
  color: var(--tinta);
  font-size: var(--t-s);
  line-height: 1;
  cursor: pointer;
}

.stepper button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.masa-pie {
  display: flex;
  align-items: baseline;
  gap: var(--e1);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.aviso-riesgo {
  margin: var(--e3) 0 0;
  padding: var(--e2);
  border-radius: var(--r-control);
  background: var(--lavado-riesgo);
  color: var(--riesgo);
  font-size: var(--t-micro);
}

.total {
  margin: var(--e3) 0 0;
  padding-top: var(--e2);
  border-top: 1px solid var(--borde);
  font-size: var(--t-s);
}

.tenue {
  color: var(--tinta-tenue);
}

.sin-fondos {
  color: var(--riesgo);
}
</style>
