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
  LOTES_AGUA_VALIDOS,
  PRECIO_AGUA,
  precioCompraHarina,
  precioVentaHarina,
  type LoteAguaPct,
} from '../../data/preciosHarina'
import type { TipoHarina } from '../../types'

const emit = defineEmits<{ cerrar: [] }>()

const TIPOS_HARINA: TipoHarina[] = ['Blanca', 'Integral', 'Centeno']

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const mercado = computed(() => store.estado!.market)
const temperatura = computed(() => store.estado!.environment.temperatura_actual)

const operacionHarina = reactive<Record<TipoHarina, '' | 'comprar' | 'vender'>>({
  Blanca: '',
  Integral: '',
  Centeno: '',
})
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
    const op = operacionHarina[tipo]
    const posicion = mercado.value.posiciones_harina[tipo]
    if (op === 'comprar') monedas -= precioCompraHarina(tipo, posicion)
    else if (op === 'vender') monedas += precioVentaHarina(tipo, posicion)
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
      <select v-model="operacionHarina[tipo]">
        <option value="">— sin transacción —</option>
        <option value="comprar">Comprar — {{ precioCompraHarina(tipo, mercado.posiciones_harina[tipo]) }} Monedas</option>
        <option value="vender" :disabled="yo.reserva_harina[tipo] < 100">
          Vender — {{ precioVentaHarina(tipo, mercado.posiciones_harina[tipo]) }} Monedas
        </option>
      </select>
    </div>

    <div class="campo">
      <TablaPrecioAgua />
      <select v-model="operacionAgua">
        <option value="">— sin transacción —</option>
        <option value="comprar">Comprar lote</option>
      </select>
    </div>
    <label v-if="operacionAgua === 'comprar'" class="campo">
      Tamaño de lote
      <select v-model.number="loteAgua">
        <option v-for="lote in LOTES_AGUA_VALIDOS" :key="lote" :value="lote">
          {{ lote }}% — {{ precioAgua(lote) }} Monedas
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
  color: var(--color-mal);
}
</style>
