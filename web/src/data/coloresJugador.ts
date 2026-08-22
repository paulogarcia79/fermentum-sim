// Paleta fija de colores de jugador -- debe coincidir exactamente con
// server/sessions.py:COLORES_DISPONIBLES (id + hex). No hay endpoint que la
// sirva (es estatica, como TipoHarina/Grado en types.ts), asi que se
// mantiene sincronizada a mano entre ambos lados.

export interface ColorJugador {
  id: string
  hex: string
  etiqueta: string
}

export const COLORES_JUGADOR: ColorJugador[] = [
  { id: 'rojo', hex: '#e0574f', etiqueta: 'Rojo' },
  { id: 'azul', hex: '#5b8dd9', etiqueta: 'Azul' },
  { id: 'verde', hex: '#4caf6e', etiqueta: 'Verde' },
  { id: 'amarillo', hex: '#e0c04f', etiqueta: 'Amarillo' },
  { id: 'morado', hex: '#a374d9', etiqueta: 'Morado' },
  { id: 'cian', hex: '#4fb8b0', etiqueta: 'Cian' },
]

export function hexDeColor(id: string): string {
  return COLORES_JUGADOR.find((c) => c.id === id)?.hex ?? '#a89a89'
}
