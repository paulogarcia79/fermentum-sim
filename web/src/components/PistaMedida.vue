<script setup lang="ts">
/**
 * PistaMedida -- el instrumento del juego.
 *
 * Todo lo que en Fermentum se mide vive sobre una escala con bandas:
 * Vitalidad 0-6, Acidez 0-6, fermentacion 1-20, precio de harina 1-5, PA,
 * hidratacion %. Antes cada una tenia su propio dibujo (pips, barra de 8px,
 * barra de 10px, visor de tabla), asi que cuatro cosas que son la misma cosa
 * se leian distinto. Este componente las dibuja todas con el mismo lenguaje:
 *
 *   carril reglado + bandas de zona + corchete solido en el valor actual
 *   + corchete discontinuo en el valor previsto + lectura en Plex Mono.
 *
 * El corchete discontinuo generaliza lo que PistaPrecioHarina.vue ya habia
 * inventado para marcar a donde se movera el visor esta noche.
 */
import { computed } from 'vue'

export interface BandaPista {
  desde: number
  hasta: number
  tono: 'baja' | 'optima' | 'sobre' | 'neutra'
}

type Tono = 'cobre' | 'vital' | 'riesgo' | 'frio' | 'verdin'

const VAR_TONO: Record<Tono, string> = {
  cobre: 'var(--cobre)',
  vital: 'var(--vital)',
  riesgo: 'var(--riesgo)',
  frio: 'var(--frio)',
  verdin: 'var(--verdin)',
}

const props = withDefaults(
  defineProps<{
    /** null = la escala se dibuja sin aguja (p. ej. la carta de una receta,
     * que muestra sus zonas pero no tiene posicion todavia). */
    valor: number | null
    max: number
    min?: number
    /** Valor que tendra tras la resolucion de la noche; se dibuja como
     * corchete discontinuo. null/undefined = no hay prevision. */
    previsto?: number | null
    bandas?: BandaPista[]
    etiqueta?: string
    /** Lectura de la derecha. Por defecto "valor/max". '' la oculta. */
    lectura?: string
    /** 'nivel' rellena desde el minimo (vitalidad, acidez); 'posicion' solo
     * marca el punto (fermentacion, precio). */
    modo?: 'nivel' | 'posicion'
    tono?: Tono
    /** Tono del corchete previsto, si debe diferir del actual (p. ej. la
     * fermentacion proyectada cae en zona de colapso). */
    tonoPrevisto?: Tono | null
    compacta?: boolean
  }>(),
  {
    min: 0,
    previsto: null,
    bandas: () => [],
    etiqueta: '',
    lectura: undefined,
    modo: 'nivel',
    tono: 'cobre',
    tonoPrevisto: null,
    compacta: false,
  },
)

const recorrido = computed(() => Math.max(1, props.max - props.min))

function pct(v: number): number {
  const acotado = Math.min(props.max, Math.max(props.min, v))
  return ((acotado - props.min) / recorrido.value) * 100
}

/** Una marca por paso en escalas cortas; cada 5 en las largas (1-20). */
const pasoTick = computed(() => (recorrido.value <= 8 ? 1 : 5))
const ticks = computed(() => {
  const ms: number[] = []
  for (let v = props.min; v <= props.max; v += pasoTick.value) ms.push(v)
  return ms
})

const colorPrevisto = computed(() => (props.tonoPrevisto ? VAR_TONO[props.tonoPrevisto] : undefined))

const lecturaFinal = computed(() => {
  if (props.lectura !== undefined) return props.lectura
  return props.valor === null ? '' : `${props.valor}/${props.max}`
})
</script>

<template>
  <div class="pista-medida" :class="[modo, `tono-${tono}`, { compacta }]">
    <span v-if="etiqueta" class="eyebrow etiqueta">{{ etiqueta }}</span>

    <div
      class="carril"
      role="img"
      :aria-label="`${etiqueta || 'Medida'}: ${valor ?? '—'} de ${max}${previsto !== null ? `, previsto ${previsto}` : ''}`"
    >
      <span
        v-for="(b, i) in bandas"
        :key="`b${i}`"
        class="banda"
        :class="`banda-${b.tono}`"
        :style="{ left: `${pct(b.desde)}%`, width: `${pct(b.hasta) - pct(b.desde)}%` }"
      />

      <span v-for="t in ticks" :key="`t${t}`" class="tick" :style="{ left: `${pct(t)}%` }" />

      <span v-if="modo === 'nivel' && valor !== null" class="relleno" :style="{ width: `${pct(valor)}%` }" />

      <span
        v-if="previsto !== null && previsto !== valor"
        class="corchete previsto"
        :style="{ left: `${pct(previsto)}%`, borderLeftColor: colorPrevisto }"
      />
      <span v-if="valor !== null" class="corchete actual" :style="{ left: `${pct(valor)}%` }" />
    </div>

    <span v-if="lecturaFinal" class="lectura dato">{{ lecturaFinal }}</span>
  </div>
</template>

<style scoped>
.pista-medida {
  display: grid;
  grid-template-columns: var(--ancho-etiqueta, 4.5rem) 1fr auto;
  align-items: center;
  gap: var(--e2);
  /* El color del corchete/relleno lo fija .tono-*; asi una misma pista puede
     ponerse en rojo cuando el valor es de riesgo sin duplicar reglas. */
  --tono-pista: var(--cobre);
}

.pista-medida:not(:has(.etiqueta)) {
  grid-template-columns: 1fr auto;
}

.tono-vital {
  --tono-pista: var(--vital);
}
.tono-riesgo {
  --tono-pista: var(--riesgo);
}
.tono-frio {
  --tono-pista: var(--frio);
}
.tono-verdin {
  --tono-pista: var(--verdin);
}

.etiqueta {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.carril {
  position: relative;
  height: 10px;
  background: var(--mesa);
  border: 1px solid var(--borde);
  border-radius: 2px;
  /* Los corchetes sobresalen por arriba y por abajo, como la aguja de un
     instrumento sobre su regla. */
  overflow: visible;
}

.compacta .carril {
  height: 6px;
}

.banda {
  position: absolute;
  inset-block: 0;
  border-radius: 1px;
}

.banda-baja {
  background: rgba(162, 145, 124, 0.18);
}
.banda-optima {
  background: var(--lavado-vital);
}
.banda-sobre {
  background: var(--lavado-riesgo);
}
.banda-neutra {
  background: rgba(162, 145, 124, 0.1);
}

.tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--borde);
  transform: translateX(-0.5px);
}

.relleno {
  position: absolute;
  inset-block: 0;
  left: 0;
  background: var(--tono-pista);
  opacity: 0.5;
  border-radius: 1px;
}

/* La aguja: solida = ahora, discontinua = como quedara esta noche. */
.corchete {
  position: absolute;
  top: -3px;
  bottom: -3px;
  width: 2px;
  transform: translateX(-1px);
  background: var(--tono-pista);
  border-radius: 1px;
}

.corchete.previsto {
  background: none;
  border-left: 2px dashed var(--tono-pista);
  opacity: 0.75;
  width: 0;
}

.lectura {
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
</style>
