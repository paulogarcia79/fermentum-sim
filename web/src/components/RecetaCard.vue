<script setup lang="ts">
// Tarjeta visual de una receta: icono de pan, requisitos en iconos, y una
// franja de puntos por zona del track 1-20 (misma logica de bandas que
// EstacionCard.vue). El detalle textual completo (acidez diana, tecnologia
// requerida, hidratacion%) vive en un tooltip -- hover en escritorio,
// tambien tap-toggle para que funcione en pantallas tactiles.
import { computed, ref } from 'vue'
import type { Recipe } from '../types'
import IconoPan from './IconoPan.vue'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'

const props = defineProps<{ receta: Recipe; compacta?: boolean }>()

const TRACK_MAX = 20
function pct(posicion: number): number {
  return Math.min(100, Math.max(0, (posicion / TRACK_MAX) * 100))
}

const bandas = computed(() => {
  const r = props.receta
  const baja = [pct(r.zona_baja[0] - 1), pct(r.zona_baja[1])]
  const optima = [pct(r.zona_optima[0] - 1), pct(r.zona_optima[1])]
  const sobre = [pct(r.zona_sobrefermentada[0] - 1), pct(TRACK_MAX)]
  return { baja, optima, sobre }
})

const centroExacto = computed(() =>
  Math.floor((props.receta.zona_optima[0] + props.receta.zona_optima[1]) / 2),
)

const detalleAbierto = ref(false)
</script>

<template>
  <div class="receta-card" :class="{ compacta, abierta: detalleAbierto }">
    <div class="cabecera">
      <div class="icono-pan-envoltorio"><IconoPan :id="receta.id" /></div>
      <div class="titulo">
        <span class="nombre">{{ receta.nombre }}</span>
        <span class="grado">{{ receta.grado }}</span>
      </div>
      <button
        type="button"
        class="boton-info"
        :aria-expanded="detalleAbierto"
        title="Ver todos los detalles"
        @click="detalleAbierto = !detalleAbierto"
      >
        ⓘ
      </button>
    </div>

    <div class="requisitos">
      <span class="req">
        <span class="icono-req"><IconoHarina :tipo="receta.harina_base" /></span> 1
      </span>
      <span class="req">
        <span class="icono-req"><IconoAgua /></span> {{ receta.tokens_agua }}
      </span>
    </div>

    <div class="escala-puntos">
      <div class="pista">
        <div class="banda baja" :style="{ left: bandas.baja[0] + '%', width: bandas.baja[1] - bandas.baja[0] + '%' }" />
        <div
          class="banda optima"
          :style="{ left: bandas.optima[0] + '%', width: bandas.optima[1] - bandas.optima[0] + '%' }"
        />
        <div class="banda sobre" :style="{ left: bandas.sobre[0] + '%', width: bandas.sobre[1] - bandas.sobre[0] + '%' }" />
      </div>
      <div class="etiquetas-puntos">
        <span class="pts baja">{{ receta.puntos_baja }}</span>
        <span class="pts optima">{{ receta.puntos_optimos }}</span>
        <span class="pts sobre">{{ receta.penalizacion_colapso }}</span>
      </div>
    </div>

    <div class="tooltip" role="tooltip">
      <p>
        Requiere: 1 Harina {{ receta.harina_base }} (100%) + {{ receta.tokens_agua }} tokens de Agua ({{
          receta.hidratacion_pct
        }}% hidratación)<template v-if="receta.req_tecnologico"> · Requiere {{ receta.req_tecnologico }}</template>
      </p>
      <p>Bono de sabor: Acidez ∈ {{ receta.acidez_diana.join(', ') }} al iniciar → +{{ receta.bono_sabor_pts }} pts</p>
      <p>
        Zona Óptima {{ receta.zona_optima[0] }}–{{ receta.zona_optima[1] }}: +1 Dato (centro exacto
        {{ centroExacto }}: +1 extra con Módulo Analítico)
      </p>
      <p>Sobrefermentada desde {{ receta.zona_sobrefermentada[0] }}: colapso automático.</p>
    </div>
  </div>
</template>

<style scoped>
.receta-card {
  position: relative;
  background: var(--color-fondo);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.cabecera {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.icono-pan-envoltorio {
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
}

.receta-card.compacta .icono-pan-envoltorio {
  width: 20px;
  height: 20px;
}

.titulo {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
}

.nombre {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grado {
  font-size: 0.7rem;
  color: var(--color-texto-tenue);
}

.boton-info {
  flex: 0 0 auto;
  background: none;
  border: none;
  color: var(--color-texto-tenue);
  font-size: 0.9rem;
  padding: 0 0.2rem;
  cursor: pointer;
}

.boton-info:hover {
  color: var(--color-texto);
}

.requisitos {
  display: flex;
  gap: 0.75rem;
  margin: 0.4rem 0;
}

.req {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
}

.icono-req {
  width: 16px;
  height: 16px;
}

.escala-puntos {
  margin-top: 0.3rem;
}

.pista {
  position: relative;
  height: 8px;
  background: #2a231d;
  border-radius: 4px;
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

.etiquetas-puntos {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: var(--color-texto-tenue);
  margin-top: 0.15rem;
}

.pts.optima {
  color: var(--color-bien);
}

.pts.sobre {
  color: var(--color-mal);
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + 0.4rem);
  left: 50%;
  transform: translateX(-50%);
  width: 260px;
  max-width: 70vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--color-texto);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  z-index: 30;
  transition: opacity 0.1s ease;
}

.tooltip p {
  margin: 0 0 0.35rem;
}

.tooltip p:last-child {
  margin-bottom: 0;
}

.receta-card:hover .tooltip,
.receta-card:focus-within .tooltip,
.receta-card.abierta .tooltip {
  visibility: visible;
  opacity: 1;
}
</style>
