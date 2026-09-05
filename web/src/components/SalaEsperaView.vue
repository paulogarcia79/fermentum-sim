<script setup lang="ts">
// La sala de espera: desde que entras hasta que el anfitrion arranca.
//
// Antes era una lista de nombres y un boton. Ahora es una rejilla con tantos
// huecos como jugadores se configuraron, de forma que se ve de un vistazo
// cuantos faltan sin leer un "2/4", y el codigo esta en grande porque es lo
// unico que hay que dictar por voz o pegar en un chat.
import { onMounted, onUnmounted, ref } from 'vue'
import * as api from '../api'
import type { SalaMetadata } from '../api'
import { iniciarPolling, refrescarEstado, store } from '../store'
import { ApiFallo } from '../api'
import { hexDeColor } from '../data/coloresJugador'
import { MINUTOS_EXPIRACION_LOBBY } from '../data/salas'
import {
  ENLACE_REGLAMENTO,
  SALA_ASIENTO_VACIO,
  SALA_COMPARTIR,
  SALA_MIENTRAS_ESPERAS,
  SALA_PRIVADA_CHIP,
} from '../data/copyLanding'
import IconoPeon from './IconoPeon.vue'
import TarjetasFases from './TarjetasFases.vue'

const props = defineProps<{ roomId: string }>()

const metadata = ref<SalaMetadata | null>(null)
const error = ref<string | null>(null)
const cargando = ref(false)
const confirmandoInicio = ref(false)
const copiado = ref<'codigo' | 'enlace' | null>(null)
let intervalo: number | undefined
let temporizadorCopia: number | undefined

// El lobby no tiene SSE: sondea /games/{id}, que es publico y barato. Es
// tambien como un jugador que no es el anfitrion se entera de que la partida
// arranco (status deja de ser 'lobby').
async function refrescarMetadata() {
  try {
    metadata.value = await api.verSala(props.roomId)
    if (metadata.value.status !== 'lobby') {
      if (intervalo) window.clearInterval(intervalo)
      await refrescarEstado()
      iniciarPolling()
    }
  } catch {
    // La sala podria no existir ya; se ignora y el usuario vera el error al
    // intentar cualquier accion.
  }
}

onMounted(async () => {
  await refrescarMetadata()
  intervalo = window.setInterval(refrescarMetadata, 1500)
})

onUnmounted(() => {
  if (intervalo) window.clearInterval(intervalo)
  if (temporizadorCopia) window.clearTimeout(temporizadorCopia)
})

// Los huecos vacios se pintan igual que los ocupados: la rejilla siempre tiene
// max_jugadores celdas, asi que "faltan dos" se ve sin contar.
function huecosVacios(): number {
  const meta = metadata.value
  if (!meta) return 0
  return Math.max(0, meta.max_jugadores - meta.seats.length)
}

function enlaceInvitacion(): string {
  return `${window.location.origin}${window.location.pathname}?sala=${props.roomId}`
}

async function copiar(que: 'codigo' | 'enlace') {
  try {
    await navigator.clipboard.writeText(que === 'codigo' ? props.roomId : enlaceInvitacion())
    copiado.value = que
    if (temporizadorCopia) window.clearTimeout(temporizadorCopia)
    temporizadorCopia = window.setTimeout(() => (copiado.value = null), 1500)
  } catch {
    error.value = 'No se pudo copiar. Copia el código a mano.'
  }
}

// Si hay menos jugadores sentados que el objetivo configurado al crear la
// sala, se avisa antes de arrancar en vez de iniciar directo -- facil de
// hacer sin querer con el boton a un click.
function intentarIniciar() {
  const actuales = metadata.value?.seats.length ?? 0
  const objetivo = metadata.value?.max_jugadores ?? actuales
  if (actuales < objetivo) {
    confirmandoInicio.value = true
    return
  }
  void iniciarConfirmado()
}

async function iniciarConfirmado() {
  if (!store.sesion?.hostToken) return
  cargando.value = true
  error.value = null
  try {
    if (intervalo) window.clearInterval(intervalo)
    await api.iniciarSala(store.sesion.roomId, store.sesion.hostToken)
    await refrescarEstado()
    iniciarPolling()
  } catch (e) {
    error.value = e instanceof ApiFallo ? e.message : 'No se pudo iniciar la partida.'
    confirmandoInicio.value = false
    // Se perdio el sondeo al pararlo arriba; se rearma para no dejar la sala
    // ciega tras un fallo al iniciar.
    intervalo = window.setInterval(refrescarMetadata, 1500)
  } finally {
    cargando.value = false
  }
}

function nombreAnfitrion(): string {
  return metadata.value?.seats.find((a) => a.player_index === 0)?.nombre ?? 'el anfitrión'
}
</script>

<template>
  <div class="sala">
    <header class="cabecera">
      <div>
        <p class="eyebrow">Sala de espera</p>
        <h1 class="dato codigo">
          {{ roomId }}
          <!-- Le recuerda al host por que nadie la encuentra en el listado: sin
               esto, "no entra nadie" y "la marque privada" son indistinguibles
               desde esta pantalla. -->
          <span v-if="metadata?.privada" class="marca privada">{{ SALA_PRIVADA_CHIP }}</span>
        </h1>
      </div>
      <div class="botones-copia">
        <button type="button" @click="copiar('codigo')">
          {{ copiado === 'codigo' ? '¡Copiado!' : 'Copiar código' }}
        </button>
        <button type="button" @click="copiar('enlace')">
          {{ copiado === 'enlace' ? '¡Copiado!' : 'Copiar enlace' }}
        </button>
      </div>
    </header>

    <p class="compartir">{{ SALA_COMPARTIR }}</p>

    <ul class="asientos">
      <li
        v-for="asiento in metadata?.seats ?? []"
        :key="asiento.player_index"
        class="asiento"
        :style="{ '--color-asiento': hexDeColor(asiento.color) }"
      >
        <span class="ico-m" aria-hidden="true"><IconoPeon :color="hexDeColor(asiento.color)" /></span>
        <span class="nombre">{{ asiento.nombre }}</span>
        <span class="etiquetas">
          <span v-if="asiento.player_index === 0" class="marca anfitrion">Anfitrión</span>
          <span v-if="asiento.player_index === store.sesion?.playerIndex" class="marca tu">Tú</span>
        </span>
      </li>
      <li v-for="n in huecosVacios()" :key="`vacio-${n}`" class="asiento vacio">
        <span class="ico-m" aria-hidden="true"><IconoPeon color="var(--borde-fuerte)" /></span>
        <span class="nombre">{{ SALA_ASIENTO_VACIO }}</span>
      </li>
    </ul>

    <template v-if="store.sesion?.hostToken">
      <button v-if="!confirmandoInicio" class="primario" :disabled="cargando" @click="intentarIniciar">
        Iniciar partida ({{ metadata?.seats.length ?? 0 }}/{{ metadata?.max_jugadores ?? '—' }} jugadores)
      </button>
      <div v-else class="confirmacion-inicio">
        <p class="aviso">
          Solo hay {{ metadata?.seats.length ?? 0 }} de {{ metadata?.max_jugadores ?? '—' }} jugadores
          configurados. ¿Iniciar de todas formas?
        </p>
        <div class="botones-confirmacion">
          <button :disabled="cargando" @click="confirmandoInicio = false">Cancelar</button>
          <button class="primario" :disabled="cargando" @click="iniciarConfirmado">
            Sí, iniciar con {{ metadata?.seats.length ?? 0 }}
          </button>
        </div>
      </div>
    </template>
    <p v-else class="esperando">Esperando a que {{ nombreAnfitrion() }} inicie la partida…</p>

    <p v-if="error" class="error" aria-live="polite">{{ error }}</p>

    <section class="mientras">
      <p class="eyebrow">{{ SALA_MIENTRAS_ESPERAS }}</p>
      <TarjetasFases compacto />
      <p class="pie">
        <a href="#reglamento">{{ ENLACE_REGLAMENTO }} →</a>
        <span class="caducidad">Una sala sin actividad se cierra a los {{ MINUTOS_EXPIRACION_LOBBY }} minutos.</span>
      </p>
    </section>
  </div>
</template>

<style scoped>
.sala {
  max-width: 720px;
  margin: 0 auto;
  text-align: left;
}

.cabecera {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--e3);
}

.codigo {
  margin: 0;
  font-size: var(--t-display);
  letter-spacing: 0.14em;
  color: var(--cobre);
}

.botones-copia {
  display: flex;
  gap: var(--e2);
}

.botones-copia button {
  padding: var(--e2) var(--e3);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: var(--zona);
  color: var(--tinta);
  font-family: inherit;
  font-size: var(--t-s);
  cursor: pointer;
}

.botones-copia button:hover {
  border-color: var(--borde-fuerte);
}

.compartir {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  margin: var(--e2) 0 var(--e4);
}

.asientos {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--e4);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--e2);
}

.asiento {
  display: flex;
  align-items: center;
  gap: var(--e2);
  padding: var(--e2) var(--e3);
  background: var(--carta);
  border: 1px solid var(--borde);
  border-left: 3px solid var(--color-asiento, var(--borde));
  border-radius: var(--r-carta);
  min-height: 52px;
}

.asiento.vacio {
  background: transparent;
  border: 1px dashed var(--borde);
  color: var(--tinta-tenue);
  font-size: var(--t-s);
}

.asiento.vacio .ico-m {
  opacity: 0.35;
}

.nombre {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: anywhere;
}

.etiquetas {
  display: flex;
  gap: var(--e1);
  flex: 0 0 auto;
}

.marca {
  font-size: var(--t-micro);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2px var(--e1);
  border-radius: var(--r-control);
}

.marca.anfitrion {
  color: var(--cobre);
  background: var(--lavado-cobre);
}

.marca.tu {
  color: var(--verdin);
  background: var(--lavado-verdin);
}

.marca.privada {
  vertical-align: middle;
  margin-left: var(--e2);
  color: var(--tinta-tenue);
  background: var(--zona);
  border: 1px solid var(--borde);
  font-family: var(--fuente);
  letter-spacing: normal;
}

button.primario {
  width: 100%;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--cobre);
  background: var(--cobre);
  color: var(--tinta-sobre-acento);
  font-family: inherit;
  font-size: var(--t-m);
  font-weight: 600;
  cursor: pointer;
}

button.primario:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.esperando {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  text-align: center;
  margin: 0;
}

.confirmacion-inicio {
  border: 1px solid var(--riesgo);
  border-radius: var(--r-control);
  padding: var(--e2) var(--e3);
}

.confirmacion-inicio .aviso {
  margin: 0 0 var(--e2);
  font-size: var(--t-s);
}

.botones-confirmacion {
  display: flex;
  gap: var(--e2);
}

.botones-confirmacion button {
  flex: 1;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: var(--zona);
  color: var(--tinta);
  font-family: inherit;
  cursor: pointer;
}

.error {
  color: var(--riesgo);
  font-size: var(--t-s);
  margin-top: var(--e3);
}

.mientras {
  margin-top: var(--e6);
  padding-top: var(--e4);
  border-top: 1px solid var(--borde);
}

.mientras .eyebrow {
  margin-bottom: var(--e2);
}

.pie {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--e2);
  margin: var(--e3) 0 0;
}

.pie a {
  color: var(--cobre);
  font-weight: 600;
  font-size: var(--t-s);
}

.caducidad {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}
</style>
