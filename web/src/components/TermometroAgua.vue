<script setup lang="ts">
// Termometro decorativo del Suministro Hidrico -- acompaña a
// TablaPrecioAgua.vue en BolsaHarinasPanel.vue, inspirado en
// reference_images/market_example.jpeg. Los 5 escalones de temperatura
// (10/15/20/25/30) son fijos (ver PRECIO_AGUA en preciosHarina.ts) y se
// mapean linealmente a la altura del tubo; el mercurio usa la misma
// convencion calido/frio/neutro que CartaClima.vue (temperatura respecto a
// la base de 20°C), no una escala continua de color.
import { computed } from 'vue'

const props = defineProps<{ temperatura: number }>()

const TEMPS = [30, 25, 20, 15, 10] as const
const BODY_TOP = 12
const BODY_BOTTOM = 148
const BULB_CY = 168

function yPara(temp: number): number {
  const frac = (temp - 10) / 20
  return BODY_BOTTOM - frac * (BODY_BOTTOM - BODY_TOP)
}

const ticks = TEMPS.map((temp) => ({ temp, y: yPara(temp) }))

const mercurioY = computed(() => yPara(props.temperatura))

const signoClase = computed(() => {
  if (props.temperatura > 20) return 'calido'
  if (props.temperatura < 20) return 'frio'
  return 'neutro'
})
</script>

<template>
  <svg viewBox="0 0 70 190" class="termometro" aria-hidden="true">
    <rect x="13" y="10" width="14" height="145" rx="7" fill="none" stroke="var(--borde)" stroke-width="1.5" />
    <rect
      class="mercurio"
      :class="signoClase"
      x="15.5"
      :y="mercurioY"
      width="9"
      :height="Math.max(0, 160 - mercurioY)"
      rx="4.5"
    />
    <circle class="mercurio" :class="signoClase" cx="20" :cy="BULB_CY" r="15" stroke="var(--borde)" stroke-width="1.5" />

    <g v-for="tick in ticks" :key="tick.temp" class="tick" :class="{ actual: tick.temp === temperatura }">
      <line :x1="27" :y1="tick.y" :x2="33" :y2="tick.y" stroke="currentColor" stroke-width="1.3" />
      <text :x="37" :y="tick.y + 3.5" class="etiqueta-tick">{{ tick.temp }}°</text>
    </g>
  </svg>
</template>

<style scoped>
.termometro {
  width: 56px;
  height: 152px;
  flex: 0 0 auto;
}

.mercurio {
  fill: var(--tinta);
}

.mercurio.calido {
  fill: var(--calido);
}

.mercurio.frio {
  fill: var(--frio);
}

.mercurio.neutro {
  fill: var(--tinta);
}

.tick {
  color: var(--tinta-tenue);
}

.tick.actual {
  color: var(--cobre);
  font-weight: 700;
}

.etiqueta-tick {
  fill: currentColor;
  font-size: 9px;
}
</style>
