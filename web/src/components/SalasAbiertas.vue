<script setup lang="ts">
// El listado de salas que esperan jugadores.
//
// Hasta ahora la unica forma de entrar era que alguien te pasara un codigo de
// seis letras por fuera: quien abria la pagina sin invitacion se encontraba un
// campo de codigo vacio y ninguna pista. El servidor ya filtra las privadas,
// las llenas y las empezadas (RoomManager.salas_abiertas), asi que cada fila
// que llega aqui es una sala donde unirse va a funcionar -- este componente no
// vuelve a filtrar nada.
import type { SalaAbierta } from '../api'
import { hexDeColor } from '../data/coloresJugador'
import {
  SALAS_ABIERTAS_TITULO,
  SALAS_ABIERTAS_VACIO,
  SALAS_ABIERTAS_VACIO_ACCION,
} from '../data/copyLanding'
import IconoPeon from './IconoPeon.vue'

defineProps<{ salas: SalaAbierta[] }>()
const emit = defineEmits<{ elegir: [string]; crear: [] }>()

/**
 * "hace 3 min" a partir de los segundos que manda el servidor. Se redondea
 * hacia abajo y por debajo de un minuto se dice "ahora mismo": la cifra exacta
 * no le sirve a nadie para decidir, y un "hace 0 min" se lee como un error.
 */
function antiguedad(segundos: number): string {
  if (segundos < 60) return 'ahora mismo'
  const minutos = Math.floor(segundos / 60)
  if (minutos < 60) return `hace ${minutos} min`
  const horas = Math.floor(minutos / 60)
  return `hace ${horas} h`
}
</script>

<template>
  <section class="salas">
    <p class="eyebrow">{{ SALAS_ABIERTAS_TITULO }}</p>

    <p v-if="salas.length === 0" class="vacio">
      {{ SALAS_ABIERTAS_VACIO }}
      <button type="button" class="enlace" @click="emit('crear')">
        {{ SALAS_ABIERTAS_VACIO_ACCION }}
      </button>
    </p>

    <ul v-else>
      <li v-for="sala in salas" :key="sala.room_id">
        <button type="button" class="fila" @click="emit('elegir', sala.room_id)">
          <span class="linea-superior">
            <span class="dato codigo">{{ sala.room_id }}</span>
            <span class="dato conteo">{{ sala.seats.length }}/{{ sala.max_jugadores }}</span>
          </span>
          <span class="linea-inferior">
            <span class="jugadores">
              <span v-for="asiento in sala.seats" :key="asiento.player_index" class="jugador">
                <span class="ico-xs" aria-hidden="true">
                  <IconoPeon :color="hexDeColor(asiento.color)" />
                </span>
                {{ asiento.nombre }}
              </span>
            </span>
            <span class="antiguedad">{{ antiguedad(sala.segundos_abierta) }}</span>
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.salas {
  margin-bottom: var(--e3);
}

.salas .eyebrow {
  margin-bottom: var(--e2);
}

.vacio {
  margin: 0;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
  line-height: 1.5;
}

.enlace {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  color: var(--cobre);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  /* Con muchas salas abiertas la tarjeta no debe crecer sin fin: se hace
     scroll dentro de la lista y el boton de Unirse sigue a la vista. */
  max-height: 210px;
  overflow-y: auto;
}

.fila {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  width: 100%;
  /* 44px minimos de objetivo tactil; en la practica cada fila pasa de 50. */
  min-height: 44px;
  padding: var(--e2) var(--e3);
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  color: var(--tinta);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--transicion), background var(--transicion);
}

.fila:hover {
  background: var(--carta);
  border-color: var(--borde-fuerte);
}

.linea-superior,
.linea-inferior {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e2);
}

.codigo {
  letter-spacing: 0.12em;
  font-size: var(--t-m);
}

.conteo {
  color: var(--cobre);
  font-size: var(--t-xs);
  flex: 0 0 auto;
}

.jugadores {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e1) var(--e2);
  min-width: 0;
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.jugador {
  display: inline-flex;
  align-items: center;
  gap: var(--e1);
  /* Un nombre largo se parte en vez de estirar la fila. */
  overflow-wrap: anywhere;
}

.antiguedad {
  flex: 0 0 auto;
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}
</style>
