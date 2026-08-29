<script setup lang="ts">
// Overlay para hojear toda la pila de descarte de clima (no solo la ultima
// carta) -- mismas convenciones de overlay que InicioDiaModal.vue.
// descarte_clima ya llega sin redactar desde server/views.py (es
// informacion publica), asi que no hace falta ningun endpoint nuevo.
import { computed } from 'vue'
import { store } from '../store'
import CartaClima from './CartaClima.vue'

const emit = defineEmits<{ cerrar: [] }>()

// descarte_clima incluye la carta activa (ver MazoClimaPanel.vue) -- se
// excluye la ultima entrada para no listar la carta de hoy como "descartada".
const descarte = computed(() => store.estado!.environment.descarte_clima.slice(0, -1).reverse())
</script>

<template>
  <div class="fondo-modal" @click.self="emit('cerrar')">
    <div class="modal panel">
      <div class="cabecera-modal">
        <h2>Pila de Descarte — Clima</h2>
        <button type="button" class="cerrar" title="Cerrar" @click="emit('cerrar')">✕</button>
      </div>

      <p v-if="descarte.length === 0" class="vacio">Todavía no se ha descartado ninguna carta.</p>
      <div v-else class="grilla">
        <CartaClima v-for="(carta, i) in descarte" :key="carta.id + '-' + i" :carta="carta" compacta />
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
