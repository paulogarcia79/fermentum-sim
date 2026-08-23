// Traduccion de los valores crudos de ClimateCard (models.py: EfectoBiologico /
// EfectoClimatico) a texto en español para el jugador. Compartido por
// CartaClima.vue (recuadro de efecto en la carta) y EventoClimaticoModal.vue
// (lista de detalle), para que ambos usen exactamente la misma redaccion.
import type { ClimateCard } from './types'

export function efectoBiologicoTexto(carta: ClimateCard): string | null {
  switch (carta.efecto_biologico) {
    case 'Ganancia Vitalidad':
      return 'Todos los jugadores ganan +1 Vitalidad (máx. 6).'
    case 'Ganancia Acidez':
      return 'Todos los jugadores ganan +1 Acidez (máx. 6).'
    default:
      return null
  }
}

export function efectoPasivoTexto(carta: ClimateCard): string | null {
  switch (carta.efecto_pasivo) {
    case 'Alta Humedad':
      return 'Iniciar Receta (Acción B) cuesta 1 token de Agua menos hoy.'
    case 'Aletargamiento Invernal':
      return 'Al final del día, el cultivo base de cada jugador pierde 2 de Vitalidad en vez de 1.'
    default:
      return null
  }
}
