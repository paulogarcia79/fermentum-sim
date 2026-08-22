<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import RecetaDetalle from './RecetaDetalle.vue'

const mercado = computed(() => store.estado!.market)
</script>

<template>
  <section class="panel mercado">
    <h3>Mercado Central</h3>

    <div class="sub-titulo">Recetas ({{ mercado.mazo_recetas_restantes }} en el mazo)</div>
    <ul class="lista-recetas">
      <li v-for="(receta, i) in mercado.recetas_visibles" :key="i" class="slot">
        <template v-if="receta">
          <strong>{{ receta.nombre }}</strong>
          <span class="detalle">{{ receta.grado }} · {{ receta.harina_base }} · {{ receta.hidratacion_pct }}%</span>
          <span class="detalle">{{ receta.puntos_optimos }} pts óptimo</span>
          <RecetaDetalle :receta="receta" />
        </template>
        <template v-else><span class="vacio">— tomada —</span></template>
      </li>
    </ul>

    <div class="sub-titulo">Suministros</div>
    <ul class="lista-suministros">
      <li v-for="(lote, i) in mercado.suministros" :key="i" class="slot">
        <template v-if="lote">
          <span>B:{{ lote.recursos.Blanca }}% C:{{ lote.recursos.Centeno }}% I:{{ lote.recursos.Integral }}% A:{{ lote.recursos.agua }}%</span>
        </template>
        <template v-else><span class="vacio">— tomado —</span></template>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.mercado h3 {
  margin-top: 0;
}

.sub-titulo {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--color-texto-tenue);
  margin: 0.75rem 0 0.35rem;
}

.lista-recetas,
.lista-suministros {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.slot {
  background: var(--color-fondo);
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
}

.detalle {
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
}

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}
</style>
