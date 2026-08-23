<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import RecetaCard from './RecetaCard.vue'

const mercado = computed(() => store.estado!.market)
</script>

<template>
  <section class="panel mercado">
    <h3>Mercado Central</h3>

    <div class="sub-titulo">Recetas ({{ mercado.mazo_recetas_restantes }} en el mazo)</div>
    <ul class="lista-recetas">
      <li v-for="(receta, i) in mercado.recetas_visibles" :key="i" class="slot">
        <RecetaCard v-if="receta" :receta="receta" />
        <span v-else class="vacio">— tomada —</span>
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

.lista-recetas {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.lista-recetas .slot {
  flex: 1 1 260px;
  min-width: 240px;
  max-width: 320px;
}

.slot .vacio {
  display: block;
  padding: 0.4rem 0.5rem;
}

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}
</style>
