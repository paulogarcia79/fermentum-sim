// preciosHarina.ts -- espejo de las tablas de precio de engine.py: PRECIOS_HARINA,
// PRECIO_AGUA y AGUA_TOKENS_POR_LOTE. Estas tablas NUNCA se envian por la red --
// el servidor solo envia `Market.posiciones_harina` (el visor 1-5 por tipo) y
// `Environment.temperatura_actual`; el precio resultante es una funcion pura de
// esos dos valores que el cliente reproduce aqui solo para previsualizar el costo
// ANTES de confirmar la Accion C (mismo principio que la constante
// PUNTOS_ZONA_BAJA_DIVISOR ya usada en ModalF.vue) -- el servidor sigue siendo la
// unica autoridad real y revalida todo de forma independiente al recibir la accion.
import type { TipoHarina } from '../types'

export const PRECIOS_HARINA: Record<TipoHarina, { compra: number[]; venta: number[] }> = {
  Blanca: { compra: [2, 3, 4, 5, 6], venta: [1, 2, 3, 4, 5] },
  Integral: { compra: [4, 5, 6, 7, 8], venta: [2, 3, 4, 5, 6] },
  Centeno: { compra: [6, 7, 8, 9, 10], venta: [3, 4, 5, 6, 7] },
}

export const LOTES_AGUA_VALIDOS = [10, 30, 60, 100] as const
export type LoteAguaPct = (typeof LOTES_AGUA_VALIDOS)[number]

export const PRECIO_AGUA: Record<number, Record<LoteAguaPct, number>> = {
  30: { 10: 3, 30: 6, 60: 10, 100: 14 },
  25: { 10: 2, 30: 5, 60: 8, 100: 12 },
  20: { 10: 2, 30: 4, 60: 7, 100: 10 },
  15: { 10: 1, 30: 3, 60: 6, 100: 9 },
  10: { 10: 1, 30: 2, 60: 4, 100: 7 },
}

export const AGUA_TOKENS_POR_LOTE: Record<LoteAguaPct, number> = { 10: 2, 30: 6, 60: 12, 100: 20 }

/** engine.py: CANTIDAD_BOLSA_PCT / CANTIDAD_MEDIA_BOLSA_PCT. */
export const CANTIDAD_BOLSA_PCT = 100
export const CANTIDAD_MEDIA_BOLSA_PCT = 50
export type CantidadHarina = typeof CANTIDAD_BOLSA_PCT | typeof CANTIDAD_MEDIA_BOLSA_PCT

/**
 * Media bolsa cuesta la mitad REDONDEADA HACIA ARRIBA (engine.py,
 * Market.precio_compra_harina). Es lo que impide que sea un arbitraje: con
 * precios impares sale peor por token que la bolsa entera.
 */
export function precioCompraHarina(
  tipo: TipoHarina,
  posicion: number,
  cantidad: CantidadHarina = CANTIDAD_BOLSA_PCT,
): number {
  const entero = PRECIOS_HARINA[tipo].compra[posicion - 1]
  return cantidad === CANTIDAD_BOLSA_PCT ? entero : Math.ceil(entero / 2)
}

/**
 * Media bolsa cobra la mitad REDONDEADA HACIA ABAJO. Puede dar 0 Monedas
 * (Blanca en posicion 1) y eso es legal -- el servidor lo acepta.
 */
export function precioVentaHarina(
  tipo: TipoHarina,
  posicion: number,
  cantidad: CantidadHarina = CANTIDAD_BOLSA_PCT,
): number {
  const entero = PRECIOS_HARINA[tipo].venta[posicion - 1]
  return cantidad === CANTIDAD_BOLSA_PCT ? entero : Math.floor(entero / 2)
}

/** actions.py: DESCUENTO_COMERCIANTE. */
export const DESCUENTO_COMERCIANTE = 1

/**
 * Precio final de UNA compra de la Accion C para un jugador que puede tener la
 * tecnologia Comerciante (actions.py: ActionManager._precio_compra_efectivo).
 *
 * Se aplica a harina, agua y la firma del Molino, y a ninguna venta: descontar
 * la compra Y mejorar la venta romperia el diferencial de la Bolsa (en Blanca la
 * horquilla es de 1 sola Moneda). El suelo es 1 y no 0 para que ninguna compra
 * mueva el visor gratis.
 */
export function precioCompraEfectivo(precio: number, tieneComerciante: boolean): number {
  return tieneComerciante ? Math.max(1, precio - DESCUENTO_COMERCIANTE) : precio
}
