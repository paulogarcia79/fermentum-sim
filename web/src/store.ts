// store.ts -- estado reactivo compartido por toda la app.
//
// Sin Pinia/Vuex: el servidor siempre manda el snapshot completo (no
// deltas), asi que un solo objeto reactive() actualizado por
// aplicarEstado() alcanza. Sin actualizaciones optimistas: cada accion
// espera la respuesta del servidor antes de re-renderizar -- un juego por
// turnos no tiene presupuesto de latencia que justifique la complejidad.

import { reactive } from 'vue'
import * as api from './api'
import type { AvisoAccionView, GameEventView, GameStateView, HorneadoRecord } from './types'
import {
  reproducirCierreDerrota,
  reproducirFanfarriaVictoria,
  reproducirNotificacionTurno,
  reproducirSonido,
} from './sonido'
import { SONIDOS_ACCION, type IdSonido } from './data/sonidosAccion'
import type { IdPanel } from './data/panelesTablero'

export interface Sesion {
  roomId: string
  token: string
  playerIndex: number
  hostToken: string | null
  nombre: string
}

export interface Preferencias {
  /** Avisar cuando la masa madre vaya a colapsar esta noche: badge permanente
   * en MiTablero.vue + confirmacion al pasar turno en BarraAcciones.vue. */
  alertaContaminacion: boolean
  /** Efectos de sonido: un timbre distinto por accion de cualquier jugador
   * (ver data/sonidosAccion.ts) mas el aviso de turno. Activado por defecto,
   * con el interruptor en la cabecera de GameView.vue. */
  sonido: boolean
  /** Paneles del tablero que este navegador tiene ocultos, por su IdPanel
   * (ver data/panelesTablero.ts). Se conmutan desde el dock flotante
   * DockPaneles.vue o desde la ✕ de cada panel; por defecto no hay ninguno
   * oculto, es decir la pantalla de siempre. */
  panelesOcultos: IdPanel[]
}

interface Store {
  sesion: Sesion | null
  estado: GameStateView | null
  eventos: GameEventView[]
  ultimoSeqVisto: number
  error: string | null
  cargando: boolean
  /** Dia que acaba de concluir y cuyo reporte de Fase III aun no fue
   * reconocido por el jugador -- null cuando no hay ninguno pendiente. */
  reporteDiaPendiente: number | null
  /** True si el jugador todavia no reconocio en esta pestaña la apertura del
   * dia actual: la carta de clima Y la tendencia de mercado anunciada, ambas
   * reveladas por la misma Fase I -- ver InicioDiaModal.vue. */
  inicioDiaPendiente: boolean
  /** Preferencias de UI del jugador local, persistidas en localStorage bajo
   * su propia clave. NO se resetean al cerrar sesion ni al volver al lobby:
   * son duraderas, a diferencia de las banderas por partida de mas abajo. */
  preferencias: Preferencias
  /** True si otro jugador pidio terminar la partida antes de tiempo y este
   * jugador todavia no votó ni descartó el aviso -- ver FinAnticipadoModal.vue. */
  finAnticipadoPendiente: boolean
  /** Resultado del horneado voluntario (Accion F) recien resuelto, pendiente
   * de que el jugador lo cierre. Vive en el store y no en ModalF porque la
   * Accion F termina el turno: el snapshot de respuesta desmonta
   * BarraAcciones (v-if="esMiTurno") y con ella cualquier ref local -- ver
   * ResultadoHorneadoModal.vue, montado desde GameView. */
  resultadoHorneado: HorneadoRecord | null
  /** Indice del jugador cuyo tablero se muestra en la region Tablero, o
   * `null` = el propio. Bandera POR PARTIDA y no preferencia: un indice de
   * asiento no significa nada en la partida siguiente, asi que ni se
   * persiste ni sobrevive a cerrarSesion(); ademas vuelve sola a `null`
   * cuando llega el turno (ver aplicarEstado). */
  jugadorObservado: number | null
}

export const store: Store = reactive({
  sesion: null,
  estado: null,
  eventos: [],
  ultimoSeqVisto: 0,
  error: null,
  cargando: false,
  reporteDiaPendiente: null,
  inicioDiaPendiente: false,
  // `cargarPreferenciasLocales` es una declaracion de funcion (hoisted), asi
  // que puede usarse aqui aunque este definida mas abajo junto al resto de
  // helpers de localStorage.
  preferencias: cargarPreferenciasLocales(),
  finAnticipadoPendiente: false,
  resultadoHorneado: null,
  jugadorObservado: null,
})

/** Ver Store.resultadoHorneado. Lo setea ModalF.vue tras un horneado
 * confirmado; lo limpia el boton Cerrar de ResultadoHorneadoModal.vue. */
export function mostrarResultadoHorneado(registro: HorneadoRecord): void {
  store.resultadoHorneado = registro
}

export function cerrarResultadoHorneado(): void {
  store.resultadoHorneado = null
}

/**
 * Id de la última carta de clima ya mostrada en esta pestaña -- no
 * reactivo a propósito (es solo para detectar el cambio en
 * aplicarEstado(), no algo que ningún componente deba leer). `undefined`
 * antes de la primera aplicación de estado, lo que hace que la carta del
 * Día 1 también dispare el modal, no solo las de días siguientes.
 *
 * Gatilla el modal de inicio de día COMPLETO (clima + tendencia), aunque solo
 * mire el clima: ambas cartas se revelan en la misma Fase I, y el clima es la
 * única de las dos con id estable. Los modificadores de tendencia son enteros
 * -2..+2 que se repiten entre días, así que una comparación por valor no
 * distinguiría dos "+1" seguidos.
 */
let ultimaCartaClimaId: string | null | undefined = undefined

/**
 * Conteo de `votos_fin_anticipado` en el que este jugador descartó por
 * última vez el aviso de fin anticipado (o -1 si nunca lo descartó). No
 * reactivo -- solo lo lee aplicarEstado() para decidir si vuelve a mostrar
 * el modal. Volver a mostrarlo solo si el conteo CRECIÓ (otro jugador más
 * se sumó al pedido); nunca insistir con el mismo conteo ya descartado.
 */
let finAnticipadoDescartadoEnConteo = -1

/**
 * Ultimo `jugador_en_turno_idx` observado -- no reactivo, solo para
 * detectar en aplicarEstado() cuando el turno ACABA de llegar al jugador
 * local (ver reproducirNotificacionTurno() mas abajo). Empieza en `null`
 * ("hasta donde sabemos, no es el turno de nadie todavia") a proposito: la
 * primera vez que un jugador ve el tablero -- el host recien apretó
 * "Iniciar partida", o cualquier otro jugador recien salió del lobby -- es
 * una entrega de turno EN VIVO igual que cualquier otra, y si le toca a él
 * primero, debe sonar.
 *
 * El unico caso que NO debe sonar es recargar la pestaña o reconectar a
 * mitad de partida y encontrarse con que ya es tu turno -- eso no es una
 * entrega en vivo, es solo el estado actual. `intentarReconectar()` cubre
 * ese caso llamando a `sembrarTurnoSinSonido()` antes de aplicar el primer
 * estado, para que esa aplicación puntual no dispare el sonido.
 */
let jugadorEnTurnoAnterior: number | null = null

/**
 * Si esta pestaña ya sonó el final de la partida. No reactivo -- solo lo lee
 * aplicarEstado() para que la fanfarria (o el cierre de derrota) suene UNA vez,
 * en la transición en vivo a `fase_actual === 'terminada'`, y no en cada
 * refresco posterior del estado, que en la pantalla de ranking siguen llegando
 * por el poll de respaldo.
 *
 * Igual que con el aviso de turno, recargar la pestaña sobre una partida ya
 * terminada NO es una transición en vivo: `sembrarEstadoSinSonido()` lo deja en
 * `true` antes de la primera aplicación. El confeti sí vuelve a salir en ese
 * caso, porque vive en RankingView.vue y no depende de este flag -- es parte de
 * la pantalla, no del instante.
 */
let finDePartidaSonado = false

/** Ver los comentarios de `jugadorEnTurnoAnterior` y `finDePartidaSonado`. Solo
 * debe usarse antes de la primerísima `aplicarEstado()` de una sesión
 * reconectada, para que ese estado inicial no dispare sonidos que describen
 * transiciones que este cliente no ha presenciado. */
function sembrarEstadoSinSonido(estado: GameStateView): void {
  jugadorEnTurnoAnterior = estado.jugador_en_turno_idx
  finDePartidaSonado = estado.fase_actual === 'terminada'
}

let manejadorEstado: number | undefined
let manejadorEventosRespaldo: number | undefined
let fuenteEventos: EventSource | null = null

// Cadencia de respaldo una vez que SSE es la via principal de empuje --
// mas lenta que el 1s de la Milestone 4 porque ya no es la unica forma en
// que el cliente se entera de cambios; sigue existiendo para el caso en
// que la conexion SSE falle en silencio (ver iniciarEventSource).
const INTERVALO_RESPALDO_ESTADO_MS = 4000
const INTERVALO_RESPALDO_EVENTOS_MS = 15000

// La sesion (sala + token de jugador) se guarda en localStorage para que
// cerrar la pestaña/el navegador a mitad de partida no deje al jugador sin
// forma de volver a entrar -- unirse a una sala solo funciona mientras
// esta en LOBBY, asi que sin esto, cerrar el navegador durante una
// partida en curso dejaba el asiento inaccesible para siempre.
const CLAVE_SESION_LOCAL = 'fermentum-sesion'

// Preferencias de UI del jugador. Clave SEPARADA de la sesion a proposito:
// cerrarSesion() borra la sesion, pero una preferencia es duradera y debe
// sobrevivir a salir de una partida y entrar a otra.
const CLAVE_PREFERENCIAS_LOCAL = 'fermentum-preferencias'

function cargarPreferenciasLocales(): Preferencias {
  const porDefecto: Preferencias = { alertaContaminacion: true, sonido: true, panelesOcultos: [] }
  try {
    const crudo = localStorage.getItem(CLAVE_PREFERENCIAS_LOCAL)
    if (!crudo) return porDefecto
    return { ...porDefecto, ...(JSON.parse(crudo) as Partial<Preferencias>) }
  } catch {
    return porDefecto
  }
}

/** Cambia una preferencia y la persiste. El aviso de contaminacion es opt-in
 * por jugador (se pregunta en el lobby, ver LobbyView.vue). */
export function establecerAlertaContaminacion(activa: boolean): void {
  store.preferencias.alertaContaminacion = activa
  persistirPreferencias()
}

/** Interruptor de sonido, en la cabecera de la partida (GameView.vue). */
export function establecerSonido(activo: boolean): void {
  store.preferencias.sonido = activo
  persistirPreferencias()
}

/** Muestra/oculta un panel del tablero. La preferencia es duradera: se
 * guarda en localStorage y sobrevive a salir de la partida (ver el comentario
 * de CLAVE_PREFERENCIAS_LOCAL). */
export function alternarPanel(id: IdPanel): void {
  const ocultos = store.preferencias.panelesOcultos
  const i = ocultos.indexOf(id)
  if (i === -1) ocultos.push(id)
  else ocultos.splice(i, 1)
  persistirPreferencias()
}

/**
 * Cambia el tablero que se ve en la region Tablero: `idx` de otro jugador, o
 * `null` para volver al propio. Ver Store.jugadorObservado.
 *
 * Elegir un tablero ajeno DES-oculta el panel si estaba oculto, y de forma
 * permanente -- a diferencia del force-show temporal de «Espacios de Accion»
 * durante tu turno. Pedir ver un tablero es una peticion explicita, asi que
 * sobrescribir la preferencia es lo honesto: si no, el clic en una fila de
 * oponente no haria nada visible y se leeria como un fallo.
 */
export function observarJugador(idx: number | null): void {
  // El asiento propio se normaliza a null: una sola representacion de "mi
  // tablero", para que el clic en la propia ficha y la vuelta automatica al
  // llegar el turno dejen el store en el mismo estado.
  const propio = idx !== null && idx === store.sesion?.playerIndex
  store.jugadorObservado = propio ? null : idx
  if (store.jugadorObservado === null) return

  const ocultos = store.preferencias.panelesOcultos
  const i = ocultos.indexOf('mi_tablero')
  if (i !== -1) {
    ocultos.splice(i, 1)
    persistirPreferencias()
  }
}

/** Vuelve a mostrar los nueve paneles. Es la salida de emergencia de una
 * preferencia que dura para siempre: sin esto, un jugador que oculto medio
 * tablero hace tres sesiones tendria que acordarse de que ficha apago. */
export function restaurarPaneles(): void {
  store.preferencias.panelesOcultos = []
  persistirPreferencias()
}

function persistirPreferencias(): void {
  try {
    localStorage.setItem(CLAVE_PREFERENCIAS_LOCAL, JSON.stringify(store.preferencias))
  } catch {
    // Igual que la sesion: si localStorage falla, la preferencia sigue
    // valiendo para esta pestaña, solo no sobrevive a una recarga.
  }
}

function guardarSesionLocal(s: Sesion): void {
  try {
    localStorage.setItem(CLAVE_SESION_LOCAL, JSON.stringify(s))
  } catch {
    // localStorage puede fallar (modo privado, cuota agotada) -- no es
    // critico, solo se pierde la posibilidad de reconectar automaticamente.
  }
}

function cargarSesionLocal(): Sesion | null {
  try {
    const crudo = localStorage.getItem(CLAVE_SESION_LOCAL)
    return crudo ? (JSON.parse(crudo) as Sesion) : null
  } catch {
    return null
  }
}

function borrarSesionLocal(): void {
  try {
    localStorage.removeItem(CLAVE_SESION_LOCAL)
  } catch {
    return
  }
}

export function establecerSesion(s: Sesion): void {
  store.sesion = s
  guardarSesionLocal(s)
}

export function cerrarSesion(): void {
  detenerTransmisionEnVivo()
  store.sesion = null
  store.estado = null
  store.eventos = []
  store.ultimoSeqVisto = 0
  store.error = null
  store.reporteDiaPendiente = null
  store.inicioDiaPendiente = false
  store.finAnticipadoPendiente = false
  store.resultadoHorneado = null
  store.jugadorObservado = null
  ultimaCartaClimaId = undefined
  finAnticipadoDescartadoEnConteo = -1
  jugadorEnTurnoAnterior = null
  finDePartidaSonado = false
  borrarSesionLocal()
}

/**
 * Se llama una vez al arrancar la app (ver App.vue). Si hay una sesión
 * guardada en localStorage, verifica contra el servidor que la sala
 * todavía existe y que el token todavía es válido antes de darla por
 * buena -- si cualquiera de las dos cosas falla (sala borrada por
 * limpieza de inactividad, token ya no reconocido), descarta la sesión
 * guardada en silencio y el usuario simplemente ve el formulario normal
 * de crear/unirse.
 *
 * Si la sala sigue en LOBBY, solo restaura `store.sesion` -- LobbyView es
 * quien retoma la sala de espera a partir de ahí. Si ya está en curso (o
 * terminada), además restaura el estado del juego y arranca SSE/polling,
 * dejando a App.vue mostrar GameView directamente sin pasar por el lobby.
 */
export async function intentarReconectar(): Promise<void> {
  const guardada = cargarSesionLocal()
  if (!guardada) return
  try {
    const metadata = await api.verSala(guardada.roomId)
    if (metadata.status === 'lobby') {
      store.sesion = guardada
      return
    }
    const estadoRemoto = await api.obtenerEstado(guardada.roomId, guardada.token)
    store.sesion = guardada
    // Recarga de pestaña / reconexion a mitad de partida -- si ya es el
    // turno de este jugador, no es una entrega EN VIVO, es solo el estado
    // actual. Sembrar el indice actual antes de aplicarEstado() evita que
    // esa primera aplicación dispare el sonido.
    sembrarEstadoSinSonido(estadoRemoto)
    aplicarEstado(estadoRemoto)
    iniciarPolling()
  } catch {
    borrarSesionLocal()
  }
}

export function aplicarEstado(nuevo: GameStateView): void {
  const diaAnterior = store.estado?.environment.dia_actual
  const diaAvanzo = diaAnterior !== undefined && nuevo.environment.dia_actual > diaAnterior
  if (diaAvanzo) {
    store.reporteDiaPendiente = diaAnterior
  }

  const cartaId = nuevo.environment.ultima_carta_clima?.id ?? null
  if (cartaId !== null && cartaId !== ultimaCartaClimaId) {
    store.inicioDiaPendiente = true
  }
  ultimaCartaClimaId = cartaId

  // "El turno llega" es o bien (a) otro jugador tenia el turno y ahora es
  // el mio, o (b) empezo un dia nuevo y me toca -- (b) hace falta porque en
  // una partida solo (o cualquier ronda donde nadie mas queda elegible)
  // jugador_en_turno_idx nunca se observa en OTRO indice entre una visita y
  // la siguiente: el ciclo Fase III -> Fase I -> Fase II del dia siguiente
  // ocurre server-side y el cliente solo ve "sigue siendo mi turno" de
  // snapshot a snapshot, asi que la condicion (a) sola nunca dispara.
  const miIndice = store.sesion?.playerIndex
  if (
    miIndice !== undefined &&
    nuevo.jugador_en_turno_idx === miIndice &&
    (jugadorEnTurnoAnterior !== miIndice || diaAvanzo)
  ) {
    // El tablero vuelve al propio: es donde estan la carpeta, la despensa y
    // el cultivo que las acciones del turno necesitan mirar, y el reloj de
    // pase por inactividad ya corre. Va ANTES del sonido a proposito, para
    // que la vuelta no dependa del interruptor de audio.
    store.jugadorObservado = null
    // Un poco despues: si el turno llego porque un oponente acaba de
    // actuar, su sonido de accion esta sonando ahora mismo.
    if (store.preferencias.sonido) reproducirNotificacionTurno(0.35)
  }
  jugadorEnTurnoAnterior = nuevo.jugador_en_turno_idx

  // Fin de partida: la fanfarria para quien gana, un cierre corto para el
  // resto. Es el unico sonido del juego que NO es el mismo en todas las
  // pestañas, y por eso no puede viajar por el canal `accion` del SSE (un
  // broadcast con una sola carga util); se decide aqui, donde cada cliente ya
  // sabe cual es su asiento.
  //
  // La condicion es la FASE y no `partida_terminada`: ese flag se enciende en
  // cuanto alguien hornea su quinta receta y todavia queda la jornada entera
  // por jugar (ver GameView.vue). `ranking` tampoco sirve de señal -- viaja en
  // todos los snapshots, tambien a mitad de partida, con resultados parciales.
  if (nuevo.fase_actual === 'terminada' && !finDePartidaSonado) {
    finDePartidaSonado = true
    if (store.preferencias.sonido) {
      // Puede haber mas de un ganador: un empate en los cuatro criterios
      // comparte la posicion 1 (engine.calcular_ranking_final).
      const ganadores = nuevo.ranking.filter((r) => r.posicion === 1).map((r) => r.player_idx)
      if (miIndice !== undefined && ganadores.includes(miIndice)) {
        reproducirFanfarriaVictoria()
      } else {
        reproducirCierreDerrota()
      }
    }
  }

  // Otro jugador pidió terminar la partida antes de tiempo: si yo todavía no
  // voté (ni descarté el aviso a este conteo), mostrar el modal de confirmación.
  const votos = nuevo.votos_fin_anticipado
  const otrosVotaron = votos.some((i) => i !== miIndice)
  const yoVote = miIndice !== undefined && votos.includes(miIndice)
  // La condición es la fase y no `partida_terminada`: ese flag ya está en true
  // durante la última jornada (ver GameView.vue), en la que el acuerdo unánime
  // sigue siendo válido para saltarse lo que queda de día.
  if (
    nuevo.fase_actual !== 'terminada' &&
    otrosVotaron &&
    !yoVote &&
    votos.length > finAnticipadoDescartadoEnConteo
  ) {
    store.finAnticipadoPendiente = true
  }

  store.estado = nuevo
}

export function reconocerReporteDia(): void {
  store.reporteDiaPendiente = null
}

export function reconocerInicioDia(): void {
  store.inicioDiaPendiente = false
}

/** El jugador descartó el aviso de fin anticipado ("Ahora no"). No vuelve a
 * aparecer hasta que otro jugador más se sume al pedido (el conteo crezca). */
export function reconocerFinAnticipado(): void {
  store.finAnticipadoPendiente = false
  if (store.estado) {
    finAnticipadoDescartadoEnConteo = store.estado.votos_fin_anticipado.length
  }
}

/**
 * Deja el store listo para mostrar la sala de espera de nuevo (sin tocar
 * `store.sesion`, para que LobbyView.vue la retome tal cual ya hace al
 * reconectar) -- usado tanto por `volverALobby()` (quien lo pidió) como
 * por `refrescarEstado()` (todo el resto de jugadores, que se enteran de
 * que el host reinició la sala en su próximo poll/evento).
 */
function volverAVistaDeLobby(): void {
  detenerTransmisionEnVivo()
  store.estado = null
  store.eventos = []
  store.ultimoSeqVisto = 0
  store.reporteDiaPendiente = null
  store.inicioDiaPendiente = false
  store.finAnticipadoPendiente = false
  store.resultadoHorneado = null
  store.jugadorObservado = null
  ultimaCartaClimaId = undefined
  finAnticipadoDescartadoEnConteo = -1
  jugadorEnTurnoAnterior = null
  finDePartidaSonado = false
}

export async function refrescarEstado(): Promise<void> {
  if (!store.sesion) return
  try {
    aplicarEstado(await api.obtenerEstado(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    if (e instanceof api.ApiFallo && e.codigo === 'sala_no_disponible') {
      // El host volvió la sala a LOBBY (volverALobby) -- no es un error,
      // es la señal de que este jugador también debe volver a la espera.
      volverAVistaDeLobby()
      return
    }
    store.error = e instanceof Error ? e.message : String(e)
  }
}

export async function refrescarEventos(): Promise<void> {
  if (!store.sesion) return
  try {
    // `desde` se congela aqui: mientras vuela la peticion, el SSE puede
    // empujar eventos y adelantar ultimoSeqVisto, y entonces la respuesta
    // (que arranca en `desde`) solapa con lo ya recibido. Sin recortar ese
    // solape se duplicaban filas en el Registro y en el informe de Fase III.
    // Importa mas que antes: RegistroEventos.vue intercala acciones y eventos
    // usando el INDICE de cada evento, asi que un duplicado desalinearia todo
    // lo que viene detras, no solo se veria repetido.
    const desde = store.ultimoSeqVisto
    const r = await api.obtenerEventos(store.sesion.roomId, store.sesion.token, desde)
    const yaVistos = Math.max(0, store.ultimoSeqVisto - desde)
    const nuevos = r.eventos.slice(yaVistos)
    if (nuevos.length > 0) store.eventos.push(...nuevos)
    store.ultimoSeqVisto = Math.max(store.ultimoSeqVisto, r.seq)
  } catch {
    // El polling de eventos es secundario: un fallo aqui no debe tapar el
    // error (mas importante) del polling de estado.
  }
}

/**
 * Abre la conexión SSE (Milestone 5) a GET /games/{id}/events/stream. El
 * navegador (EventSource) no puede enviar cabeceras personalizadas, así
 * que el token va como ?player_token= en la URL -- ver
 * server/app.py:_requerir_token_sse. Cada evento recibido dispara de
 * inmediato un refrescarEstado() (el evento casi siempre implica que el
 * estado cambió; no tiene sentido esperar al próximo tick de respaldo).
 *
 * EventSource reconecta solo, con backoff propio del navegador, y reenvía
 * Last-Event-ID automáticamente para retomar donde se quedó -- por eso el
 * polling de eventos (arriba) se mantiene solo como respaldo lento, no
 * como vía principal.
 */
function iniciarEventSource(): void {
  if (!store.sesion) return
  fuenteEventos?.close()

  const url =
    `/games/${store.sesion.roomId}/events/stream` +
    `?since=${store.ultimoSeqVisto}&player_token=${encodeURIComponent(store.sesion.token)}`
  const es = new EventSource(url)

  // Canal efimero paralelo (server/sessions.py:AvisoAccion): un frame con
  // nombre `accion` por cada movimiento de cualquier jugador. Llega aqui y
  // NO a onmessage precisamente por tener nombre, asi que el log de eventos
  // de abajo no se entera. No trae `id:`, asi que tampoco mueve el
  // Last-Event-ID -- un aviso no puede descolocar el resume del log.
  //
  // No hace falta ningun guard de "no repetir al reconectar" (como el
  // sembrarTurnoSinSonido() del aviso de turno): los avisos no tienen
  // backlog, asi que reconectar no reproduce nada de lo ya ocurrido.
  es.addEventListener('accion', (mensaje) => {
    let aviso: AvisoAccionView
    try {
      aviso = JSON.parse((mensaje as MessageEvent).data) as AvisoAccionView
    } catch {
      return
    }
    const sonido = SONIDOS_ACCION[aviso.accion as IdSonido]
    if (sonido && store.preferencias.sonido) reproducirSonido(sonido)
    // Ademas del sonido: hasta ahora, 11 de las 12 acciones no emitian
    // ningun evento, asi que el tablero de un oponente solo se actualizaba
    // cuando caia el poll de respaldo (hasta 4s despues). Refrescar aqui
    // hace que lo que se oye y lo que se ve lleguen juntos.
    void refrescarEstado()
  })

  es.onmessage = (mensaje) => {
    try {
      const evento = JSON.parse(mensaje.data)
      // `id:` es 1-based (el evento de indice i llega con id i+1), asi que
      // ultimoSeqVisto es "cuantos eventos llevo" y store.eventos[i] es el
      // evento i del motor. Mantener esa alineacion es lo que permite que
      // RegistroEventos.vue ordene por `pos_eventos`; un frame ya visto
      // (reconexion que reenvia backlog, carrera con refrescarEventos) se
      // descarta en vez de desplazar todo el hilo.
      const seq = Number(mensaje.lastEventId)
      if (!Number.isNaN(seq) && seq <= store.ultimoSeqVisto) return
      store.eventos.push(evento)
      if (!Number.isNaN(seq)) store.ultimoSeqVisto = seq
    } catch {
      return
    }
    void refrescarEstado()
  }

  fuenteEventos = es
}

export function iniciarPolling(): void {
  detenerTransmisionEnVivo()
  iniciarEventSource()
  manejadorEstado = window.setInterval(refrescarEstado, INTERVALO_RESPALDO_ESTADO_MS)
  manejadorEventosRespaldo = window.setInterval(refrescarEventos, INTERVALO_RESPALDO_EVENTOS_MS)
}

export function detenerTransmisionEnVivo(): void {
  if (manejadorEstado !== undefined) window.clearInterval(manejadorEstado)
  if (manejadorEventosRespaldo !== undefined) window.clearInterval(manejadorEventosRespaldo)
  manejadorEstado = undefined
  manejadorEventosRespaldo = undefined
  fuenteEventos?.close()
  fuenteEventos = null
}

export async function despacharAccion(
  accion: string,
  params: Record<string, unknown> = {},
): Promise<void> {
  if (!store.sesion || !store.estado) return
  store.cargando = true
  try {
    aplicarEstado(
      await api.enviarAccion(store.sesion.roomId, store.sesion.token, accion, params, store.estado.turno_nonce),
    )
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
    throw e
  } finally {
    store.cargando = false
  }
}

export async function pasar(): Promise<void> {
  if (!store.sesion) return
  store.cargando = true
  try {
    aplicarEstado(await api.pasarTurno(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}

/** Deshace la visita en curso (restaura al inicio de la visita). El servidor
 * es la autoridad: el boton solo se muestra cuando estado.puede_deshacer. */
export async function deshacer(): Promise<void> {
  if (!store.sesion) return
  store.cargando = true
  try {
    aplicarEstado(await api.deshacerAccion(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}

/** Milestone 6: cualquier jugador puede forzar el pase del jugador activo
 * si lleva mucho tiempo inactivo. El servidor decide si corresponde --
 * este cliente no intenta llevar la cuenta de cuánto tiempo pasó, solo
 * ofrece el botón y muestra el error del servidor si todavía es pronto. */
export async function forzarPase(): Promise<void> {
  if (!store.sesion) return
  store.cargando = true
  try {
    aplicarEstado(await api.forzarPase(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}

/** Confirma que este jugador quiere terminar la partida antes de tiempo.
 * No hay forma de retirar el voto (ver store.ts:GameView.vue). */
export async function confirmarFinAnticipado(): Promise<void> {
  if (!store.sesion) return
  store.cargando = true
  try {
    aplicarEstado(await api.confirmarFinAnticipado(store.sesion.roomId, store.sesion.token))
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}

/** Crea una sala nueva reutilizando el nombre/color de este jugador y la
 * misma cantidad de jugadores que la partida recién terminada, y entra
 * directo a su sala de espera -- usado desde RankingView.vue como una de
 * las dos opciones de fin de partida (la otra es cerrarSesion()), ahora
 * que cualquier jugador (no solo el host) decide qué hacer al terminar. */
export async function crearSalaNueva(): Promise<void> {
  if (!store.sesion || !store.estado) return
  const jugadorActual = store.estado.players[store.sesion.playerIndex]
  const nombre = jugadorActual.nombre
  const color = jugadorActual.color
  const maxJugadores = store.estado.players.length
  store.cargando = true
  try {
    const r = await api.crearSala(nombre, color, maxJugadores)
    volverAVistaDeLobby()
    establecerSesion({
      roomId: r.room_id,
      token: r.player_token,
      playerIndex: r.player_index,
      hostToken: r.host_token,
      nombre,
    })
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}

/** Solo el host: vuelve la sala a LOBBY tras una partida terminada. Los
 * demás jugadores se enteran solos en su próximo refrescarEstado().
 * No usado actualmente (ver RankingView.vue), se deja intacto por si se
 * retoma la opción de reusar la sala. */
export async function volverALobby(): Promise<void> {
  if (!store.sesion?.hostToken) return
  store.cargando = true
  try {
    await api.volverALobby(store.sesion.roomId, store.sesion.hostToken)
    volverAVistaDeLobby()
    store.error = null
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.cargando = false
  }
}
