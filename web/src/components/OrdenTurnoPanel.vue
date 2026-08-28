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

    <p class="nota">Se recalcula cada Fase I · Vitalidad › Datos de Investigación</p>
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
  gap: 0.35rem;
}

.fila {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.4rem;
  border-radius: 5px;
  border-left: 3px solid transparent;
  font-size: 0.85rem;
}

.fila.activo {
  border-left-color: var(--color-acento);
  background: var(--color-fondo);
  color: var(--color-acento);
  font-weight: 600;
}

.recuadro-num {
  flex: 0 0 auto;
  width: 1.3rem;
  height: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-fondo);
  border: 1px solid var(--color-borde);
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
}

.fila.activo .recuadro-num {
  color: var(--color-acento);
  border-color: var(--color-acento);
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
  color: var(--color-texto-tenue);
  font-weight: 400;
  font-size: 0.75rem;
}

.tag {
  flex: 0 0 auto;
  font-size: 0.68rem;
  color: var(--color-texto-tenue);
}

.tag.jefe {
  color: var(--color-acento);
}

.nota {
  margin: 0.6rem 0 0;
  font-size: 0.7rem;
  color: var(--color-texto-tenue);
}
</style>
