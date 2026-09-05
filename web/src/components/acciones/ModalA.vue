<script setup lang="ts">
// Acción A (Alimentar): 0 PA, una vez al día, se paga en harina según la
// escalera HARINA_ALIMENTAR (10% = +1, 30% = +2). El input es un stepper de
// tokens por tipo de harina -- una traducción directa del `harina`
// {tipo: porcentaje} que espera el servidor, que DERIVA los puntos de la suma:
// aquí el jugador elige primero el escalón y el modal solo deja confirmar
// cuando los tokens repartidos suman exactamente su precio.
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { fmtHarina, PCT_POR_TOKEN_HARINA } from '../../data/unidades'
import { ESCALONES_ALIMENTAR, HARINA_ALIMENTAR, VITALIDAD_MAX } from '../../data/alimentar'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const tipos = computed(() => Object.keys(yo.value.reserva_harina) as TipoHarina[])
const harinaTotal = computed(() =>
  tipos.value.reduce((acc, t) => acc + yo.value.reserva_harina[t], 0),
)
const mayorStock = computed(() => Math.max(0, ...tipos.value.map((t) => yo.value.reserva_harina[t])))

/** El escalón barato exige un MISMO tipo; el caro se puede mezclar. */
function puedePagarEscalon(puntos: number): boolean {
  const precio = HARINA_ALIMENTAR[puntos]
  return puntos === 1 ? mayorStock.value >= precio : harinaTotal.value >= precio
}

/** Reparto por defecto: rellena desde el tipo con más stock. Cubre el caso
 *  corriente (un solo tipo) sin clics extra. */
function repartoAutomatico(puntos: number): Record<string, number> {
  let restante = HARINA_ALIMENTAR[puntos] / PCT_POR_TOKEN_HARINA
  const reparto: Record<string, number> = {}
  const ordenados = [...tipos.value].sort(
    (a, b) => yo.value.reserva_harina[b] - yo.value.reserva_harina[a],
  )
  for (const t of ordenados) {
    if (restante <= 0) break
    const tokens = Math.min(restante, Math.floor(yo.value.reserva_harina[t] / PCT_POR_TOKEN_HARINA))
    if (tokens > 0) {
      reparto[t] = tokens
      restante -= tokens
    }
  }
  return reparto
}

// Valor INICIAL: el mejor escalón pagable. Después manda lo que elija el jugador.
const escalonInicial = [...ESCALONES_ALIMENTAR].reverse().find(puedePagarEscalon) ?? 1
const puntos = ref<number>(escalonInicial)
// tipo -> tokens (1 token = 10%).
const reparto = ref<Record<string, number>>(repartoAutomatico(escalonInicial))
const enviando = ref(false)
const error = ref<string | null>(null)

function elegir(p: number) {
  puntos.value = p
  reparto.value = repartoAutomatico(p)
}

const tokensObjetivo = computed(() => HARINA_ALIMENTAR[puntos.value] / PCT_POR_TOKEN_HARINA)
const tokensRepartidos = computed(() =>
  Object.values(reparto.value).reduce((a, b) => a + b, 0),
)
const listo = computed(() => tokensRepartidos.value === tokensObjetivo.value)

function puedeSumar(t: TipoHarina): boolean {
  if (tokensRepartidos.value >= tokensObjetivo.value) return false
  return ((reparto.value[t] ?? 0) + 1) * PCT_POR_TOKEN_HARINA <= yo.value.reserva_harina[t]
}

function sumar(t: TipoHarina) {
  if (!puedeSumar(t)) return
  reparto.value = { ...reparto.value, [t]: (reparto.value[t] ?? 0) + 1 }
}

function restar(t: TipoHarina) {
  const actual = reparto.value[t] ?? 0
  if (actual <= 0) return
  const siguiente = { ...reparto.value }
  if (actual === 1) delete siguiente[t]
  else siguiente[t] = actual - 1
  reparto.value = siguiente
}

/** Proyección: la Vitalidad de hoy tras alimentar, y la de mañana tras el
 *  desgaste. El desgaste (-1, -2 con Aletargamiento, 0 con Criopreservación)
 *  llega del servidor en `vitalidad_prevista`; aquí no se replica ninguna regla. */
const vitalidadHoy = computed(() =>
  Math.min(VITALIDAD_MAX, yo.value.vitalidad + puntos.value),
)
const vitalidadManana = computed(() => {
  const desgaste = yo.value.vitalidad_prevista - yo.value.vitalidad
  return Math.max(0, Math.min(VITALIDAD_MAX, vitalidadHoy.value + desgaste))
})

async function confirmar() {
  error.value = null
  if (!listo.value) return
  enviando.value = true
  try {
    const harina: Record<string, number> = {}
    for (const [t, tokens] of Object.entries(reparto.value)) {
      if (tokens > 0) harina[t] = tokens * PCT_POR_TOKEN_HARINA
    }
    await despacharAccion('A', { harina })
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
      Una vez por día. El +1 repone exactamente el −1 que el desgaste metabólico quita cada
      noche; el +2 cuesta tres tokens y contrarresta un Aletargamiento Invernal.
    </p>
    <p class="info-nota">La Acidez se ajusta en la acción «Descarte», no aquí.</p>

    <div class="opciones-radio">
      <label
        v-for="p in ESCALONES_ALIMENTAR"
        :key="p"
        :class="{ inerte: !puedePagarEscalon(p) }"
        ><input
          type="radio"
          :value="p"
          :checked="puntos === p"
          :disabled="!puedePagarEscalon(p)"
          @change="elegir(p)"
        />
        +{{ p }} Vitalidad
        <span class="dato">{{ fmtHarina(HARINA_ALIMENTAR[p]) }}</span>
        <span v-if="p === 1" class="tenue">de un mismo tipo</span>
        <span v-else class="tenue">de un tipo o mezclados</span>
        <span v-if="!puedePagarEscalon(p)" class="falta">· tienes {{ fmtHarina(harinaTotal) }}</span>
      </label>
    </div>

    <div v-for="t in tipos" :key="t" class="tipo">
      <span>{{ t }} <span class="tenue">— {{ fmtHarina(yo.reserva_harina[t]) }}</span></span>
      <div class="stepper">
        <button type="button" :disabled="!(reparto[t] ?? 0)" @click="restar(t)">−</button>
        <span class="dato">{{ reparto[t] ?? 0 }}</span>
        <button type="button" :disabled="!puedeSumar(t)" @click="sumar(t)">+</button>
      </div>
    </div>

    <p class="total" :class="{ falta: !listo }">
      <span class="dato">{{ tokensRepartidos }}</span>/<span class="dato">{{ tokensObjetivo }}</span>
      tokens repartidos
      <template v-if="listo">
        · Vitalidad <span class="dato">{{ yo.vitalidad }}</span> →
        <span class="dato">{{ vitalidadHoy }}</span> hoy ·
        <span class="dato">{{ vitalidadManana }}</span> tras la noche
      </template>
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando || !listo" @click="confirmar">Confirmar</button>
    </template>
  </ModalShell>
</template>

<style scoped>
.info-nota {
  margin: calc(var(--e1) * -1) 0 var(--e3);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.opciones-radio {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  margin-bottom: var(--e3);
}

.opciones-radio label {
  display: flex;
  align-items: baseline;
  gap: var(--e1);
  flex-wrap: wrap;
}

.inerte {
  color: var(--tinta-tenue);
}

.tenue {
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
}

.falta {
  color: var(--riesgo);
}

.tipo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e2);
  border-top: 1px solid var(--borde);
  padding-top: var(--e2);
  margin-top: var(--e2);
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

.total {
  margin: var(--e3) 0 0;
  font-size: var(--t-s);
}
</style>
