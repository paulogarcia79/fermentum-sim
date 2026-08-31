<script setup lang="ts">
// Track de Orden de Turno -- lista vertical de los jugadores en el orden de
// juego del día (estado.turno_orden viene del motor, [0] = Investigador
// Jefe). Réplica del componente físico del tablero central
// (reference_images/turn_order_example.jpeg). La fila del jugador activo se
// resalta con el acento; el jugador local se marca con "(tú)".
import { computed } from 'vue'
import { store } from '../store'
import { hexDeColor } from '../data/coloresJugador'
import IconoPeon from './IconoPeon.vue'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)

// turno_orden puede venir vacío antes del primer día -- entonces se muestra
// el orden de inscripción como aproximación.
const orden = computed(() =>
  estado.value.turno_orden.length > 0
    ? estado.value.turno_orden
    : estado.value.players.map((_, i) => i),
)

// Quien ocupó hoy el espacio (global) de la Jefatura y abrirá mañana. El orden
// de arriba es el de HOY y no se rebaraja a media jornada, así que esto se
// muestra como nota aparte y nunca reordenando la lista.
const reclamante = computed(() => {
  const idx = estado.value.jefatura_reclamada_por
  return idx === null ? null : estado.value.players[idx].nombre
})
</script>

<template>
  <section class="panel orden-turno">
    <h3>Orden de Turno</h3>

    <ol class="lista">
      <li
        v-for="(idx, pos) in orden"
        :key="idx"
        class="fila"
        :class="{ activo: idx === estado.jugador_en_turno_idx }"
      >
        <span class="recuadro-num">{{ pos + 1 }}</span>
        <span class="peon"><IconoPeon :color="hexDeColor(estado.players[idx].color)" /></span>
        <span class="nombre">
          {{ estado.players[idx].nombre }}
          <span v-if="idx === miIndice" class="tu">(tú)</span>
        </span>
        <span v-if="pos === 0" class="tag jefe">👑 Jefe</span>
        <span v-else-if="orden.length > 1 && pos === orden.length - 1" class="tag ultimo">Último</span>
      </li>
    </ol>

    <p v-if="reclamante" class="nota reclamada">
      👑 Mañana abre <strong>{{ reclamante }}</strong
      >: ya reclamó la Jefatura hoy.
    </p>
    <p v-else class="nota">
      Jefatura libre hoy — se reclama con 1 PA (y paga 1 Dato). Si nadie la reclama, se queda donde
      está.
    </p>
  </section>
</template>

<style scoped>
.orden-turno h3 {
  margin-top: 0;
}

.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
}

.fila {
  display: flex;
  align-items: center;
  gap: var(--e2);
  padding: var(--e2) var(--e2);
  border-radius: var(--r-control);
  border-left: 3px solid transparent;
  font-size: var(--t-s);
}

.fila.activo {
  border-left-color: var(--cobre);
  background: var(--carta);
  color: var(--cobre);
  font-weight: 600;
}

.recuadro-num {
  flex: 0 0 auto;
  width: 1.3rem;
  height: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.fila.activo .recuadro-num {
  color: var(--cobre);
  border-color: var(--cobre);
}

.peon {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
}

.nombre {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tu {
  color: var(--tinta-tenue);
  font-weight: 400;
  font-size: var(--t-xs);
}

.tag {
  flex: 0 0 auto;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.tag.jefe {
  color: var(--cobre);
}

.nota {
  margin: var(--e2) 0 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.nota.reclamada {
  color: var(--cobre);
}
</style>
