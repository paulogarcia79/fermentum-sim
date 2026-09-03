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
  precioCompraEfectivo,
  precioCompraHarina,
  precioVentaHarina,
  type CantidadHarina,
  type LoteAguaPct,
} from '../../data/preciosHarina'
import { PRECIO_CONTRATO_MOLINO, RENDIMIENTO_MOLINO_PCT } from '../../data/preciosMolino'
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

// La tecnologia Comerciante descuenta 1 Moneda (suelo 1) de cada COMPRA de la
// visita, y de ninguna venta (actions.py: DESCUENTO_COMERCIANTE). Las pistas de
// precio de arriba -- PistaPrecioHarina y TablaPrecioAgua -- siguen mostrando el
// precio IMPRESO a proposito: son el estado compartido de la mesa, igual para
// todos, y el precio propio se lee en la opcion que se elige.
const tieneComerciante = computed(() => yo.value.tecnologias.comerciante)

/** Monedas que aporta (+) o cuesta (−) una operacion en la posicion actual. */
function deltaMonedas(tipo: TipoHarina, op: OperacionHarina): number {
  const posicion = mercado.value.posiciones_harina[tipo]
  return op.direccion === 'comprar'
    ? -precioCompraEfectivo(
        precioCompraHarina(tipo, posicion, op.cantidad),
        tieneComerciante.value,
      )
    : precioVentaHarina(tipo, posicion, op.cantidad)
}
const operacionAgua = ref<'' | 'comprar'>('')
const loteAgua = ref<LoteAguaPct>(10)

// Contrato con el Molino: su propia fila porque en el wire es su propio
// tipo_recurso ('molino'), no el de la harina contratada -- por eso firmar
// Centeno y comprar Centeno en la misma visita no choca con la Regla de
// Exclusividad. Uno por partida: si ya hay contrato, la fila solo informa.
const harinaMolino = ref<'' | TipoHarina>('')
const yaTieneContrato = computed(() => yo.value.contrato_molino !== null)

const enviando = ref(false)
const error = ref<string | null>(null)

function precioAgua(lote: LoteAguaPct): number {
  const impreso = PRECIO_AGUA[temperatura.value]?.[lote] ?? 0
  return precioCompraEfectivo(impreso, tieneComerciante.value)
}

function precioMolino(tipo: TipoHarina): number {
  return precioCompraEfectivo(PRECIO_CONTRATO_MOLINO[tipo], tieneComerciante.value)
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
  if (harinaMolino.value) {
    lista.push({
      tipo_recurso: 'molino',
      operacion: 'contratar',
      tipo_harina: harinaMolino.value,
    })
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
  if (harinaMolino.value) monedas -= precioMolino(harinaMolino.value)
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
    <p v-if="tieneComerciante" class="info-linea comerciante">
      <strong>Comerciante</strong>: cada compra de esta visita te cuesta 1 Moneda menos (mínimo 1).
      Los precios de las pistas son los de la mesa; los tuyos son los de cada opción. Las ventas
      cobran lo mismo que a todos.
    </p>

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

    <div class="campo molino">
      <p class="eyebrow">Contrato con el Molino</p>
      <p v-if="yaTieneContrato" class="info-linea">
        Ya tienes contratada <strong>Harina {{ yo.contrato_molino }}</strong
        >: te entrega {{ fmtHarina(RENDIMIENTO_MOLINO_PCT) }} cada noche. Solo se firma uno por
        partida y no puede cambiarse.
      </p>
      <template v-else>
        <p class="info-linea">
          Pago único. A partir de esta noche el molino te entrega
          {{ fmtHarina(RENDIMIENTO_MOLINO_PCT) }} de esa harina en cada Fase III, para siempre — sin
          pasar por la Bolsa y sin mover el visor. Se amortiza a la cuarta noche.
        </p>
        <select v-model="harinaMolino">
          <option value="">— sin contrato —</option>
          <option v-for="tipo in TIPOS_HARINA" :key="tipo" :value="tipo">
            Contratar {{ tipo }} — {{ precioMolino(tipo) }} Monedas
          </option>
        </select>
      </template>
    </div>

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

.comerciante {
  color: var(--cobre);
}
</style>
