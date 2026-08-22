<script setup lang="ts">
// Espiga de trigo, coloreada segun el tipo de harina -- un solo icono
// compartido diferenciado por color en vez de 3 siluetas distintas, ya que
// la cantidad/tipo ya se distingue por texto junto al icono.
import { computed } from 'vue'
import type { TipoHarina } from '../types'

const props = defineProps<{ tipo: TipoHarina }>()

const COLOR: Record<TipoHarina, string> = {
  Blanca: '#e8ddc2',
  Centeno: '#8a5a35',
  Integral: '#b8834a',
}

const color = computed(() => COLOR[props.tipo])
</script>

<template>
  <svg viewBox="0 0 24 24" class="icono-harina" aria-hidden="true">
    <path d="M12 21 L12 5" stroke="#7a4f22" stroke-width="1" stroke-linecap="round" />
    <ellipse cx="12" cy="5.5" rx="1.3" ry="1.9" :fill="color" stroke="#7a4f22" stroke-width="0.4" />
    <ellipse cx="9.7" cy="8" rx="1.3" ry="1.9" :fill="color" stroke="#7a4f22" stroke-width="0.4" transform="rotate(-25 9.7 8)" />
    <ellipse cx="14.3" cy="8" rx="1.3" ry="1.9" :fill="color" stroke="#7a4f22" stroke-width="0.4" transform="rotate(25 14.3 8)" />
    <ellipse cx="9.7" cy="11.5" rx="1.3" ry="1.9" :fill="color" stroke="#7a4f22" stroke-width="0.4" transform="rotate(-25 9.7 11.5)" />
    <ellipse cx="14.3" cy="11.5" rx="1.3" ry="1.9" :fill="color" stroke="#7a4f22" stroke-width="0.4" transform="rotate(25 14.3 11.5)" />
  </svg>
</template>

<style scoped>
.icono-harina {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
