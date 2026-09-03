// Descripciones de cada acción para los tooltips de BarraAcciones.vue --
// fuente única de verdad, adaptada de context/ACTIONS_REGISTRY.md. También
// se reutilizan como el texto de los ModalConfirmacion de H/I/horas_extras
// en vez de mantener una segunda copia escrita a mano.
import { AGUA_PEDIDO_URGENCIA_TOKENS, HARINA_PEDIDO_URGENCIA_PCT } from './pedidoUrgencia'
import { fmtAgua, fmtHarina } from './unidades'

export type IdAccion =
  | 'A'
  | 'B'
  | 'C'
  | 'D'
  | 'E'
  | 'descarte'
  | 'F'
  | 'G'
  | 'simposio'
  | 'jefatura'
  | 'mostrador'
  | 'H'
  | 'I'
  | 'horas_extras'
  | 'pedido_urgencia'
  | 'estasis'
  | 'incubadora'

/**
 * Todo lo que puede aparecer como una linea del registro de la partida: las
 * 14 acciones mas los tres movimientos que no pasan por /actions. Vive aqui,
 * junto al IdAccion que extiende, por el mismo motivo que GRUPOS_ACCION: la
 * tabla al lado del tipo que indexa. Espejo de los ids que
 * server/sessions.py:EntradaRegistro.accion puede tomar.
 *
 * Ojo: NO es IdSonido (data/sonidosAccion.ts). Un pase forzado suena como un
 * pase normal, asi que el canal de sonido no lo distingue; el registro si,
 * porque solo el necesita decir quien lo forzo.
 */
export type IdMovimiento = IdAccion | 'pasar' | 'deshacer' | 'pase_forzado'

export const descripcionesAcciones: Record<IdAccion, string> = {
  A: 'Gratis, una vez por día. Resta 1 token de Harina (10%, cualquier tipo) por +1 Vitalidad (máx. 6). Repone exactamente el -1 que el desgaste metabólico quita cada noche. Ya no toca la Acidez: eso es ahora la acción «Descarte».',
  B: 'Consume 10 tokens de Harina de un tipo (100%, una bolsa entera) + los tokens de Agua exactos que pida la receta (1 token = 5% de hidratación). Sella tu Vitalidad (dado de inóculo) y, si tu Acidez cae en el rango de bono de la receta, también tu Acidez.',
  C: 'Compra y/o vende Harina (Blanca, Integral o Centeno) contra el visor de precio compartido de la Bolsa de Harinas, y/o compra un lote de Agua al precio de la temperatura actual (los lotes son de 2 tokens (10%), 6 (30%), 12 (60%) o 20 (100%)). Cada compra o venta de harina mueve una bolsa entera de 10 tokens (100%) o media bolsa de 5 (50%); la media cuesta la mitad del precio visible redondeando hacia arriba al comprar y hacia abajo al vender, y mueve el visor una casilla igual que una bolsa entera. Puedes combinar varias transacciones en la misma visita, pero como máximo una por tipo de recurso (no puedes comprar y vender la misma harina, ni comprar dos veces). Aquí se firma también el Contrato con el Molino: un pago único (Blanca 3, Integral 4, Centeno 6 Monedas) por el que el molino te entrega 2 tokens (20%) de esa harina cada Fase III, para siempre y sin mover el visor. Uno solo por partida, sin cambio ni cancelación; se amortiza a la cuarta noche. Es la única harina que no compras, y por eso la única que puedes vender sin haberla pagado antes al precio de la Bolsa.',
  D: 'Gasta Datos de Investigación en una mejora permanente de laboratorio: Incubadora (3 Datos, ajusta la temperatura local ±5°C), Cámara B (4 Datos, desbloquea Estación 03 y mejora Pliegues), Módulo Analítico (4 Datos, ensancha la Zona Óptima una casilla por lado —y retrasa el colapso con ella—, y sube el horneado óptimo a 2 Datos, 3 en el centro exacto) o Criopreservación (2 Datos, ignora el desgaste metabólico de Vitalidad en Fase III). Cada mejora solo puede instalarse una vez, pero puedes llegar a instalar varias distintas a lo largo de la partida. Ninguna mejora desbloquea recetas: ninguna carta está restringida por tecnología.',
  E: 'Gratis en PA, una vez por día: se paga en Monedas. Compra 1, 2 o 3 espacios de avance de fermentación por 1, 3 o 6 Monedas y repártelos entre tus masas. Con la mejora Cámara B puedes repartirlos entre dos masas distintas (la mejora no aumenta cuántos compras), o bien recuperar +1 Vitalidad de tu cultivo base por 6 Monedas. Ojo: pasarte de la zona óptima empuja la masa a la zona de colapso, que la Fase III hornea automáticamente.',
  descarte:
    'Gratis en PA, una vez por día: es el único control voluntario de tu Acidez, y va en los dos sentidos. SUBIR se paga en Agua (2, 5 o 9 tokens por +1, +2 o +3); BAJAR se paga en Monedas (1, 3 o 6 por -1, -2 o -3), porque descartar parte del cultivo y refrescarlo es tirar producto. Un solo sentido por visita. Sirve para caer dentro de la Acidez Diana de una receta antes de iniciarla (Bono de Sabor), pero recuerda que la Madurez final premia el equilibrio: el pico está en Acidez 3 y los extremos 0 y 6 no puntúan.',
  F: 'Finaliza el protocolo de una masa y la vende de inmediato: obtiene Puntos de Maestría y Monedas según su zona (más Datos de Investigación si cae en Zona Óptima). El bono de Acidez, si la carta lo tiene sellado, suma puntos y +2 Monedas — salvo en un colapso.',
  G: 'Toma 1 carta de receta del Mercado Central y la guarda boca arriba en tu Carpeta de Proyectos (máximo 3; si está llena, debes descartar una previa). El espacio del mercado queda vacío hasta el reabastecimiento al inicio del día siguiente.',
  simposio: 'Sacrifica un horneado exitoso de tu Archivo para publicarlo y ganar Datos de Investigación según su grado (Básica 1, Intermedia 2, Avanzada 3). El registro sale del archivo para siempre: pierdes sus Puntos de Maestría, su renta diaria, su paso hacia el 5/5 y, si era el único de su tipo, un escalón de Variedad de Recetas. Es una palanca de emergencia, nunca una jugada eficiente.',
  jefatura:
    'Cuesta 1 PA y paga 1 Dato de Investigación al instante. Mañana abrirás la Fase II como Investigador Jefe: el orden de turno se calcula una sola vez al día, así que lo que compras es la salida de mañana, no la de hoy. Es el único espacio GLOBAL del tablero — lo ocupa un jugador por día en toda la mesa, no uno por jugador — así que reclamarla también se la quita a los demás. Si nadie la reclama, la Jefatura se queda donde está; reclamarla siendo ya Jefe es legal y es la única forma de retenerla.',
  mostrador:
    'Cuesta 1 PA y paga 1 Moneda. Es el suelo del tablero: la acción que existe para que un turno con Puntos de Acción nunca se quede sin nada que hacer. A diferencia del resto de acciones con costo de PA, NO ocupa espacio — puedes repetirla mientras te queden PA. Cualquier otra acción rinde más: úsala cuando ninguna te sirva, en vez de pasar turno y renunciar también a tus acciones gratuitas del resto del día.',
  H: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 3 tokens de Harina (30%, cualquier tipo), sin costo de Agua. Limpia la Contaminación y fija Vitalidad=1, Acidez=1.',
  I: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 1 Dato de Investigación. Limpia la Contaminación y fija Vitalidad=2, Acidez=2.',
  horas_extras:
    'Gratis, en cualquier momento de tu turno, una vez por día. Costo: 1 Dato de Investigación. Otorga inmediatamente +1 Punto de Acción.',
  incubadora:
    'Solo con la Incubadora instalada y alguna masa fermentando. Gratis, sin costo, sin límite de usos: no ocupa espacio de acción ni termina tu turno. Fija, masa por masa, si esta noche avanza una casilla MENOS (−1), las de siempre (0) o una MÁS (+1). Sirve para frenar una masa que se pasaría de la Zona Óptima, o para empujar una que se quedaría corta. El ajuste dura una sola noche: la Fase III lo aplica y devuelve el dial a 0. Ojo: un +1 puede meter la masa en Colapso, y eso se hornea solo con penalización — el juego te enseña dónde caerá antes de confirmar, pero no te lo impide.',
  estasis:
    'Solo con la Criopreservación instalada. Gratis, sin costo, sin límite de usos: no ocupa espacio de acción ni termina tu turno. Decide si esta noche tu cultivo base sufre el desgaste metabólico normal (−1 Vitalidad, −2 con Aletargamiento Invernal) en vez de ignorarlo. Sirve para BAJAR la Vitalidad a voluntad: la Acción B sella el Dado de Inóculo con tu Vitalidad del día, así que una Vitalidad alta hace avanzar tus masas demasiado rápido para la zona óptima de las recetas Avanzadas. La Estasis se reactiva sola al día siguiente.',
  pedido_urgencia: `Gratis, sin límite por ronda. Costo: 1 Dato de Investigación. Ignora el mercado y entrega una parcela FIJA: ${fmtHarina(HARINA_PEDIDO_URGENCIA_PCT)} de un tipo de Harina (media bolsa) o ${fmtAgua(AGUA_PEDIDO_URGENCIA_TOKENS)} de Agua — uno de los dos, no ambos, y tú solo eliges cuál. Las cantidades son fijas porque el Pedido es un rescate, no un atajo para saltarse el mercado: media bolsa y no una entera para que revender lo pedido deje de ser el mejor negocio de la partida, y un lote de agua y no los que quieras porque 1 Dato llegaba a cubrir toda el agua de la partida.`,
}

/**
 * Acciones que REVELAN información oculta al resolverse — espejo de
 * ACCIONES_QUE_REVELAN en server/commands.py. Hoy NINGUNA acción lo hace
 * (todas operan sobre información pública), pero el contrato ya está
 * cableado: una acción listada aquí muestra en su tooltip el aviso de que
 * lo revelado no se puede deshacer (el servidor re-toma el checkpoint de
 * visita justo después de resolverla, así que un deshacer posterior
 * restaura DESDE ese punto, nunca antes).
 */
export const ACCIONES_QUE_REVELAN: ReadonlySet<IdAccion> = new Set()

/**
 * Los tres grupos de espacios de acción del tablero, en el orden en que se
 * pintan -- espejo de la división que hace context/ACTIONS_REGISTRY.md:
 * §2 "Catálogo de Acciones Principales (Costo: 1 PA)" y §3 "Acciones
 * Auxiliares y de Emergencia (Costo: 0 PA)", con los Protocolos de Emergencia
 * separados en su propia zona.
 *
 * OJO con la tercera zona: H e I son reactivas por DISPONIBILIDAD (solo se
 * habilitan con Contaminación activa), no por coste -- cuestan 1 PA y terminan
 * el turno igual que las principales. Su insignia dice 1 PA, no 0 PA.
 *
 * La tabla vive aquí, junto a IdAccion y las descripciones, para que
 * BarraAcciones.vue no tenga que mantener un segundo catálogo en paralelo.
 */
export type GrupoAccionId = 'principales' | 'gratuitas' | 'emergencia'

export interface GrupoAccion {
  id: GrupoAccionId
  /** Título de la zona. */
  titulo: string
  /** Insignia de coste en la cabecera: lo que cuesta CADA espacio de la zona. */
  costo: string
  /** La regla que define al grupo, en una línea. */
  nota: string
  acciones: { id: IdAccion; etiqueta: string; costo: string }[]
}

export const GRUPOS_ACCION: readonly GrupoAccion[] = [
  {
    id: 'principales',
    titulo: 'Acciones Principales',
    costo: '1 PA',
    nota: 'Terminan tu turno · un espacio distinto por visita',
    acciones: [
      { id: 'B', etiqueta: 'Iniciar Receta', costo: '1 PA' },
      { id: 'C', etiqueta: 'Visitar Mercado', costo: '1 PA' },
      { id: 'D', etiqueta: 'Implementar Mejora', costo: '1 PA' },
      { id: 'F', etiqueta: 'Hornear y Vender', costo: '1 PA' },
      { id: 'G', etiqueta: 'Investigar Protocolo', costo: '1 PA' },
      { id: 'simposio', etiqueta: 'Simposio Técnico', costo: '1 PA' },
      { id: 'jefatura', etiqueta: 'Reclamar Jefatura', costo: '1 PA' },
      { id: 'mostrador', etiqueta: 'Turno de Mostrador', costo: '1 PA' },
    ],
  },
  {
    id: 'gratuitas',
    titulo: 'Acciones Gratuitas',
    costo: '0 PA',
    nota: 'No terminan tu turno · puedes encadenarlas',
    acciones: [
      { id: 'A', etiqueta: 'Alimentar Cultivo', costo: '0 PA' },
      { id: 'E', etiqueta: 'Pliegues', costo: '1-6 Monedas' },
      { id: 'descarte', etiqueta: 'Descarte', costo: 'Agua o Monedas' },
      { id: 'horas_extras', etiqueta: 'Horas Extras', costo: '0 PA' },
      { id: 'pedido_urgencia', etiqueta: 'Pedido de Urgencia', costo: '0 PA' },
      { id: 'estasis', etiqueta: 'Estasis Biológica', costo: '0 PA' },
      { id: 'incubadora', etiqueta: 'Incubadora', costo: '0 PA' },
    ],
  },
  {
    id: 'emergencia',
    titulo: 'Protocolos de Emergencia',
    costo: '1 PA',
    nota: 'Solo con Contaminación activa (Vitalidad 0)',
    acciones: [
      { id: 'H', etiqueta: 'Re-cultivo Manual', costo: '1 PA' },
      { id: 'I', etiqueta: 'Inóculo de Emergencia', costo: '1 PA' },
    ],
  },
]
