// Catalogo de los paneles persistentes del tablero, para el dock flotante
// que los muestra/oculta (DockPaneles.vue). Vive aqui y no dentro de
// GameView.vue por la misma razon que GRUPOS_ACCION vive en
// descripcionesAcciones.ts: la tabla acompaña al tipo que la indexa, y asi
// la vista no mantiene un catalogo paralelo que se pueda desincronizar.
//
// El orden de la lista es el orden de lectura del tablero (Mesa Comun de
// arriba a abajo, despues el tablero propio y la columna lateral): el dock
// se dibuja con ese mismo orden para que la posicion de cada ficha se
// corresponda con la posicion del panel en pantalla.

export type IdPanel =
  | 'clima'
  | 'mercado'
  | 'bolsa'
  | 'tendencias'
  | 'acciones'
  | 'mi_tablero'
  | 'orden'
  | 'oponentes'
  | 'registro'

export interface PanelTablero {
  id: IdPanel
  /** Glifo de la ficha del dock. Las fichas son solo icono para que el dock
   * ocupe una franja estrecha; la etiqueta va en title/aria-label. */
  icono: string
  etiqueta: string
}

export const PANELES: readonly PanelTablero[] = [
  { id: 'clima', icono: '⛅', etiqueta: 'Clima' },
  { id: 'mercado', icono: '🛒', etiqueta: 'Mercado Central' },
  { id: 'bolsa', icono: '🌾', etiqueta: 'Bolsa de Harinas' },
  { id: 'tendencias', icono: '📈', etiqueta: 'Tendencias de Mercado' },
  { id: 'acciones', icono: '🎯', etiqueta: 'Espacios de Acción' },
  { id: 'mi_tablero', icono: '🧪', etiqueta: 'Mi Tablero' },
  { id: 'orden', icono: '🔢', etiqueta: 'Orden de Turno' },
  { id: 'oponentes', icono: '👥', etiqueta: 'Otros investigadores' },
  { id: 'registro', icono: '📜', etiqueta: 'Registro' },
]
