<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import * as api from '../api'
import { ApiFallo } from '../api'
import { establecerSesion, iniciarPolling, refrescarEstado, store } from '../store'
import type { SalaMetadata } from '../api'

const nombre = ref('')
const codigoSala = ref('')
const error = ref<string | null>(null)
const cargando = ref(false)

const salaCreada = ref<{ roomId: string; hostToken: string; nombre: string } | null>(null)
const metadata = ref<SalaMetadata | null>(null)
let intervaloLobby: number | undefined

async function entrarASalaDeEspera(roomId: string, hostToken: string, nombreJugador: string) {
  salaCreada.value = { roomId, hostToken, nombre: nombreJugador }
  await refrescarMetadata()
  intervaloLobby = window.setInterval(refrescarMetadata, 1500)
}

// Si App.vue ya recuperó una sesión guardada (localStorage, ver
// store.ts:intentarReconectar) y la sala seguía en LOBBY, store.sesion ya
// está poblado al montar este componente -- solo hace falta retomar la
// sala de espera con esos datos, sin volver a crear/unirse.
onMounted(() => {
  if (store.sesion) {
    void entrarASalaDeEspera(store.sesion.roomId, store.sesion.hostToken ?? '', store.sesion.nombre)
  }
})

async function crear() {
  if (!nombre.value.trim()) {
    error.value = 'Escribe tu nombre primero.'
    return
  }
  cargando.value = true
  error.value = null
  try {
    const r = await api.crearSala(nombre.value.trim())
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
  if (!nombre.value.trim() || !codigoSala.value.trim()) {
    error.value = 'Escribe tu nombre y el código de sala.'
    return
  }
  cargando.value = true
  error.value = null
  const roomId = codigoSala.value.trim().toUpperCase()
  try {
    const r = await api.unirseSala(roomId, nombre.value.trim())
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

async function iniciar() {
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
    <p class="subtitulo">Simulador de laboratorio de panadería — multijugador</p>

    <div v-if="!salaCreada" class="panel formulario">
      <label>
        Tu nombre
        <input v-model="nombre" placeholder="Investigador α" maxlength="24" />
      </label>

      <div class="acciones-lobby">
        <button class="primario" :disabled="cargando" @click="crear">Crear sala nueva</button>
        <div class="separador">o</div>
        <label>
          Código de sala
          <input v-model="codigoSala" placeholder="ABC123" maxlength="6" style="text-transform: uppercase" />
        </label>
        <button :disabled="cargando" @click="unirse">Unirse a sala</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div v-else class="panel sala-espera">
      <h2>Sala {{ salaCreada.roomId }}</h2>
      <p class="subtitulo">Comparte este código con el resto de investigadores.</p>

      <ul class="lista-asientos">
        <li v-for="asiento in metadata?.seats ?? []" :key="asiento.player_index">
          {{ asiento.nombre }}
        </li>
      </ul>

      <button v-if="store.sesion?.hostToken" class="primario" :disabled="cargando" @click="iniciar">
        Iniciar partida ({{ metadata?.seats.length ?? 0 }} jugador{{ (metadata?.seats.length ?? 0) === 1 ? '' : 'es' }})
      </button>
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

label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-texto-tenue);
}

input {
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

.lista-asientos {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}

.lista-asientos li {
  padding: 0.4rem 0.6rem;
  background: var(--color-fondo);
  border-radius: 4px;
  margin-bottom: 0.35rem;
}

.error {
  color: var(--color-mal);
  margin-top: 0.75rem;
}
</style>
