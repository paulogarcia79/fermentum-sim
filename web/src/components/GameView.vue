<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import {
  alternarPanel,
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
import DockPaneles from './DockPaneles.vue'
import PanelOcultable from './PanelOcultable.vue'
import type { IdPanel } from '../data/panelesTablero'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)
const esMiTurno = computed(() => estado.value.jugador_en_turno_idx === miIndice.value)

const NOMBRE_FASE: Record<string, string> = {
  preparacion: 'Preparación',
  fase_i: 'Fase I · Ambiente',
  fase_ii: 'Fase II · Acción',
  fase_iii: 'Fase III · Fermentación',
  terminada: 'Terminada',
}

// Visibilidad de cada modulo del tablero (dock de la cabecera, DockPaneles.vue).
// Los paneles se esconden con v-show y no con v-if: siguen montados, asi que
// conservan su estado local (el scroll del Registro, un tooltip ⓘ abierto).
// Las REGIONES si usan v-if -- en un tablero de una pantalla, ocultar una
// region tiene que devolver su espacio a las vecinas, no dejar un hueco.
//
// Unica excepcion a la preferencia guardada: los Espacios de Accion se
// muestran siempre que sea tu turno -- ocultarlos ahi te dejaria sin poder
// jugar mientras corre el reloj de inactividad. Es una anulacion temporal:
// la preferencia no se toca y el panel vuelve a esconderse al acabar el turno.
function visible(id: IdPanel): boolean {
  if (id === 'acciones' && esMiTurno.value) return true
  return !store.preferencias.panelesOcultos.includes(id)
}

const regionMesa = computed(() => visible('mercado'))
const regionMedio = computed(() => visible('clima') || visible('tendencias') || visible('bolsa'))
const regionTablero = computed(() => visible('mi_tablero'))
const regionLateral = computed(
  () => visible('orden') || visible('oponentes') || visible('registro'),
)
const filaSuperior = computed(() => regionMesa.value || regionMedio.value)

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
  <div class="game-view" :class="{ terminada: estado.partida_terminada }">
    <header class="cabecera">
      <div class="identidad">
        <h1>Fermentum</h1>
        <span class="sala dato">SALA {{ store.sesion?.roomId }}</span>
      </div>

      <div class="reloj">
        <span class="dia dato">DÍA {{ estado.environment.dia_actual }}</span>
        <span class="fase">{{ NOMBRE_FASE[estado.fase_actual] ?? estado.fase_actual }}</span>
      </div>

      <p class="turno-indicador" :class="{ 'mi-turno': esMiTurno }">
        <template v-if="estado.partida_terminada">La partida ha terminado.</template>
        <template v-else-if="esMiTurno">Es tu turno.</template>
        <template v-else-if="estado.jugador_en_turno_idx !== null">
          Turno de {{ estado.players[estado.jugador_en_turno_idx].nombre }}…
        </template>
        <template v-else>Resolviendo fin de día…</template>
      </p>

      <div class="controles-cabecera">
        <!-- El dock vive en la cabecera y no flotando sobre el tablero: en una
             vista que no hace scroll, un raíl flotante es cromo de más. -->
        <DockPaneles v-if="!estado.partida_terminada" />
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
    </header>

    <p v-if="store.error" class="error">⚠ {{ store.error }}</p>

    <RankingView v-if="estado.partida_terminada" />

    <template v-else>
      <div class="cuerpo">
        <div v-if="filaSuperior || regionTablero" class="bloque-principal">
          <div v-if="filaSuperior" class="fila-superior">
            <section v-if="regionMesa" class="region region-mesa" aria-label="Mesa Común">
              <h2 class="eyebrow rotulo-region">Mesa Común</h2>
              <PanelOcultable etiqueta="Mercado Central" @ocultar="alternarPanel('mercado')">
                <MercadoPanel />
              </PanelOcultable>
            </section>

            <section v-if="regionMedio" class="region region-medio" aria-label="Ambiente y mercado">
              <h2 class="eyebrow rotulo-region">Ambiente</h2>
              <PanelOcultable
                v-show="visible('clima')"
                etiqueta="Clima"
                @ocultar="alternarPanel('clima')"
              >
                <MazoClimaPanel />
              </PanelOcultable>

              <PanelOcultable
                v-show="visible('tendencias')"
                etiqueta="Tendencias de Mercado"
                @ocultar="alternarPanel('tendencias')"
              >
                <MazoTendenciasPanel />
              </PanelOcultable>

              <PanelOcultable
                v-show="visible('bolsa')"
                etiqueta="Bolsa de Harinas"
                @ocultar="alternarPanel('bolsa')"
              >
                <BolsaHarinasPanel />
              </PanelOcultable>
            </section>
          </div>

          <section v-if="regionTablero" class="region region-tablero" aria-label="Mi tablero">
            <h2 class="eyebrow rotulo-region">Mi Tablero</h2>
            <PanelOcultable etiqueta="Mi Tablero" @ocultar="alternarPanel('mi_tablero')">
              <MiTablero />
            </PanelOcultable>
          </section>
        </div>

        <section v-if="regionLateral" class="region region-lateral" aria-label="Partida">
          <h2 class="eyebrow rotulo-region">Partida</h2>
          <PanelOcultable
            v-show="visible('orden')"
            etiqueta="Orden de Turno"
            @ocultar="alternarPanel('orden')"
          >
            <OrdenTurnoPanel />
          </PanelOcultable>

          <PanelOcultable
            v-show="visible('oponentes')"
            etiqueta="Otros investigadores"
            @ocultar="alternarPanel('oponentes')"
          >
            <TablerosOponentes />
          </PanelOcultable>

          <PanelOcultable
            v-show="visible('registro')"
            etiqueta="Registro"
            @ocultar="alternarPanel('registro')"
          >
            <RegistroEventos />
          </PanelOcultable>

          <div class="fin-anticipado">
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
        </section>
      </div>

      <!-- La barra de acciones es una region permanente del borde de la mesa:
           conserva su sitio también en el turno de otro, para que la pantalla
           no salte a mitad de ronda. -->
      <footer v-show="visible('acciones')" class="region region-acciones">
        <BarraAcciones v-if="esMiTurno" />
        <div v-else class="espera-turno">
          <p class="espera">
            <template v-if="estado.jugador_en_turno_idx !== null">
              Juega {{ estado.players[estado.jugador_en_turno_idx].nombre }}. Esperando su acción…
            </template>
            <template v-else>Resolviendo el fin del día…</template>
          </p>
          <button class="forzar-pase" :disabled="forzandoPase" @click="onForzarPase">
            ¿Jugador inactivo? Forzar pase de turno
          </button>
        </div>
      </footer>
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
/* El tablero ocupa la ventana entera y NO hace scroll de pagina: cada region
   se desplaza por dentro. Asi la mesa comun, tu tablero y tus acciones estan
   siempre a la vista a la vez, que es lo que separa un tablero de un
   documento. */
.game-view {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  height: 100dvh;
  padding: var(--e3);
  overflow: hidden;
}

/* El ranking si es un documento: columna centrada y con scroll normal. */
.game-view.terminada {
  height: auto;
  min-height: 100dvh;
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--e4);
  overflow: visible;
}

/* --- Cabecera ------------------------------------------------------------ */
.cabecera {
  display: flex;
  align-items: center;
  gap: var(--e4);
  flex-wrap: wrap;
  flex: 0 0 auto;
  padding: var(--e2) var(--e3);
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
}

.identidad {
  display: flex;
  align-items: baseline;
  gap: var(--e2);
}

.identidad h1 {
  font-size: var(--t-l);
  letter-spacing: -0.01em;
}

.sala,
.dia {
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
}

.reloj {
  display: flex;
  align-items: baseline;
  gap: var(--e2);
  padding-left: var(--e4);
  border-left: 1px solid var(--borde);
}

.reloj .dia {
  color: var(--cobre);
}

.fase {
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.turno-indicador {
  flex: 1 1 auto;
  margin: 0;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.turno-indicador.mi-turno {
  color: var(--cobre);
  font-weight: 600;
}

.controles-cabecera {
  display: flex;
  align-items: center;
  gap: var(--e2);
  margin-left: auto;
}

.interruptor-sonido {
  flex: 0 0 auto;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: transparent;
  font-size: var(--t-s);
  line-height: 1;
  transition: border-color var(--transicion);
}

.interruptor-sonido:hover {
  border-color: var(--borde-fuerte);
}

.interruptor-sonido.apagado {
  opacity: 0.55;
}

/* --- Regiones ------------------------------------------------------------ */
.cuerpo {
  display: flex;
  gap: var(--e2);
  flex: 1 1 auto;
  min-height: 0;
}

.bloque-principal {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
}

.fila-superior {
  display: flex;
  gap: var(--e2);
  flex: 1 1 55%;
  min-height: 0;
}

/* Una region es una zona impresa del tablero: marco fino, rotulo serigrafiado
   y su propio scroll. Las cartas y paneles de dentro son lo que se levanta. */
.region {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  min-height: 0;
  min-width: 0;
  padding: var(--e2);
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
  overflow-y: auto;
  /* Doble filete: el marco impreso de una zona del tablero. Es lo unico que
     distingue una region de una carta -- las cartas se levantan con sombra,
     las zonas estan impresas sobre la mesa. */
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.35);
}

.rotulo-region {
  flex: 0 0 auto;
}

/* Los paneles que van DENTRO de una region no vuelven a dibujar su propio
   marco: la region ya es la zona impresa. Sin esto habria dos rectangulos
   concentricos del mismo color por cada modulo, que es justo lo que hacia
   que la pantalla se leyera como una lista de cajas. Lo que se levanta de la
   mesa son las cartas (.receta-card, .carta-clima), no los paneles.

   Ojo: :deep() compila a `.region[data-v-x] .panel`, o sea alcanza a CUALQUIER
   descendiente en el DOM -- incluido un modal `position: fixed` abierto desde
   dentro de la region, que se quedaria sin fondo ni padding. Por eso todo
   overlay va con <Teleport to="body"> y con .modal (tier --carta), nunca con
   .panel. */
.region :deep(.panel) {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
}

/* Excepcion: el tablero propio conserva su raíl de color, que es como
   identificas de un vistazo que esa zona es la tuya. */
.region :deep(.mi-tablero) {
  border-left: 3px solid;
  padding-left: var(--e3);
}

/* Separacion entre modulos apilados en una misma region. */
.region > .envoltorio-panel + .envoltorio-panel {
  padding-top: var(--e2);
  border-top: 1px solid var(--borde);
}

.region-mesa {
  flex: 1 1 auto;
}

.region-medio {
  flex: 0 0 21rem;
}

.region-tablero {
  flex: 1 1 45%;
}

.region-lateral {
  flex: 0 0 17rem;
}

.region-acciones {
  flex: 0 0 auto;
  max-height: 40vh;
}

.espera-turno {
  display: flex;
  align-items: center;
  gap: var(--e3);
  flex-wrap: wrap;
}

.espera {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  margin: 0;
}

.forzar-pase {
  padding: var(--e1) var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: transparent;
  color: var(--tinta-tenue);
  font-size: var(--t-xs);
  transition: border-color var(--transicion), color var(--transicion);
}

.forzar-pase:hover:not(:disabled) {
  border-color: var(--riesgo);
  color: var(--riesgo);
}

/* --- Fin anticipado (al pie del raíl lateral) ---------------------------- */
.fin-anticipado {
  display: flex;
  align-items: center;
  gap: var(--e2);
  flex-wrap: wrap;
  margin-top: auto;
  padding-top: var(--e2);
  border-top: 1px solid var(--borde);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.confirmar-fin {
  padding: var(--e1) var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: transparent;
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
  transition: border-color var(--transicion), color var(--transicion);
}

.confirmar-fin:hover:not(:disabled) {
  border-color: var(--cobre);
  color: var(--cobre);
}

.ya-confirmaste {
  color: var(--vital);
}

.error {
  flex: 0 0 auto;
  margin: 0;
  color: var(--riesgo);
  background: var(--lavado-riesgo);
  border: 1px solid var(--riesgo);
  border-radius: var(--r-carta);
  padding: var(--e2) var(--e3);
  font-size: var(--t-s);
}

/* --- Responsive ---------------------------------------------------------- */
/* 1100px: los raíles ya no caben en columna; el tablero se despliega y la
   pagina vuelve a hacer scroll. */
@media (max-width: 1100px) {
  .game-view {
    height: auto;
    min-height: 100dvh;
    overflow: visible;
  }

  .cuerpo,
  .fila-superior {
    flex-direction: column;
  }

  .region {
    overflow-y: visible;
  }

  .region-medio,
  .region-lateral,
  .region-mesa,
  .region-tablero {
    flex: 0 0 auto;
  }

  .region-acciones {
    max-height: none;
  }
}

/* 720px: primero lo tuyo. Tus acciones y tu tablero por delante de la mesa. */
@media (max-width: 720px) {
  .game-view {
    padding: var(--e2);
  }

  /* Reordenado explicito: en movil primero la cabecera, luego lo que puedes
     hacer, luego tu tablero, y la mesa comun al final. */
  .cabecera {
    order: -3;
  }

  .error {
    order: -2;
  }

  .region-acciones {
    order: -1;
  }

  .bloque-principal {
    display: contents;
  }

  .region-tablero {
    order: -1;
  }

  .cabecera {
    gap: var(--e2);
  }

  .reloj {
    padding-left: 0;
    border-left: none;
  }
}
</style>
