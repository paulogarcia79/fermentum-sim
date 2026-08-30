<script setup lang="ts">
// Visitar el Mercado (GDD v0.0.2, ACTIONS_REGISTRY.md §2C) -- reemplaza la
// vieja Accion C de "Adquirir Insumos" (lotes aleatorios de 150%). Ahora es
// una visita de 1 PA en la que se puede comprar y/o vender Harina (Blanca,
// Integral, Centeno) contra el visor de precio compartido, y/o comprar un
// lote de Agua al precio de la temperatura actual -- como maximo UNA
// transaccion por tipo de recurso (Regla de Exclusividad). Usar 4 filas fijas
// (una por tipo de recurso) hace esa regla estructuralmente imposible de
// violar desde la UI, en vez de necesitar una comprobacion posterior.
import { computed, reactive, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import PistaPrecioHarina from '../PistaPrecioHarina.vue'
import TablaPrecioAgua from '../TablaPrecioAgua.vue'
import {
  AGUA_TOKENS_POR_LOTE,
  CANTIDAD_BOLSA_PCT,
  CANTIDAD_MEDIA_BOLSA_PCT,
  LOTES_AGUA_VALIDOS,
  PRECIO_AGUA,
  precioCompraHarina,
  precioVentaHarina,
  type CantidadHarina,
  type LoteAguaPct,
} from '../../data/preciosHarina'
import { fmtAgua, fmtHarina } from '../../data/unidades'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const TIPOS_HARINA: TipoHarina[] = ['Blanca', 'Integral', 'Centeno']

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const mercado = computed(() => store.estado!.market)
const temperatura = computed(() => store.estado!.environment.temperatura_actual)

type IdOperacion = 'comprar' | 'comprar_media' | 'vender' | 'vender_media'

interface OperacionHarina {
  id: IdOperacion
  etiqueta: string
  direccion: 'comprar' | 'vender'
  cantidad: CantidadHarina
}

// Espejo de actions.py:OPERACIONES_HARINA, y por el mismo motivo que alli: la
// cantidad de cada operacion se escribe UNA vez y la leen el precio, el
// disabled del <option> y el saldo proyectado. Las cuatro opciones se muestran
// siempre juntas a proposito -- asi se ve de un vistazo que media bolsa nunca
// sale a mejor precio por token que una entera.
const OPERACIONES_HARINA: OperacionHarina[] = [
  { id: 'comprar', etiqueta: 'Comprar bolsa', direccion: 'comprar', cantidad: CANTIDAD_BOLSA_PCT },
  {
    id: 'comprar_media',
    etiqueta: 'Comprar media',
    direccion: 'comprar',
    cantidad: CANTIDAD_MEDIA_BOLSA_PCT,
  },
  { id: 'vender', etiqueta: 'Vender bolsa', direccion: 'vender', cantidad: CANTIDAD_BOLSA_PCT },
  {
    id: 'vender_media',
    etiqueta: 'Vender media',
    direccion: 'vender',
    cantidad: CANTIDAD_MEDIA_BOLSA_PCT,
  },
]

const operacionHarina = reactive<Record<TipoHarina, '' | IdOperacion>>({
  Blanca: '',
  Integral: '',
  Centeno: '',
})

/** Monedas que aporta (+) o cuesta (−) una operacion en la posicion actual. */
function deltaMonedas(tipo: TipoHarina, op: OperacionHarina): number {
  const posicion = mercado.value.posiciones_harina[tipo]
  return op.direccion === 'comprar'
    ? -precioCompraHarina(tipo, posicion, op.cantidad)
    : precioVentaHarina(tipo, posicion, op.cantidad)
}
const operacionAgua = ref<'' | 'comprar'>('')
const loteAgua = ref<LoteAguaPct>(10)

const enviando = ref(false)
const error = ref<string | null>(null)

function precioAgua(lote: LoteAguaPct): number {
  return PRECIO_AGUA[temperatura.value]?.[lote] ?? 0
}

const transacciones = computed(() => {
  const lista: Record<string, unknown>[] = []
  for (const tipo of TIPOS_HARINA) {
    const op = operacionHarina[tipo]
    if (op) lista.push({ tipo_recurso: tipo, operacion: op })
  }
  if (operacionAgua.value === 'comprar') {
    lista.push({ tipo_recurso: 'agua', operacion: 'comprar', lote_pct: loteAgua.value })
  }
  return lista
})

// Previsualizacion del saldo de Monedas tras la visita -- solo una pista de
// UX (misma logica que precioCompraHarina/precioVentaHarina), el servidor
// sigue siendo quien valida el lote completo de forma atomica al recibirlo.
const saldoProyectado = computed(() => {
  let monedas = yo.value.monedas
  for (const tipo of TIPOS_HARINA) {
    const elegida = OPERACIONES_HARINA.find((o) => o.id === operacionHarina[tipo])
    if (elegida) monedas += deltaMonedas(tipo, elegida)
  }
  if (operacionAgua.value === 'comprar') monedas -= precioAgua(loteAgua.value)
  return monedas
})

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('C', { transacciones: transacciones.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar la visita al mercado.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Visitar Mercado (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">Máximo una transacción por tipo de recurso en esta visita.</p>

    <div v-for="tipo in TIPOS_HARINA" :key="tipo" class="campo">
      <PistaPrecioHarina :tipo="tipo" />
      <p class="info-linea">En reserva: {{ fmtHarina(yo.reserva_harina[tipo]) }}</p>
      <select v-model="operacionHarina[tipo]">
        <option value="">— sin transacción —</option>
        <option
          v-for="op in OPERACIONES_HARINA"
          :key="op.id"
          :value="op.id"
          :disabled="op.direccion === 'vender' && yo.reserva_harina[tipo] < op.cantidad"
        >
          {{ op.etiqueta }}
          {{ op.direccion === 'comprar' ? '+' : '−' }}{{ fmtHarina(op.cantidad) }} —
          {{ deltaMonedas(tipo, op) >= 0 ? '+' : '−' }}{{ Math.abs(deltaMonedas(tipo, op)) }} Monedas
        </option>
      </select>
    </div>

    <div class="campo">
      <TablaPrecioAgua />
      <p class="info-linea">En reserva: {{ fmtAgua(yo.reserva_agua) }} de hidratación</p>
      <select v-model="operacionAgua">
        <option value="">— sin transacción —</option>
        <option value="comprar">Comprar lote</option>
      </select>
    </div>
    <label v-if="operacionAgua === 'comprar'" class="campo">
      Tamaño de lote
      <select v-model.number="loteAgua">
        <option v-for="lote in LOTES_AGUA_VALIDOS" :key="lote" :value="lote">
          {{ AGUA_TOKENS_POR_LOTE[lote] }} ({{ lote }}%) — {{ precioAgua(lote) }} Monedas
        </option>
      </select>
    </label>

    <p class="info-linea">
      Monedas actuales: <strong>{{ yo.monedas }}</strong> → tras esta visita:
      <strong :class="{ error: saldoProyectado < 0 }">{{ saldoProyectado }}</strong>
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || transacciones.length === 0 || saldoProyectado < 0"
        @click="confirmar"
      >
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.error {
  color: var(--riesgo);
}
</style>
