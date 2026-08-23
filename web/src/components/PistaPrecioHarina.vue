<script setup lang="ts">
// Pista de precio completa de un tipo de harina: las 5 posiciones posibles
// del visor (Compra y Venta), con la posicion actual resaltada -- en vez de
// solo mostrar el precio vigente como texto. Reusado por BolsaHarinasPanel.vue
// (panel de mercado) y ModalC.vue (para dar contexto al comprar/vender).
import { computed } from 'vue'
import { store } from '../store'
import IconoHarina from './IconoHarina.vue'
import { PRECIOS_HARINA } from '../data/preciosHarina'
import type { TipoHarina } from '../types'

const props = defineProps<{ tipo: TipoHarina }>()

const posicionActual = computed(() => store.estado!.market.posiciones_harina[props.tipo])
const tabla = computed(() => PRECIOS_HARINA[props.tipo])
</script>

<template>
  <div class="pista-harina">
    <div class="etiqueta-harina">
      <span class="icono"><IconoHarina :tipo="tipo" /></span>
      {{ tipo }}
    </div>
    <table class="tabla-precios">
      <tbody>
        <tr>
          <th>Compra</th>
          <td
            v-for="(precio, i) in tabla.compra"
            :key="'c' + i"
            :class="{ actual: i + 1 === posicionActual, arriba: i + 1 === posicionActual }"
          >
            {{ precio }}
          </td>
        </tr>
        <tr>
          <th>Venta</th>
          <td
            v-for="(precio, i) in tabla.venta"
            :key="'v' + i"
            :class="{ actual: i + 1 === posicionActual, abajo: i + 1 === posicionActual }"
          >
            {{ precio }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.pista-harina {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.etiqueta-harina {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  font-weight: 600;
  flex: 0 0 auto;
  min-width: 4.5rem;
}

.icono {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.tabla-precios {
  border-collapse: collapse;
  font-size: 0.72rem;
}

.tabla-precios th {
  font-weight: 400;
  color: var(--color-texto-tenue);
  text-align: right;
  padding: 0.1rem 0.4rem 0.1rem 0;
  white-space: nowrap;
}

.tabla-precios td {
  width: 1.8rem;
  text-align: center;
  padding: 0.1rem 0.15rem;
  border: 1px solid transparent;
  color: var(--color-texto-tenue);
}

.tabla-precios td.actual {
  color: var(--color-texto);
  font-weight: 700;
  background: rgba(217, 154, 63, 0.16);
  border-left-color: var(--color-acento);
  border-right-color: var(--color-acento);
}

.tabla-precios td.arriba {
  border-top-color: var(--color-acento);
  border-bottom-color: transparent;
}

.tabla-precios td.abajo {
  border-bottom-color: var(--color-acento);
  border-top-color: transparent;
}
</style>
