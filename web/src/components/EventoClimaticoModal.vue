<script setup lang="ts">
// Modal obligatorio al inicio de cada dia, explicando la carta de clima
// recien revelada y sus efectos concretos -- mismo tratamiento que
// FermentationReportModal.vue le da a los colapsos: algo que se le dice
// explicitamente al jugador, no algo que tenga que notar por su cuenta en
// el panel de MazoClimaPanel.vue. A diferencia de ese modal, este se arma a
// partir del estado actual (no del registro de eventos), ya que
// environment.ultima_carta_clima siempre refleja la carta de "hoy". La
// carta se muestra con CartaClima.vue (el mismo componente del mazo/pila de
// descarte) para que el jugador la reconozca visualmente; la lista debajo
// da los numeros concretos que la carta sola no transmite.
import { computed } from 'vue'
import { reconocerClima, store } from '../store'
import { efectoBiologicoTexto as bioTexto, efectoPasivoTexto as pasivoTexto } from '../climaTexto'
import CartaClima from './CartaClima.vue'

const env = computed(() => store.estado!.environment)
const carta = computed(() => env.value.ultima_carta_clima!)
const avanceBase = computed(() => Math.floor(env.value.temperatura_actual / 5))

const efectoBiologicoTexto = computed(() => bioTexto(carta.value))
const efectoPasivoTexto = computed(() => pasivoTexto(carta.value) ?? 'Ninguno — desgaste y costos normales hoy.')
</script>

<template>
  <div class="fondo-modal">
    <div class="modal panel">
      <h2>🌦️ Evento Climático — Día {{ env.dia_actual }}</h2>

      <div class="carta-envoltorio">
        <CartaClima :carta="carta" />
      </div>

      <ul class="lista">
        <li>
          Modificador térmico: {{ carta.modificador_termico >= 0 ? '+' : '' }}{{ carta.modificador_termico }}°C →
          Temperatura hoy: {{ env.temperatura_actual }}°C
        </li>
        <li>Avance base de fermentación hoy: {{ avanceBase }} casillas (antes del dado de inóculo y la incubadora)</li>
        <li v-if="efectoBiologicoTexto">🧪 {{ efectoBiologicoTexto }}</li>
        <li>⚙️ Efecto pasivo vigente: {{ efectoPasivoTexto }}</li>
      </ul>

      <button class="primario" @click="reconocerClima">Entendido</button>
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
  max-width: 480px;
  width: 100%;
}

.modal h2 {
  margin-top: 0;
}

.carta-envoltorio {
  display: flex;
  justify-content: center;
  margin-bottom: 0.75rem;
}

.lista {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.88rem;
}

button.primario {
  width: 100%;
  padding: 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}
</style>
