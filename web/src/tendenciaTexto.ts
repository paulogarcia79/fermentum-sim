// Traduccion del modificador crudo de una carta de Tendencia de Mercado
// (un entero -2..+2, ver engine.py: Market.aplicar_tendencia) a texto en
// español -- mismo rol que climaTexto.ts, compartido por CartaTendencia.vue.
export function textoTendencia(modificador: number): string {
  if (modificador === 0) {
    return 'Sin cambio en la Bolsa de Harinas.'
  }
  const casillas = Math.abs(modificador)
  const plural = casillas === 1 ? 'casilla' : 'casillas'
  if (modificador > 0) {
    return `Los 3 visores de harina suben ${casillas} ${plural} (máx. 5) — comprar sale más caro, vender rinde más.`
  }
  return `Los 3 visores de harina bajan ${casillas} ${plural} (mín. 1) — comprar sale más barato, vender rinde menos.`
}
