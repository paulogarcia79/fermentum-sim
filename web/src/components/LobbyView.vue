<script setup lang="ts">
// Interruptor entre las dos mitades de la pre-partida: la portada
// (LandingView, con el formulario) y la sala de espera (SalaEsperaView).
//
// Antes las dos vivian en este mismo fichero, 577 lineas con un `salaCreada`
// booleano en medio. Se partieron porque son dos pantallas distintas con dos
// trabajos distintos -- una convence, la otra hace esperar -- y porque la
// portada necesitaba crecer.
//
// Lo unico que queda aqui, ademas del interruptor, es la lectura del enlace
// de invitacion: no hay router en la app, asi que esta es la unica lectura de
// la query string que existe.
import { ref } from 'vue'
import { store } from '../store'
import LandingView from './LandingView.vue'
import SalaEsperaView from './SalaEsperaView.vue'

// OJO: esto va en el cuerpo del setup y NO en `onMounted`. Los hijos montan
// ANTES que el padre, asi que un `onMounted` aqui rellenaria
// `codigoInvitacion` cuando FormularioSala ya ha leido la prop -- el enlace
// de invitacion abria la pestaña "Crear sala" con el codigo vacio. Cuando
// esto era un unico componente de 577 lineas el problema no existia; partirlo
// lo saco a la luz.
function leerSesionGuardada(): string | null {
  // Si App.vue ya recupero una sesion guardada (localStorage, ver
  // store.ts:intentarReconectar) y la sala seguia en LOBBY, store.sesion ya
  // esta poblado -- solo hay que retomar la sala de espera.
  return store.sesion?.roomId ?? null
}

function leerCodigoDeInvitacion(): string | null {
  if (store.sesion) return null
  const salaInvitacion = new URLSearchParams(window.location.search).get('sala')
  if (!salaInvitacion) return null
  // Se limpia la URL pero se conserva el hash: si alguien llega con
  // `?sala=X#reglamento`, la vista del reglamento no debe desaparecer.
  window.history.replaceState({}, '', window.location.pathname + window.location.hash)
  return salaInvitacion.trim().toUpperCase()
}

const salaActual = ref<string | null>(leerSesionGuardada())
const codigoInvitacion = ref<string | null>(leerCodigoDeInvitacion())

function alEntrar(datos: { roomId: string }) {
  salaActual.value = datos.roomId
}
</script>

<template>
  <SalaEsperaView v-if="salaActual" :room-id="salaActual" />
  <LandingView v-else :codigo-invitacion="codigoInvitacion" @entrar="alEntrar" />
</template>
