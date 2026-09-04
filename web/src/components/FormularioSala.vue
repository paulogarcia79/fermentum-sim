<script setup lang="ts">
// La tarjeta de crear/unirse. Es lo unico que se levanta de la mesa en la
// portada, asi que usa la superficie --carta.
//
// Antes crear y unirse convivian en un solo formulario separado por un "o",
// con dos botones de aspecto casi igual y todos los campos siempre visibles.
// Ahora hay un control segmentado: los campos compartidos (nombre, color)
// estan arriba y solo se muestra lo propio del modo elegido, de forma que hay
// UNA accion primaria en pantalla en cada momento.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { reproducirAvisoSalaNueva } from '../sonido'
import * as api from '../api'
import { ApiFallo } from '../api'
import type { SalaAbierta, SalaMetadata } from '../api'
import { establecerAlertaContaminacion, establecerSesion, store } from '../store'
import { COLORES_JUGADOR, hexDeColor } from '../data/coloresJugador'
import { SALA_PRIVADA_ETIQUETA, SALA_PRIVADA_NOTA } from '../data/copyLanding'
import IconoPeon from './IconoPeon.vue'
import SalasAbiertas from './SalasAbiertas.vue'

const NOMBRE_LONGITUD_MINIMA = 3
const JUGADORES_POSIBLES = [1, 2, 3, 4]
const LONGITUD_CODIGO = 6

const props = defineProps<{ codigoInvitacion: string | null }>()
const emit = defineEmits<{ entrar: [{ roomId: string; hostToken: string; nombre: string }] }>()

type Modo = 'crear' | 'unirse'
const modo = ref<Modo>('crear')

const nombre = ref('')
const codigoSala = ref('')
const colorSeleccionado = ref<string | null>(null)
const jugadoresObjetivo = ref(4)
const privada = ref(false)
const cargando = ref(false)

// Tres errores separados en vez de uno compartido: cada mensaje se pinta
// debajo del campo al que se refiere, que es donde se mira despues de que un
// boton no haga nada.
const errorNombre = ref<string | null>(null)
const errorColor = ref<string | null>(null)
const errorEnvio = ref<string | null>(null)

// --- Listado de salas abiertas -------------------------------------------
//
// El sondeo vive AQUI y no dentro de SalasAbiertas.vue aunque solo ese panel
// dibuje la lista: la pestaña "Unirse" lleva el numero de salas en la propia
// etiqueta, asi que quien esta en "Crear sala" tambien tiene que enterarse de
// que hay partidas esperando sin cambiar de pestaña. Como el panel se monta y
// desmonta con la pestaña, dejarlo alli apagaria justo el contador que sirve
// para descubrirlo.
const SONDEO_SALAS_MS = 3000
/** Cuanto se queda resaltada una sala recien aparecida. */
const DURACION_RESALTE_MS = 6000
/** Cuanto pulsa la insignia de la pestaña. Basta con que se note el cambio. */
const DURACION_PULSO_MS = 1200

const salasAbiertas = ref<SalaAbierta[]>([])
const salasRecientes = ref<Set<string>>(new Set())
const insigniaPulsando = ref(false)
let sondeoSalas: number | undefined
const temporizadores: number[] = []

// Ids ya vistos, NO reactivo: solo sirve para calcular la diferencia entre dos
// sondeos, nada lo pinta. Empieza sin sembrar y `primerSondeo` decide.
let conocidas = new Set<string>()
// Las salas que ya existian al abrir la pagina no son un evento: avisar de
// ellas al cargar seria confundir "esto acaba de pasar" con "esto ya estaba".
// Misma regla que store.ts aplica al aviso de turno y a la fanfarria de fin de
// partida con `sembrarEstadoSinSonido` -- una reconexion no es una transicion.
let primerSondeo = true

const tituloBase = document.title

function avisarDeSalasNuevas(nuevas: string[]) {
  // Un solo sonido por tanda: si aparecen tres salas a la vez, tres pitidos
  // encadenados suenan a error, no a aviso.
  if (store.preferencias.sonido) reproducirAvisoSalaNueva()

  const conResalte = new Set(salasRecientes.value)
  for (const id of nuevas) conResalte.add(id)
  salasRecientes.value = conResalte

  insigniaPulsando.value = true
  temporizadores.push(
    window.setTimeout(() => (insigniaPulsando.value = false), DURACION_PULSO_MS),
  )
  temporizadores.push(
    window.setTimeout(() => {
      const restantes = new Set(salasRecientes.value)
      for (const id of nuevas) restantes.delete(id)
      salasRecientes.value = restantes
    }, DURACION_RESALTE_MS),
  )
}

async function refrescarSalas() {
  try {
    const salas = (await api.listarSalas()).salas
    salasAbiertas.value = salas

    const ids = new Set(salas.map((sala) => sala.room_id))
    const nuevas = [...ids].filter((id) => !conocidas.has(id))
    // Se reemplaza entero en vez de acumular: asi una sala que se cierra y otra
    // que abre despues son las dos un cambio limpio de diferencia de conjuntos.
    conocidas = ids
    if (primerSondeo) {
      primerSondeo = false
      return
    }
    if (nuevas.length) avisarDeSalasNuevas(nuevas)
  } catch {
    // Un fallo de red deja la lista como estaba: es informacion de apoyo, no
    // vale la pena gritarlo encima del formulario.
  }
}

// El titulo de la pestaña es el unico canal que llega a alguien que se fue a
// otra pestaña -- que es exactamente lo que hace quien espera a que alguien
// abra una sala. El sonido no basta: sin un gesto previo en la pestaña el
// navegador no deja crear el AudioContext (ver sonido.ts:habilitarAudio).
watch(
  () => salasAbiertas.value.length,
  (n) => {
    document.title = n > 0 ? `(${n}) ${tituloBase}` : tituloBase
  },
)

onMounted(() => {
  // Quien llega por un enlace de invitacion viene a unirse, no a crear.
  if (props.codigoInvitacion) {
    codigoSala.value = props.codigoInvitacion
    modo.value = 'unirse'
  }
  void refrescarSalas()
  sondeoSalas = window.setInterval(refrescarSalas, SONDEO_SALAS_MS)
})

onUnmounted(() => {
  if (sondeoSalas) window.clearInterval(sondeoSalas)
  for (const t of temporizadores) window.clearTimeout(t)
  document.title = tituloBase
})

/** Elegir una sala de la lista rellena el codigo; el watcher de abajo hace el
 * resto (vista previa y colores tomados), asi que no hay una segunda ruta. */
function elegirSala(roomId: string) {
  codigoSala.value = roomId
}

// --- Vista previa de la sala a la que se va a entrar ----------------------
//
// GET /games/{id} es publico (no pide token), asi que en cuanto el codigo
// esta completo se puede enseñar quien hay dentro y que colores quedan. Sirve
// para tres cosas a la vez: confirmar que el codigo esta bien tecleado, no
// dejar elegir un color que el servidor va a rechazar, y avisar de una sala ya
// empezada antes de gastar un click. Si hay una carrera real, unirse() sigue
// manejando el error color_ya_tomado del servidor, que es la autoridad.
const vistaPrevia = ref<SalaMetadata | null>(null)
const errorCodigo = ref<string | null>(null)
const consultandoCodigo = ref(false)

const codigoLimpio = computed(() => codigoSala.value.trim().toUpperCase())

watch(codigoLimpio, async (codigo) => {
  vistaPrevia.value = null
  errorCodigo.value = null
  // Nada de mensajes mientras se teclea: solo con el codigo entero.
  if (codigo.length !== LONGITUD_CODIGO) {
    consultandoCodigo.value = false
    return
  }
  consultandoCodigo.value = true
  try {
    const meta = await api.verSala(codigo)
    // Descartar una respuesta que ya no corresponde a lo escrito (el usuario
    // pudo seguir tecleando mientras volaba la peticion).
    if (codigoLimpio.value !== codigo) return
    vistaPrevia.value = meta
    if (meta.status !== 'lobby') {
      errorCodigo.value = 'Esta partida ya empezó. Pide otro código.'
    }
  } catch {
    if (codigoLimpio.value !== codigo) return
    errorCodigo.value = 'No existe ninguna sala con ese código.'
  } finally {
    if (codigoLimpio.value === codigo) consultandoCodigo.value = false
  }
})

const coloresTomados = computed(
  () => new Set((modo.value === 'unirse' ? vistaPrevia.value?.seats ?? [] : []).map((a) => a.color)),
)

function colorDisponible(id: string): boolean {
  return !coloresTomados.value.has(id)
}

// Si el color elegido resulta estar tomado en la sala que se acaba de
// consultar, se suelta la eleccion en vez de dejar seleccionado un swatch
// deshabilitado.
watch(coloresTomados, (tomados) => {
  if (colorSeleccionado.value && tomados.has(colorSeleccionado.value)) {
    colorSeleccionado.value = null
  }
})

// --- Validacion y envio ---------------------------------------------------

function camposValidos(): boolean {
  errorNombre.value = null
  errorColor.value = null
  errorEnvio.value = null
  let ok = true
  const limpio = nombre.value.trim()
  if (!limpio) {
    errorNombre.value = 'Escribe tu nombre primero.'
    ok = false
  } else if (limpio.length < NOMBRE_LONGITUD_MINIMA) {
    errorNombre.value = `El nombre debe tener al menos ${NOMBRE_LONGITUD_MINIMA} caracteres.`
    ok = false
  }
  if (!colorSeleccionado.value) {
    errorColor.value = 'Elige un color.'
    ok = false
  }
  return ok
}

async function crear() {
  if (!camposValidos()) return
  cargando.value = true
  try {
    const r = await api.crearSala(
      nombre.value.trim(),
      colorSeleccionado.value!,
      jugadoresObjetivo.value,
      privada.value,
    )
    establecerSesion({
      roomId: r.room_id,
      token: r.player_token,
      playerIndex: r.player_index,
      hostToken: r.host_token,
      nombre: nombre.value.trim(),
    })
    emit('entrar', { roomId: r.room_id, hostToken: r.host_token, nombre: nombre.value.trim() })
  } catch (e) {
    errorEnvio.value = e instanceof ApiFallo ? e.message : 'No se pudo crear la sala.'
  } finally {
    cargando.value = false
  }
}

async function unirse() {
  errorEnvio.value = null
  if (!codigoLimpio.value) {
    errorCodigo.value = 'Escribe el código de sala.'
    return
  }
  if (!camposValidos()) return
  cargando.value = true
  const roomId = codigoLimpio.value
  try {
    const r = await api.unirseSala(roomId, nombre.value.trim(), colorSeleccionado.value!)
    establecerSesion({
      roomId,
      token: r.player_token,
      playerIndex: r.player_index,
      hostToken: null,
      nombre: nombre.value.trim(),
    })
    emit('entrar', { roomId, hostToken: '', nombre: nombre.value.trim() })
  } catch (e) {
    errorEnvio.value = e instanceof ApiFallo ? e.message : 'No se pudo unir a la sala.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <section class="tarjeta-sala">
    <div class="segmentado" role="tablist" aria-label="Crear o unirse a una sala">
      <button
        type="button"
        role="tab"
        :aria-selected="modo === 'crear'"
        :class="{ activo: modo === 'crear' }"
        @click="modo = 'crear'"
      >
        Crear sala
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="modo === 'unirse'"
        :class="{ activo: modo === 'unirse' }"
        @click="modo = 'unirse'"
      >
        Unirse
        <!-- El contador esta en la pestaña, no solo dentro del panel, para que
             quien esta en "Crear sala" vea que hay partidas esperando. -->
        <span
          v-if="salasAbiertas.length"
          class="dato insignia"
          :class="{ pulso: insigniaPulsando }"
          >{{ salasAbiertas.length }}</span
        >
      </button>
    </div>

    <label class="campo">
      Tu nombre
      <input
        v-model="nombre"
        maxlength="24"
        autocomplete="nickname"
        placeholder="Ada"
        :aria-invalid="errorNombre !== null"
        @input="errorNombre = null"
      />
    </label>
    <p v-if="errorNombre" class="error" aria-live="polite">{{ errorNombre }}</p>

    <fieldset class="campo-color">
      <legend>Tu color</legend>
      <div class="swatches">
        <button
          v-for="c in COLORES_JUGADOR"
          :key="c.id"
          type="button"
          class="swatch"
          :class="{ activo: colorSeleccionado === c.id }"
          :disabled="!colorDisponible(c.id)"
          :style="{ background: c.hex }"
          :aria-pressed="colorSeleccionado === c.id"
          :aria-label="colorDisponible(c.id) ? c.etiqueta : `${c.etiqueta} (ya elegido)`"
          :title="colorDisponible(c.id) ? c.etiqueta : `${c.etiqueta} (ya elegido)`"
          @click="((colorSeleccionado = c.id), (errorColor = null))"
        >
          <!-- Marca visible ademas del anillo: la seleccion no puede
               distinguirse solo por color en un selector DE colores. -->
          <svg v-if="colorSeleccionado === c.id" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M5 12.5 L10 17.5 L19 7"
              fill="none"
              stroke="var(--tinta-sobre-acento)"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>
    </fieldset>
    <p v-if="errorColor" class="error" aria-live="polite">{{ errorColor }}</p>

    <!-- --- Crear ------------------------------------------------------- -->
    <template v-if="modo === 'crear'">
      <fieldset class="campo-color">
        <legend>Jugadores en la sala</legend>
        <div class="swatches">
          <button
            v-for="n in JUGADORES_POSIBLES"
            :key="n"
            type="button"
            class="swatch-numero dato"
            :class="{ activo: jugadoresObjetivo === n }"
            :aria-pressed="jugadoresObjetivo === n"
            @click="jugadoresObjetivo = n"
          >
            {{ n }}
          </button>
        </div>
      </fieldset>

      <label class="campo-alerta">
        <input v-model="privada" type="checkbox" />
        <span>
          {{ SALA_PRIVADA_ETIQUETA }}
          <small>{{ SALA_PRIVADA_NOTA }}</small>
        </span>
      </label>

      <button class="primario" :disabled="cargando" @click="crear">
        {{ cargando ? 'Creando…' : 'Crear sala' }}
      </button>
    </template>

    <!-- --- Unirse ------------------------------------------------------ -->
    <template v-else>
      <SalasAbiertas
        :salas="salasAbiertas"
        :recientes="salasRecientes"
        @elegir="elegirSala"
        @crear="modo = 'crear'"
      />

      <label class="campo">
        Código de sala
        <input
          v-model="codigoSala"
          class="entrada-codigo dato"
          maxlength="6"
          placeholder="K7MPX3"
          autocapitalize="characters"
          autocomplete="off"
          spellcheck="false"
          :aria-invalid="errorCodigo !== null"
        />
      </label>

      <p v-if="errorCodigo" class="error" aria-live="polite">{{ errorCodigo }}</p>

      <div v-else-if="vistaPrevia" class="vista-previa" aria-live="polite">
        <p class="cabecera-previa">
          <span class="dato">Sala {{ vistaPrevia.room_id }}</span>
          <span class="conteo dato">{{ vistaPrevia.seats.length }}/{{ vistaPrevia.max_jugadores }}</span>
        </p>
        <ul>
          <li v-for="asiento in vistaPrevia.seats" :key="asiento.player_index">
            <span class="ico-xs" aria-hidden="true">
              <IconoPeon :color="hexDeColor(asiento.color)" />
            </span>
            {{ asiento.nombre }}
          </li>
        </ul>
      </div>

      <button class="primario" :disabled="cargando || consultandoCodigo" @click="unirse">
        {{ cargando ? 'Uniéndose…' : 'Unirse a la sala' }}
      </button>
    </template>

    <p v-if="errorEnvio" class="error" aria-live="polite">{{ errorEnvio }}</p>

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
  </section>
</template>

<style scoped>
.tarjeta-sala {
  background: var(--carta);
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-zona);
  box-shadow: var(--sombra-carta);
  padding: var(--e4);
  text-align: left;
}

.segmentado {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--e1);
  padding: var(--e1);
  background: var(--mesa);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  margin-bottom: var(--e4);
}

.segmentado button {
  padding: var(--e2);
  border: none;
  border-radius: var(--r-control);
  background: transparent;
  color: var(--tinta-tenue);
  font-family: inherit;
  font-size: var(--t-s);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transicion), color var(--transicion);
}

.segmentado button.activo {
  background: var(--zona);
  color: var(--cobre);
}

.insignia {
  display: inline-block;
  margin-left: var(--e1);
  padding: 0 var(--e1);
  border-radius: 999px;
  background: var(--lavado-cobre);
  color: var(--cobre);
  font-size: var(--t-micro);
}

/* El pulso avisa desde la pestaña "Crear sala", que es donde el panel de
   salas ni siquiera esta montado. @keyframes por lo mismo que el resalte de
   la fila: la regla global de prefers-reduced-motion lo recorta sola. */
.insignia.pulso {
  animation: pulso-insignia 0.4s ease-out 3;
}

@keyframes pulso-insignia {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.25);
  }
}

/* La casilla de "Sala privada" vive dentro del panel de crear, asi que no
   lleva la linea superior que separa la de la alerta de contaminacion. */
.campo-color + .campo-alerta {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.campo-color {
  border: none;
  padding: 0;
  margin: 0 0 var(--e3);
}

.campo-color legend {
  padding: 0;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  margin-top: var(--e2);
}

.swatch,
.swatch-numero {
  /* 36px + 8px de hueco: el objetivo real ronda los 44px recomendados sin
     que los circulos se vean como botones de barra. */
  width: 36px;
  height: 36px;
  padding: 0;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.swatch {
  border-radius: 50%;
  border: 2px solid transparent;
}

.swatch svg {
  width: 18px;
  height: 18px;
}

.swatch.activo {
  border-color: var(--tinta);
}

.swatch:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.swatch-numero {
  border-radius: var(--r-control);
  border: 2px solid var(--borde);
  background: var(--mesa);
  color: var(--tinta);
  font-weight: 600;
}

.swatch-numero.activo {
  border-color: var(--cobre);
  color: var(--cobre);
}

.entrada-codigo {
  text-transform: uppercase;
  letter-spacing: 0.18em;
}

.vista-previa {
  background: var(--mesa);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  padding: var(--e2) var(--e3);
  margin-bottom: var(--e3);
  font-size: var(--t-s);
}

.cabecera-previa {
  display: flex;
  justify-content: space-between;
  gap: var(--e2);
  margin: 0 0 var(--e2);
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.conteo {
  color: var(--cobre);
}

.vista-previa ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--e1) var(--e3);
}

.vista-previa li {
  display: flex;
  align-items: center;
  gap: var(--e1);
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

.campo-alerta {
  display: flex;
  align-items: flex-start;
  gap: var(--e2);
  margin: var(--e4) 0 0;
  padding-top: var(--e3);
  border-top: 1px solid var(--borde);
  cursor: pointer;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.campo-alerta input {
  width: auto;
  margin-top: var(--e1);
  flex-shrink: 0;
  cursor: pointer;
}

.campo-alerta small {
  display: block;
  font-size: var(--t-xs);
  margin-top: var(--e1);
}

.error {
  color: var(--riesgo);
  font-size: var(--t-s);
  margin: calc(-1 * var(--e2)) 0 var(--e3);
}
</style>
