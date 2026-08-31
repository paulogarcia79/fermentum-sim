import type { TecnologiaID } from '../types'

export interface Tecnologia {
  id: TecnologiaID
  nombre: string
  costo: number
  descripcion: string
}

export const TECNOLOGIAS: Tecnologia[] = [
  { id: 'incubadora', nombre: 'Incubadora', costo: 3, descripcion: 'Ajuste ±5°C local (±1 en Fase III) por masa.' },
  { id: 'camara_b', nombre: 'Cámara B', costo: 4, descripcion: 'Desbloquea Estación 03 y mejora la Acción E.' },
  { id: 'modulo_analitico', nombre: 'Módulo Analítico', costo: 4, descripcion: 'Ensancha la Zona Óptima ±1 casilla (y retrasa el colapso); 2 Datos al hornear en óptima, 3 en el centro exacto.' },
  { id: 'criopreservacion', nombre: 'Criopreservación', costo: 2, descripcion: 'Estasis Biológica: ignora el desgaste metabólico de Vitalidad en Fase III.' },
]
