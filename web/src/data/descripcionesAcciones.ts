// Descripciones de cada acción para los tooltips de BarraAcciones.vue --
// fuente única de verdad, adaptada de context/ACTIONS_REGISTRY.md. También
// se reutilizan como el texto de los ModalConfirmacion de H/I/horas_extras
// en vez de mantener una segunda copia escrita a mano.

export type IdAccion =
  | 'A'
  | 'B'
  | 'C'
  | 'D'
  | 'E'
  | 'F'
  | 'G'
  | 'simposio'
  | 'H'
  | 'I'
  | 'horas_extras'
  | 'pedido_urgencia'

export const descripcionesAcciones: Record<IdAccion, string> = {
  A: 'Gratis, una vez por día. Puedes restar 10% de Harina (cualquier tipo) por +1 Vitalidad y/o 10% de Agua por +1 Acidez (máx. 6 cada una) — uno, otro, o ambos en la misma acción.',
  B: 'Consume 1 Harina (100% de un tipo) + los tokens de Agua exactos que pida la receta. Sella tu Vitalidad (dado de inóculo) y, si tu Acidez cae en el rango de bono de la receta, también tu Acidez.',
  C: 'Compra y/o vende Harina (Blanca, Integral o Centeno) contra el visor de precio compartido de la Bolsa de Harinas, y/o compra un lote de Agua al precio de la temperatura actual. Puedes combinar varias transacciones en la misma visita, pero como máximo una por tipo de recurso (no puedes comprar y vender la misma harina, ni comprar dos veces).',
  D: 'Gasta Datos de Investigación en una mejora permanente de laboratorio: Incubadora (3 Datos, ajusta la temperatura local ±5°C), Cámara B (4 Datos, desbloquea Estación 03 y mejora Pliegues), Módulo Analítico (3 Datos, +1 Dato extra al hornear en zona óptima y habilita recetas Avanzadas) o Criopreservación (2 Datos, ignora el desgaste metabólico de Vitalidad en Fase III). Cada mejora solo puede instalarse una vez, pero puedes llegar a instalar varias distintas a lo largo de la partida.',
  E: 'Avanza el marcador de Inóculo de una masa 1 casilla. Con la mejora Cámara B, puedes en su lugar recuperar +1 Vitalidad de tu cultivo base, o afectar dos masas a la vez.',
  F: 'Finaliza el protocolo de una masa y la vende de inmediato: obtiene Puntos de Maestría y Monedas según su zona (más Datos de Investigación si cae en Zona Óptima). El bono de Acidez, si la carta lo tiene sellado, suma puntos y +2 Monedas — salvo en un colapso.',
  G: 'Toma 1 carta de receta del Mercado Central y la guarda boca arriba en tu Carpeta de Proyectos (máximo 3; si está llena, debes descartar una previa). El espacio del mercado queda vacío hasta el reabastecimiento al inicio del día siguiente.',
  simposio: 'Descarta una carta de receta de tu carpeta de proyectos o de una estación de fermentación para ganar 1 Dato de Investigación de inmediato.',
  H: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 50% de Harina (cualquier tipo), sin costo de Agua. Limpia la Contaminación y fija Vitalidad=1, Acidez=1.',
  I: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 1 Dato de Investigación. Limpia la Contaminación y fija Vitalidad=2, Acidez=2.',
  horas_extras:
    'Gratis, en cualquier momento de tu turno, una vez por día. Costo: 1 Dato de Investigación. Otorga inmediatamente +1 Punto de Acción.',
  pedido_urgencia:
    'Gratis, sin límite por ronda. Costo: 1 Dato de Investigación. Ignora el mercado y obtiene directamente 100% de un tipo de Harina, o los tokens de Agua que elijas — uno de los dos, no ambos.',
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
