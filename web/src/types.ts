// types.ts -- espejo TypeScript del JSON que produce server/views.py
// (game_state_view), que a su vez envuelve serialization.snapshot() con
// redaccion (mazo_clima/mazo_recetas/mazo_tendencias -> conteos) y los campos
// de turno/fase/disponibilidad. Mantener sincronizado con:
//   - models.py: Player (incl. monedas), Recipe, FermentationSlot,
//     HorneadoRecord, Technologies (incl. criopreservacion)
//   - engine.py: Environment (via models.py), Market (posiciones_harina,
//     mazo_tendencias -- ya no hay SupplyLote/suministros, GDD v0.0.2), Fase
//   - disponibilidad.py: AccionDisponible

export type Grado = 'Básica' | 'Intermedia' | 'Avanzada'
export type TipoHarina = 'Blanca' | 'Centeno' | 'Integral'
export type TecnologiaID = 'incubadora' | 'camara_b' | 'modulo_analitico' | 'criopreservacion'
export type FaseActual = 'preparacion' | 'fase_i' | 'fase_ii' | 'fase_iii' | 'terminada'

export interface Recipe {
  id: string
  nombre: string
  grado: Grado
  // Harinas impresas en la carta, como pares [tipo, porcentaje], en orden de
  // impresion. Suman siempre 100: una entrada al 100% (Basica si es Blanca,
  // Avanzada si es especial) o dos entradas distintas al 50% (Intermedia).
  // El `grado` de arriba lo deriva models.py de este reparto.
  harinas: [TipoHarina, number][]
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
  acidez_inicial: number
}

export interface HorneadoRecord {
  recipe: Recipe
  posicion_final: number
  puntos_base: number
  bono_sabor_aplicado: boolean
  fue_colapso: boolean
  datos_obtenidos: number
  monedas_obtenidos: number
  /** base + bono de sabor. Inyectado por server/views.py (es una @property que
   * asdict no incluye) -- nunca recalcular aqui. */
  puntos_totales: number
  /** Zona alcanzada al hornear, derivada por el servidor (logica de reglas). */
  zona_resultado: 'colapso' | 'optima' | 'baja'
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
  /** Ids de espacios de acción con costo de PA (B, C, D, E, F, G, H, I,
   * 'simposio') que este jugador ya visitó hoy -- cada uno solo puede
   * usarse una vez por Día de Laboratorio. Ver BarraAcciones.vue. */
  acciones_pa_usadas_hoy: string[]
  contador_contaminaciones: number
  puntos_maestria_final: number
  /** Puntos acumulados por horneados (exitosos + colapsos, base + bono) hasta
   * ahora -- el marcador "en vivo". Inyectado por server/views.py, igual que
   * puntos_maestria_final. */
  puntos_horneados: number
  /** Insumos sin usar contados como en la regla de desperdicio (-1 PM por cada 3,
   * CORE_MECHANICS.md 3.4): tokens de harina del 10% + tokens de agua del 5%,
   * sumados 1:1. Lo calcula el servidor (Player.total_tokens_recursos). */
  total_tokens_recursos: number
  /** Vitalidad que tendra este jugador tras el desgaste de esta noche (Fase III).
   * La calcula el servidor (engine.vitalidad_prevista): la formula del desgaste
   * -- incluida la exencion por Criopreservacion y el -2 de Aletargamiento
   * Invernal -- es una regla de CLIMATE_LOGIC.md y no se duplica aqui. */
  vitalidad_prevista: number
  /** True si el desgaste de esta noche llevara a este jugador a Vitalidad 0
   * por primera vez (episodio de contaminacion NUEVO: -3 Puntos de Maestria).
   * Un jugador ya contaminado devuelve false. Ver engine.riesgo_colapso. */
  en_riesgo_colapso: boolean
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
  /** Tendencias ya APLICADAS (la revelada hoy todavia no esta aqui -- ver
   * `tendencia_pendiente`). */
  descarte_tendencias: number[]
  /** Carta de Tendencia revelada esta manana y pendiente de aplicarse al final
   * de HOY: no mueve los precios de hoy, rige los de manana. `null` fuera de esa
   * ventana (incluido el Dia 1 antes de su Fase I). Ver engine.py: Market. */
  tendencia_pendiente: number | null
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
  /** Índices de jugador en orden de juego del día ([0] = Investigador Jefe).
   * Ver OrdenTurnoPanel.vue. Puede estar vacío antes del primer día. */
  turno_orden: number[]
  acciones_disponibles: AccionDisponible[][]
  ranking: { posicion: number; player_idx: number }[]
  /** Índices de jugador que confirmaron terminar la partida antes de
   * tiempo -- ver GameView.vue. No hay forma de retirar un voto. */
  votos_fin_anticipado: number[]
  /** True si el jugador activo puede deshacer su visita en curso (ya hizo
   * alguna accion gratuita esta visita) -- ver POST /games/{id}/undo y el
   * boton Deshacer en BarraAcciones.vue. */
  puede_deshacer: boolean
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

/**
 * Aviso efimero de que un jugador ejecuto una accion -- espejo de
 * server/sessions.py:AvisoAccion. No es un GameEventView: llega por el canal
 * `event: accion` del SSE, no entra en el log de eventos y no tiene `seq`.
 * Ver data/sonidosAccion.ts.
 */
export interface AvisoAccionView {
  /** Id de accion, o 'pasar' / 'deshacer'. */
  accion: string
  jugador_idx: number
}
