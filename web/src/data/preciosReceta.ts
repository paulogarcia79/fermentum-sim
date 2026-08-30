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
