<script setup lang="ts">
// Sustituye a ClimaBanner.vue -- ademas de las estadisticas de
// Dia/Temperatura/Avance base (ahora una linea compacta), el clima se
// presenta como un mazo fisico real: pila de descarte boca-arriba y
// hojeable (descarte_clima ya llega sin redactar, ver server/views.py) a la
// izquierda, mazo boca-abajo (solo el conteo es publico,
// cartas_clima_restantes) en el medio, y la carta revelada de hoy a tamaño
// completo a la derecha.
import { computed, ref } from 'vue'
import { store } from '../store'
import CartaClima from './CartaClima.vue'
import PilaDescarteClimaModal from './PilaDescarteClimaModal.vue'

const env = computed(() => store.estado!.environment)
const avanceBase = computed(() => Math.floor(env.value.temperatura_actual / 5))

// descarte_clima incluye la carta activa (engine.py la agrega al robarla,
// antes de asignarla a ultima_carta_clima) -- la pila de descarte "real"
// (cartas ya reemplazadas) es todo menos la ultima entrada.
const descarte = computed(() => env.value.descarte_clima.slice(0, -1))
const topeDescarte = computed(() => descarte.value.slice(-3))

const pilaDescarteAbierta = ref(false)
</script>

<template>
  <section class="panel mazo-clima">
    <div class="cabecera-mazo">
      <h3>Clima</h3>
      <div class="stats">
        <span>Día {{ env.dia_actual }}</span>
        <span>{{ env.temperatura_actual }}°C</span>
        <span>Avance base: {{ avanceBase }} casillas</span>
        <span v-if="env.efecto_pasivo_activo !== 'ninguno'" class="efecto-activo">{{ env.efecto_pasivo_activo }}</span>
      </div>
    </div>

    <div class="fila-mazo">
      <button
        type="button"
        class="pila pila-descarte"
        :disabled="descarte.length === 0"
        :title="descarte.length ? 'Ver toda la pila de descarte' : 'Todavía no hay cartas descartadas'"
        @click="pilaDescarteAbierta = true"
      >
        <div class="abanico">
          <CartaClima v-if="descarte.length === 0" compacta boca-abajo class="carta-abanico" style="--offset: 0" />
          <CartaClima
            v-for="(carta, i) in topeDescarte"
            :key="carta.id + '-' + i"
            :carta="carta"
            compacta
            class="carta-abanico"
            :style="{ '--offset': i }"
          />
        </div>
        <span class="etiqueta-pila">Descarte ({{ descarte.length }})</span>
      </button>

      <div class="pila mazo-boca-abajo">
        <div class="abanico">
          <CartaClima v-for="n in 3" :key="n" compacta boca-abajo class="carta-abanico" :style="{ '--offset': n - 1 }" />
        </div>
        <span class="etiqueta-pila">Mazo ({{ env.cartas_clima_restantes }})</span>
      </div>

      <div class="pila carta-revelada">
        <CartaClima :carta="env.ultima_carta_clima" />
        <span class="etiqueta-pila">Carta de hoy</span>
      </div>
    </div>

    <PilaDescarteClimaModal v-if="pilaDescarteAbierta" @cerrar="pilaDescarteAbierta = false" />
  </section>
</template>

<style scoped>
.mazo-clima h3 {
  margin: 0;
}

.cabecera-mazo {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem 1rem;
  margin-bottom: 0.75rem;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.9rem;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
}

.efecto-activo {
  color: var(--color-acento);
  font-weight: 600;
}

.fila-mazo {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1.5rem;
}

.pila {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  background: none;
  border: none;
  padding: 0;
  color: inherit;
}

.pila-descarte {
  cursor: pointer;
}

.pila-descarte:hover:not(:disabled) .carta-abanico {
  filter: brightness(1.1);
}

.abanico {
  position: relative;
  width: calc(108px + 2 * 12px);
  height: calc(148px + 2 * 6px);
}

.carta-abanico {
  position: absolute;
  left: calc(var(--offset) * 12px);
  top: calc((2 - var(--offset)) * 6px);
  transform: rotate(calc((var(--offset) - 1) * 4deg));
  transition: filter 0.15s ease;
}

.carta-revelada {
  margin-left: 0.5rem;
}

.etiqueta-pila {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-texto-tenue);
}

@media (max-width: 640px) {
  .fila-mazo {
    justify-content: center;
  }
}
</style>
