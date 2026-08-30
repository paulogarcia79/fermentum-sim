<script setup lang="ts">
// Tabla de rendimiento por zona (Monedas / Puntos de Maestria / Datos) --
// monedas_*/puntos_*/penalizacion_colapso son campos fijos de Recipe (nunca
// mostrados en ningun otro lugar de la UI hasta ahora); Datos es una regla
// pareja para todas las recetas (0 en Baja/Sobre, 1 en Optima, +1 extra solo
// en el centro exacto y solo con Modulo Analitico -- engine.py:
// _calcular_datos_horneado), no un campo por receta, asi que se anota como
// nota al pie en vez de una columna con contenido variable.
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
        <tr class="fila-optima">
          <th>Óptima</th>
          <td>{{ receta.monedas_optima }}</td>
          <td>{{ receta.puntos_optimos }}</td>
          <td>1*</td>
        </tr>
        <tr class="fila-baja">
          <th>Baja</th>
          <td>{{ receta.monedas_baja }}</td>
          <td>{{ receta.puntos_baja }}</td>
          <td>0</td>
        </tr>
        <tr class="fila-sobre">
          <th>Sobre</th>
          <td>{{ receta.monedas_sobre }}</td>
          <td>{{ receta.penalizacion_colapso }}</td>
          <td>0</td>
        </tr>
      </tbody>
    </table>
    <p class="nota-pie">* +1 Dato extra en el centro exacto ({{ centroExacto }}) con Módulo Analítico.</p>
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
