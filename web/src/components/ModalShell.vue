<script setup lang="ts">
defineProps<{ titulo: string; error?: string | null; enviando?: boolean }>()
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
          <h3>{{ titulo }}</h3>
          <button class="cerrar" @click="emit('cerrar')">✕</button>
        </div>
        <slot />
        <p v-if="error" class="error-modal">⚠ {{ error }}</p>
        <div class="pie-modal">
          <slot name="acciones" />
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
  z-index: 40;
  padding: var(--e4);
}

.modal {
  max-width: 420px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
}

.cabecera-modal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--e3);
}

.cabecera-modal h3 {
  margin: 0;
}

.cerrar {
  background: none;
  border: none;
  color: var(--tinta-tenue);
  font-size: var(--t-l);
  padding: 0 var(--e1);
}

.error-modal {
  color: var(--riesgo);
  font-size: var(--t-s);
  margin-top: var(--e2);
}

.pie-modal {
  margin-top: var(--e4);
  display: flex;
  gap: var(--e2);
}
</style>
