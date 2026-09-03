// Espejo de engine.DATOS_SIMPOSIO: Datos de Investigacion que entrega el Simposio
// Tecnico por el horneado sacrificado, por grado. Mismo precedente que
// preciosReceta.ts / preciosHarina.ts / preciosPliegues.ts -- el cliente lo necesita
// para etiquetar cada fila del archivo antes de enviar nada, pero la autoridad sigue
// siendo ActionManager.
//
// Un cambio en la tabla del servidor exige tocar este archivo tambien.
//
// Ojo: NO es lo mismo que la renta diaria, aunque hoy tengan los mismos valores.
// Son dos reglas distintas y en el servidor son dos constantes separadas a proposito
// (engine.PRECIO_RENTA vs engine.DATOS_SIMPOSIO). La renta ademas no se espeja aqui:
// llega ya calculada en `renta_diaria`.
import type { Grado } from '../types'

export const DATOS_SIMPOSIO: Record<Grado, number> = {
  'Básica': 1,
  'Intermedia': 2,
  'Avanzada': 3,
}

// Espejo de engine.PRECIO_RENTA, necesario SOLO para decir cuanta renta diaria
// se pierde al sacrificar un horneado concreto. El total que cobra un jugador
// llega siempre del servidor en `renta_diaria`; esto nunca lo recalcula.
export const RENTA_POR_GRADO: Record<Grado, number> = {
  'Básica': 1,
  'Intermedia': 2,
  'Avanzada': 3,
}

// Espejo de engine.PRECIO_DATO_SIMPOSIO y engine.MAX_DATOS_PONENCIA: el otro modo
// del Simposio, que compra Datos con Monedas sin tocar el Archivo. El modal los
// necesita para etiquetar el coste y desactivar Confirmar antes de enviar nada.
//
// Un cambio en el servidor exige tocar este archivo tambien.
//
// Ojo: la tecnologia Comerciante NO descuenta aqui (solo abarata las compras de la
// Accion C), asi que este precio nunca se corrige con DESCUENTO_COMERCIANTE.
export const PRECIO_DATO_SIMPOSIO = 5
export const MAX_DATOS_PONENCIA = 3
