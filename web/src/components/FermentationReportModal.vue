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
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <div class="fondo-modal">
      <div class="modal">
        <h2>Reporte de Fermentación — Día {{ dia }}</h2>

        <div v-for="(jugador, idx) in store.estado?.players ?? []" :key="idx" class="bloque-jugador">
          <h3>{{ jugador.nombre }}</h3>

          <ul class="lista">
            <li
              v-for="(ev, i) in porJugador(idx, ['horneado'])"
              :key="'h' + i"
              :class="{ colapso: ev.datos.fue_colapso, exito: !ev.datos.fue_colapso }"
            >
              <template v-if="ev.datos.fue_colapso">
                ⚠ COLAPSO: '{{ ev.datos.receta_nombre }}' → {{ ev.datos.puntos_totales }} pts,
                {{ ev.datos.monedas_obtenidas }} Monedas (auto-horneado)
              </template>
              <template v-else>
                ✔ Horneado exitoso: '{{ ev.datos.receta_nombre }}' → {{ ev.datos.puntos_totales }} pts,
                {{ ev.datos.monedas_obtenidas }} Monedas
                <template v-if="Number(ev.datos.datos_generados) > 0"> (+{{ ev.datos.datos_generados }} Datos)</template>
              </template>
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
  </Teleport>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: var(--velo-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: var(--e4);
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
  margin-bottom: var(--e4);
}

.bloque-jugador h3 {
  margin: 0 0 var(--e2);
  font-size: var(--t-m);
}

.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  font-size: var(--t-s);
}

.lista .colapso {
  color: var(--riesgo);
}

.lista .exito {
  color: var(--vital);
}

.fin-partida {
  background: var(--lavado-cobre);
  border: 1px solid var(--cobre);
  border-radius: var(--r-carta);
  padding: var(--e2);
  margin-bottom: var(--e4);
}

button.primario {
  width: 100%;
  padding: var(--e2);
  border-radius: var(--r-control);
  border: 1px solid var(--cobre);
  background: var(--cobre);
  color: var(--tinta-sobre-acento);
  font-weight: 600;
}
</style>
