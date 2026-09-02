<script setup lang="ts">
import { computed, ref } from 'vue'
import { deshacer, pasar, store } from '../store'
import ModalShell from './ModalShell.vue'
import Tooltip from './Tooltip.vue'
import ModalA from './acciones/ModalA.vue'
import ModalB from './acciones/ModalB.vue'
import ModalC from './acciones/ModalC.vue'
import ModalD from './acciones/ModalD.vue'
import ModalE from './acciones/ModalE.vue'
import ModalDescarte from './acciones/ModalDescarte.vue'
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
const ESPACIOS_GRATIS_UNA_VEZ_POR_DIA: IdAccion[] = ['A', 'E', 'horas_extras']

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
          <Tooltip v-for="b in g.acciones" :key="b.id" class="envoltorio-boton">
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
            <!-- Sin `title`: el motivo ya sale en la caja de abajo, y el
                 tooltip nativo del navegador se le montaba encima. -->
            <button :disabled="!estado(b.id).habilitada" @click="abrir(b.id)">
              {{ b.etiqueta }}
            </button>

            <template #contenido>
              <p>{{ descripcionesAcciones[b.id] }}</p>
              <p v-if="ACCIONES_QUE_REVELAN.has(b.id)" class="tooltip-motivo">
                ⚠ Revela información oculta: ese paso no se puede deshacer.
              </p>
              <p v-if="!estado(b.id).habilitada && estado(b.id).motivo" class="tooltip-motivo">
                ⚠ {{ estado(b.id).motivo }}
              </p>
            </template>
          </Tooltip>
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
    <ModalDescarte v-if="modalAbierto === 'descarte'" @cerrar="cerrar" />
    <ModalF v-if="modalAbierto === 'F'" @cerrar="cerrar" />
    <ModalG v-if="modalAbierto === 'G'" @cerrar="cerrar" />
    <ModalSimposio v-if="modalAbierto === 'simposio'" @cerrar="cerrar" />
    <ModalConfirmacion
      v-if="modalAbierto === 'jefatura'"
      titulo="Reclamar la Jefatura (1 PA)"
      :descripcion="descripcionesAcciones.jefatura"
      accion="jefatura"
      @cerrar="cerrar"
    />
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
/* La barra vive en el borde inferior de la mesa (region .region-acciones de
   GameView.vue): las tres familias de espacios en fila -- Principales,
   Gratuitas y Protocolos de Emergencia (ver GRUPOS_ACCION) -- y los controles
   de turno al extremo derecho, siempre en el mismo sitio.

   Ojo con el error facil: la insignia de Emergencia dice 1 PA, no 0 PA. H e I
   son reactivas por DISPONIBILIDAD (necesitan contaminacion activa), no por
   costo: cobran su PA y terminan el turno igual que las principales. */
.barra-acciones {
  display: flex;
  align-items: stretch;
  gap: var(--e2);
}

.zonas {
  display: flex;
  flex: 1 1 auto;
  gap: var(--e2);
  min-width: 0;
}

.zona-accion {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  min-width: 0;
  padding: var(--e2);
  border: 1px solid var(--borde);
  border-top: 2px solid var(--acento-zona);
  border-radius: var(--r-carta);
}

.zona-principales {
  --acento-zona: var(--cobre);
  flex: 3 1 auto;
}

.zona-gratuitas {
  --acento-zona: var(--vital);
  flex: 1 1 auto;
}

.zona-emergencia {
  --acento-zona: var(--borde-fuerte);
  flex: 1 1 auto;
  opacity: 0.6;
}

/* Solo se enciende en rojo cuando el rescate esta de verdad en juego. */
.zona-emergencia.activa {
  --acento-zona: var(--riesgo);
  opacity: 1;
  background: var(--lavado-riesgo);
}

.cabecera-zona {
  display: flex;
  align-items: baseline;
  gap: var(--e1);
  flex-wrap: wrap;
}

.cabecera-zona h4 {
  font-size: var(--t-micro);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
}

.insignia-costo {
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  padding: 0 var(--e1);
  border: 1px solid var(--acento-zona);
  border-radius: 999px;
  color: var(--acento-zona);
}

.nota-zona {
  flex-basis: 100%;
  margin: 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.grid-botones {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(6.5rem, 1fr));
  gap: var(--e1);
}

/* Cada espacio de accion es una casilla impresa del tablero. */
.envoltorio-boton {
  position: relative;
}

.envoltorio-boton button {
  width: 100%;
  height: 100%;
  padding: var(--e2) var(--e1);
  border: 1px solid var(--borde);
  border-top: 2px solid var(--acento-zona, var(--cobre));
  border-radius: var(--r-control);
  background: var(--carta);
  color: var(--tinta);
  font-size: var(--t-xs);
  text-align: center;
  transition: background var(--transicion), border-color var(--transicion);
}

.envoltorio-boton button:hover:not(:disabled) {
  background: var(--zona);
  border-color: var(--acento-zona, var(--cobre));
}

/* Peones de quien ya visito el espacio hoy. Aro hueco = espacio gratuito de
   una vez al dia; punto solido = espacio con costo de PA. */
.marcadores-jugador {
  position: absolute;
  top: 3px;
  right: 3px;
  display: flex;
  gap: 2px;
  z-index: 10;
}

.marcador-jugador {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-marcador);
  box-shadow: 0 0 0 1px var(--mesa);
}

.marcador-jugador.gratis {
  background: none;
  border: 2px solid var(--color-marcador);
  box-shadow: none;
}

/* La caja la dibuja Tooltip.vue (teleportada al body). Aqui solo queda el
   color de las lineas de aviso, que son contenido de slot y por tanto llevan
   el scope de ESTE componente. */
.tooltip-motivo {
  color: var(--riesgo);
}

/* --- Controles de turno -------------------------------------------------- */
.fila-controles {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--e1);
  flex: 0 0 auto;
}

.pasar,
.deshacer {
  padding: var(--e2) var(--e3);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: var(--carta);
  color: var(--tinta);
  font-size: var(--t-xs);
  white-space: nowrap;
  transition: border-color var(--transicion), color var(--transicion);
}

.pasar:hover:not(:disabled) {
  border-color: var(--cobre);
  color: var(--cobre);
}

.deshacer:hover:not(:disabled) {
  border-color: var(--verdin);
  color: var(--verdin);
}

/* --- Modal de confirmacion de pase --------------------------------------- */
.intro-pase {
  margin: 0 0 var(--e3);
  font-size: var(--t-s);
}

.lista-restantes {
  list-style: none;
  margin: 0 0 var(--e3);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
}

.accion-restante {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  text-align: left;
  padding: var(--e2);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--carta);
  color: var(--tinta);
  transition: border-color var(--transicion);
}

.accion-restante:hover {
  border-color: var(--cobre);
}

.titulo-restante {
  font-size: var(--t-s);
  font-weight: 600;
}

.costo {
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  font-weight: 400;
  color: var(--tinta-tenue);
}

.blurb-restante {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  line-height: 1.35;
}

.peligro-colapso {
  margin: 0;
  padding: var(--e2);
  border: 1px solid var(--riesgo);
  border-radius: var(--r-control);
  background: var(--lavado-riesgo);
  font-size: var(--t-xs);
  line-height: 1.4;
}

.confirmar-pase {
  flex: 1;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--riesgo);
  background: transparent;
  color: var(--riesgo);
  font-size: var(--t-s);
}

.confirmar-pase:hover:not(:disabled) {
  background: var(--lavado-riesgo);
}

/* Bajo 1100px la barra deja de ser una sola fila: las zonas se apilan igual
   que el resto del tablero (ver GameView.vue). */
@media (max-width: 1100px) {
  .barra-acciones {
    flex-direction: column;
  }

  .zonas {
    flex-wrap: wrap;
  }

  .zona-principales {
    flex: 1 1 20rem;
  }

  .zona-gratuitas,
  .zona-emergencia {
    flex: 1 1 12rem;
  }

  .fila-controles {
    flex-direction: row;
  }

  .pasar {
    flex: 1;
  }
}
</style>
