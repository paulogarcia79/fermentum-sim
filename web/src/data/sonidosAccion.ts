// Un sonido por accion, para reconocer de oido que hizo el jugador en turno
// sin tener que mirar su tablero. Lo oyen TODAS las pestañas conectadas
// (incluida la de quien actua), disparado por el canal efimero `event: accion`
// del SSE -- ver server/sessions.py:AvisoAccion y store.ts.
//
// Criterio de diseño: TIMBRE POR FAMILIA, TONO POR ACCION. Doce sonidos
// completamente distintos serian doce cosas que memorizar; en cambio cada
// zona del tablero (ver GRUPOS_ACCION en descripcionesAcciones.ts) tiene su
// propio timbre, que se reconoce al instante, y dentro de la familia cada
// accion cambia de altura, que se aprende con el uso:
//
//   Principales  -> `triangle`, par de notas ASCENDENTE, registro medio
//   Gratuitas    -> `sine`, un tic corto y agudo, ganancia baja (suenan mucho)
//   Emergencia   -> `sawtooth`, par de notas DESCENDENTE y grave (alarma)
//
// Dos destacados se salen de su familia a proposito, por ser los momentos
// mas consecuentes de la partida: Hornear (arpegio de tres notas) y los dos
// protocolos de emergencia (el timbre de sierra, unico en todo el juego).
import type { Sonido, Tono } from '../sonido'
import type { IdAccion } from './descripcionesAcciones'

/** Los avisos que el servidor difunde: las 12 acciones, mas los dos
 * movimientos que no pasan por `/actions` (ver server/app.py). */
export type IdSonido = IdAccion | 'pasar' | 'deshacer'

/** Par ascendente: el timbre de las acciones con costo de PA. */
function principal(base: number): Sonido {
  const comun = { duracion: 0.13, onda: 'triangle' as const, ganancia: 0.16 }
  const tonos: Tono[] = [
    { frecuencia: base, retraso: 0, ...comun },
    { frecuencia: base * 1.5, retraso: 0.085, ...comun },
  ]
  return { clase: 'sintetizado', tonos }
}

/** Tic corto y agudo: el timbre de las acciones gratuitas. Mas bajo de
 * volumen que el resto porque son las que mas se repiten en un turno. */
function gratuita(frecuencia: number): Sonido {
  return {
    clase: 'sintetizado',
    tonos: [{ frecuencia, retraso: 0, duracion: 0.07, onda: 'sine', ganancia: 0.12 }],
  }
}

/** Par descendente grave en sierra: alarma. Solo lo usan H e I. */
function emergencia(alta: number, baja: number): Sonido {
  const comun = { duracion: 0.26, onda: 'sawtooth' as const, ganancia: 0.15 }
  return {
    clase: 'sintetizado',
    tonos: [
      { frecuencia: alta, retraso: 0, ...comun },
      { frecuencia: baja, retraso: 0.18, ...comun, duracion: 0.34 },
    ],
  }
}

export const SONIDOS_ACCION: Record<IdSonido, Sonido> = {
  // --- Principales (1 PA) -------------------------------------------------
  B: principal(392), // Sol4
  C: principal(440), // La4
  D: principal(494), // Si4
  E: principal(523), // Do5
  G: principal(587), // Re5
  simposio: principal(659), // Mi5

  // Hornear y Vender: el momento de cobrar. Arpegio ascendente de tres
  // notas con cola larga -- el unico sonido "de premio" del juego.
  F: {
    clase: 'sintetizado',
    tonos: [
      { frecuencia: 523.25, retraso: 0, duracion: 0.15, onda: 'sine', ganancia: 0.2 },
      { frecuencia: 659.25, retraso: 0.1, duracion: 0.15, onda: 'sine', ganancia: 0.2 },
      { frecuencia: 783.99, retraso: 0.2, duracion: 0.42, onda: 'sine', ganancia: 0.22 },
    ],
  },

  // --- Gratuitas (0 PA) ---------------------------------------------------
  A: gratuita(1046.5), // Do6
  horas_extras: gratuita(1244.5), // Re#6
  pedido_urgencia: gratuita(1396.9), // Fa6

  // --- Protocolos de emergencia ------------------------------------------
  H: emergencia(220, 164.81), // La3 -> Mi3
  I: emergencia(246.94, 185), // Si3 -> Fa#3

  // --- Movimientos que no son acciones -----------------------------------
  // Pasar: un golpe grave y seco, deliberadamente anodino -- "no pasó nada".
  pasar: {
    clase: 'sintetizado',
    tonos: [{ frecuencia: 293.66, retraso: 0, duracion: 0.11, onda: 'sine', ganancia: 0.14 }],
  },
  // Deshacer: el tic de las gratuitas, pero al reves (desciende) -- se lee
  // como "eso que acabas de oir, quitalo".
  deshacer: {
    clase: 'sintetizado',
    tonos: [
      { frecuencia: 1244.5, retraso: 0, duracion: 0.06, onda: 'sine', ganancia: 0.1 },
      { frecuencia: 880, retraso: 0.06, duracion: 0.09, onda: 'sine', ganancia: 0.1 },
    ],
  },
}
