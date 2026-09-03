// Espejo de actions.HARINA_PEDIDO_URGENCIA / actions.AGUA_PEDIDO_URGENCIA: las
// dos parcelas FIJAS que entrega el Pedido de Urgencia. Mismo precedente que
// preciosReceta.ts y datosSimposio.ts -- el cliente solo necesita las cifras
// para etiquetar las dos opciones del modal, y la autoridad sigue siendo
// ActionManager.
//
// El jugador NO elige cantidad, solo cual de los dos recursos quiere: el agua
// tuvo cantidad libre y 1 Dato compraba toda el agua de la partida (una receta
// pide 10-17 tokens y un lote del 100% cuesta 7-14 Monedas). Los 6 tokens son
// el lote del 30%, que vale lo mismo en Monedas que la media bolsa de harina.
//
// Un cambio en cualquiera de las dos cantidades del servidor exige tocar este
// archivo tambien.

/** actions.HARINA_PEDIDO_URGENCIA -- PORCENTAJE (media bolsa = 5 tokens). */
export const HARINA_PEDIDO_URGENCIA_PCT = 50

/** actions.AGUA_PEDIDO_URGENCIA -- CONTEO DE TOKENS (6 = 30%). */
export const AGUA_PEDIDO_URGENCIA_TOKENS = 6
