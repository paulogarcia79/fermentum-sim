<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as api from '../api'
import { ApiFallo } from '../api'
import {
  establecerAlertaContaminacion,
  establecerSesion,
  iniciarPolling,
  refrescarEstado,
  store,
} from '../store'
import type { SalaMetadata } from '../api'
import { COLORES_JUGADOR, hexDeColor } from '../data/coloresJugador'

const NOMBRE_LONGITUD_MINIMA = 3
const JUGADORES_POSIBLES = [1, 2, 3, 4]

const nombre = ref('')
const codigoSala = ref('')
const colorSeleccionado = ref<string | null>(null)
const jugadoresObjetivo = ref(4)
const error = ref<string | null>(null)
const cargando = ref(false)
const enlaceCopiado = ref(false)
const llegoPorInvitacion = ref(false)
const confirmandoInicio = ref(false)

const salaCreada = ref<{ roomId: string; hostToken: string; nombre: string } | null>(null)
const metadata = ref<SalaMetadata | null>(null)
let intervaloLobby: number | undefined

// Colores ya tomados en la sala a la que se está por unir -- consultado en
// vivo mientras se escribe el código (GET /games/{id} es público, no
// requiere token) para no dejar elegir un color que el servidor va a
// rechazar de todas formas. Si dos jugadores chocan por una carrera real,
// unirse() igual maneja el error color_ya_tomado que devuelve el servidor.
const coloresTomadosAlUnirse = ref<Set<string>>(new Set())
watch(codigoSala, async (codigo) => {
  const limpio = codigo.trim().toUpperCase()
  if (limpio.length !== 6) {
    coloresTomadosAlUnirse.value = new Set()
    return
  }
  try {
    const meta = await api.verSala(limpio)
    coloresTomadosAlUnirse.value = new Set(meta.seats.map((a) => a.color))
  } catch {
    coloresTomadosAlUnirse.value = new Set()
  }
})

function colorDisponible(id: string): boolean {
  return !coloresTomadosAlUnirse.value.has(id)
}

async function entrarASalaDeEspera(roomId: string, hostToken: string, nombreJugador: string) {
  salaCreada.value = { roomId, hostToken, nombre: nombreJugador }
  await refrescarMetadata()
  intervaloLobby = window.setInterval(refrescarMetadata, 1500)
}

// Si App.vue ya recuperó una sesión guardada (localStorage, ver
// store.ts:intentarReconectar) y la sala seguía en LOBBY, store.sesion ya
// está poblado al montar este componente -- solo hace falta retomar la
// sala de espera con esos datos, sin volver a crear/unirse. Si no hay
// sesión previa, se revisa si se llegó por un enlace de invitación
// (?sala=CODIGO, ver el botón "Copiar enlace" en la sala de espera) para
// precargar el código de sala -- no hay ningún router en la app, así que
// esto es la única lectura de la URL que existe.
onMounted(() => {
  if (store.sesion) {
    void entrarASalaDeEspera(store.sesion.roomId, store.sesion.hostToken ?? '', store.sesion.nombre)
    return
  }
  const parametros = new URLSearchParams(window.location.search)
  const salaInvitacion = parametros.get('sala')
  if (salaInvitacion) {
    codigoSala.value = salaInvitacion.trim().toUpperCase()
    llegoPorInvitacion.value = true
    window.history.replaceState({}, '', window.location.pathname)
  }
})

function nombreValido(): boolean {
  if (!nombre.value.trim()) {
    error.value = 'Escribe tu nombre primero.'
    return false
  }
  if (nombre.value.trim().length < NOMBRE_LONGITUD_MINIMA) {
    error.value = `El nombre debe tener al menos ${NOMBRE_LONGITUD_MINIMA} caracteres.`
    return false
  }
  return true
}

async function crear() {
  if (!nombreValido()) return
  if (!colorSeleccionado.value) {
    error.value = 'Elige un color.'
    return
  }
  cargando.value = true
  error.value = null
  try {
    const r = await api.crearSala(nombre.value.trim(), colorSeleccionado.value, jugadoresObjetivo.value)
    establecerSesion({
      roomId: r.room_id,
      token: r.player_token,
      playerIndex: r.player_index,
      hostToken: r.host_token,
      nombre: nombre.value.trim(),
    })
    await entrarASalaDeEspera(r.room_id, r.host_token, nombre.value.trim())
  } catch (e) {
    error.value = e instanceof ApiFallo ? e.message : 'No se pudo crear la sala.'
  } finally {
    cargando.value = false
  }
}

async function unirse() {
  if (!codigoSala.value.trim()) {
    error.value = 'Escribe el código de sala.'
    return
  }
  if (!nombreValido()) return
  if (!colorSeleccionado.value) {
    error.value = 'Elige un color.'
    return
  }
  cargando.value = true
  error.value = null
  const roomId = codigoSala.value.trim().toUpperCase()
  try {
    const r = await api.unirseSala(roomId, nombre.value.trim(), colorSeleccionado.value)
    establecerSesion({
      roomId,
      token: r.player_token,
      playerIndex: r.player_index,
      hostToken: null,
      nombre: nombre.value.trim(),
    })
    await entrarASalaDeEspera(roomId, '', nombre.value.trim())
  } catch (e) {
    error.value = e instanceof ApiFallo ? e.message : 'No se pudo unir a la sala.'
  } finally {
    cargando.value = false
  }
}

async function copiarEnlace() {
  if (!salaCreada.value) return
  const url = `${window.location.origin}${window.location.pathname}?sala=${salaCreada.value.roomId}`
  try {
    await navigator.clipboard.writeText(url)
    enlaceCopiado.value = true
    window.setTimeout(() => {
      enlaceCopiado.value = false
    }, 1500)
  } catch {
    error.value = 'No se pudo copiar el enlace. Copia el código manualmente.'
  }
}

async function refrescarMetadata() {
  if (!salaCreada.value) return
  try {
    metadata.value = await api.verSala(salaCreada.value.roomId)
    if (metadata.value.status !== 'lobby') {
      // El host ya inicio la partida: pasar a juego.
      if (intervaloLobby) window.clearInterval(intervaloLobby)
      await refrescarEstado()
      iniciarPolling()
    }
  } catch {
    // La sala podria no existir mas; se ignora, el usuario vera el error al reintentar.
  }
}

// Si hay menos jugadores sentados que el objetivo configurado al crear la
// sala, se avisa antes de arrancar en vez de iniciar directo -- fácil de
// hacer sin querer con el botón a un click. Si ya se alcanzó el objetivo
// (el caso normal), arranca directo, igual que antes.
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
    if (intervaloLobby) window.clearInterval(intervaloLobby)
    await api.iniciarSala(store.sesion.roomId, store.sesion.hostToken)
    await refrescarEstado()
    iniciarPolling()
  } catch (e) {
    error.value = e instanceof ApiFallo ? e.message : 'No se pudo iniciar la partida.'
    confirmandoInicio.value = false
  } finally {
    cargando.value = false
  }
}

onUnmounted(() => {
  if (intervaloLobby) window.clearInterval(intervaloLobby)
})
</script>

<template>
  <div class="lobby">
    <h1>🍞 Fermentum</h1>
    <p class="subtitulo">Simulador de laboratorio de fermentación — multijugador</p>

    <div v-if="!salaCreada" class="flavor">
      <p>
        Eres la nueva investigadora jefa de un laboratorio artesanal de fermentación. Cada Día de
        Laboratorio cuidas tu cultivo base — su <strong>Vitalidad</strong> y su
        <strong>Acidez</strong> deciden si tu próxima hornada sale perfecta o colapsa —, inicias
        recetas en tus cámaras de fermentación y corres contra el reloj: cada masa avanza sola por
        el track de fermentación con el calor del día, y hornear justo en su zona óptima, ni cruda
        ni pasada, es lo que separa a un panadero mediocre de uno legendario. Investiga
        protocolos, negocia el mercado de insumos, mejora tu laboratorio, y acumula
        <strong>Puntos de Maestría</strong> — quien más sume al terminar la partida, gana.
      </p>
      <ul class="destacados">
        <li>🧫 Cultivo base — Vitalidad y Acidez, la base de cada receta</li>
        <li>⏳ Track de fermentación — hornea en la zona óptima antes del colapso</li>
        <li>🏆 Maestría — la puntuación final, entre investigadores rivales</li>
      </ul>
    </div>

    <div v-if="!salaCreada" class="panel formulario">
      <label>
        Tu nombre
        <input v-model="nombre" placeholder="Investigador α" maxlength="24" :minlength="NOMBRE_LONGITUD_MINIMA" />
      </label>

      <label class="campo-color">
        Tu color
        <div class="swatches">
          <button
            v-for="c in COLORES_JUGADOR"
            :key="c.id"
            type="button"
            class="swatch"
            :class="{ activo: colorSeleccionado === c.id }"
            :disabled="!colorDisponible(c.id)"
            :style="{ background: c.hex }"
            :title="colorDisponible(c.id) ? c.etiqueta : `${c.etiqueta} (ya elegido)`"
            @click="colorSeleccionado = c.id"
          />
        </div>
      </label>

      <label class="campo-alerta">
        <input
          type="checkbox"
          :checked="store.preferencias.alertaContaminacion"
          @change="establecerAlertaContaminacion(($event.target as HTMLInputElement).checked)"
        />
        <span>
          Avisarme si mi masa madre va a colapsar esta noche
          <small>Marca la Vitalidad en rojo y refuerza el aviso al pasar turno.</small>
        </span>
      </label>

      <div class="acciones-lobby">
        <template v-if="!llegoPorInvitacion">
          <label class="campo-jugadores">
            Jugadores en la sala
            <div class="swatches">
              <button
                v-for="n in JUGADORES_POSIBLES"
                :key="n"
                type="button"
                class="swatch-numero"
                :class="{ activo: jugadoresObjetivo === n }"
                @click="jugadoresObjetivo = n"
              >
                {{ n }}
              </button>
            </div>
          </label>
          <button class="primario" :disabled="cargando" @click="crear">Crear sala nueva</button>
          <div class="separador">o</div>
        </template>
        <label>
          Código de sala
          <input v-model="codigoSala" placeholder="ABC123" maxlength="6" style="text-transform: uppercase" />
        </label>
        <button :disabled="cargando" @click="unirse">Unirse a sala</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div v-else class="panel sala-espera">
      <div class="cabecera-sala">
        <h2>Sala {{ salaCreada.roomId }}</h2>
        <button type="button" class="copiar-enlace" @click="copiarEnlace">
          {{ enlaceCopiado ? '¡Copiado!' : 'Copiar enlace' }}
        </button>
      </div>
      <p class="subtitulo">Comparte el código o el enlace con el resto de investigadores.</p>

      <ul class="lista-asientos">
        <li v-for="asiento in metadata?.seats ?? []" :key="asiento.player_index">
          <span class="punto-color" :style="{ background: hexDeColor(asiento.color) }" />
          {{ asiento.nombre }}
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
      <p v-else class="subtitulo">Esperando a que el host inicie la partida…</p>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.lobby {
  max-width: 480px;
  margin: 3rem auto;
  text-align: center;
}

h1 {
  margin-bottom: 0;
  font-size: 2.2rem;
}

.subtitulo {
  color: var(--color-texto-tenue);
  margin-top: 0.25rem;
}

.formulario,
.sala-espera {
  margin-top: 1.5rem;
  text-align: left;
}

.flavor {
  margin-top: 1.25rem;
  text-align: left;
}

.flavor p {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-texto);
}

.flavor strong {
  color: var(--color-acento);
}

.destacados {
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
}

label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-texto-tenue);
}

/* Solo los campos de texto del formulario (nombre / código de sala). El
   :not() es necesario: sin el, un checkbox tambien heredaria width: 100% y
   se comeria toda la fila, empujando su etiqueta fuera del panel. */
input:not([type='checkbox']) {
  display: block;
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.5rem;
  background: var(--color-fondo);
  border: 1px solid var(--color-borde);
  border-radius: 4px;
  color: var(--color-texto);
  font-size: 1rem;
}

.campo-color {
  margin-bottom: 0.9rem;
}

.campo-alerta {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.campo-alerta input {
  /* `width: auto` explicito, igual que `.campo-checkbox input` en App.vue:
     la regla de arriba ya no le aplica, pero dejarlo escrito documenta el
     tamaño nativo y evita que cualquier otra regla vuelva a estirarla.
     flex-shrink: 0 para que la casilla no se aplaste cuando la etiqueta
     ocupa dos lineas. */
  width: auto;
  margin-top: 0.15rem;
  flex-shrink: 0;
  cursor: pointer;
}

.campo-alerta small {
  display: block;
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
  margin-top: 0.1rem;
}

.swatches {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.35rem;
}

.swatch {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
}

.swatch.activo {
  border-color: var(--color-texto);
}

.swatch:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.campo-jugadores {
  margin-bottom: 0.9rem;
}

.swatch-numero {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 4px;
  border: 2px solid var(--color-borde);
  background: var(--color-fondo);
  color: var(--color-texto);
  cursor: pointer;
  font-weight: 600;
}

.swatch-numero.activo {
  border-color: var(--color-acento);
  color: var(--color-acento);
}

button {
  width: 100%;
  padding: 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: var(--color-panel);
  color: var(--color-texto);
}

button.primario {
  background: var(--color-acento);
  border-color: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}

.separador {
  text-align: center;
  color: var(--color-texto-tenue);
  margin: 0.75rem 0;
}

.cabecera-sala {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.cabecera-sala h2 {
  margin: 0;
}

.copiar-enlace {
  width: auto;
  flex: 0 0 auto;
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
}

.lista-asientos {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}

.lista-asientos li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  background: var(--color-fondo);
  border-radius: 4px;
  margin-bottom: 0.35rem;
}

.punto-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.error {
  color: var(--color-mal);
  margin-top: 0.75rem;
}

.confirmacion-inicio {
  border: 1px solid var(--color-mal);
  border-radius: 4px;
  padding: 0.6rem 0.7rem;
}

.confirmacion-inicio .aviso {
  margin: 0 0 0.6rem;
  font-size: 0.85rem;
  color: var(--color-texto);
}

.botones-confirmacion {
  display: flex;
  gap: 0.5rem;
}
</style>
