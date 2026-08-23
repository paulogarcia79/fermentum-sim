// types.ts -- espejo TypeScript del JSON que produce server/views.py
// (game_state_view), que a su vez envuelve serialization.snapshot() con
// redaccion (mazo_clima/mazo_recetas/mazo_tendencias -> conteos) y los campos
// de turno/fase/disponibilidad. Mantener sincronizado con:
//   - models.py: Player (incl. monedas), Recipe, FermentationSlot,
//     HorneadoRecord, Technologies (incl. criopreservacion)
//   - engine.py: Environment (via models.py), Market (posiciones_harina,
//     mazo_tendencias -- ya no hay SupplyLote/suministros, GDD v0.0.2), Fase
//   - disponibilidad.py: AccionDisponible

export type Grado = 'Básica' | 'Avanzada'
export type TipoHarina = 'Blanca' | 'Centeno' | 'Integral'
export type TecnologiaID = 'incubadora' | 'camara_b' | 'modulo_analitico' | 'criopreservacion'
export type FaseActual = 'preparacion' | 'fase_i' | 'fase_ii' | 'fase_iii' | 'terminada'

export interface Recipe {
  id: string
  nombre: string
  grado: Grado
  harina_base: TipoHarina
  hidratacion_pct: number
  tokens_agua: number
  acidez_diana: number[]
  bono_sabor_pts: number
  zona_baja: [number, number]
  zona_optima: [number, number]
  zona_sobrefermentada: [number, number]
  puntos_baja: number
  puntos_optimos: number
  penalizacion_colapso: number
  monedas_baja: number
  monedas_optima: number
  monedas_sobre: number
  req_tecnologico: TecnologiaID | null
}

export interface FermentationSlot {
  recipe: Recipe
  dado_inoculo: number
  posicion_track: number
  bono_sabor: boolean
  modificador_incubadora: number
}

export interface HorneadoRecord {
  recipe: Recipe
  posicion_final: number
  puntos_base: number
  bono_sabor_aplicado: boolean
  fue_colapso: boolean
  datos_obtenidos: number
  monedas_obtenidos: number
}

export interface Technologies {
  incubadora: boolean
  camara_b: boolean
  modulo_analitico: boolean
  criopreservacion: boolean
}

export interface Player {
  nombre: string
  /** Id de la paleta fija en data/coloresJugador.ts, elegido en el lobby
   * (ver server/sessions.py:COLORES_DISPONIBLES). */
  color: string
  vitalidad: number
  acidez: number
  en_estado_contaminacion: boolean
  puntos_accion: number
  datos_investigacion: number
  monedas: number
  reserva_harina: Record<TipoHarina, number>
  accion_alimentar_usada: boolean
  reserva_agua: number
  estaciones_fermentacion: (FermentationSlot | null)[]
  dados_inoculo: number
  tecnologias: Technologies
  carpeta_proyectos: Recipe[]
  archivo_horneado_exitoso: HorneadoRecord[]
  archivo_colapsos: HorneadoRecord[]
  horas_extras_usadas: boolean
  contador_contaminaciones: number
  puntos_maestria_final: number
}

export interface ClimateCard {
  id: string
  nombre: string
  modificador_termico: number
  efecto_biologico: string
  efecto_pasivo: string
}

export interface Environment {
  temperatura_actual: number
  dia_actual: number
  efecto_pasivo_activo: string
  descarte_clima: ClimateCard[]
  ultima_carta_clima: ClimateCard | null
  cartas_clima_restantes: number
}

export interface Market {
  recetas_visibles: (Recipe | null)[]
  descarte_recetas: Recipe[]
  posiciones_harina: Record<TipoHarina, number>
  descarte_tendencias: number[]
  mazo_recetas_restantes: number
  mazo_tendencias_restantes: number
}

export interface AccionDisponible {
  id: string
  habilitada: boolean
  motivo: string
}

export interface GameStateView {
  players: Player[]
  environment: Environment
  market: Market
  partida_terminada: boolean
  fase_actual: FaseActual
  turno_nonce: number
  jugador_en_turno_idx: number | null
  jefe_investigador_idx: number | null
  acciones_disponibles: AccionDisponible[][]
  ranking: { posicion: number; player_idx: number }[]
  /** Índices de jugador que confirmaron terminar la partida antes de
   * tiempo -- ver GameView.vue. No hay forma de retirar un voto. */
  votos_fin_anticipado: number[]
}

export interface GameEventView {
  tipo: string
  dia: number
  jugador_idx: number | null
  datos: Record<string, unknown>
  mensaje: string
}

export interface EventsResponse {
  seq: number
  eventos: GameEventView[]
}

export interface ApiError {
  error: string
  mensaje: string
}
