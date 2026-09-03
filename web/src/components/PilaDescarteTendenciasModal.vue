<script setup lang="ts">
// Overlay para hojear toda la pila de descarte de Tendencias de Mercado --
// mismas convenciones que PilaDescarteClimaModal.vue. descarte_tendencias ya
// llega sin redactar desde server/views.py (es informacion publica).
import { computed } from 'vue'
import { store } from '../store'
import CartaTendencia from './CartaTendencia.vue'

const emit = defineEmits<{ cerrar: [] }>()

// `descarte_tendencias` ya solo contiene cartas APLICADAS -- la revelada hoy
// esta en `tendencia_pendiente` y no aqui, asi que se listan todas (la mas
// reciente primero).
const descarte = computed(() => [...store.estado!.market.descarte_tendencias].reverse())
</script>

<template>
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <div class="fondo-modal" @click.self="emit('cerrar')">
      <div class="modal">
        <div class="cabecera-modal">
          <h2>Pila de Descarte — Tendencias</h2>
          <button type="button" class="cerrar" title="Cerrar" @click="emit('cerrar')">✕</button>
        </div>

        <p v-if="descarte.length === 0" class="vacio">Todavía no se ha descartado ninguna carta.</p>
        <div v-else class="grilla">
          <CartaTendencia v-for="(modificador, i) in descarte" :key="i" :modificador="modificador" compacta />
        </div>
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
  max-width: 560px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
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

.vacio {
  color: var(--tinta-tenue);
  font-style: italic;
}

.grilla {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  overflow-y: auto;
  padding-bottom: var(--e1);
}
</style>
