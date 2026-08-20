<script setup lang="ts">
import { computed } from 'vue'
import LobbyView from './components/LobbyView.vue'
import GameView from './components/GameView.vue'
import { store } from './store'

const enPartida = computed(() => store.sesion !== null && store.estado !== null)
</script>

<template>
  <main class="app-shell">
    <GameView v-if="enPartida" />
    <LobbyView v-else />
  </main>
</template>

<style>
:root {
  --color-fondo: #14110f;
  --color-panel: #1f1a16;
  --color-borde: #3a322a;
  --color-texto: #ede4d8;
  --color-texto-tenue: #a89a89;
  --color-acento: #d99a3f;
  --color-bien: #6fae5c;
  --color-mal: #c65a4b;
  --fuente: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--color-fondo);
  color: var(--color-texto);
  font-family: var(--fuente);
}

.app-shell {
  min-height: 100vh;
  padding: 1rem;
  max-width: 1100px;
  margin: 0 auto;
}

button {
  font-family: inherit;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.panel {
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 8px;
  padding: 1rem;
}

/* Estilos compartidos por los 11 modales de accion (BarraAcciones.vue) */
.campo {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-texto-tenue);
}

.campo select,
.campo input {
  display: block;
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.45rem;
  background: var(--color-fondo);
  border: 1px solid var(--color-borde);
  border-radius: 4px;
  color: var(--color-texto);
  font-size: 0.95rem;
}

.campo-checkbox {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
  font-size: 0.85rem;
}

.campo-checkbox input {
  width: auto;
}

.opciones-radio {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
}

.opciones-radio label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

button.confirmar {
  flex: 1;
  padding: 0.55rem;
  border-radius: 4px;
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}

button.secundario {
  flex: 1;
  padding: 0.55rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: var(--color-panel);
  color: var(--color-texto);
}

.info-linea {
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
  margin-bottom: 0.5rem;
}
</style>
