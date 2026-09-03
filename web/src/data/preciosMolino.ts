// preciosMolino.ts -- espejo de engine.py: PRECIO_CONTRATO_MOLINO y
// RENDIMIENTO_MOLINO_PCT. Sigue el precedente de preciosHarina.ts /
// preciosReceta.ts: el precio no viaja por la red, asi que ModalC lo reproduce
// aqui para etiquetar los tres contratos y deshabilitar Confirmar antes de
// enviar. El servidor revalida por su cuenta y sigue siendo la unica autoridad;
// un reajuste de precios alla obliga a editar este fichero tambien.
import type { TipoHarina } from '../types'

/** Coste unico en Monedas de firmar el Contrato con el Molino, por harina. */
export const PRECIO_CONTRATO_MOLINO: Record<TipoHarina, number> = {
  Blanca: 3,
  Integral: 4,
  Centeno: 6,
}

/**
 * Harina que el contrato entrega cada Fase III. Es PLANO para los tres tipos
 * -- lo que escala es el precio -- asi que solo hay un numero de produccion
 * que aprender y elegir tipo es una pregunta sobre que harina necesitas.
 */
export const RENDIMIENTO_MOLINO_PCT = 20
