// api.ts -- cliente HTTP delgado sobre server/app.py (Milestone 3).
// Sin actualizaciones optimistas: cada llamada espera la respuesta del
// servidor (la unica autoridad de reglas) y devuelve el GameStateView
// fresco para que el store lo aplique tal cual.

import type { EventsResponse, GameStateView } from './types'

export class ApiFallo extends Error {
  codigo: string
  status: number
  constructor(codigo: string, mensaje: string, status: number) {
    super(mensaje)
    this.codigo = codigo
    this.status = status
  }
}

async function pedir<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(input, init)
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({ error: 'desconocido', mensaje: respuesta.statusText }))
    throw new ApiFallo(cuerpo.error ?? 'desconocido', cuerpo.mensaje ?? respuesta.statusText, respuesta.status)
  }
  return respuesta.json() as Promise<T>
}

function conToken(token: string, init: RequestInit = {}): RequestInit {
  return { ...init, headers: { ...(init.headers ?? {}), 'X-Player-Token': token } }
}

function conJson(cuerpo: unknown): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) }
}

export interface CrearSalaResultado {
  room_id: string
  host_token: string
  player_token: string
  player_index: number
}

export function crearSala(nombre: string, color: string): Promise<CrearSalaResultado> {
  return pedir('/games', conJson({ nombre, color }))
}

export interface UnirseSalaResultado {
  player_token: string
  player_index: number
}

export function unirseSala(roomId: string, nombre: string, color: string): Promise<UnirseSalaResultado> {
  return pedir(`/games/${roomId}/join`, conJson({ nombre, color }))
}

export interface SalaMetadata {
  room_id: string
  status: 'lobby' | 'en_curso' | 'terminada'
  seats: { player_index: number; nombre: string; color: string }[]
}

export function verSala(roomId: string): Promise<SalaMetadata> {
  return pedir(`/games/${roomId}`)
}

export function iniciarSala(roomId: string, hostToken: string): Promise<GameStateView> {
  return pedir(`/games/${roomId}/start`, conToken(hostToken, { method: 'POST' }))
}

export function obtenerEstado(roomId: string, token: string): Promise<GameStateView> {
  return pedir(`/games/${roomId}/state`, conToken(token))
}

export function obtenerEventos(roomId: string, token: string, desde: number): Promise<EventsResponse> {
  return pedir(`/games/${roomId}/events?since=${desde}`, conToken(token))
}

export function enviarAccion(
  roomId: string,
  token: string,
  accion: string,
  params: Record<string, unknown>,
  turnoNonce: number,
): Promise<GameStateView> {
  return pedir(
    `/games/${roomId}/actions`,
    conToken(token, conJson({ accion, params, turno_nonce: turnoNonce })),
  )
}

export function pasarTurno(roomId: string, token: string): Promise<GameStateView> {
  return pedir(`/games/${roomId}/pass`, conToken(token, { method: 'POST' }))
}

/** Milestone 6: cualquier jugador sentado puede pedir esto para destrabar
 * la partida si el jugador activo lleva mucho tiempo sin interactuar
 * (server/sessions.py:UMBRAL_INACTIVIDAD_SEGUNDOS). El servidor rechaza
 * con 409 "jugador_no_inactivo" si todavía no pasó suficiente tiempo. */
export function forzarPase(roomId: string, token: string): Promise<GameStateView> {
  return pedir(`/games/${roomId}/force-pass`, conToken(token, { method: 'POST' }))
}

/** Confirma que este jugador quiere terminar la partida antes de tiempo.
 * No hay forma de retirar el voto. Cuando confirman todos los asientos, el
 * servidor fuerza el fin de la partida en la misma respuesta. */
export function confirmarFinAnticipado(roomId: string, token: string): Promise<GameStateView> {
  return pedir(`/games/${roomId}/confirm-end`, conToken(token, { method: 'POST' }))
}

/** Solo el host: vuelve la sala a LOBBY tras una partida terminada,
 * conservando los asientos (nombres/tokens/colores) para otra partida. */
export function volverALobby(roomId: string, hostToken: string): Promise<SalaMetadata> {
  return pedir(`/games/${roomId}/return-to-lobby`, conToken(hostToken, { method: 'POST' }))
}
