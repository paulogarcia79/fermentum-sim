<script setup lang="ts">
// Peón (meeple) de jugador, coloreado con el color de mesa del jugador --
// mismo patrón que IconoHarina.vue (prop + fill). El color se pasa ya
// resuelto a hex (hexDeColor(p.color)) para no acoplar este icono al
// catálogo de colores.
defineProps<{ color: string }>()
</script>

<template>
  <svg viewBox="0 0 24 24" class="icono-peon" aria-hidden="true">
    <path
      d="M12 2a3 3 0 0 0-2.4 4.8C7 7.6 5 9 3.5 11.2c-.6.9.1 2 1.2 2 .9 0 3.6-.3 4.6-1.6-.4 1.7-2 5.6-3.3 7.6-.6.9.1 2.1 1.2 2.1h1.9c.9 0 1.7-.6 1.9-1.5l1-3.8 1 3.8c.2.9 1 1.5 1.9 1.5h1.9c1.1 0 1.8-1.2 1.2-2.1-1.3-2-2.9-5.9-3.3-7.6 1 1.3 3.7 1.6 4.6 1.6 1.1 0 1.8-1.1 1.2-2C19 9 17 7.6 14.4 6.8A3 3 0 0 0 12 2z"
      :fill="color"
      stroke="rgba(0, 0, 0, 0.35)"
      stroke-width="0.6"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.icono-peon {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
