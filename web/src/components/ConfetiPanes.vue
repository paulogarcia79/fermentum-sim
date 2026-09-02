<script setup lang="ts">
// Lluvia de panes sobre la pantalla de resultados, solo para quien gana.
//
// Tres decisiones que conviene no deshacer sin querer:
//
//  - Es @keyframes de CSS, no un bucle de requestAnimationFrame sobre un
//    <canvas>. La regla global de App.vue (`prefers-reduced-motion`) anula
//    toda `animation-duration`, asi que el confeti se respeta solo; un bucle en
//    JS quedaria fuera de esa red y tendria que consultar matchMedia a mano.
//    Ademas asi se reutiliza IconoPan tal cual, sin rasterizar nada.
//  - Se teletransporta a <body> por el mismo motivo que los modales y los
//    tooltips: cada `.region` de GameView es un contenedor con overflow, y una
//    capa nacida dentro de una de ellas quedaria recortada.
//  - Dura una pasada y se desmonta. Es una celebracion, no un ambiente: quien
//    gana tambien quiere leer el desglose de puntuacion sin panes cayendole
//    por encima.
import { onMounted, onUnmounted, ref } from 'vue'
import IconoPan from './IconoPan.vue'

// Solo las recetas con silueta propia en IconoPan.vue. El catalogo tiene 12,
// pero 4 caen en la elipse generica: incluirlas seria repetir el mismo pan
// anodino un tercio de las veces.
const RECETAS_CON_SILUETA = [
  'pan_de_campo',
  'focaccia',
  'baguette',
  'pizza_napolitana',
  'brioche',
  'hogaza_centeno',
  'pan_semillas',
  'panettone',
] as const

const NUM_PIEZAS = 40
const RETRASO_MAX = 2.5
const CAIDA_MAX = 4.5

interface Pieza {
  id: string
  clase: string
  estilo: Record<string, string>
}

function aleatorio(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

// Se generan una sola vez, en el setup: si fueran reactivas y se recalcularan,
// cada pieza saltaria de sitio a mitad de caida.
const piezas: Pieza[] = Array.from({ length: NUM_PIEZAS }, (_, i) => {
  const retraso = aleatorio(0, RETRASO_MAX)
  const duracion = aleatorio(3, CAIDA_MAX)
  return {
    id: RECETAS_CON_SILUETA[i % RECETAS_CON_SILUETA.length],
    // Dos tamaños de la escala de iconos ya existente en vez de un px suelto.
    clase: Math.random() < 0.5 ? 'ico-m' : 'ico-l',
    estilo: {
      left: `${aleatorio(0, 100)}vw`,
      '--retraso': `${retraso}s`,
      '--duracion': `${duracion}s`,
      '--deriva': `${aleatorio(-12, 12)}vw`,
      '--giro': `${(Math.random() < 0.5 ? -1 : 1) * aleatorio(360, 900)}deg`,
    },
  }
})

// Un poco de margen sobre el ultimo pan en llegar al suelo.
const MS_TOTAL = (RETRASO_MAX + CAIDA_MAX + 0.3) * 1000

const activo = ref(true)
let temporizador: number | undefined

onMounted(() => {
  temporizador = window.setTimeout(() => {
    activo.value = false
  }, MS_TOTAL)
})

onUnmounted(() => {
  if (temporizador !== undefined) window.clearTimeout(temporizador)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="activo" class="confeti-panes" aria-hidden="true">
      <div
        v-for="(pieza, i) in piezas"
        :key="i"
        class="pieza"
        :class="pieza.clase"
        :style="pieza.estilo"
      >
        <IconoPan :id="pieza.id" />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.confeti-panes {
  position: fixed;
  inset: 0;
  overflow: hidden;
  /* Nunca se interpone: la tabla de resultados y sus botones siguen debajo y
     siguen siendo clicables. */
  pointer-events: none;
  /* Por debajo del velo de los modales (40) y de los modales obligatorios (50):
     el informe de Fase III de la ultima noche puede seguir pendiente. */
  z-index: 30;
}

.pieza {
  position: absolute;
  top: 0;
  animation: caer var(--duracion) linear var(--retraso) 1 forwards;
  /* Hasta que le toque su retraso, la pieza no debe verse quieta arriba. */
  opacity: 0;
}

@keyframes caer {
  0% {
    transform: translate3d(0, -12vh, 0) rotate(0deg);
    opacity: 0;
  }
  8% {
    opacity: 1;
  }
  85% {
    opacity: 1;
  }
  100% {
    transform: translate3d(var(--deriva), 108vh, 0) rotate(var(--giro));
    opacity: 0;
  }
}
</style>
