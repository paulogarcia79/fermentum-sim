// sonido.ts -- notificacion sonora de turno. Sin assets de audio en el
// proyecto (web/public/ solo tiene favicon.svg) y sin poder obtener/licenciar
// un archivo externo desde este entorno, se sintetiza un timbre corto con
// Web Audio en vez de reproducir un <audio src>. Si mas adelante se quiere
// un sonido real, solo hay que reemplazar reproducirNotificacionTurno() --
// el trigger en store.ts no cambia.
let contexto: AudioContext | null = null

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

/** Timbre corto de dos tonos (subida rapida) para avisar que llego el turno. */
export function reproducirNotificacionTurno(): void {
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
    const tonos: [frecuencia: number, inicio: number][] = [
      [880, ahora],
      [1108.73, ahora + 0.11],
    ]

    for (const [frecuencia, inicio] of tonos) {
      const oscilador = contexto.createOscillator()
      const ganancia = contexto.createGain()
      oscilador.type = 'sine'
      oscilador.frequency.value = frecuencia
      oscilador.connect(ganancia)
      ganancia.connect(contexto.destination)

      const fin = inicio + 0.16
      ganancia.gain.setValueAtTime(0, inicio)
      ganancia.gain.linearRampToValueAtTime(0.22, inicio + 0.012)
      ganancia.gain.exponentialRampToValueAtTime(0.0001, fin)

      oscilador.start(inicio)
      oscilador.stop(fin + 0.02)
    }
  } catch (e) {
    // Igual que arriba: un fallo aqui nunca debe interrumpir el juego.
    console.debug('[sonido] reproducirNotificacionTurno() falló:', e)
  }
}
