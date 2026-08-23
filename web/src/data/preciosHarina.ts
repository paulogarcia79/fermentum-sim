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

export function precioCompraHarina(tipo: TipoHarina, posicion: number): number {
  return PRECIOS_HARINA[tipo].compra[posicion - 1]
}

export function precioVentaHarina(tipo: TipoHarina, posicion: number): number {
  return PRECIOS_HARINA[tipo].venta[posicion - 1]
}
