<script setup lang="ts">
// Aviso al resto de jugadores cuando alguien pide terminar la partida antes
// de tiempo (POST /games/{id}/confirm-end). Mismo tratamiento de modal
// obligatorio que EventoClimaticoModal.vue: se arma desde el estado actual
// (store.estado.votos_fin_anticipado), no del registro de eventos, y lo
// gobierna un flag del store (store.finAnticipadoPendiente) con un guard no
// reactivo -- ver store.ts. A diferencia de los otros modales obligatorios
// tiene dos botones: confirmar el fin (emite el voto de este jugador) o
// "Ahora no" (descarta el aviso; sigue disponible el boton de la tira gris
// en GameView.vue).
import { computed, ref } from 'vue'
import { confirmarFinAnticipado, reconocerFinAnticipado, store } from '../store'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)

const nombresSolicitantes = computed(() =>
  estado.value.votos_fin_anticipado
    .filter((i) => i !== miIndice.value)
    .map((i) => estado.value.players[i]?.nombre ?? `Jugador ${i + 1}`),
)
const totalJugadores = computed(() => estado.value.players.length)
const votosActuales = computed(() => estado.value.votos_fin_anticipado.length)
const seréElÚltimo = computed(() => votosActuales.value === totalJugadores.value - 1)

const enviando = ref(false)
async function onConfirmar() {
  enviando.value = true
  try {
    await confirmarFinAnticipado()
    store.finAnticipadoPendiente = false
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="fondo-modal">
    <div class="modal panel">
      <h2>🏁 ¿Terminar la partida antes de tiempo?</h2>

      <p class="solicitud">
        <template v-if="nombresSolicitantes.length === 1">
          <strong>{{ nombresSolicitantes[0] }}</strong> pidió terminar la partida antes de tiempo.
        </template>
        <template v-else>
          <strong>{{ nombresSolicitantes.join(', ') }}</strong> pidieron terminar la partida antes de tiempo.
        </template>
      </p>

      <ul class="lista">
        <li>{{ votosActuales }}/{{ totalJugadores }} jugadores han confirmado.</li>
        <li v-if="seréElÚltimo" class="aviso-ultimo">
          Si confirmas, la partida terminará de inmediato y se mostrará el ranking final.
        </li>
        <li v-else>La partida terminará cuando todos los jugadores confirmen.</li>
      </ul>

      <div class="acciones">
        <button class="secundario" :disabled="enviando" @click="reconocerFinAnticipado">Ahora no</button>
        <button class="primario" :disabled="enviando" @click="onConfirmar">Confirmar fin de partida</button>
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
  max-width: 460px;
  width: 100%;
}

.modal h2 {
  margin-top: 0;
}

.solicitud {
  margin: 0 0 0.75rem;
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

.aviso-ultimo {
  color: var(--color-acento);
}

.acciones {
  display: flex;
  gap: 0.6rem;
}

.acciones button {
  flex: 1;
  padding: 0.6rem;
  border-radius: 4px;
  font-weight: 600;
}

button.primario {
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
}

button.secundario {
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto-tenue);
}

button.secundario:hover:not(:disabled) {
  border-color: var(--color-texto);
  color: var(--color-texto);
}
</style>
