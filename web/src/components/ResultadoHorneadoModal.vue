<script setup lang="ts">
// Resultado del horneado voluntario (Accion F) que se acaba de resolver.
// Montado desde GameView (no desde ModalF): la Accion F termina el turno, asi
// que BarraAcciones -- y ModalF con ella -- se desmonta en cuanto llega el
// snapshot de respuesta (v-if="esMiTurno" en GameView). El registro vive en
// store.resultadoHorneado, que sobrevive a ese desmontaje.
//
// `puntos_totales` y `zona_resultado` son las @property del HorneadoRecord
// que server/views.py inyecta por registro -- el resultado real que calculo
// el motor, no la estimacion previa de ModalF.
import { computed } from 'vue'
import { cerrarResultadoHorneado, store } from '../store'
import type { HorneadoRecord } from '../types'

const ETIQUETA_ZONA: Record<HorneadoRecord['zona_resultado'], string> = {
  optima: 'Zona Óptima',
  baja: 'Zona Baja',
  colapso: 'Colapso',
}

const registro = computed(() => store.resultadoHorneado!)
</script>

<template>
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <div class="fondo-modal">
      <div class="modal">
        <h2>🍞 ¡Horneado!</h2>

        <p class="linea">
          <strong>'{{ registro.recipe.nombre }}'</strong> — {{ ETIQUETA_ZONA[registro.zona_resultado] }}
        </p>
        <p class="linea">
          Ganaste <strong>{{ registro.puntos_totales }} pts</strong><template v-if="registro.bono_sabor_aplicado">
            (incluye Bono de Sabor)</template>
          y <strong>{{ registro.monedas_obtenidos }} Monedas</strong><template v-if="registro.datos_obtenidos > 0">
            · <strong>+{{ registro.datos_obtenidos }} Datos</strong></template>.
          Tu marcador y tu Archivo de Horneados ya lo reflejan.
        </p>

        <button class="primario" @click="cerrarResultadoHorneado">Cerrar</button>
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
  max-width: 420px;
  width: 100%;
}

.modal h2 {
  margin-top: 0;
}

.linea {
  margin: 0 0 var(--e3);
  font-size: var(--t-m);
  line-height: 1.45;
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
