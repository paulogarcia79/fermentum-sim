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

const props = defineProps<{
  slot: FermentationSlot | null
  indice: number
  bloqueada?: boolean
  mostrarFantasma?: boolean
}>()

const TRACK_MAX = 20

function pct(posicion: number): number {
  return Math.min(100, Math.max(0, (posicion / TRACK_MAX) * 100))
}

const zonas = computed(() => {
  const r = props.slot?.recipe
  if (!r) return null
  return {
    baja: [pct(r.zona_baja[0] - 1), pct(r.zona_baja[1])],
    optima: [pct(r.zona_optima[0] - 1), pct(r.zona_optima[1])],
    sobre: [pct(r.zona_sobrefermentada[0] - 1), pct(TRACK_MAX)],
  }
})

const posicionActualPct = computed(() => (props.slot ? pct(props.slot.posicion_track) : 0))

const posicionFantasma = computed(() => {
  if (!props.slot || !store.estado) return null
  const avanceBase = Math.floor(store.estado.environment.temperatura_actual / 5)
  const proyectada = props.slot.posicion_track + avanceBase + props.slot.dado_inoculo + props.slot.modificador_incubadora
  return Math.min(proyectada, TRACK_MAX + 4) // deja ver que se sale del track sin romper el layout
})

const zonaProyectada = computed(() => {
  if (!props.slot || posicionFantasma.value === null) return null
  const r = props.slot.recipe
  if (posicionFantasma.value >= r.zona_sobrefermentada[0]) return 'colapso'
  if (posicionFantasma.value >= r.zona_optima[0] && posicionFantasma.value <= r.zona_optima[1]) return 'optima'
  return 'baja'
})

const detalleAbierto = ref(false)
</script>

<template>
  <div class="estacion" :class="{ bloqueada }">
    <div class="titulo">
      <span>Est-{{ (indice + 1).toString().padStart(2, '0') }}</span>
    </div>

    <template v-if="bloqueada">
      <div class="vacia">Bloqueada (requiere Cámara B)</div>
    </template>
    <template v-else-if="!slot">
      <div class="vacia">— libre —</div>
    </template>
    <template v-else>
      <div class="track">
        <div class="banda baja" :style="{ left: zonas!.baja[0] + '%', width: zonas!.baja[1] - zonas!.baja[0] + '%' }" />
        <div class="banda optima" :style="{ left: zonas!.optima[0] + '%', width: zonas!.optima[1] - zonas!.optima[0] + '%' }" />
        <div class="banda sobre" :style="{ left: zonas!.sobre[0] + '%', width: zonas!.sobre[1] - zonas!.sobre[0] + '%' }" />
        <div class="marcador" :style="{ left: posicionActualPct + '%' }" :title="`Posición ${slot.posicion_track}`" />
        <div
          v-if="mostrarFantasma && posicionFantasma !== null"
          class="marcador fantasma"
          :class="zonaProyectada"
          :style="{ left: pct(posicionFantasma) + '%' }"
          :title="`Próxima posición proyectada: ${posicionFantasma}`"
        />
      </div>
      <div class="detalle-fila">
        <span>pos {{ slot.posicion_track }}/20</span>
        <span>dado {{ slot.dado_inoculo }}</span>
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
  background: var(--color-fondo);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
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
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.boton-tarjeta:hover :deep(.receta-card) {
  border-color: var(--color-acento);
}

.titulo {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
  margin-bottom: 0.3rem;
}

.vacia {
  color: var(--color-texto-tenue);
  font-style: italic;
  font-size: 0.85rem;
}

.track {
  position: relative;
  height: 10px;
  background: #2a231d;
  border-radius: 5px;
  overflow: visible;
}

.banda {
  position: absolute;
  top: 0;
  height: 100%;
}

.banda.baja {
  background: #4a4038;
}

.banda.optima {
  background: var(--color-bien);
  opacity: 0.55;
}

.banda.sobre {
  background: var(--color-mal);
  opacity: 0.55;
}

.marcador {
  position: absolute;
  top: -3px;
  width: 4px;
  height: 16px;
  background: var(--color-acento);
  border-radius: 2px;
  transform: translateX(-50%);
}

.marcador.fantasma {
  opacity: 0.5;
  background: var(--color-texto);
}

.marcador.fantasma.optima {
  background: var(--color-bien);
}

.marcador.fantasma.colapso {
  background: var(--color-mal);
}

.detalle-fila {
  display: flex;
  gap: 0.6rem;
  font-size: 0.7rem;
  color: var(--color-texto-tenue);
  margin-top: 0.3rem;
}
</style>
