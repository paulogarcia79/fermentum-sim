<script setup lang="ts">
// Tabla de rendimiento por las CUATRO zonas (Monedas / Puntos de Maestria / Datos).
//
// Crecimiento no tiene numeros a proposito: no se puede hornear ahi (Accion F la
// rechaza), asi que la carta no imprime pago para esa zona -- una fila de guiones
// ensena la regla mejor que tres ceros, que insinuarian que hornear ahi es legal
// pero pobre.
//
// Datos SIGUE siendo una regla pareja para todas las recetas, no un campo por
// receta: 0 salvo en Optima, donde da 1 (+1 con Modulo Analitico y +1 mas en el
// centro exacto -- engine.py: _calcular_datos_horneado). De ahi la nota al pie.
import { computed } from 'vue'
import type { Recipe } from '../types'
import IconoMonedas from './IconoMonedas.vue'
import IconoMaestria from './IconoMaestria.vue'
import IconoDatos from './IconoDatos.vue'

const props = defineProps<{ receta: Recipe }>()

const centroExacto = computed(() => Math.floor((props.receta.zona_optima[0] + props.receta.zona_optima[1]) / 2))
</script>

<template>
  <div class="rendimiento">
    <table class="tabla-rendimiento">
      <thead>
        <tr>
          <th></th>
          <th><span class="icono-cabecera"><IconoMonedas /></span></th>
          <th><span class="icono-cabecera"><IconoMaestria /></span></th>
          <th><span class="icono-cabecera"><IconoDatos /></span></th>
        </tr>
      </thead>
      <tbody>
        <tr class="fila-crecimiento">
          <th>Crecimiento</th>
          <td>—</td>
          <td>—</td>
          <td>—</td>
        </tr>
        <tr class="fila-optima">
          <th>Óptima</th>
          <td>{{ receta.monedas_optima }}</td>
          <td>{{ receta.puntos_optimos }}</td>
          <td>1*</td>
        </tr>
        <tr class="fila-baja">
          <th>Pre-fermento</th>
          <td>{{ receta.monedas_pre_fermento }}</td>
          <td>{{ receta.puntos_pre_fermento }}</td>
          <td>0</td>
        </tr>
        <tr class="fila-sobre">
          <th>Colapso</th>
          <td>{{ receta.monedas_colapso }}</td>
          <td>{{ receta.penalizacion_colapso }}</td>
          <td>0</td>
        </tr>
      </tbody>
    </table>
    <p class="nota-pie">Crecimiento (1–{{ receta.zona_crecimiento[1] }}): la masa aún no es pan, no se puede hornear.</p>
    <p class="nota-pie">* +1 Dato con Módulo Analítico, y +1 más en el centro exacto ({{ centroExacto }}).</p>
    <p class="nota-pie">Bono de Sabor (sin colapso): +{{ receta.bono_sabor_pts }} Maestría, +2 Monedas.</p>
  </div>
</template>

<style scoped>
.rendimiento {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
}

.tabla-rendimiento {
  border-collapse: collapse;
  font-size: var(--t-xs);
  width: 100%;
}

.tabla-rendimiento th,
.tabla-rendimiento td {
  padding: var(--e1) var(--e2);
  text-align: center;
}

.tabla-rendimiento thead th {
  border-bottom: 1px solid var(--borde);
}

.icono-cabecera {
  display: inline-block;
  width: 14px;
  height: 14px;
  vertical-align: middle;
}

.tabla-rendimiento tbody th {
  text-align: left;
  color: var(--tinta-tenue);
  font-weight: 400;
}

.fila-crecimiento td,
.fila-crecimiento th {
  color: var(--tinta-tenue);
}

.fila-optima {
  background: var(--lavado-vital);
}

.fila-optima td,
.fila-optima th {
  color: var(--vital);
}

.fila-sobre {
  background: var(--lavado-riesgo);
}

.fila-sobre td,
.fila-sobre th {
  color: var(--riesgo);
}

.nota-pie {
  margin: 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  line-height: 1.3;
}
</style>
