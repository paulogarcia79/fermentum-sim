<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import {
  confirmarFinAnticipado,
  detenerTransmisionEnVivo,
  establecerSonido,
  forzarPase,
  store,
} from '../store'
import MazoClimaPanel from './MazoClimaPanel.vue'
import MercadoPanel from './MercadoPanel.vue'
import BolsaHarinasPanel from './BolsaHarinasPanel.vue'
import MazoTendenciasPanel from './MazoTendenciasPanel.vue'
import MiTablero from './MiTablero.vue'
import OrdenTurnoPanel from './OrdenTurnoPanel.vue'
import TablerosOponentes from './TablerosOponentes.vue'
import BarraAcciones from './BarraAcciones.vue'
import RegistroEventos from './RegistroEventos.vue'
import FermentationReportModal from './FermentationReportModal.vue'
import InicioDiaModal from './InicioDiaModal.vue'
import FinAnticipadoModal from './FinAnticipadoModal.vue'
import ResultadoHorneadoModal from './ResultadoHorneadoModal.vue'
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

const yaConfirmeFinAnticipado = computed(() => estado.value.votos_fin_anticipado.includes(miIndice.value))
const nombresPidieronFin = computed(() =>
  estado.value.votos_fin_anticipado.map((i) => estado.value.players[i]?.nombre ?? `Jugador ${i + 1}`),
)
const confirmandoFin = ref(false)
async function onConfirmarFin() {
  confirmandoFin.value = true
  try {
    await confirmarFinAnticipado()
  } finally {
    confirmandoFin.value = false
  }
}

onUnmounted(() => detenerTransmisionEnVivo())
</script>

<template>
  <div class="game-view">
    <header class="cabecera">
      <div class="fila-titulo">
        <h1>🍞 Fermentum — Sala {{ store.sesion?.roomId }}</h1>
        <!-- Vive aqui y no en BarraAcciones.vue porque ese componente solo
             se monta con v-if="esMiTurno", y el control tiene que existir
             justo cuando el que actua es otro. -->
        <button
          class="interruptor-sonido"
          :class="{ apagado: !store.preferencias.sonido }"
          :title="
            store.preferencias.sonido
              ? 'Silenciar los efectos de sonido de las acciones'
              : 'Activar los efectos de sonido de las acciones'
          "
          :aria-pressed="store.preferencias.sonido"
          @click="establecerSonido(!store.preferencias.sonido)"
        >
          {{ store.preferencias.sonido ? '🔊' : '🔇' }}
        </button>
      </div>
      <p class="turno-indicador" :class="{ 'mi-turno': esMiTurno }">
        <template v-if="estado.partida_terminada">La partida ha terminado.</template>
        <template v-else-if="esMiTurno">Es tu turno.</template>
        <template v-else-if="estado.jugador_en_turno_idx !== null">
          Turno de {{ estado.players[estado.jugador_en_turno_idx].nombre }}…
        </template>
        <template v-else>Resolviendo fin de día…</template>
      </p>
    </header>

    <div v-if="!estado.partida_terminada" class="fin-anticipado">
      <span class="tally">
        <template v-if="nombresPidieronFin.length > 0">
          {{ nombresPidieronFin.join(', ') }} pidió terminar antes de tiempo ·
        </template>
        {{ estado.votos_fin_anticipado.length }}/{{ estado.players.length }} confirmaron
      </span>
      <span v-if="yaConfirmeFinAnticipado" class="ya-confirmaste">✓ Ya confirmaste</span>
      <button v-else class="confirmar-fin" :disabled="confirmandoFin" @click="onConfirmarFin">
        Confirmar fin de partida
      </button>
    </div>

    <p v-if="store.error" class="error">⚠ {{ store.error }}</p>

    <RankingView v-if="estado.partida_terminada" />

    <template v-else>
      <section class="mesa-comun">
        <h2 class="titulo-mesa">Mesa Común</h2>
        <MazoClimaPanel />
        <MercadoPanel />

        <div class="fila-harinas">
          <BolsaHarinasPanel />
          <MazoTendenciasPanel />
        </div>

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
          <OrdenTurnoPanel />
          <TablerosOponentes />
          <RegistroEventos />
        </div>
      </div>
    </template>

    <!-- El resultado del propio horneado va primero: es la respuesta
         inmediata a lo que el jugador acaba de hacer. Si el mismo snapshot
         tambien cerro el dia, el reporte de Fase III espera a que lo cierre. -->
    <ResultadoHorneadoModal v-if="store.resultadoHorneado" />
    <FermentationReportModal v-else-if="store.reporteDiaPendiente !== null" />
    <InicioDiaModal v-else-if="store.inicioDiaPendiente" />
    <FinAnticipadoModal v-else-if="store.finAnticipadoPendiente" />
  </div>
</template>

<style scoped>
.fila-titulo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.interruptor-sonido {
  flex: 0 0 auto;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  font-size: 1rem;
  line-height: 1;
}

.interruptor-sonido.apagado {
  opacity: 0.55;
}

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

.fin-anticipado {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
  margin-bottom: 0.75rem;
}

.confirmar-fin {
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
}

.confirmar-fin:hover:not(:disabled) {
  border-color: var(--color-acento);
  color: var(--color-acento);
}

.ya-confirmaste {
  color: var(--color-bien);
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

.fila-harinas {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.fila-harinas > :first-child {
  flex: 2 1 380px;
}

.fila-harinas > :last-child {
  flex: 1 1 260px;
}

@media (max-width: 700px) {
  .fila-harinas {
    flex-direction: column;
  }
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
