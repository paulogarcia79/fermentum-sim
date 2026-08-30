<script setup lang="ts">
// Hornear y Vender (GDD v0.0.2, antes "Hornear"). Vista previa de puntos y
// Monedas: replica solo la lectura de zona (no una decision de reglas)
// leyendo puntos_pre_fermento/monedas_pre_fermento/monedas_optima/monedas_colapso directamente
// de la Recipe que ya viaja en el snapshot (a diferencia de los precios de
// la Bolsa de Harinas en ModalC.vue, estos SI son campos reales de la
// receta, no una tabla del motor que haya que duplicar). MONEDAS_BONO_SABOR
// = 2 es el unico numero "mágico" duplicado de engine.py, puramente para
// mostrar una estimacion antes de confirmar (ver engine.py:resolver_horneado).
// El servidor sigue siendo quien calcula el resultado real al recibir la accion.
import { computed, ref } from 'vue'
import { despacharAccion, mostrarResultadoHorneado, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import { estaEnCrecimiento } from '../../data/zonasReceta'

const MONEDAS_BONO_SABOR = 2

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const estacionesActivas = computed(
  () => yo.value.estaciones_fermentacion.map((s, i) => ({ s, i })).filter(({ s }) => s !== null),
)

const slotIndex = ref(estacionesActivas.value[0]?.i ?? 0)
const enviando = ref(false)
const error = ref<string | null>(null)

const slotSeleccionado = computed(() => yo.value.estaciones_fermentacion[slotIndex.value])

const previa = computed(() => {
  const slot = slotSeleccionado.value
  if (!slot) return null
  const r = slot.recipe
  const pos = slot.posicion_track
  // La masa que todavia crece no es pan: el servidor rechaza hornearla, asi que el
  // modal lo dice antes de dejar enviar (mismo patron que ModalG con las Monedas).
  if (estaEnCrecimiento(r, pos)) {
    return { zona: 'Crecimiento', puntos: 0, monedas: 0, datos: 0, horneable: false }
  }
  if (pos >= r.zona_colapso[0]) {
    // Un colapso nunca aplica el Bono de Sabor, ni en puntos ni en Monedas.
    return { zona: 'Colapso', puntos: r.penalizacion_colapso, monedas: r.monedas_colapso, datos: 0, horneable: true }
  }
  const bonoPuntos = slot.bono_sabor ? r.bono_sabor_pts : 0
  const bonoMonedas = slot.bono_sabor ? MONEDAS_BONO_SABOR : 0
  if (pos >= r.zona_optima[0] && pos <= r.zona_optima[1]) {
    // Datos: 1 en zona óptima, +1 si es el centro exacto y el Módulo Analítico está
    // instalado (espejo de engine._calcular_datos_horneado / DATOS_BAKE_*).
    const centro = Math.floor((r.zona_optima[0] + r.zona_optima[1]) / 2)
    const bonoDatos = pos === centro && yo.value.tecnologias.modulo_analitico ? 1 : 0
    return { zona: 'Óptima', puntos: r.puntos_optimos + bonoPuntos, monedas: r.monedas_optima + bonoMonedas, datos: 1 + bonoDatos, horneable: true }
  }
  return { zona: 'Pre-fermento', puntos: r.puntos_pre_fermento + bonoPuntos, monedas: r.monedas_pre_fermento + bonoMonedas, datos: 0, horneable: true }
})

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('F', { slot_index: slotIndex.value })
    // Mostrar el resultado REAL en vez de cerrar en silencio.
    // `despacharAccion` ya aplico el snapshot fresco, y un horneado
    // voluntario siempre aterriza en archivo_horneado_exitoso: su ultimo
    // registro ES este horneado, con puntos_totales/zona_resultado ya
    // calculados por el servidor. Va al store (no a un ref local) porque la
    // Accion F termina el turno y este modal se desmonta con BarraAcciones
    // en cuanto el snapshot llega -- ver ResultadoHorneadoModal.vue.
    const archivo = yo.value.archivo_horneado_exitoso
    const registro = archivo[archivo.length - 1]
    if (registro) mostrarResultadoHorneado(registro)
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo hornear.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Hornear y Vender (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <label class="campo">
      Masa
      <select v-model.number="slotIndex">
        <option v-for="{ s, i } in estacionesActivas" :key="i" :value="i">Est-{{ i + 1 }}: {{ s!.recipe.nombre }} (pos {{ s!.posicion_track }})</option>
      </select>
    </label>

    <p v-if="previa && !previa.horneable" class="info-linea aviso">
      Zona {{ previa.zona }} — la masa todavía no es pan y no se puede hornear. Espera a que
      llegue al Pre-fermento, o abandónala con el Simposio Técnico.
    </p>
    <p v-else-if="previa" class="info-linea">
      Zona {{ previa.zona }} — resultado estimado: <strong>{{ previa.puntos }} pts</strong>,
      <strong>{{ previa.monedas }} Monedas</strong><template v-if="previa.datos > 0"> ·
      <strong>+{{ previa.datos }} Datos</strong></template>
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || estacionesActivas.length === 0 || previa?.horneable === false"
        @click="confirmar"
      >
        Confirmar
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.aviso {
  color: var(--riesgo);
}
</style>
