// insumosReceta.ts -- como se leen en pantalla los insumos que faltan.
//
// El calculo NO esta aqui: lo hace `disponibilidad.insumos_receta` y viaja ya
// resuelto en cada carta de la carpeta (`Recipe.insumos`), por la misma razon que
// `zonas_efectivas` o `vitalidad_prevista` -- el descuento de agua de Alta Humedad
// es una regla de CLIMATE_LOGIC.md y tenerla dos veces, una en Python y otra en
// TypeScript, es exactamente la deriva que este reparto existe para evitar. De
// hecho ya paso: ModalB.vue calculaba el agua por su cuenta y se olvidaba del
// descuento, asi que en un dia humedo tachaba una receta que el servidor aceptaba.
//
// Aqui solo se le da formato, con las unidades de unidades.ts.
import type { InsumosReceta } from '../types'
import { fmtHarina, fmtTokensAgua } from './unidades'

/** Los insumos que faltan, en una linea: `Falta: 5 (50%) Harina Centeno · 2 tokens Agua`. */
export function fmtFaltantes(insumos: InsumosReceta): string {
  const partes = insumos.harinas
    .filter((h) => h.falta)
    .map((h) => `${fmtHarina(h.necesita - h.tiene)} Harina ${h.tipo}`)

  if (insumos.agua.falta) {
    partes.push(`${fmtTokensAgua(insumos.agua.necesita - insumos.agua.tiene)} Agua`)
  }

  return partes.length > 0 ? `Falta: ${partes.join(' · ')}` : ''
}

/**
 * La carta en una linea para las listas: `Miche — Falta: 2 tokens Agua`.
 *
 * La usan el tooltip del espacio «Iniciar Receta» y el modal de confirmacion de
 * pase, que enumeran la carpeta entera y necesitan decir de cada carta si esta
 * lista o que le falta.
 */
export function fmtLineaReceta(nombre: string, insumos?: InsumosReceta): string {
  if (!insumos) return nombre
  return insumos.completos ? `${nombre} — insumos completos` : `${nombre} — ${fmtFaltantes(insumos)}`
}
