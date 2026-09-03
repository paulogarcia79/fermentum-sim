<script setup lang="ts">
// Tarjeta de una estación de fermentación: dibuja el track 1-20 con sus
// cuatro bandas de zona y un marcador en la posición actual. `mostrarFantasma`
// añade un segundo marcador semitransparente en la posición proyectada tras
// la próxima Fase III (temp//5 + dado_inoculo + modificador_incubadora).
// Esa aritmética vive en `data/proyeccionMasa.ts` y no aquí, porque
// ModalIncubadora dibuja exactamente la misma proyección mientras el jugador
// mueve el dial: dos copias podrían discrepar, y el jugador estaría eligiendo
// contra una cifra que su propio tablero desmiente.
import { computed, ref } from 'vue'
import type { FermentationSlot } from '../types'
import { store } from '../store'
import RecetaCard from './RecetaCard.vue'
import DetalleRecetaModal from './DetalleRecetaModal.vue'
import { zonasDe } from '../data/zonasReceta'
import {
  TRACK_MAX,
  bandasDe,
  posicionProyectada,
  tonoProyectado,
} from '../data/proyeccionMasa'
import PistaMedida from './PistaMedida.vue'

const props = defineProps<{
  slot: FermentationSlot | null
  indice: number
  bloqueada?: boolean
  mostrarFantasma?: boolean
}>()

// Zonas ya ampliadas por el Modulo Analitico del propietario (zonasDe): esta es
// la superficie donde de verdad importa, porque es la que muestra el umbral de
// colapso contra el que el jugador decide si hornear esta noche.
const zonas = computed(() => (props.slot ? zonasDe(props.slot.recipe) : null))

const bandas = computed(() => (zonas.value ? bandasDe(zonas.value) : []))

// El marcador se dibuja en el CENTRO de su celda del track (pos - 0.5), no en el
// borde derecho: así una masa en `zona_optima[0] - 1` (que el motor puntúa como zona
// baja, 0 Datos) queda visiblemente a la izquierda de la banda verde, y una en
// `zona_optima[0]` queda dentro — coincidiendo con lo que `resolver_horneado` hará.
const posicionActual = computed(() => (props.slot ? props.slot.posicion_track - 0.5 : 0))

const posicionFantasma = computed(() => {
  if (!props.slot || !store.estado) return null
  return posicionProyectada(
    props.slot,
    store.estado.environment.temperatura_actual,
    props.slot.modificador_incubadora,
  )
})

const tonoFantasma = computed<'riesgo' | 'vital' | 'cobre' | null>(() => {
  const z = zonas.value
  if (posicionFantasma.value === null || !z) return null
  return tonoProyectado(z, posicionFantasma.value)
})

const detalleAbierto = ref(false)
</script>

<template>
  <div class="estacion" :class="{ bloqueada }">
    <div class="titulo">
      <span class="eyebrow">Est-{{ (indice + 1).toString().padStart(2, '0') }}</span>
      <span v-if="slot" class="dato posicion">{{ slot.posicion_track }}/20</span>
    </div>

    <template v-if="bloqueada">
      <div class="vacia">Bloqueada (requiere Cámara B)</div>
    </template>
    <template v-else-if="!slot">
      <div class="vacia">— libre —</div>
    </template>
    <template v-else>
      <PistaMedida
        :valor="posicionActual"
        :min="0"
        :max="TRACK_MAX"
        :previsto="mostrarFantasma && posicionFantasma !== null ? posicionFantasma - 0.5 : null"
        :tono-previsto="tonoFantasma"
        :bandas="bandas"
        modo="posicion"
        lectura=""
      />
      <div class="detalle-fila">
        <span>dado <span class="dato">{{ slot.dado_inoculo }}</span></span>
        <!-- El dial de la Incubadora se ve en el tablero, no solo dentro de su
             modal: es un ajuste que dura una noche y hay que poder comprobarlo
             de un vistazo antes de pasar el turno. -->
        <span v-if="slot.modificador_incubadora" class="dial">
          🌡 <span class="dato">{{ slot.modificador_incubadora > 0 ? '+' : ''
          }}{{ slot.modificador_incubadora }}</span>
        </span>
        <span v-if="mostrarFantasma && posicionFantasma !== null">
          esta noche → <span class="dato">{{ posicionFantasma }}</span>
        </span>
        <span v-if="slot.bono_sabor">🧪 bono sabor</span>
      </div>
      <button type="button" class="boton-tarjeta" title="Ver receta completa" @click="detalleAbierto = true">
        <RecetaCard :receta="slot.recipe" compacta />
      </button>
    </template>

    <DetalleRecetaModal
      v-if="detalleAbierto && slot"
      :receta="slot.recipe"
      :acidez-inicial="slot.acidez_inicial"
      :bono-sellado="slot.bono_sabor"
      @cerrar="detalleAbierto = false"
    />
  </div>
</template>

<style scoped>
.estacion {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  padding: var(--e2);
}

.estacion.bloqueada {
  opacity: 0.5;
}

.dial {
  color: var(--cobre);
}

.boton-tarjeta {
  display: block;
  width: 100%;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  text-align: left;
  font: inherit;
  color: inherit;
}

.boton-tarjeta:hover :deep(.receta-card) {
  border-color: var(--cobre);
}

.titulo {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--e2);
}

.posicion {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.vacia {
  color: var(--tinta-tenue);
  font-style: italic;
  font-size: var(--t-xs);
}

.detalle-fila {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}
</style>
