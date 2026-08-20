<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'

const env = computed(() => store.estado!.environment)
const avanceBase = computed(() => Math.floor(env.value.temperatura_actual / 5))
</script>

<template>
  <section class="panel clima-banner">
    <div class="dato">
      <span class="etiqueta">Día</span>
      <span class="valor">{{ env.dia_actual }}</span>
    </div>
    <div class="dato">
      <span class="etiqueta">Temperatura</span>
      <span class="valor">{{ env.temperatura_actual }}°C</span>
    </div>
    <div class="dato">
      <span class="etiqueta">Avance base</span>
      <span class="valor">{{ avanceBase }} casillas</span>
    </div>
    <div class="dato carta" v-if="env.ultima_carta_clima">
      <span class="etiqueta">Carta de clima</span>
      <span class="valor">{{ env.ultima_carta_clima.nombre }}</span>
    </div>
    <div class="dato">
      <span class="etiqueta">Cartas restantes</span>
      <span class="valor">{{ env.cartas_clima_restantes }}</span>
    </div>
    <div class="dato" v-if="env.efecto_pasivo_activo !== 'Ninguno'">
      <span class="etiqueta">Efecto pasivo</span>
      <span class="valor efecto">{{ env.efecto_pasivo_activo }}</span>
    </div>
  </section>
</template>

<style scoped>
.clima-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
}

.dato {
  display: flex;
  flex-direction: column;
}

.etiqueta {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-texto-tenue);
}

.valor {
  font-size: 1.1rem;
  font-weight: 600;
}

.valor.efecto {
  color: var(--color-acento);
}

.carta {
  flex: 1 1 auto;
}
</style>
