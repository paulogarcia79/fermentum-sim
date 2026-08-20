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

export function crearSala(nombre: string): Promise<CrearSalaResultado> {
  return pedir('/games', conJson({ nombre }))
}

export interface UnirseSalaResultado {
  player_token: string
  player_index: number
}

export function unirseSala(roomId: string, nombre: string): Promise<UnirseSalaResultado> {
  return pedir(`/games/${roomId}/join`, conJson({ nombre }))
}

export interface SalaMetadata {
  room_id: string
  status: 'lobby' | 'en_curso' | 'terminada'
  seats: { player_index: number; nombre: string }[]
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
