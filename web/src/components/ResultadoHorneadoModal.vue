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
  <div class="fondo-modal">
    <div class="modal panel">
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
  max-width: 420px;
  width: 100%;
}

.modal h2 {
  margin-top: 0;
}

.linea {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  line-height: 1.45;
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
