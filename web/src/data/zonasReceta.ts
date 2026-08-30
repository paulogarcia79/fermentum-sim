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
  baja: [number, number]
  optima: [number, number]
  sobre: [number, number]
}

export function zonasDe(receta: Recipe): ZonasReceta {
  const efectivas = receta.zonas_efectivas
  if (efectivas) {
    const [baja, optima, sobre] = efectivas
    return { baja, optima, sobre }
  }
  return {
    baja: receta.zona_baja,
    optima: receta.zona_optima,
    sobre: receta.zona_sobrefermentada,
  }
}

/** True si la receta se muestra con la zona optima ensanchada por el Modulo Analitico. */
export function tieneZonaAmpliada(receta: Recipe): boolean {
  const z = zonasDe(receta)
  return z.optima[0] < receta.zona_optima[0]
}
