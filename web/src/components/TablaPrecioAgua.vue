<script setup lang="ts">
// Tabla de precio de agua completa: 5 filas de temperatura x 4 columnas de
// tamaño de lote, con la fila de la temperatura actual resaltada -- en vez
// de solo la fila vigente. Reusada por BolsaHarinasPanel.vue (con
// TermometroAgua.vue al lado) y ModalC.vue (tabla sola, sin termometro).
import { computed } from 'vue'
import { store } from '../store'
import { AGUA_TOKENS_POR_LOTE, LOTES_AGUA_VALIDOS, PRECIO_AGUA } from '../data/preciosHarina'

const TEMPERATURAS = [30, 25, 20, 15, 10] as const

const temperaturaActual = computed(() => store.estado!.environment.temperatura_actual)
</script>

<template>
  <table class="tabla-agua">
    <thead>
      <tr>
        <th>°C \ Lote</th>
        <th v-for="lote in LOTES_AGUA_VALIDOS" :key="lote" :title="`Lote de ${lote}% = ${AGUA_TOKENS_POR_LOTE[lote]} tokens de agua`">
          {{ AGUA_TOKENS_POR_LOTE[lote] }}
          <span class="unidad-secundaria">({{ lote }}%)</span>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="temp in TEMPERATURAS" :key="temp" :class="{ actual: temp === temperaturaActual }">
        <th>{{ temp }}°</th>
        <td v-for="lote in LOTES_AGUA_VALIDOS" :key="lote">{{ PRECIO_AGUA[temp]?.[lote] ?? '—' }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.tabla-agua {
  border-collapse: collapse;
  font-size: var(--t-xs);
}

.tabla-agua thead th .unidad-secundaria {
  display: block;
  font-size: 0.75em;
}

.tabla-agua th {
  font-weight: 400;
  color: var(--tinta-tenue);
  padding: var(--e1) var(--e2);
  white-space: nowrap;
}

.tabla-agua thead th {
  text-align: center;
  border-bottom: 1px solid var(--borde);
}

.tabla-agua tbody th {
  text-align: right;
}

.tabla-agua td {
  width: 1.8rem;
  text-align: center;
  padding: var(--e1) var(--e2);
  color: var(--tinta-tenue);
}

.tabla-agua tr.actual th,
.tabla-agua tr.actual td {
  color: var(--tinta);
  font-weight: 700;
  background: var(--lavado-cobre);
}

.tabla-agua tr.actual td:first-of-type {
  border-left: 1px solid var(--cobre);
}

.tabla-agua tr.actual td:last-child {
  border-right: 1px solid var(--cobre);
}

.tabla-agua tr.actual th,
.tabla-agua tr.actual td {
  border-top: 1px solid var(--cobre);
  border-bottom: 1px solid var(--cobre);
}
</style>
