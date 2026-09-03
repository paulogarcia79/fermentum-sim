<script setup lang="ts">
// Reporte de Fase III como modal obligatorio, no una linea mas en el
// registro -- un colapso estructural le puede costar varios puntos a un
// jugador sin que haya tomado ninguna decision, y debe ser algo que se le
// diga explicitamente, no algo que tenga que notar por su cuenta.
import { computed } from 'vue'
import { reconocerReporteDia, store } from '../store'
import { fmtHarina } from '../data/unidades'
import type { GameEventView } from '../types'
import ModalObligatorio from './ModalObligatorio.vue'

const dia = computed(() => store.reporteDiaPendiente!)
const eventosDelDia = computed(() => store.eventos.filter((e) => e.dia === dia.value))

function porJugador(idx: number, tipos: string[]): GameEventView[] {
  return eventosDelDia.value.filter((e) => e.jugador_idx === idx && tipos.includes(e.tipo))
}
</script>

<template>
  <ModalObligatorio
    :ceja="`Fase III · Día ${dia}`"
    titulo="Reporte de Fermentación"
    ancho="l"
    etiqueta-boton="Continuar"
    @reconocer="reconocerReporteDia"
  >
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

        <li v-for="(ev, i) in porJugador(idx, ['renta_panaderia'])" :key="'r' + i" class="renta">
          🥖 Ingresos de panadería: +{{ ev.datos.monedas_recibidas }} Monedas
          ({{ (ev.datos.desglose as { receta_nombre: string; monedas: number }[])
                .map((d) => `${d.receta_nombre} +${d.monedas}`).join(', ') }})
        </li>

        <li
          v-for="(ev, i) in porJugador(idx, ['rendimiento_molino'])"
          :key="'mo' + i"
          class="renta"
        >
          🌾 Contrato con el Molino: +{{ fmtHarina(Number(ev.datos.harina_pct)) }} de Harina
          {{ ev.datos.tipo_harina }}
        </li>

        <li v-for="(ev, i) in porJugador(idx, ['masa_avanzo'])" :key="'m' + i">
          Est-{{ (ev.datos.estacion_idx as number) + 1 }}: '{{ ev.datos.receta_nombre }}' pos
          {{ ev.datos.posicion_antes }} → {{ ev.datos.posicion_despues }} (avanzó +{{ ev.datos.avance }}<template
            v-if="ev.datos.modificador_incubadora"
          >, Incubadora {{ (ev.datos.modificador_incubadora as number) > 0 ? '+' : ''
          }}{{ ev.datos.modificador_incubadora }}</template>)
        </li>
      </ul>
    </div>

    <div
      v-for="(ev, i) in eventosDelDia.filter((e) => e.tipo === 'fin_de_partida')"
      :key="'f' + i"
      class="fin-partida"
    >
      🏁 {{ ev.mensaje }}
    </div>
  </ModalObligatorio>
</template>

<style scoped>
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

.renta {
  color: var(--verdin);
}

.fin-partida {
  background: var(--lavado-cobre);
  border: 1px solid var(--cobre);
  border-radius: var(--r-carta);
  padding: var(--e2);
}

/* El ultimo bloque no separa de nada: el pie del modal ya pone su regla. */
.bloque-jugador:last-child,
.fin-partida:last-child {
  margin-bottom: 0;
}
</style>
