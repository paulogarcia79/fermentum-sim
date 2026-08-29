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
  <div class="fondo-modal" @click.self="emit('cerrar')">
    <div class="modal panel">
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

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}

.grilla {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  overflow-y: auto;
  padding-bottom: 0.2rem;
}
</style>
