<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import { hexDeColor } from '../data/coloresJugador'

// No hay informacion oculta entre jugadores en Fermentum (la Carpeta de
// Proyectos es boca arriba, ACTIONS_REGISTRY.md SS2G), asi que mostrar
// filas compactas del resto de jugadores es solo una decision de espacio
// en pantalla, no una restriccion de reglas.
const oponentes = computed(() =>
  store.estado!.players
    .map((p, i) => ({ p, i }))
    .filter(({ i }) => i !== store.sesion!.playerIndex),
)

function esJefe(i: number): boolean {
  return store.estado!.jefe_investigador_idx === i
}

function esTurno(i: number): boolean {
  return store.estado!.jugador_en_turno_idx === i
}
</script>

<template>
  <section class="panel oponentes">
    <h3>Otros investigadores</h3>
    <div v-for="{ p, i } in oponentes" :key="i" class="fila" :class="{ turno: esTurno(i) }">
      <div class="nombre-fila">
        <span class="punto-color" :style="{ background: hexDeColor(p.color) }" />
        {{ p.nombre }}
        <span v-if="esJefe(i)" title="Investigador Jefe">👑</span>
        <span v-if="p.en_estado_contaminacion" class="badge-contaminado">◉</span>
      </div>
      <div class="stats">
        <span>Vit {{ p.vitalidad }}/6</span>
        <span>Acidez {{ p.acidez }}/6</span>
        <span>PA {{ p.puntos_accion }}</span>
        <span>Datos {{ p.datos_investigacion }}</span>
        <span>Monedas {{ p.monedas }}</span>
        <span :title="`${p.archivo_horneado_exitoso.length} horneados exitosos de los 5 que terminan la partida · ${p.archivo_colapsos.length} colapsos`">
          🍞 {{ p.archivo_horneado_exitoso.length }}/5
          <template v-if="p.archivo_colapsos.length"> · {{ p.archivo_colapsos.length }}⚠</template>
        </span>
        <span :title="`${p.puntos_horneados} pts horneados · proyección final ${p.puntos_maestria_final} PM`">
          Maestría {{ p.puntos_maestria_final }}
        </span>
      </div>
      <div class="masas" v-if="p.estaciones_fermentacion.some((s) => s)">
        <span v-for="(slot, idx) in p.estaciones_fermentacion" :key="idx">
          <template v-if="slot">Est-{{ idx + 1 }}: {{ slot.recipe.nombre }} (pos {{ slot.posicion_track }})</template>
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.oponentes h3 {
  margin-top: 0;
}

.fila {
  border-top: 1px solid var(--borde);
  padding: var(--e2) 0;
  font-size: var(--t-s);
}

.fila:first-of-type {
  border-top: none;
}

.fila.turno {
  color: var(--cobre);
}

.nombre-fila {
  font-weight: 600;
  display: flex;
  gap: var(--e2);
  align-items: center;
}

.badge-contaminado {
  color: var(--riesgo);
}

.punto-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  color: var(--tinta-tenue);
  margin-top: var(--e1);
}

.masas {
  display: flex;
  flex-direction: column;
  color: var(--tinta-tenue);
  margin-top: var(--e1);
}
</style>
