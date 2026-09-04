// Espejo de los umbrales de sala de server/sessions.py, para poder decirlos en
// la interfaz. Mismo precedente que preciosHarina.ts / pedidoUrgencia.ts: el
// cliente solo los necesita para redactar un aviso, y la autoridad sigue
// estando entera en el servidor (RoomManager.limpiar_inactivas).
//
// Un cambio en el servidor exige tocar este archivo tambien.

/**
 * server/sessions.py:UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS, en minutos.
 *
 * Una sala en LOBBY se borra tras este tiempo sin actividad -- y hasta ahora
 * no habia forma de saberlo desde la interfaz: el codigo simplemente dejaba de
 * existir. Se dice en la sala de espera, que es exactamente donde alguien se
 * queda mirando un codigo sin tocar nada.
 */
export const MINUTOS_EXPIRACION_LOBBY = 30
