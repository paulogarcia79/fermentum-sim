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
export type TecnologiaID =
  | 'incubadora'
  | 'camara_b'
  | 'modulo_analitico'
  | 'criopreservacion'
  | 'comerciante'
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
  zona_crecimiento: [number, number]
  zona_pre_fermento: [number, number]
  zona_optima: [number, number]
  zona_colapso: [number, number]
  puntos_pre_fermento: number
  puntos_optimos: number
  penalizacion_colapso: number
  monedas_pre_fermento: number
  monedas_optima: number
  monedas_colapso: number
  // Zonas [baja, optima, sobre] ya ampliadas por el Modulo Analitico del jugador
  // que posee la carta. Solo lo inyecta server/views.py en las recetas que alguien
  // POSEE (carpeta, estaciones, archivos); las del mercado llegan sin el campo y se
  // leen con sus zonas impresas. Ver web/src/data/zonasReceta.ts.
  zonas_efectivas?: [
    [number, number],
    [number, number],
    [number, number],
    [number, number],
  ]
  // Harina y agua que le faltan a ESTA carta para poder iniciarse hoy. Igual que
  // `zonas_efectivas` lo inyecta server/views.py, pero solo en `carpeta_proyectos`:
  // las del mercado no son de nadie y las de estaciones/archivos ya estan pagadas.
  // Ver web/src/data/insumosReceta.ts.
  insumos?: InsumosReceta
}

/**
 * Espejo de `disponibilidad.insumos_receta`.
 *
 * Mide SOLO los insumos de la carta, nunca los bloqueos del jugador (PA, dado de
 * inoculo, estacion libre, contaminacion): esos ya viajan una sola vez en el
 * `motivo` de la Accion B dentro de `acciones_disponibles`. O sea que
 * `completos: true` NO promete que Confirmar vaya a funcionar, promete que lo que
 * falte, si falta algo, no es la despensa.
 *
 * Las cantidades llegan en la unidad del dominio -- harina en PORCENTAJE, agua en
 * TOKENS -- y se les da formato con web/src/data/unidades.ts, como en todas partes.
 */
export interface InsumosReceta {
  harinas: { tipo: TipoHarina; necesita: number; tiene: number; falta: boolean }[]
  // `necesita` ya lleva aplicado el descuento de Alta Humedad: lo calcula
  // engine.agua_requerida, el mismo metodo que le cobra a la Accion B.
  agua: { necesita: number; tiene: number; falta: boolean }
  completos: boolean
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
  zona_resultado: 'colapso' | 'optima' | 'pre_fermento'
}

export interface Technologies {
  incubadora: boolean
  camara_b: boolean
  modulo_analitico: boolean
  criopreservacion: boolean
  comerciante: boolean
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
  /** Harina del Contrato con el Molino firmado por este jugador, o null si no
   * ha firmado ninguno. Uno por partida y permanente; entrega
   * RENDIMIENTO_MOLINO_PCT de esa harina cada Fase III. Es la unica fuente de
   * harina que no pasa por la Bolsa. Campo de models.Player, llega por
   * serialization.snapshot como cualquier otro. */
  contrato_molino: TipoHarina | null
  accion_alimentar_usada: boolean
  reserva_agua: number
  estaciones_fermentacion: (FermentationSlot | null)[]
  dados_inoculo: number
  tecnologias: Technologies
  carpeta_proyectos: Recipe[]
  archivo_horneado_exitoso: HorneadoRecord[]
  archivo_colapsos: HorneadoRecord[]
  horas_extras_usadas: boolean
  /** True si este jugador ha suspendido su Estasis Biológica para la Fase III
   * de HOY, es decir, si su cultivo va a sufrir el desgaste normal esta noche
   * pese a tener la Criopreservación. La Fase III la limpia tras aplicar el
   * desgaste, así que la Estasis se reactiva sola cada día. Inerte en quien no
   * tiene la mejora. Ver ModalEstasis.vue. */
  estasis_suspendida: boolean
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
  /** Los 8 terminos de la puntuacion final (CORE_MECHANICS.md 3), ya en orden
   * de presentacion: la vista de ranking los recorre sin conocer ni cuantos
   * son ni su aritmetica. Lo calcula el servidor
   * (Player.desglose_maestria), que es la unica fuente de verdad de la
   * formula. */
  desglose_maestria: Record<string, number>
  /** Recetas DISTINTAS horneadas con exito -- el recuento que alimenta el
   * termino «Variedad de Recetas» (curva triangular n*(n+1)/2) y el primer
   * criterio de desempate. Viaja aparte del desglose porque se muestra
   * durante la partida, donde no hay desglose a la vista. */
  recetas_distintas_horneadas: number
  /** Insumos sin usar contados como en la regla de desperdicio (-1 PM por cada 3,
   * CORE_MECHANICS.md 3.4): tokens de harina del 10% + tokens de agua del 5%,
   * sumados 1:1. Lo calcula el servidor (Player.total_tokens_recursos). */
  total_tokens_recursos: number
  /** Vitalidad que tendra este jugador tras el desgaste de esta noche (Fase III).
   * La calcula el servidor (engine.vitalidad_prevista): la formula del desgaste
   * -- incluida la exencion por Criopreservacion y el -2 de Aletargamiento
   * Invernal -- es una regla de CLIMATE_LOGIC.md y no se duplica aqui. */
  vitalidad_prevista: number
  /** La misma proyeccion con la Estasis Biologica en el ajuste CONTRARIO al
   * actual, para que ModalEstasis.vue ensene las dos cifras a la vez sin
   * calcular nada. La da el servidor (engine.vitalidad_prevista_alterna); en
   * quien no tiene Criopreservacion coincide con vitalidad_prevista. */
  vitalidad_prevista_alterna: number
  /** True si el desgaste de esta noche llevara a este jugador a Vitalidad 0
   * por primera vez (episodio de contaminacion NUEVO: -3 Puntos de Maestria).
   * Un jugador ya contaminado devuelve false. Ver engine.riesgo_colapso. */
  en_riesgo_colapso: boolean
  /** Monedas que este jugador cobrara esta noche por «Ingresos de Panaderia»:
   * la suma de engine.PRECIO_RENTA sobre su archivo de horneados exitosos.
   * Lo calcula el servidor (server/views.py) por el mismo criterio que
   * vitalidad_prevista: la tasa por grado es una regla del motor y duplicarla
   * aqui seria un punto de deriva. Los colapsos no rinden nada. */
  renta_diaria: number
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
  /** Jugador que ocupó hoy el espacio (GLOBAL) de la Jefatura y abrirá mañana,
   * o null si sigue libre. A diferencia del resto de espacios, uno por día en
   * toda la mesa: por eso vive en el estado del motor y no en
   * `acciones_pa_usadas_hoy` de cada jugador. Ver OrdenTurnoPanel.vue. */
  jefatura_reclamada_por: number | null
  acciones_disponibles: AccionDisponible[][]
  ranking: { posicion: number; player_idx: number }[]
  /** Índices de jugador que confirmaron terminar la partida antes de
   * tiempo -- ver GameView.vue. No hay forma de retirar un voto. */
  votos_fin_anticipado: number[]
  /** True si el jugador activo puede deshacer su visita en curso (ya hizo
   * alguna accion gratuita esta visita) -- ver POST /games/{id}/undo y el
   * boton Deshacer en BarraAcciones.vue. */
  puede_deshacer: boolean
  /** Registro append-only de los movimientos de la partida -- espejo de
   * server/sessions.py:EntradaRegistro. Llega entero en cada snapshot (no por
   * delta) porque un deshacer MUTA entradas viejas marcandolas `deshecha`.
   * Ver RegistroEventos.vue, que lo intercala con `store.eventos`. */
  registro_acciones: RegistroAccionView[]
}

/**
 * Una linea del registro de movimientos -- espejo de
 * server/sessions.py:EntradaRegistro.
 *
 * No es un GameEventView y no vive en el log de eventos del motor: las
 * acciones gratuitas ocurren dentro de la ventana de deshacer, donde
 * `engine.eventos` tiene que quedar byte a byte identico. Ver el docstring
 * de EntradaRegistro para el porque completo.
 */
export interface RegistroAccionView {
  /** Correlativo 1-based; desempata a las entradas con igual `pos_eventos`. */
  seq: number
  /** Un IdMovimiento (ver data/descripcionesAcciones.ts). */
  accion: string
  /** Quien movio. Para 'pase_forzado', a quien se lo pasaron. */
  jugador_idx: number
  dia: number
  /** `len(engine.eventos)` antes de la mutacion: la entrada va despues del
   * evento `pos_eventos - 1` y antes del evento `pos_eventos`. Es la clave
   * de ordenacion que permite un solo hilo cronologico sin marcas de tiempo. */
  pos_eventos: number
  /** Frase ya redactada por el servidor, sin el nombre del actor. */
  mensaje: string
  /** True si un deshacer la revirtio: se tacha, no se borra. */
  deshecha: boolean
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
  /** Id de accion, o 'pasar' / 'deshacer'. Un pase forzado llega como
   * 'pasar': el aviso es el canal de sonido y suena igual. Solo el registro
   * (RegistroAccionView) lo distingue como 'pase_forzado'. */
  accion: string
  jugador_idx: number
}
