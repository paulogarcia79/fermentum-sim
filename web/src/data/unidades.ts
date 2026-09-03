// unidades.ts -- las dos unidades en las que el juego mide sus dos insumos
// fisicos, para poder mostrar siempre ambas.
//
// LA REGLA DE LA UI: todo se cuenta en TOKENS y se imprime `N (P%)`, primero
// el numero de tokens y luego su porcentaje. Lo unico que cambia entre los dos
// insumos es cuanto vale un token:
//
//   Harina -> 1 token = 10%     10 (100%)
//   Agua   -> 1 token = 5%      20 (100%)
//
// Que ambos sean tokens no es una licencia de presentacion: es la unidad en la
// que las reglas los suman. La penalizacion por desperdicio del final de
// partida (models.py, Player.total_tokens_recursos = sum(v // 10 for v in
// reserva_harina.values()) + reserva_agua) cuenta un token de harina del 10% y
// uno de agua del 5% exactamente igual, 1:1.
//
// El dominio, en cambio, guarda cada insumo en la unidad que le resulto comoda
// (ver models.py): `reserva_agua` YA es un conteo de tokens, pero
// `reserva_harina` son PORCENTAJES en multiplos de 10. Por eso las funciones de
// harina de aqui reciben un porcentaje aunque impriman tokens.
//
// Nota sobre ACTIONS_REGISTRY.md: ahi "1 Token de Harina (100% base)" se
// refiere a una BOLSA entera, no al token atomico. La UI no usa esa lectura --
// una bolsa son 10 tokens -- para que un tablero no mezcle dos tamanos de token
// con el mismo nombre.
//
// Igual que preciosHarina.ts, esto es un espejo de constantes de Python usado
// SOLO para presentacion: no valida nada, el servidor sigue siendo la unica
// autoridad de reglas.
import type { Recipe } from '../types'

/** models.py: `reserva_agua` -- "Cada unidad representa un 5% de hidratacion". */
export const PCT_POR_TOKEN_AGUA = 5

/** models.py: `total_tokens_recursos` -- `sum(v // 10 ...)`. */
export const PCT_POR_TOKEN_HARINA = 10

/**
 * Porcentaje equivalente a N tokens de agua.
 *
 * Valido para reservas de jugador, lotes de mercado y costos de accion, que
 * siempre son multiplos exactos. NO sirve para la hidratacion impresa de una
 * receta: ver `fmtAguaReceta`.
 */
export function pctAgua(tokens: number): number {
  return tokens * PCT_POR_TOKEN_AGUA
}

/** Porcentaje equivalente a N tokens de harina. */
export function pctHarina(tokens: number): number {
  return tokens * PCT_POR_TOKEN_HARINA
}

/** Tokens de agua equivalentes a un porcentaje (lotes de 10/30/60/100). */
export function tokensAgua(pct: number): number {
  return Math.round(pct / PCT_POR_TOKEN_AGUA)
}

/** Tokens de harina equivalentes a un porcentaje de reserva. */
export function tokensHarina(pct: number): number {
  return Math.floor(pct / PCT_POR_TOKEN_HARINA)
}

function plural(cantidad: number, singular: string, plural_: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural_}`
}

/** "12 tokens" / "1 token", a partir de un CONTEO DE TOKENS de agua. */
export function fmtTokensAgua(tokens: number): string {
  return plural(tokens, 'token', 'tokens')
}

/** "10 tokens" / "1 token", a partir de un PORCENTAJE de harina. */
export function fmtTokensHarina(pct: number): string {
  return plural(tokensHarina(pct), 'token', 'tokens')
}

/** Reserva/costo de agua: `20 (100%)`. Recibe un CONTEO DE TOKENS. */
export function fmtAgua(tokens: number): string {
  return `${tokens} (${pctAgua(tokens)}%)`
}

/**
 * Reserva/costo de harina: `10 (100%)`.
 *
 * Ojo: recibe un PORCENTAJE (es como lo guarda `Player.reserva_harina`) aunque
 * imprima los tokens primero. Su gemela de agua, `fmtAgua`, recibe tokens.
 */
export function fmtHarina(pct: number): string {
  return `${tokensHarina(pct)} (${pct}%)`
}

/**
 * Agua que pide una receta, con SU porcentaje impreso: `13 (62%)`.
 *
 * Existe aparte de `fmtAgua` porque `hidratacion_pct` NO es `tokens_agua * 5`:
 * la carta redondea hacia arriba (`tokens_agua = ceil(hidratacion_pct / 5)`) y
 * las dos cifras difieren en 5 de las 8 recetas del catalogo -- p.ej. Pizza
 * Napolitana imprime 62% y cuesta 13 tokens (13 * 5 = 65). Siempre hay que leer
 * el campo de la carta, nunca convertir.
 */
export function fmtAguaReceta(receta: Recipe): string {
  return `${receta.tokens_agua} (${receta.hidratacion_pct}%)`
}
