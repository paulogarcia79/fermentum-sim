// Zonas del track de una receta, ya ampliadas si corresponde.
//
// El Modulo Analitico ensancha la zona optima una casilla por lado -- y con ella
// retrasa el umbral de colapso -- de modo que las zonas dejan de ser una propiedad
// de la carta y pasan a depender de quien la tenga. Esa aritmetica NO se reimplementa
// aqui: `server/views.py` inyecta `zonas_efectivas` en cada receta que el jugador
// posee (carpeta, estaciones y archivos), por la misma razon por la que calcula
// `vitalidad_prevista` en el servidor -- el umbral de colapso es la regla que el
// jugador lee para medir su riesgo, y duplicarla en TypeScript es justo el punto de
// deriva que se quiere evitar.
//
// Las cartas del MERCADO llegan sin el campo: no son de nadie todavia, asi que
// muestran las zonas impresas. De ahi el fallback.
import type { Recipe } from '../types'

export interface ZonasReceta {
  crecimiento: [number, number]
  preFermento: [number, number]
  optima: [number, number]
  colapso: [number, number]
}

export function zonasDe(receta: Recipe): ZonasReceta {
  const efectivas = receta.zonas_efectivas
  if (efectivas) {
    const [crecimiento, preFermento, optima, colapso] = efectivas
    return { crecimiento, preFermento, optima, colapso }
  }
  return {
    crecimiento: receta.zona_crecimiento,
    preFermento: receta.zona_pre_fermento,
    optima: receta.zona_optima,
    colapso: receta.zona_colapso,
  }
}

/**
 * True si la masa en `posicion` todavia crece y por tanto NO se puede hornear.
 * Espeja `Recipe.esta_en_crecimiento`: es el caso por defecto, no un rango cerrado,
 * de modo que la casilla 0 -- donde nace toda masa -- cuenta como crecimiento.
 */
export function estaEnCrecimiento(receta: Recipe, posicion: number): boolean {
  const z = zonasDe(receta)
  return !(
    (posicion >= z.preFermento[0] && posicion <= z.preFermento[1]) ||
    (posicion >= z.optima[0] && posicion <= z.optima[1]) ||
    posicion >= z.colapso[0]
  )
}

/** True si la receta se muestra con la zona optima ensanchada por el Modulo Analitico. */
export function tieneZonaAmpliada(receta: Recipe): boolean {
  const z = zonasDe(receta)
  return z.optima[0] < receta.zona_optima[0]
}
