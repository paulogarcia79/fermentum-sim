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
  SALA_NUEVA_CHIP,
  SONIDO_ACTIVAR,
  SONIDO_SILENCIAR,
} from '../data/copyLanding'
import { establecerSonido, store } from '../store'
import IconoPeon from './IconoPeon.vue'

defineProps<{
  salas: SalaAbierta[]
  /** Ids que acaban de aparecer: se resaltan unos segundos. Lo mantiene
   *  FormularioSala.vue, que es quien sondea. */
  recientes: Set<string>
}>()
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
    <div class="cabecera">
      <p class="eyebrow">{{ SALAS_ABIERTAS_TITULO }}</p>
      <!-- El aviso de sala nueva suena en esta pantalla, y el unico
           interruptor de sonido que habia vive en la cabecera de la partida.
           Un sonido sin forma visible de callarlo es el peor de los dos
           errores posibles, asi que el interruptor viene con el. Escribe la
           MISMA preferencia duradera que el de GameView. -->
      <button
        type="button"
        class="interruptor-sonido"
        :class="{ apagado: !store.preferencias.sonido }"
        :title="store.preferencias.sonido ? SONIDO_SILENCIAR : SONIDO_ACTIVAR"
        :aria-label="store.preferencias.sonido ? SONIDO_SILENCIAR : SONIDO_ACTIVAR"
        :aria-pressed="store.preferencias.sonido"
        @click="establecerSonido(!store.preferencias.sonido)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linejoin="round"
          />
          <path
            v-if="store.preferencias.sonido"
            d="M15.5 9.5a4 4 0 0 1 0 5M18 7.5a7 7 0 0 1 0 9"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
          />
          <path
            v-else
            d="M16 10l4 4M20 10l-4 4"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
          />
        </svg>
      </button>
    </div>

    <p v-if="salas.length === 0" class="vacio">
      {{ SALAS_ABIERTAS_VACIO }}
      <button type="button" class="enlace" @click="emit('crear')">
        {{ SALAS_ABIERTAS_VACIO_ACCION }}
      </button>
    </p>

    <ul v-else>
      <li v-for="sala in salas" :key="sala.room_id">
        <button
          type="button"
          class="fila"
          :class="{ nueva: recientes.has(sala.room_id) }"
          @click="emit('elegir', sala.room_id)"
        >
          <span class="linea-superior">
            <span class="dato codigo">{{ sala.room_id }}</span>
            <span v-if="recientes.has(sala.room_id)" class="chip-nueva">{{ SALA_NUEVA_CHIP }}</span>
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

.cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e2);
  margin-bottom: var(--e2);
}

.cabecera .eyebrow {
  margin: 0;
}

/* Mismas medidas que el interruptor de la cabecera de la partida
   (GameView.vue), copiadas y no compartidas: son dos controles de dos
   pantallas distintas que casualmente miden igual, no un componente. */
.interruptor-sonido {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border-radius: var(--r-control);
  border: 1px solid var(--borde);
  background: transparent;
  color: var(--tinta-tenue);
  cursor: pointer;
  transition: border-color var(--transicion), color var(--transicion);
}

.interruptor-sonido:hover {
  border-color: var(--borde-fuerte);
  color: var(--tinta);
}

.interruptor-sonido.apagado {
  opacity: 0.55;
}

.interruptor-sonido svg {
  width: 0.9rem;
  height: 0.9rem;
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

/* Una sala recien aparecida arranca con el lavado de cobre y vuelve sola al
   reposo. Se hace con @keyframes y no con un temporizador que cambie estilos
   porque la regla global de prefers-reduced-motion en App.vue recorta
   `animation-duration`: el caso de movimiento reducido sale gratis, igual que
   en ConfetiPanes.vue. La clase la quita FormularioSala.vue a los 6 s; la
   animacion solo pinta esa espera. */
.fila.nueva {
  border-color: var(--cobre);
  animation: aparece-sala 6s ease-out forwards;
}

@keyframes aparece-sala {
  0% {
    background: var(--lavado-cobre);
  }
  70% {
    background: var(--lavado-cobre);
  }
  100% {
    background: var(--zona);
  }
}

.chip-nueva {
  flex: 0 0 auto;
  margin-right: auto;
  padding: 1px var(--e1);
  border-radius: var(--r-control);
  background: var(--lavado-cobre);
  color: var(--cobre);
  font-size: var(--t-micro);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
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
  /* Con el chip "nueva" en medio, el margen automatico se lo lleva el chip;
     sin el, el conteo tiene que seguir pegado a la derecha. */
  margin-left: auto;
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
