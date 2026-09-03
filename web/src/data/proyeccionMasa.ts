// Como se dibuja una masa sobre el track 1-20: sus bandas de zona, donde va a
// caer esta noche y de que color se pinta esa proyeccion.
//
// Vive aqui, y no dentro de un componente, porque tiene DOS consumidores que no
// pueden discrepar: `EstacionCard.vue` (el corchete discontinuo del tablero) y
// `ModalIncubadora.vue` (el mismo corchete, moviendose mientras eliges el dial).
// Si el modal enseñara una proyeccion y la tarjeta otra, el jugador estaria
// eligiendo contra una cifra que su tablero desmiente.
//
// Aritmetica pura sobre datos que ya vienen en el snapshot: temperatura del
// entorno, dado sellado en la masa y el dial de la Incubadora. Ninguna regla de
// negocio se reimplementa aqui -- las zonas ya llegan ampliadas del servidor
// (`zonasReceta.ts`) y la formula de avance es la que el motor documenta en
// CLIMATE_LOGIC.md §3, que el cliente solo PROYECTA, nunca aplica.
import type { FermentationSlot } from '../types'
import type { BandaPista } from '../components/PistaMedida.vue'
import { zonasDe, type ZonasReceta } from './zonasReceta'

/** Ultima casilla del track de fermentacion. */
export const TRACK_MAX = 20

/**
 * Bandas de color del track para una masa, en unidades de casilla (1-20).
 *
 * Se restan 0.5 casillas en los bordes por lo mismo que el marcador se centra en
 * su celda: asi una masa en `optima[0] - 1` queda visiblemente a la izquierda de
 * la banda verde, coincidiendo con lo que `resolver_horneado` hara.
 */
export function bandasDe(zonas: ZonasReceta): BandaPista[] {
  return [
    // Crecimiento va con trama, no con un tono mas palido: es una zona de otra
    // clase (ahi no se puede hornear en absoluto).
    { desde: zonas.crecimiento[0] - 1, hasta: zonas.crecimiento[1], tono: 'crecimiento' },
    { desde: zonas.preFermento[0] - 1, hasta: zonas.preFermento[1], tono: 'baja' },
    { desde: zonas.optima[0] - 1, hasta: zonas.optima[1], tono: 'optima' },
    { desde: zonas.colapso[0] - 1, hasta: TRACK_MAX, tono: 'sobre' },
  ]
}

/**
 * Casilla en la que caera la masa tras la proxima Fase III.
 *
 * `modificador` se pasa aparte en vez de leerse de `slot.modificador_incubadora`
 * porque ModalIncubadora necesita proyectar el valor que el jugador esta
 * *considerando*, no el que hay guardado. Quien quiera el estado actual pasa
 * `slot.modificador_incubadora`.
 *
 * El tope deja ver que la masa se sale del track sin romper el layout.
 */
export function posicionProyectada(
  slot: FermentationSlot,
  temperaturaActual: number,
  modificador: number,
): number {
  const avanceBase = Math.floor(temperaturaActual / 5)
  const proyectada = slot.posicion_track + avanceBase + slot.dado_inoculo + modificador
  return Math.min(proyectada, TRACK_MAX + 4)
}

/** Tono del corchete discontinuo segun la zona en la que aterrizara la masa. */
export function tonoProyectado(
  zonas: ZonasReceta,
  posicion: number,
): 'riesgo' | 'vital' | 'cobre' {
  if (posicion >= zonas.colapso[0]) return 'riesgo'
  if (posicion >= zonas.optima[0] && posicion <= zonas.optima[1]) return 'vital'
  return 'cobre'
}

/** True si la masa acabaria la noche en Colapso: horneado automatico con penalizacion. */
export function acabaEnColapso(slot: FermentationSlot, posicion: number): boolean {
  return posicion >= zonasDe(slot.recipe).colapso[0]
}
