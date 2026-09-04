// Todo el texto de la portada y de la sala de espera, en un solo sitio.
//
// Vive aparte de las plantillas por dos motivos. Uno: repasar el tono de la
// pagina de entrada es leer un fichero, no cinco `<template>`. Dos, y es el
// importante: aqui NO PUEDE HABER NUMEROS DE REGLA. Ni precios, ni PA, ni
// umbrales, ni cuantas cartas trae un mazo. El reglamento
// (RULEBOOK.md/.html) es normativo y tests/test_reglamento_al_dia.py lo
// vigila contra el codigo; una cifra suelta en la portada seria una sexta
// copia que nadie comprueba y que envejece en silencio. La unica cifra
// permitida es "1-4 jugadores", que es una propiedad del producto y no una
// regla (server/sessions.py:MAX_JUGADORES la fija).
//
// Voz: segunda persona, sin marcar genero ("investigador jefe" no; "diriges"
// si), mezcla de laboratorio y panaderia. El descriptor y la ficha tecnica
// son la excepcion en tercera persona, porque son la contraportada de la caja.

export const TITULO = 'Fermentum'

/** El lema. Tres imperativos: lo que haces, en orden, cada dia. */
export const LEMA = 'Cultiva. Fermenta. Hornea a tiempo.'

/** Encima del titulo, en la ceja. */
export const CEJA = 'Laboratorio de fermentación · multijugador'

/** Una linea en tercera persona: que ES esto, para quien lo ve por primera vez. */
export const DESCRIPTOR =
  'Fermentum es un eurogame de gestión de recursos y construcción de motores para 1–4 ' +
  'investigadores, ambientado en un laboratorio de panadería científica.'

/** La ficha tecnica de la contraportada. Sin duracion: nada en el repo la fija. */
export const FICHA: string[] = [
  '1–4 jugadores',
  'Gestión de recursos · engine-building',
  'Online, por código de sala',
]

/**
 * El parrafo de ambientacion. Las palabras entre `**` se resaltan en cobre
 * (las convierte en `<strong>` la propia plantilla, para no meter HTML aqui).
 */
export const RELATO =
  'Diriges un laboratorio artesanal de fermentación. Tu masa madre está viva: su ' +
  '**Vitalidad** y su **Acidez** deciden si la próxima hornada sale perfecta o se viene ' +
  'abajo. Cada Día de Laboratorio inicias recetas, las dejas crecer con el calor de la ' +
  'jornada y eliges el momento justo para hornear: ni cruda, ni pasada. Investiga ' +
  'protocolos, negocia harina y agua en la bolsa, mejora tu equipo y acumula **Puntos de ' +
  'Maestría**. Quien más sume cuando cierre el laboratorio, gana.'

export interface FaseResumen {
  /** El ordinal romano tal y como lo usa el reglamento. */
  numero: string
  titulo: string
  texto: string
}

/**
 * El bucle del dia, que es la unica estructura que hay que entender antes de
 * sentarse. Se pinta igual en la portada y en la sala de espera
 * (TarjetasFases.vue), para que lo que lees mientras esperas sea lo mismo que
 * te convencio de entrar.
 */
export const FASES: FaseResumen[] = [
  {
    numero: 'I',
    titulo: 'Ambiente',
    texto: 'Se revela el clima del día y se anuncia hacia dónde se moverá el mercado.',
  },
  {
    numero: 'II',
    titulo: 'Acción',
    texto:
      'Por turnos, cada investigador ocupa espacios de acción: iniciar recetas, comerciar, ' +
      'mejorar el laboratorio, hornear.',
  },
  {
    numero: 'III',
    titulo: 'Fermentación',
    texto:
      'Las masas avanzan solas por el track. Lo que llega a la zona óptima vale; lo que se ' +
      'pasa, colapsa.',
  },
]

export interface Pilar {
  titulo: string
  texto: string
}

/** Los tres ejes de decision, en el orden en que los descubres jugando. */
export const PILARES: Pilar[] = [
  {
    titulo: 'Cultivo base',
    texto: 'Vitalidad y Acidez. Aliméntalo cada día o se contamina.',
  },
  {
    titulo: 'Track de fermentación',
    texto: 'Hornea dentro de la zona óptima, antes de que la masa colapse.',
  },
  {
    titulo: 'Maestría',
    texto: 'Puntos por hornear bien, por variar recetas y por el equipo que montes.',
  },
]

export const ENLACE_REGLAMENTO = 'Leer el reglamento completo'

// --- Sala de espera -------------------------------------------------------

export const SALA_COMPARTIR =
  'Pasa el código o el enlace al resto de investigadores. Entran desde esta misma pantalla.'

export const SALA_MIENTRAS_ESPERAS = 'Mientras esperas'

export const SALA_ASIENTO_VACIO = 'Esperando investigador…'
