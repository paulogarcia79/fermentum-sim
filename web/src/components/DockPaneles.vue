<script setup lang="ts">
/**
 * Fichas para mostrar/ocultar cada modulo del tablero.
 *
 * Viven en la cabecera (GameView.vue) y no flotando sobre el tablero: desde
 * que la partida cabe en una pantalla sin scroll, un raíl flotante era cromo
 * redundante -- no hay nada de lo que "sobrevivir" al hacer scroll.
 *
 * Las fichas NO se pueden ocultar y hay un "Restaurar todos": la preferencia
 * se guarda para siempre, asi que tiene que existir un camino de vuelta desde
 * cualquier estado.
 */
import { computed } from 'vue'
import { alternarPanel, restaurarPaneles, store } from '../store'
import { PANELES, type IdPanel } from '../data/panelesTablero'

const ocultos = computed(() => store.preferencias.panelesOcultos)
function visible(id: IdPanel): boolean {
  return !ocultos.value.includes(id)
}
const hayOcultos = computed(() => ocultos.value.length > 0)
</script>

<template>
  <div class="fichas" role="group" aria-label="Mostrar u ocultar paneles">
    <button
      v-for="panel in PANELES"
      :key="panel.id"
      type="button"
      class="ficha"
      :class="{ apagada: !visible(panel.id) }"
      :aria-pressed="visible(panel.id)"
      :aria-label="visible(panel.id) ? `Ocultar ${panel.etiqueta}` : `Mostrar ${panel.etiqueta}`"
      :title="visible(panel.id) ? `Ocultar ${panel.etiqueta}` : `Mostrar ${panel.etiqueta}`"
      @click="alternarPanel(panel.id)"
    >
      {{ panel.icono }}
    </button>

    <button
      type="button"
      class="ficha restaurar"
      :disabled="!hayOcultos"
      title="Restaurar todos los paneles"
      aria-label="Restaurar todos los paneles"
      @click="restaurarPaneles()"
    >
      ⟳
    </button>
  </div>
</template>

<style scoped>
.fichas {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--mesa);
}

.ficha {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  color: var(--tinta);
  font-size: var(--t-xs);
  line-height: 1;
  transition: border-color var(--transicion), opacity var(--transicion);
}

.ficha:hover:not(:disabled) {
  border-color: var(--cobre);
}

.ficha.apagada {
  opacity: 0.28;
  filter: grayscale(1);
}

.restaurar {
  color: var(--tinta-tenue);
  border-left: 1px solid var(--borde);
  border-radius: 0 3px 3px 0;
}
</style>
