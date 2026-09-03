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
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <div class="fondo-modal" @click.self="emit('cerrar')">
      <div class="modal">
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
