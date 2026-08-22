<script setup lang="ts">
// Desglose completo de una receta -- requisitos, bono de sabor, y puntos por
// cada zona del track. <details> en vez de un tooltip por hover (como
// BarraAcciones.vue) porque este contenido es mas largo/multilinea y debe
// funcionar en pantallas tactiles, donde :hover no sirve.
import { computed } from 'vue'
import type { Recipe } from '../types'

const props = defineProps<{ receta: Recipe }>()

const centroExacto = computed(() =>
  Math.floor((props.receta.zona_optima[0] + props.receta.zona_optima[1]) / 2),
)
</script>

<template>
  <details class="detalle-receta">
    <summary>Detalles ▾</summary>
    <dl>
      <div>
        <dt>Requiere</dt>
        <dd>
          1 Harina {{ receta.harina_base }} (100%) + {{ receta.tokens_agua }} tokens de Agua
          ({{ receta.hidratacion_pct }}% hidratación)
          <template v-if="receta.req_tecnologico">· Requiere {{ receta.req_tecnologico }}</template>
        </dd>
      </div>
      <div>
        <dt>Bono de sabor</dt>
        <dd>Acidez ∈ {{ receta.acidez_diana.join(', ') }} al iniciar → +{{ receta.bono_sabor_pts }} pts</dd>
      </div>
      <div>
        <dt>Zona Baja</dt>
        <dd>
          {{ receta.zona_baja[0] }}–{{ receta.zona_baja[1] }} →
          {{ receta.puntos_zona_baja ?? '?' }} pts
        </dd>
      </div>
      <div>
        <dt>Zona Óptima</dt>
        <dd>
          {{ receta.zona_optima[0] }}–{{ receta.zona_optima[1] }} → {{ receta.puntos_optimos }} pts
          · +1 Dato (centro exacto {{ centroExacto }}: +1 Dato extra con Módulo Analítico)
        </dd>
      </div>
      <div>
        <dt>Sobrefermentada</dt>
        <dd>desde {{ receta.zona_sobrefermentada[0] }} → colapso, {{ receta.penalizacion_colapso }} pts</dd>
      </div>
    </dl>
  </details>
</template>

<style scoped>
.detalle-receta {
  margin-top: 0.3rem;
  font-size: 0.75rem;
}

.detalle-receta summary {
  cursor: pointer;
  color: var(--color-texto-tenue);
  user-select: none;
}

.detalle-receta summary:hover {
  color: var(--color-texto);
}

.detalle-receta dl {
  margin: 0.4rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detalle-receta dl div {
  display: flex;
  gap: 0.4rem;
}

.detalle-receta dt {
  flex: 0 0 auto;
  min-width: 5.5rem;
  color: var(--color-texto-tenue);
  font-weight: 600;
}

.detalle-receta dd {
  margin: 0;
  color: var(--color-texto);
}
</style>
