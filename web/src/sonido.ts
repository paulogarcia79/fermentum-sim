// sonido.ts -- sintesis de los efectos de sonido del juego. Sin assets de
// audio en el proyecto (web/public/ solo tiene favicon.svg) y sin poder
// obtener/licenciar un archivo externo desde este entorno, cada sonido se
// escribe a mano como una receta de tonos Web Audio en vez de reproducir un
// <audio src> -- el mismo criterio que siguen los Icono*.vue, que dibujan
// cada silueta a mano en SVG en vez de importar imagenes.
//
// La tabla de recetas vive en data/sonidosAccion.ts; aqui solo esta el
// motorcito que las reproduce.
let contexto: AudioContext | null = null

/** Un tono dentro de una receta: todo relativo al inicio de la reproduccion. */
export interface Tono {
  frecuencia: number
  /** Segundos desde el inicio del sonido. 0 = inmediato. */
  retraso: number
  duracion: number
  onda: OscillatorType
  /** Pico de ganancia (0-1). Los sonidos frecuentes van mas bajos. */
  ganancia: number
}

/**
 * Un sonido reproducible. Hoy todas las entradas son `sintetizado`; la rama
 * `archivo` existe para poder cambiar una receta concreta por un .ogg real
 * sin tocar nada del disparador (store.ts) ni de la tabla. Esta implementada
 * entera, pero sin ejercitar hasta que se use por primera vez.
 */
export type Sonido =
  | { clase: 'sintetizado'; tonos: Tono[] }
  | { clase: 'archivo'; url: string; volumen?: number }

/**
 * Crea (o retoma, si el navegador la suspendio) el AudioContext. Los
 * navegadores exigen un gesto del usuario antes de permitir audio -- ver
 * App.vue, que llama a esto en la primera interaccion de la pestaña, bien
 * antes de que un cambio de turno real necesite sonar.
 */
export function habilitarAudio(): void {
  try {
    if (!contexto) {
      contexto = new AudioContext()
    }
    if (contexto.state === 'suspended') {
      void contexto.resume()
    }
  } catch (e) {
    // Sin Web Audio disponible (navegador viejo, contexto bloqueado) -- la
    // notificacion sonora simplemente no suena, no debe romper la app.
    console.debug('[sonido] habilitarAudio() falló:', e)
  }
}

/**
 * Primitivo de sintesis: reproduce una lista de tonos como un solo sonido.
 * Un fallo aqui nunca debe interrumpir el juego, asi que se traga todo.
 */
function tocarTonos(tonos: Tono[]): void {
  try {
    if (!contexto) {
      console.debug('[sonido] Sin AudioContext -- habilitarAudio() no corrio todavia en esta pestaña.')
      return
    }
    // Algunos navegadores suspenden el AudioContext de una pestaña en
    // segundo plano/inactiva tras un rato, incluso si ya se habilito con un
    // gesto anterior -- retomarlo aqui no necesita un gesto nuevo (el
    // contexto ya fue desbloqueado una vez), solo hace falta pedirlo de
    // nuevo antes de reproducir.
    if (contexto.state !== 'running') {
      void contexto.resume()
    }
    const ahora = contexto.currentTime

    for (const tono of tonos) {
      const oscilador = contexto.createOscillator()
      const ganancia = contexto.createGain()
      oscilador.type = tono.onda
      oscilador.frequency.value = tono.frecuencia
      oscilador.connect(ganancia)
      ganancia.connect(contexto.destination)

      const inicio = ahora + tono.retraso
      const fin = inicio + tono.duracion
      ganancia.gain.setValueAtTime(0, inicio)
      ganancia.gain.linearRampToValueAtTime(tono.ganancia, inicio + 0.012)
      ganancia.gain.exponentialRampToValueAtTime(0.0001, fin)

      oscilador.start(inicio)
      oscilador.stop(fin + 0.02)
    }
  } catch (e) {
    console.debug('[sonido] tocarTonos() falló:', e)
  }
}

/** Reproduce cualquier `Sonido`, venga de sintesis o de un archivo. */
export function reproducirSonido(sonido: Sonido): void {
  if (sonido.clase === 'sintetizado') {
    tocarTonos(sonido.tonos)
    return
  }
  try {
    const audio = new Audio(sonido.url)
    audio.volume = sonido.volumen ?? 0.5
    void audio.play()
  } catch (e) {
    console.debug('[sonido] reproducirSonido(archivo) falló:', e)
  }
}

/**
 * Aviso de que acaba de aparecer una sala abierta en la portada.
 *
 * Vive aqui y no en `data/sonidosAccion.ts` por el mismo motivo que la
 * fanfarria de fin de partida: esa tabla es un `Record<IdSonido, Sonido>`
 * exhaustivo sobre los ids de accion del protocolo, y esto no es la accion de
 * nadie -- es un cambio en la lista de salas que el cliente detecta sondeando.
 *
 * Dos decisiones de timbre, ambas por contraste con sonidos que ya existen:
 *
 *   - Mas grave y mas flojo que `reproducirNotificacionTurno` (E5-A5 a 0.16 de
 *     ganancia, contra A5-C#6 a 0.22). "Te toca jugar" es una afirmacion mas
 *     fuerte que "ha aparecido algo", y si sonaran igual el aviso mas urgente
 *     del juego perderia su significado.
 *   - `sine` y no `sawtooth`: la onda de sierra es el timbre de los Protocolos
 *     de Emergencia (ver SONIDOS_ACCION.H/I), y se leeria como que algo ha
 *     fallado.
 *
 * Suena UNA vez por sondeo aunque aparezcan varias salas a la vez: el
 * disparador (FormularioSala.vue) llama a esto una sola vez por tanda.
 */
export function reproducirAvisoSalaNueva(): void {
  tocarTonos([
    { frecuencia: 659.25, retraso: 0, duracion: 0.12, onda: 'sine', ganancia: 0.16 },
    { frecuencia: 880, retraso: 0.1, duracion: 0.14, onda: 'sine', ganancia: 0.16 },
  ])
}

/** Timbre corto de dos tonos (subida rapida) para avisar que llego el turno. */
export function reproducirNotificacionTurno(retraso = 0): void {
  tocarTonos([
    { frecuencia: 880, retraso, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
    { frecuencia: 1108.73, retraso: retraso + 0.11, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
  ])
}

/*
 * FIN DE PARTIDA -- los dos unicos sonidos que NO suenan igual en todas las
 * pestañas. Cada sonido de accion viaja por el canal `accion` del SSE, que es
 * un broadcast con una unica carga util identica para todos; "una fanfarria
 * para el ganador y otra cosa para los demas" no cabe ahi. Lo decide cada
 * cliente en `store.ts:aplicarEstado()`, que es donde la pestaña ya sabe cual
 * es su propio asiento. Viven aqui y no en `data/sonidosAccion.ts` porque esa
 * tabla es un `Record<IdSonido, Sonido>` exhaustivo sobre los ids de accion
 * del protocolo, y estos dos no son acciones de nadie.
 */

/**
 * Fanfarria de victoria: triada mayor ascendente C5-E5-G5, octava C6 y un
 * acorde final sostenido.
 *
 * Deliberadamente mas larga, mas aguda y mas rica que el arpegio de la Accion F
 * (`SONIDOS_ACCION.F`, el otro sonido «de premio» del juego): si sonaran
 * parecido, ganar la partida se confundiria con que alguien acaba de hornear.
 */
export function reproducirFanfarriaVictoria(): void {
  tocarTonos([
    { frecuencia: 523.25, retraso: 0, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
    { frecuencia: 659.25, retraso: 0.13, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
    { frecuencia: 783.99, retraso: 0.26, duracion: 0.16, onda: 'sine', ganancia: 0.24 },
    { frecuencia: 1046.5, retraso: 0.39, duracion: 0.75, onda: 'sine', ganancia: 0.26 },
    // El acorde debajo de la nota larga: la deja sonar a triada, no a pitido.
    { frecuencia: 659.25, retraso: 0.42, duracion: 0.7, onda: 'sine', ganancia: 0.14 },
    { frecuencia: 783.99, retraso: 0.42, duracion: 0.7, onda: 'sine', ganancia: 0.12 },
  ])
}

/**
 * Cierre para quien no gana: tres tonos descendentes, cortos y bajos de
 * ganancia.
 *
 * Es un punto final, no una burla -- y es `sine` a proposito: el `sawtooth`
 * descendente esta reservado al timbre de los Protocolos de Emergencia
 * (`data/sonidosAccion.ts`), y reutilizarlo aqui diria "algo ha fallado".
 */
export function reproducirCierreDerrota(): void {
  tocarTonos([
    { frecuencia: 659.25, retraso: 0, duracion: 0.16, onda: 'sine', ganancia: 0.16 },
    { frecuencia: 523.25, retraso: 0.15, duracion: 0.16, onda: 'sine', ganancia: 0.15 },
    { frecuencia: 440.0, retraso: 0.3, duracion: 0.34, onda: 'sine', ganancia: 0.14 },
  ])
}
