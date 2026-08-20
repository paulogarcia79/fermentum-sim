// store.ts -- estado reactivo compartido por toda la app.
//
// Sin Pinia/Vuex: el servidor siempre manda el snapshot completo (no
// deltas), asi que un solo objeto reactive() actualizado por
// aplicarEstado() alcanza. Sin actualizaciones optimistas: cada accion
// espera la respuesta del servidor antes de re-renderizar -- un juego por
// turnos no tiene presupuesto de latencia que justifique la complejidad.

import { reactive } from 'vue'
import * as api from './api'
import type { GameEventView, GameStateView } from './types'

export interface Sesion {
  roomId: string
  token: string
  playerIndex: number
  hostToken: string | null
  nombre: string
}

interface Store {
  sesion: Sesion | null
  estado: GameStateView | null
  eventos: GameEventView[]
  ultimoSeqVisto: number
  error: string | null
  cargando: boolean
  /** Dia que acaba de concluir y cuyo reporte de Fase III aun no fue
   * reconocido por el jugador -- null cuando no hay ninguno pendiente. */
  reporteDiaPendiente: number | null
}

export const store: Store = reactive({
  sesion: null,
  estado: null,
  eventos: [],
  ultimoSeqVisto: 0,
  error: null,
  cargando: false,
  reporteDiaPendiente: null,
})

let manejadorEstado: number | undefined
let manejadorEventosRespaldo: number | undefined
let fuenteEventos: EventSource | null = null

// Cadencia de respaldo una vez que SSE es la via principal de empuje --
// mas lenta que el 1s de la Milestone 4 porque ya no es la unica forma en
// que el cliente se entera de cambios; sigue existiendo para el caso en
// que la conexion SSE falle en silencio (ver iniciarEventSource).
const INTERVALO_RESPALDO_ESTADO_MS = 4000
const INTERVALO_RESPALDO_EVENTOS_MS = 15000

export function establecerSesion(s: Sesion): void {
  store.sesion = s
}

export function cerrarSesion(): void {
  detenerTransmisionEnVivo()
  store.sesion = null
  store.estado = null
  store.eventos = []
  store.ultimoSeqVisto = 0
  store.error = null
  store.reporteDiaPendiente = null
}

export function aplicarEstado(nuevo: GameStateView): void {
  const diaAnterior = store.estado?.environment.dia_actual
  if (diaAnterior !== undefined && nuevo.environment.dia_actual > diaAnterior) {
    store.reporteDiaPendiente = diaAnterior
  }
  store.estado = nuevo
}

export function reconocerReporteDia(): void {
  store.reporteDiaPendiente = null
}

export async function refrescarEstado(): Promise<void> {
  if (!store.sesion) return
  try {
    aplicarEstado(await api.obtenerEstado(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  }
}

export async function refrescarEventos(): Promise<void> {
  if (!store.sesion) return
  try {
    const r = await api.obtenerEventos(store.sesion.roomId, store.sesion.token, store.ultimoSeqVisto)
    if (r.eventos.length > 0) {
      store.eventos.push(...r.eventos)
      store.ultimoSeqVisto = r.seq
    }
  } catch {
    // El polling de eventos es secundario: un fallo aqui no debe tapar el
    // error (mas importante) del polling de estado.
  }
}

/**
 * Abre la conexión SSE (Milestone 5) a GET /games/{id}/events/stream. El
 * navegador (EventSource) no puede enviar cabeceras personalizadas, así
 * que el token va como ?player_token= en la URL -- ver
 * server/app.py:_requerir_token_sse. Cada evento recibido dispara de
 * inmediato un refrescarEstado() (el evento casi siempre implica que el
 * estado cambió; no tiene sentido esperar al próximo tick de respaldo).
 *
 * EventSource reconecta solo, con backoff propio del navegador, y reenvía
 * Last-Event-ID automáticamente para retomar donde se quedó -- por eso el
 * polling de eventos (arriba) se mantiene solo como respaldo lento, no
 * como vía principal.
 */
function iniciarEventSource(): void {
  if (!store.sesion) return
  fuenteEventos?.close()

  const url =
    `/games/${store.sesion.roomId}/events/stream` +
    `?since=${store.ultimoSeqVisto}&player_token=${encodeURIComponent(store.sesion.token)}`
  const es = new EventSource(url)

  es.onmessage = (mensaje) => {
    try {
      const evento = JSON.parse(mensaje.data)
      store.eventos.push(evento)
      const seq = Number(mensaje.lastEventId)
      if (!Number.isNaN(seq)) store.ultimoSeqVisto = seq
    } catch {
      return
    }
    void refrescarEstado()
  }

  fuenteEventos = es
}

export function iniciarPolling(): void {
  detenerTransmisionEnVivo()
  iniciarEventSource()
  manejadorEstado = window.setInterval(refrescarEstado, INTERVALO_RESPALDO_ESTADO_MS)
  manejadorEventosRespaldo = window.setInterval(refrescarEventos, INTERVALO_RESPALDO_EVENTOS_MS)
}

export function detenerTransmisionEnVivo(): void {
  if (manejadorEstado !== undefined) window.clearInterval(manejadorEstado)
  if (manejadorEventosRespaldo !== undefined) window.clearInterval(manejadorEventosRespaldo)
  manejadorEstado = undefined
  manejadorEventosRespaldo = undefined
  fuenteEventos?.close()
  fuenteEventos = null
}

export async function despacharAccion(
  accion: string,
  params: Record<string, unknown> = {},
): Promise<void> {
  if (!store.sesion || !store.estado) return
  store.cargando = true
  try {
    aplicarEstado(
      await api.enviarAccion(store.sesion.roomId, store.sesion.token, accion, params, store.estado.turno_nonce),
    )
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
    throw e
  } finally {
    store.cargando = false
  }
}

export async function pasar(): Promise<void> {
  if (!store.sesion) return
  store.cargando = true
  try {
    aplicarEstado(await api.pasarTurno(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}
