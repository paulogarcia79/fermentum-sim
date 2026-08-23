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
  <div class="fondo-modal" @click.self="emit('cerrar')">
    <div class="modal panel">
      <div class="cabecera-modal">
        <h2>Detalle de Receta</h2>
        <button type="button" class="cerrar" title="Cerrar" @click="emit('cerrar')">✕</button>
      </div>

      <RecetaCard :receta="receta" :acidez-inicial="acidezInicial" :bono-sellado="bonoSellado" />
    </div>
  </div>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 1rem;
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
  margin-bottom: 0.5rem;
}

.cabecera-modal h2 {
  margin: 0;
  font-size: 1.05rem;
}

.cerrar {
  background: none;
  border: none;
  color: var(--color-texto-tenue);
  font-size: 1.1rem;
  padding: 0.2rem 0.4rem;
}

.cerrar:hover {
  color: var(--color-texto);
}
</style>
