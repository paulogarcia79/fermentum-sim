<script setup lang="ts">
/**
 * Envoltorio que añade una ✕ flotante a un panel del tablero, como segundo
 * camino para ocultarlo sin ir al dock (DockPaneles.vue, que sigue siendo el
 * unico camino de vuelta).
 *
 * Es un wrapper y no una prop en cada panel a proposito: los nueve
 * componentes de panel siguen sin saber nada de esta funcionalidad de
 * disposicion. La ✕ va posicionada en absoluto sobre la esquina del
 * <section class="panel">; los tres paneles que ya tienen contenido alineado
 * a la derecha en su cabecera (Clima, Tendencias, MiTablero) reservan hueco
 * con un padding-right propio desde GameView.vue.
 */
defineProps<{ etiqueta: string }>()
defineEmits<{ ocultar: [] }>()
</script>

<template>
  <div class="envoltorio-panel">
    <slot />
    <button
      type="button"
      class="ocultar-panel"
      :title="`Ocultar ${etiqueta}`"
      :aria-label="`Ocultar ${etiqueta}`"
      @click="$emit('ocultar')"
    >
      ✕
    </button>
  </div>
</template>

<style scoped>
.envoltorio-panel {
  position: relative;
}

.ocultar-panel {
  position: absolute;
  top: var(--e1);
  right: var(--e1);
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--r-control);
  background: transparent;
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
  line-height: 1;
  opacity: 0;
  transition: opacity var(--transicion);
}

.envoltorio-panel:hover .ocultar-panel,
.ocultar-panel:focus-visible {
  opacity: 1;
}

.ocultar-panel:hover {
  border-color: var(--borde);
  color: var(--tinta);
}
</style>
