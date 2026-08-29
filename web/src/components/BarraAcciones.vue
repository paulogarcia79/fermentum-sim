<script setup lang="ts">
import { computed, ref } from 'vue'
import { deshacer, pasar, store } from '../store'
import ModalShell from './ModalShell.vue'
import ModalA from './acciones/ModalA.vue'
import ModalB from './acciones/ModalB.vue'
import ModalC from './acciones/ModalC.vue'
import ModalD from './acciones/ModalD.vue'
import ModalE from './acciones/ModalE.vue'
import ModalF from './acciones/ModalF.vue'
import ModalG from './acciones/ModalG.vue'
import ModalSimposio from './acciones/ModalSimposio.vue'
import ModalConfirmacion from './acciones/ModalConfirmacion.vue'
import ModalPedidoUrgencia from './acciones/ModalPedidoUrgencia.vue'
import {
  ACCIONES_QUE_REVELAN,
  GRUPOS_ACCION,
  descripcionesAcciones,
  type IdAccion,
} from '../data/descripcionesAcciones'
import { hexDeColor } from '../data/coloresJugador'
import type { Player } from '../types'

/** Los 12 espacios en plano, sin zonas -- para el modal de confirmación de
 * pase, que los lista como una sola lista de "lo que te queda por hacer".
 * Deriva de GRUPOS_ACCION para que no haya dos catálogos que mantener. */
const ACCIONES_PLANAS = GRUPOS_ACCION.flatMap((g) => g.acciones)

const disponibilidad = computed(() => store.estado!.acciones_disponibles[store.sesion!.playerIndex])

function estado(id: IdAccion) {
  return disponibilidad.value.find((a) => a.id === id) ?? { habilitada: false, motivo: '' }
}

/** Espacios de acción gratuitos (0 PA) que igual solo se pueden visitar una
 * vez por día -- se marcan visualmente distinto (aro hueco) de los espacios
 * con costo de PA (punto sólido), ver .marcador-jugador.gratis más abajo. */
const ESPACIOS_GRATIS_UNA_VEZ_POR_DIA: IdAccion[] = ['A', 'horas_extras']

/** Jugadores que ya visitaron el espacio de acción `id` hoy -- recorre a
 * TODOS los jugadores (no solo el propio, a diferencia de `disponibilidad`)
 * para poder mostrar el marcador de color de cada uno. Pedido de Urgencia
 * no tiene límite diario, así que nunca devuelve marcadores. */
function jugadoresQueUsaron(id: IdAccion): Player[] {
  if (id === 'A') return store.estado!.players.filter((p) => p.accion_alimentar_usada)
  if (id === 'horas_extras') return store.estado!.players.filter((p) => p.horas_extras_usadas)
  if (id === 'pedido_urgencia') return []
  return store.estado!.players.filter((p) => p.acciones_pa_usadas_hoy.includes(id))
}

const modalAbierto = ref<IdAccion | null>(null)
function abrir(id: IdAccion) {
  if (!estado(id).habilitada) return
  modalAbierto.value = id
}
function cerrar() {
  modalAbierto.value = null
}

const pasando = ref(false)
const confirmandoPase = ref(false)

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])

/** Pasar es una renuncia TOTAL al resto del día: cede los PA restantes y
 * también las acciones gratuitas sin usar (ver engine.pasar_turno). Antes de
 * dejar que el jugador tire algo por accidente, se le muestra exactamente qué
 * le queda -- y un atajo para usarlo -- en un modal de confirmación.
 *
 * "Qué le queda" se lee de `acciones_disponibles` (filtrando la propia tabla
 * ACCIONES_PLANAS por `habilitada`), que ya lo calcula el servidor por
 * jugador --
 * nunca se reimplementa aquí ninguna regla de habilitación. */
const accionesRestantes = computed(() => ACCIONES_PLANAS.filter((b) => estado(b.id).habilitada))

/** El bloque rojo de colapso dentro del modal sigue siendo opt-in (checkbox
 * del lobby); el modal en sí ya no -- aparece siempre que quede algo por
 * hacer, tenga o no la alerta activada. */
/** La zona de Protocolos de Emergencia siempre se ve (para que el jugador
 * sepa que el rescate existe antes de necesitarlo), pero solo se enciende en
 * rojo cuando de verdad está en juego. */
const contaminado = computed(() => yo.value.en_estado_contaminacion)

const avisoColapso = computed(
  () => store.preferencias.alertaContaminacion && yo.value.en_riesgo_colapso,
)

function onPasar() {
  if (accionesRestantes.value.length > 0) {
    confirmandoPase.value = true
    return
  }
  void pasarDeVerdad()
}

/** Deshacer la visita: restaura al estado previo a la primera accion
 * gratuita de esta visita. El servidor manda `puede_deshacer` -- el boton
 * solo existe cuando hay algo que deshacer, y una accion con costo de PA
 * (que termina la visita) lo hace desaparecer para siempre. */
const deshaciendo = ref(false)
async function onDeshacer() {
  deshaciendo.value = true
  try {
    await deshacer()
  } finally {
    deshaciendo.value = false
  }
}

/** Atajo del modal de confirmación: en vez de pasar, saltar directo a una de
 * las acciones que quedaban -- cierra la confirmación y abre el modal normal
 * de esa acción (mismo flujo que clickear su espacio en el tablero). */
function usarAccionRestante(id: IdAccion) {
  confirmandoPase.value = false
  abrir(id)
}

async function pasarDeVerdad() {
  confirmandoPase.value = false
  pasando.value = true
  try {
    await pasar()
  } finally {
    pasando.value = false
  }
}
</script>

<template>
  <section class="barra-acciones">
    <div class="zonas">
      <section
        v-for="g in GRUPOS_ACCION"
        :key="g.id"
        class="zona-accion"
        :class="[`zona-${g.id}`, { activa: g.id === 'emergencia' && contaminado }]"
      >
        <header class="cabecera-zona">
          <h4>{{ g.titulo }}</h4>
          <span class="insignia-costo">{{ g.costo }}</span>
          <p class="nota-zona">{{ g.nota }}</p>
        </header>

        <div class="grid-botones">
          <div v-for="b in g.acciones" :key="b.id" class="envoltorio-boton">
            <div v-if="jugadoresQueUsaron(b.id).length > 0" class="marcadores-jugador">
              <span
                v-for="p in jugadoresQueUsaron(b.id)"
                :key="p.nombre"
                class="marcador-jugador"
                :class="{ gratis: ESPACIOS_GRATIS_UNA_VEZ_POR_DIA.includes(b.id) }"
                :style="{ '--color-marcador': hexDeColor(p.color) }"
                :title="`${p.nombre} ya visitó este espacio hoy`"
              />
            </div>
            <button
              :disabled="!estado(b.id).habilitada"
              :title="estado(b.id).motivo"
              @click="abrir(b.id)"
            >
              {{ b.etiqueta }}
            </button>
            <div class="tooltip" role="tooltip">
              <p>{{ descripcionesAcciones[b.id] }}</p>
              <p v-if="ACCIONES_QUE_REVELAN.has(b.id)" class="tooltip-motivo">
                ⚠ Revela información oculta: ese paso no se puede deshacer.
              </p>
              <p v-if="!estado(b.id).habilitada && estado(b.id).motivo" class="tooltip-motivo">
                ⚠ {{ estado(b.id).motivo }}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div class="fila-controles">
      <button
        v-if="store.estado!.puede_deshacer"
        class="deshacer"
        :disabled="deshaciendo || pasando"
        title="Restaura el estado al inicio de tu visita, deshaciendo las acciones gratuitas que hiciste. La información oculta revelada nunca se restaura (hoy ninguna acción revela nada)."
        @click="onDeshacer"
      >
        ↩ Deshacer
      </button>
      <button class="pasar" :disabled="pasando || deshaciendo" @click="onPasar">Pasar turno</button>
    </div>

    <ModalShell
      v-if="confirmandoPase"
      titulo="¿Pasar turno? Todavía puedes actuar"
      @cerrar="confirmandoPase = false"
    >
      <p class="intro-pase">
        Pasar renuncia a <strong>todo</strong> lo que te queda hoy — incluidas las acciones
        gratuitas sin usar. Puedes usar cualquiera de estas antes de pasar:
      </p>

      <ul class="lista-restantes">
        <li v-for="b in accionesRestantes" :key="b.id">
          <button type="button" class="accion-restante" @click="usarAccionRestante(b.id)">
            <span class="titulo-restante">
              {{ b.etiqueta }} <span class="costo">[{{ b.costo }}]</span>
            </span>
            <span class="blurb-restante">{{ descripcionesAcciones[b.id] }}</span>
          </button>
        </li>
      </ul>

      <p v-if="avisoColapso" class="peligro-colapso">
        <strong>⚠ Tu masa madre colapsa esta noche.</strong>
        La Vitalidad bajará de {{ yo.vitalidad }} a {{ yo.vitalidad_prevista }} y entrarás en
        Contaminación: -3 Puntos de Maestría y no podrás Iniciar Receta hasta usar un protocolo
        de emergencia.
      </p>

      <template #acciones>
        <button class="secundario" :disabled="pasando" @click="confirmandoPase = false">
          Seguir jugando
        </button>
        <button class="confirmar-pase" :disabled="pasando" @click="pasarDeVerdad">
          Pasar de todos modos
        </button>
      </template>
    </ModalShell>

    <ModalA v-if="modalAbierto === 'A'" @cerrar="cerrar" />
    <ModalB v-if="modalAbierto === 'B'" @cerrar="cerrar" />
    <ModalC v-if="modalAbierto === 'C'" @cerrar="cerrar" />
    <ModalD v-if="modalAbierto === 'D'" @cerrar="cerrar" />
    <ModalE v-if="modalAbierto === 'E'" @cerrar="cerrar" />
    <ModalF v-if="modalAbierto === 'F'" @cerrar="cerrar" />
    <ModalG v-if="modalAbierto === 'G'" @cerrar="cerrar" />
    <ModalSimposio v-if="modalAbierto === 'simposio'" @cerrar="cerrar" />
    <ModalConfirmacion
      v-if="modalAbierto === 'H'"
      titulo="Re-cultivo Manual (1 PA)"
      :descripcion="descripcionesAcciones.H"
      accion="H"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'I'"
      titulo="Inóculo de Emergencia (1 PA)"
      :descripcion="descripcionesAcciones.I"
      accion="I"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'horas_extras'"
      titulo="Horas Extras (0 PA)"
      :descripcion="descripcionesAcciones.horas_extras"
      accion="horas_extras"
      @cerrar="cerrar"
    />
    <ModalPedidoUrgencia v-if="modalAbierto === 'pedido_urgencia'" @cerrar="cerrar" />
  </section>
</template>

<style scoped>
/* Tres zonas de tablero, una por familia de acciones (ver GRUPOS_ACCION):
   Principales y Gratuitas en paralelo -- 2fr/1fr porque son 7 espacios contra
   3 -- y Emergencia a lo ancho debajo. Se apilan bajo 800px, el mismo
   breakpoint que usa .columnas en GameView.vue. */
.zonas {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

@media (max-width: 800px) {
  .zonas {
    grid-template-columns: 1fr;
  }
}

/* Cada zona tiñe su cabecera y el borde superior de sus espacios con
   --acento-zona; sin overflow: hidden, o recortaría los tooltips de los
   espacios (que se posicionan por encima del tile). */
.zona-accion {
  border: 1px solid var(--color-borde);
  border-top: 2px solid var(--acento-zona);
  border-radius: 8px;
  padding: 0.6rem;
}

.zona-principales {
  --acento-zona: var(--color-acento);
}

.zona-gratuitas {
  --acento-zona: var(--color-bien);
}

.zona-emergencia {
  grid-column: 1 / -1;
  --acento-zona: var(--color-mal);
}

/* Solo cuando el rescate está realmente en juego. */
.zona-emergencia.activa {
  border-color: var(--color-mal);
  background: rgba(198, 90, 75, 0.08);
}

.cabecera-zona {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem;
  margin-bottom: 0.55rem;
}

.cabecera-zona h4 {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--acento-zona);
}

.insignia-costo {
  padding: 0.05rem 0.35rem;
  border: 1px solid var(--acento-zona);
  border-radius: 999px;
  font-size: 0.66rem;
  letter-spacing: 0.04em;
  color: var(--acento-zona);
}

.nota-zona {
  flex-basis: 100%;
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.3;
  color: var(--color-texto-tenue);
}

.grid-botones {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 0.6rem;
}

.envoltorio-boton {
  position: relative;
}

.envoltorio-boton button {
  width: 100%;
  padding: 0.6rem 0.5rem 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-borde);
  border-top: 3px solid var(--acento-zona, var(--color-acento));
  background: var(--color-fondo);
  color: var(--color-texto);
  font-size: 0.82rem;
  text-align: center;
}

.envoltorio-boton button:disabled {
  border-top-color: var(--color-borde);
}

.marcadores-jugador {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  gap: 2px;
  z-index: 10;
}

.marcador-jugador {
  box-sizing: border-box;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-marcador);
  box-shadow: 0 0 0 1px var(--color-fondo);
}

.marcador-jugador.gratis {
  background: transparent;
  border: 2px solid var(--color-marcador);
  box-shadow: none;
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + 0.4rem);
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  max-width: 60vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  font-size: 0.78rem;
  line-height: 1.35;
  color: var(--color-texto);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  z-index: 30;
  pointer-events: none;
  transition: opacity 0.1s ease;
}

.tooltip p {
  margin: 0;
}

.tooltip-motivo {
  margin-top: 0.4rem !important;
  color: var(--color-mal);
}

.envoltorio-boton:hover .tooltip,
.envoltorio-boton:focus-within .tooltip {
  visibility: visible;
  opacity: 1;
}

/* El coste por espacio ya no se repite en cada tile (lo dice la insignia de
   su zona); esto solo aplica a la lista plana del modal de pase. */
.costo {
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
}

.fila-controles {
  display: flex;
  gap: 0.5rem;
}

.pasar {
  flex: 1;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto-tenue);
}

.deshacer {
  flex: 0 0 auto;
  padding: 0.5rem 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-acento);
  background: transparent;
  color: var(--color-acento);
  cursor: pointer;
}

/* Modal de confirmación de pase: qué queda por hacer, con atajo directo a
   cada acción, y el bloque rojo de colapso (opt-in) cuando aplica. */
.intro-pase {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  line-height: 1.45;
}

.lista-restantes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.accion-restante {
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  background: transparent;
  color: var(--color-texto);
  cursor: pointer;
}

.accion-restante:hover {
  border-color: var(--color-acento);
}

.titulo-restante {
  display: block;
  font-weight: 600;
  font-size: 0.82rem;
}

.titulo-restante .costo {
  font-weight: 400;
}

.blurb-restante {
  display: block;
  font-size: 0.72rem;
  color: var(--color-texto-tenue);
  margin-top: 0.15rem;
  line-height: 1.35;
}

.peligro-colapso {
  margin: 0.75rem 0 0;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--color-mal);
  border-radius: 6px;
  background: rgba(198, 90, 75, 0.12);
  font-size: 0.78rem;
  line-height: 1.4;
}

.peligro-colapso strong {
  color: var(--color-mal);
}

.secundario,
.confirmar-pase {
  flex: 1;
  padding: 0.45rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto);
  font-size: 0.8rem;
}

.confirmar-pase {
  border-color: var(--color-mal);
  color: var(--color-mal);
}
</style>
