<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { detenerTransmisionEnVivo, forzarPase, store } from '../store'
import ClimaBanner from './ClimaBanner.vue'
import MercadoPanel from './MercadoPanel.vue'
import SuministrosPanel from './SuministrosPanel.vue'
import MiTablero from './MiTablero.vue'
import TablerosOponentes from './TablerosOponentes.vue'
import BarraAcciones from './BarraAcciones.vue'
import RegistroEventos from './RegistroEventos.vue'
import FermentationReportModal from './FermentationReportModal.vue'
import RankingView from './RankingView.vue'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)
const esMiTurno = computed(() => estado.value.jugador_en_turno_idx === miIndice.value)

const forzandoPase = ref(false)
async function onForzarPase() {
  forzandoPase.value = true
  try {
    await forzarPase()
  } finally {
    forzandoPase.value = false
  }
}

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

      <section class="mesa-comun">
        <h2 class="titulo-mesa">Mesa Común</h2>
        <MercadoPanel />
        <SuministrosPanel />

        <div class="panel espacios-accion">
          <h3>Espacios de Acción</h3>
          <BarraAcciones v-if="esMiTurno" />
          <div v-else class="espera-turno">
            <p class="espera">Esperando tu turno…</p>
            <button class="forzar-pase" :disabled="forzandoPase" @click="onForzarPase">
              ¿Jugador inactivo? Forzar pase de turno
            </button>
          </div>
        </div>
      </section>

      <div class="columnas">
        <div class="columna-principal">
          <MiTablero />
        </div>

        <div class="columna-lateral">
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

.mesa-comun {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.titulo-mesa {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-texto-tenue);
  margin: 0;
}

.espacios-accion h3 {
  margin-top: 0;
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

.espera-turno {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.espera {
  color: var(--color-texto-tenue);
  font-style: italic;
  margin: 0;
}

.forzar-pase {
  padding: 0.4rem 0.7rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto-tenue);
  font-size: 0.8rem;
}

.forzar-pase:hover:not(:disabled) {
  border-color: var(--color-mal);
  color: var(--color-mal);
}

@media (max-width: 800px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}
</style>
