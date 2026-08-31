// preciosAcidez.ts -- espejo de engine.py: PRECIO_DESCARTE y COSTE_REFRESCO_AGUA
// (la accion «Descarte» es 0 PA y se paga en Monedas o en Agua segun el sentido).
//
// Mismo criterio que preciosPliegues.ts / preciosReceta.ts: son constantes de
// reglas que no cambian durante una partida, asi que no viajan en el snapshot
// de estado y se replican aqui solo para poder mostrar el costo ANTES de
// confirmar. El servidor revalida y sigue siendo la unica autoridad; un cambio
// de precio alli obliga a editar este archivo tambien.

/** Niveles de Acidez retirados -> costo en Monedas. Bajar es descartar parte
 *  del cultivo y reponerlo: se tira producto, y por eso se paga en la moneda
 *  del juego. Creciente al margen (1, 2 y 3 Monedas por el 1er, 2do y 3er
 *  nivel): comprar mas nunca es un descuento por volumen. */
export const PRECIO_DESCARTE: Record<number, number> = { 1: 1, 2: 3, 3: 6 }

/** Niveles de Acidez ganados -> costo en tokens de Agua. Subir es solo anadir
 *  agua, asi que no cuesta Monedas: la asimetria es deliberada y deja un
 *  sentido del dial en manos de un jugador sin dinero. Creciente al margen
 *  (2, 3 y 4 tokens), en espejo de PRECIO_DESCARTE. */
export const COSTE_REFRESCO_AGUA: Record<number, number> = { 1: 2, 2: 5, 3: 9 }

/** Los dos sentidos, con el recurso que cobra cada uno. Espejo de
 *  actions.py:OPERACIONES_ACIDEZ. */
export type OperacionAcidez = 'subir' | 'bajar'

export const OPERACIONES_ACIDEZ: Record<
  OperacionAcidez,
  { signo: 1 | -1; recurso: 'agua' | 'monedas'; escalera: Record<number, number>; etiqueta: string }
> = {
  subir: { signo: 1, recurso: 'agua', escalera: COSTE_REFRESCO_AGUA, etiqueta: 'Subir Acidez' },
  bajar: { signo: -1, recurso: 'monedas', escalera: PRECIO_DESCARTE, etiqueta: 'Bajar Acidez' },
}

/** Niveles comprables en una sola visita, derivado de la tabla. */
export const NIVELES_ACIDEZ = Object.keys(PRECIO_DESCARTE)
  .map(Number)
  .sort((a, b) => a - b)

/** Pico de la curva de «Madurez del Cultivo» -- espejo de
 *  models.py:ACIDEZ_EQUILIBRIO_CENTRO. La Madurez ya no premia la acidez
 *  cruda sino el equilibrio, y el modal lo muestra para que el jugador vea lo
 *  que le cuesta perseguir una diana extrema. */
export const ACIDEZ_EQUILIBRIO_CENTRO = 3
export const PUNTOS_EQUILIBRIO_MAX = 3

/** Puntos de Madurez que aporta un nivel de Acidez dado. Espejo de
 *  Player.puntos_equilibrio_acidez. */
export function puntosEquilibrio(acidez: number): number {
  return PUNTOS_EQUILIBRIO_MAX - Math.abs(acidez - ACIDEZ_EQUILIBRIO_CENTRO)
}
