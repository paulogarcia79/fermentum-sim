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
let manejadorEventos: number | undefined

export function establecerSesion(s: Sesion): void {
  store.sesion = s
}

export function cerrarSesion(): void {
  detenerPolling()
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

export function iniciarPolling(): void {
  detenerPolling()
  manejadorEstado = window.setInterval(refrescarEstado, 1000)
  manejadorEventos = window.setInterval(refrescarEventos, 1000)
}

export function detenerPolling(): void {
  if (manejadorEstado !== undefined) window.clearInterval(manejadorEstado)
  if (manejadorEventos !== undefined) window.clearInterval(manejadorEventos)
  manejadorEstado = undefined
  manejadorEventos = undefined
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
