<script setup lang="ts">
// Reporte de Fase III como modal obligatorio, no una linea mas en el
// registro -- un colapso estructural le puede costar varios puntos a un
// jugador sin que haya tomado ninguna decision, y debe ser algo que se le
// diga explicitamente, no algo que tenga que notar por su cuenta.
import { computed } from 'vue'
import { reconocerReporteDia, store } from '../store'
import type { GameEventView } from '../types'

const dia = computed(() => store.reporteDiaPendiente!)
const eventosDelDia = computed(() => store.eventos.filter((e) => e.dia === dia.value))

function porJugador(idx: number, tipos: string[]): GameEventView[] {
  return eventosDelDia.value.filter((e) => e.jugador_idx === idx && tipos.includes(e.tipo))
}
</script>

<template>
  <div class="fondo-modal">
    <div class="modal panel">
      <h2>Reporte de Fermentación — Día {{ dia }}</h2>

      <div v-for="(jugador, idx) in store.estado?.players ?? []" :key="idx" class="bloque-jugador">
        <h3>{{ jugador.nombre }}</h3>

        <ul class="lista">
          <li
            v-for="(ev, i) in porJugador(idx, ['horneado'])"
            :key="'h' + i"
            :class="{ colapso: ev.datos.fue_colapso, exito: !ev.datos.fue_colapso }"
          >
            <template v-if="ev.datos.fue_colapso">⚠ COLAPSO: '{{ ev.datos.receta_nombre }}' → {{ ev.datos.puntos_totales }} pts (auto-horneado)</template>
            <template v-else>✔ Horneado exitoso: '{{ ev.datos.receta_nombre }}' → {{ ev.datos.puntos_totales }} pts</template>
          </li>

          <li v-for="(ev, i) in porJugador(idx, ['desgaste'])" :key="'d' + i">
            Vitalidad: {{ ev.datos.vitalidad_antes }} → {{ ev.datos.vitalidad_despues }}
          </li>

          <li v-for="(_ev, i) in porJugador(idx, ['contaminacion'])" :key="'c' + i" class="colapso">
            ☣ ¡Entró en estado de Contaminación!
          </li>

          <li v-for="(ev, i) in porJugador(idx, ['masa_avanzo'])" :key="'m' + i">
            Est-{{ (ev.datos.estacion_idx as number) + 1 }}: '{{ ev.datos.receta_nombre }}' pos
            {{ ev.datos.posicion_antes }} → {{ ev.datos.posicion_despues }} (avanzó +{{ ev.datos.avance }})
          </li>
        </ul>
      </div>

      <div v-for="(ev, i) in eventosDelDia.filter((e) => e.tipo === 'fin_de_partida')" :key="'f' + i" class="fin-partida">
        🏁 {{ ev.mensaje }}
      </div>

      <button class="primario" @click="reconocerReporteDia">Continuar</button>
    </div>
  </div>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 1rem;
}

.modal {
  max-width: 560px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h2 {
  margin-top: 0;
}

.bloque-jugador {
  margin-bottom: 1rem;
}

.bloque-jugador h3 {
  margin: 0 0 0.35rem;
  font-size: 1rem;
}

.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
}

.lista .colapso {
  color: var(--color-mal);
}

.lista .exito {
  color: var(--color-bien);
}

.fin-partida {
  background: rgba(217, 154, 63, 0.15);
  border: 1px solid var(--color-acento);
  border-radius: 6px;
  padding: 0.5rem;
  margin-bottom: 1rem;
}

button.primario {
  width: 100%;
  padding: 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}
</style>
