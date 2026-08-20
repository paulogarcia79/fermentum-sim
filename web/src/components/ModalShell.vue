<script setup lang="ts">
defineProps<{ titulo: string; error?: string | null; enviando?: boolean }>()
const emit = defineEmits<{ cerrar: [] }>()
</script>

<template>
  <div class="fondo-modal" @click.self="emit('cerrar')">
    <div class="modal panel">
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
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
  padding: 1rem;
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
  margin-bottom: 0.75rem;
}

.cabecera-modal h3 {
  margin: 0;
}

.cerrar {
  background: none;
  border: none;
  color: var(--color-texto-tenue);
  font-size: 1.1rem;
  padding: 0 0.25rem;
}

.error-modal {
  color: var(--color-mal);
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.pie-modal {
  margin-top: 1rem;
  display: flex;
  gap: 0.5rem;
}
</style>
