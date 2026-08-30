<script setup lang="ts">
// Overlay para ver la carta de receta completa desde una Estacion (que solo
// muestra la version compacta anidada, por espacio) -- mismas convenciones
// de overlay que PilaDescarteClimaModal.vue. acidezInicial/bonoSellado
// vienen de FermentationSlot (ver EstacionCard.vue), asi que aqui la Escala
// de Acidez muestra el Registro de pH real, no solo la diana objetivo.
import type { Recipe } from '../types'
import RecetaCard from './RecetaCard.vue'

defineProps<{
  receta: Recipe
  acidezInicial?: number | null
  bonoSellado?: boolean
}>()

const emit = defineEmits<{ cerrar: [] }>()
</script>

<template>
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <div class="fondo-modal" @click.self="emit('cerrar')">
      <div class="modal">
        <div class="cabecera-modal">
          <h2>Detalle de Receta</h2>
          <button type="button" class="cerrar" title="Cerrar" @click="emit('cerrar')">✕</button>
        </div>

        <RecetaCard :receta="receta" :acidez-inicial="acidezInicial" :bono-sellado="bonoSellado" />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: var(--velo-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: var(--e4);
}

.modal {
  max-width: 360px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
}

.cabecera-modal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--e2);
}

.cabecera-modal h2 {
  margin: 0;
  font-size: var(--t-l);
}

.cerrar {
  background: none;
  border: none;
  color: var(--tinta-tenue);
  font-size: var(--t-l);
  padding: var(--e1) var(--e2);
}

.cerrar:hover {
  color: var(--tinta);
}
</style>
