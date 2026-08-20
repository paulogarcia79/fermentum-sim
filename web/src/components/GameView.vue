<script setup lang="ts">
import { computed, onUnmounted } from 'vue'
import { detenerTransmisionEnVivo, store } from '../store'
import ClimaBanner from './ClimaBanner.vue'
import MercadoPanel from './MercadoPanel.vue'
import MiTablero from './MiTablero.vue'
import TablerosOponentes from './TablerosOponentes.vue'
import BarraAcciones from './BarraAcciones.vue'
import RegistroEventos from './RegistroEventos.vue'
import FermentationReportModal from './FermentationReportModal.vue'
import RankingView from './RankingView.vue'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)
const esMiTurno = computed(() => estado.value.jugador_en_turno_idx === miIndice.value)

onUnmounted(() => detenerTransmisionEnVivo())
</script>

<template>
  <div class="game-view">
    <header class="cabecera">
      <h1>🍞 Fermentum — Sala {{ store.sesion?.roomId }}</h1>
      <p class="turno-indicador" :class="{ 'mi-turno': esMiTurno }">
        <template v-if="estado.partida_terminada">La partida ha terminado.</template>
        <template v-else-if="esMiTurno">Es tu turno.</template>
        <template v-else-if="estado.jugador_en_turno_idx !== null">
          Turno de {{ estado.players[estado.jugador_en_turno_idx].nombre }}…
        </template>
        <template v-else>Resolviendo fin de día…</template>
      </p>
    </header>

    <p v-if="store.error" class="error">⚠ {{ store.error }}</p>

    <RankingView v-if="estado.partida_terminada" />

    <template v-else>
      <ClimaBanner />

      <div class="columnas">
        <div class="columna-principal">
          <MiTablero />
          <BarraAcciones v-if="esMiTurno" />
          <p v-else class="espera">Esperando tu turno…</p>
        </div>

        <div class="columna-lateral">
          <MercadoPanel />
          <TablerosOponentes />
          <RegistroEventos />
        </div>
      </div>
    </template>

    <FermentationReportModal v-if="store.reporteDiaPendiente !== null" />
  </div>
</template>

<style scoped>
.cabecera h1 {
  margin-bottom: 0.1rem;
  font-size: 1.4rem;
}

.turno-indicador {
  color: var(--color-texto-tenue);
  margin-top: 0;
}

.turno-indicador.mi-turno {
  color: var(--color-acento);
  font-weight: 600;
}

.error {
  color: var(--color-mal);
  background: rgba(198, 90, 75, 0.12);
  border: 1px solid var(--color-mal);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}

.columnas {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  align-items: start;
}

.columna-principal,
.columna-lateral {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.espera {
  color: var(--color-texto-tenue);
  font-style: italic;
}

@media (max-width: 800px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}
</style>
