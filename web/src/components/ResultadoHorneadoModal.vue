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
import ModalObligatorio from './ModalObligatorio.vue'

const ETIQUETA_ZONA: Record<HorneadoRecord['zona_resultado'], string> = {
  optima: 'Zona Óptima',
  pre_fermento: 'Pre-fermento',
  colapso: 'Colapso',
}

const registro = computed(() => store.resultadoHorneado!)
</script>

<template>
  <ModalObligatorio
    ceja="Acción F"
    titulo="🍞 ¡Horneado!"
    etiqueta-boton="Cerrar"
    @reconocer="cerrarResultadoHorneado"
  >
    <p class="linea">
      <strong>'{{ registro.recipe.nombre }}'</strong> — {{ ETIQUETA_ZONA[registro.zona_resultado] }}
    </p>
    <p class="linea ultima">
      Ganaste <strong>{{ registro.puntos_totales }} pts</strong><template v-if="registro.bono_sabor_aplicado">
        (incluye Bono de Sabor)</template>
      y <strong>{{ registro.monedas_obtenidos }} Monedas</strong><template v-if="registro.datos_obtenidos > 0">
        · <strong>+{{ registro.datos_obtenidos }} Datos</strong></template>.
      Tu marcador y tu Archivo de Horneados ya lo reflejan.
    </p>
  </ModalObligatorio>
</template>

<style scoped>
.linea {
  margin: 0 0 var(--e3);
  font-size: var(--t-m);
  line-height: 1.45;
}

.linea.ultima {
  margin-bottom: 0;
}
</style>
