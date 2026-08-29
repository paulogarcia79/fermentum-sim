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

/** Timbre corto de dos tonos (subida rapida) para avisar que llego el turno. */
export function reproducirNotificacionTurno(retraso = 0): void {
  tocarTonos([
    { frecuencia: 880, retraso, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
    { frecuencia: 1108.73, retraso: retraso + 0.11, duracion: 0.16, onda: 'sine', ganancia: 0.22 },
  ])
}
