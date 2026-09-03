// Espejo de engine.PRECIO_RECETA: coste en Monedas de adquirir una receta del
// mercado (Accion G), por grado. Mismo precedente que preciosHarina.ts y
// preciosPliegues.ts -- el cliente necesita el precio para etiquetar el desplegable
// y desactivar Confirmar antes de enviar, pero la autoridad sigue siendo
// ActionManager: aqui solo se evita mandar una accion que se sabe que va a fallar.
//
// Un cambio en el precio del servidor exige tocar este archivo tambien.
import type { Grado } from '../types'

export const PRECIO_RECETA: Record<Grado, number> = {
  'Básica': 1,
  'Intermedia': 2,
  'Avanzada': 3,
}

// Espejo de engine.PRECIO_RECETA_MAZO: coste PLANO de la «Investigacion a ciegas»
// (Accion G con origen="mazo"), robando la carta de arriba del mazo sin verla.
// Vale lo mismo que PRECIO_RECETA['Intermedia'] pero NO se deriva de el, igual
// que en el servidor: reajustar la tabla visible no debe reajustar la apuesta.
export const PRECIO_RECETA_MAZO = 2
