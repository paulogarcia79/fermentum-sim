// Traduccion de los valores crudos de ClimateCard (models.py: EfectoBiologico /
// EfectoClimatico) a texto en español para el jugador. Compartido por
// CartaClima.vue (recuadro de efecto en la carta) y InicioDiaModal.vue
// (lista de detalle), para que ambos usen exactamente la misma redaccion.
import type { ClimateCard } from './types'
import { HARINA_ALIMENTAR } from './data/alimentar'

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
      return 'Iniciar Receta (Acción B) cuesta 1 token de Agua menos hoy (−5% de hidratación).'
    case 'Aletargamiento Invernal':
      return (
        'Al final del día, el cultivo base de cada jugador pierde 2 de Vitalidad en vez de 1. ' +
        `Alimentar el Cultivo puede reponer +2 por ${HARINA_ALIMENTAR[2]}% de harina.`
      )
    default:
      return null
  }
}
