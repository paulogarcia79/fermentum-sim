<script setup lang="ts">
// Tarjeta de una estación de fermentación: dibuja el track 1-20 con sus
// tres bandas de zona y un marcador en la posición actual. `mostrarFantasma`
// añade un segundo marcador semitransparente en la posición proyectada tras
// la próxima Fase III (temp//5 + dado_inoculo + modificador_incubadora) --
// aritmética pura del lado del cliente sobre datos que ya vienen en el
// snapshot, sin duplicar ninguna regla de negocio.
import { computed, ref } from 'vue'
import type { FermentationSlot } from '../types'
import { store } from '../store'
import RecetaCard from './RecetaCard.vue'
import DetalleRecetaModal from './DetalleRecetaModal.vue'
import PistaMedida, { type BandaPista } from './PistaMedida.vue'

const props = defineProps<{
  slot: FermentationSlot | null
  indice: number
  bloqueada?: boolean
  mostrarFantasma?: boolean
}>()

const TRACK_MAX = 20

// Las bandas van en unidades del track (1-20), no en %: PistaMedida hace la
// conversion. Se restan 0.5 casillas en los bordes por lo mismo que el
// marcador se centra en su celda (ver abajo).
const bandas = computed<BandaPista[]>(() => {
  const r = props.slot?.recipe
  if (!r) return []
  return [
    { desde: r.zona_baja[0] - 1, hasta: r.zona_baja[1], tono: 'baja' },
    { desde: r.zona_optima[0] - 1, hasta: r.zona_optima[1], tono: 'optima' },
    { desde: r.zona_sobrefermentada[0] - 1, hasta: TRACK_MAX, tono: 'sobre' },
  ]
})

// El marcador se dibuja en el CENTRO de su celda del track (pos - 0.5), no en el
// borde derecho: así una masa en `zona_optima[0] - 1` (que el motor puntúa como zona
// baja, 0 Datos) queda visiblemente a la izquierda de la banda verde, y una en
// `zona_optima[0]` queda dentro — coincidiendo con lo que `resolver_horneado` hará.
const posicionActual = computed(() => (props.slot ? props.slot.posicion_track - 0.5 : 0))

const posicionFantasma = computed(() => {
  if (!props.slot || !store.estado) return null
  const avanceBase = Math.floor(store.estado.environment.temperatura_actual / 5)
  const proyectada = props.slot.posicion_track + avanceBase + props.slot.dado_inoculo + props.slot.modificador_incubadora
  return Math.min(proyectada, TRACK_MAX + 4) // deja ver que se sale del track sin romper el layout
})

const tonoProyectado = computed<'riesgo' | 'vital' | 'cobre' | null>(() => {
  if (!props.slot || posicionFantasma.value === null) return null
  const r = props.slot.recipe
  if (posicionFantasma.value >= r.zona_sobrefermentada[0]) return 'riesgo'
  if (posicionFantasma.value >= r.zona_optima[0] && posicionFantasma.value <= r.zona_optima[1]) return 'vital'
  return 'cobre'
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
        :tono-previsto="tonoProyectado"
        :bandas="bandas"
        modo="posicion"
        lectura=""
      />
      <div class="detalle-fila">
        <span>dado <span class="dato">{{ slot.dado_inoculo }}</span></span>
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
