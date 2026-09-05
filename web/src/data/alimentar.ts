// alimentar.ts -- espejo de models.py: HARINA_ALIMENTAR (la Accion A se paga
// en harina y tiene dos escalones).
//
// Mismo criterio que preciosPliegues.ts: es una constante de reglas que nunca
// cambia durante una partida, asi que no viaja en el snapshot de estado -- se
// replica aqui solo para poder mostrar el costo ANTES de confirmar la accion.
// El servidor revalida el reparto por su cuenta y sigue siendo la unica
// autoridad. Un cambio de precio en models.py necesita tocar este archivo.

/** Vitalidad ganada -> harina gastada, en porcentaje. Creciente al margen (10 y
 *  luego 20 por el segundo punto): comprar +2 nunca es un descuento. */
export const HARINA_ALIMENTAR: Record<number, number> = { 1: 10, 2: 30 }

/** Escalones disponibles, derivados de la tabla. */
export const ESCALONES_ALIMENTAR = Object.keys(HARINA_ALIMENTAR)
  .map(Number)
  .sort((a, b) => a - b)

export const MAX_VITALIDAD_ALIMENTAR = Math.max(...ESCALONES_ALIMENTAR)

/** models.py: `Player.ajustar_vitalidad` recorta a [0, 6]. */
export const VITALIDAD_MAX = 6
