// Descripciones de cada acción para los tooltips de BarraAcciones.vue --
// fuente única de verdad, adaptada de context/ACTIONS_REGISTRY.md. También
// se reutilizan como el texto de los ModalConfirmacion de H/I/horas_extras
// en vez de mantener una segunda copia escrita a mano.

export type IdAccion = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'simposio' | 'H' | 'I' | 'horas_extras'

export const descripcionesAcciones: Record<IdAccion, string> = {
  A: 'Gratis, una vez por día. Puedes restar 10% de Harina (cualquier tipo) por +1 Vitalidad y/o 10% de Agua por +1 Acidez (máx. 6 cada una) — uno, otro, o ambos en la misma acción.',
  B: 'Consume 1 Harina (100% de un tipo) + los tokens de Agua exactos que pida la receta. Sella tu Vitalidad (dado de inóculo) y, si tu Acidez cae en el rango de bono de la receta, también tu Acidez.',
  C: 'Toma un lote aleatorio del mercado central (Harina + Agua que suman 150%). Pagando +1 Dato de Investigación, ignoras el mercado y recibes 150% en los recursos que elijas.',
  D: 'Gasta Datos de Investigación en una mejora permanente de laboratorio: Incubadora (3 Datos, ajusta la temperatura local ±5°C), Cámara B (4 Datos, desbloquea Estación 03 y mejora Pliegues) o Módulo Analítico (3 Datos, +1 Dato extra al hornear en zona óptima). Solo una mejora por partida.',
  E: 'Avanza el marcador de Inóculo de una masa 1 casilla. Con la mejora Cámara B, puedes en su lugar recuperar +1 Vitalidad de tu cultivo base, o afectar dos masas a la vez.',
  F: 'Finaliza el protocolo de una masa y obtiene Puntos de Maestría según su zona (más Datos de Investigación si cae en Zona Óptima, y el bono de Acidez si la carta lo tiene sellado). Zona Baja o Sobre-fermentada no generan Datos.',
  G: 'Toma 1 carta de receta del Mercado Central y la guarda boca arriba en tu Carpeta de Proyectos (máximo 3; si está llena, debes descartar una previa). El espacio del mercado queda vacío hasta el refresco del día siguiente.',
  simposio: 'Descarta una carta de receta de tu carpeta de proyectos o de una estación de fermentación para ganar 1 Dato de Investigación de inmediato.',
  H: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 2 Harina (10% c/u de cualquier tipo) + 2 Agua. Limpia la Contaminación y fija Vitalidad=1, Acidez=1.',
  I: 'Solo disponible con Vitalidad en 0 (penalización de -3 Puntos de Maestría). Costo: 2 Datos de Investigación. Limpia la Contaminación y fija Vitalidad=2, Acidez=2.',
  horas_extras:
    'Gratis, en cualquier momento de tu turno, una vez por día. Costo: 1 Dato de Investigación. Otorga inmediatamente +1 Punto de Acción.',
}
