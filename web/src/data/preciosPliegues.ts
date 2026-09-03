// preciosPliegues.ts -- espejo de engine.py: PRECIO_PLIEGUES y
// PRECIO_PLIEGUES_VITALIDAD (la Accion E se paga en Monedas, no en PA).
//
// Mismo criterio que preciosHarina.ts: estas tablas son constantes de reglas
// que nunca cambian durante una partida, asi que no viajan en el snapshot de
// estado -- se replican aqui solo para poder mostrar el costo ANTES de
// confirmar la accion. El servidor revalida el precio por su cuenta al recibir
// la accion y sigue siendo la unica autoridad.

/** Espacios totales comprados -> costo en Monedas. Creciente al margen (1, 2 y
 *  3 Monedas por el 1er, 2do y 3er espacio): comprar mas nunca es un descuento
 *  por volumen. */
export const PRECIO_PLIEGUES: Record<number, number> = { 1: 1, 2: 3, 3: 6 }

/** Variante 'recuperar_vitalidad' (requiere Camara B): precio fijo. */
export const PRECIO_PLIEGUES_VITALIDAD = 6

/** Espacios comprables en una sola visita, derivado de la tabla. */
export const ESPACIOS_PLIEGUES = Object.keys(PRECIO_PLIEGUES)
  .map(Number)
  .sort((a, b) => a - b)

export const MAX_ESPACIOS_PLIEGUES = Math.max(...ESPACIOS_PLIEGUES)

/** Masas distintas entre las que se pueden repartir los espacios comprados.
 *  La Camara B cambia el reparto, no la cantidad (ver actions.py). */
export const MAX_MASAS_SIN_CAMARA_B = 1
export const MAX_MASAS_CON_CAMARA_B = 2
