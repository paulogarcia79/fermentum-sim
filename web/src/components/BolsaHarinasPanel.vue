<script setup lang="ts">
// Bolsa de Harinas + Suministro Hídrico Global (GDD v0.0.2) -- reemplaza el
// viejo panel de "Suministros" (3 lotes aleatorios de 150% que se tomaban
// enteros). Ahora es un tablero de precios estático: 3 visores de harina
// compartidos (posiciones_harina, 1-5) y una fila de precio de agua por
// tamaño de lote según la temperatura actual. Ya no hay "tomar" un lote ni
// slots que se vacían -- comprar/vender es la Acción C (Visitar el Mercado,
// ver ModalC.vue), este panel solo muestra el precio vigente.
import { computed } from 'vue'
import { store } from '../store'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'
import IconoMonedas from './IconoMonedas.vue'
import { LOTES_AGUA_VALIDOS, PRECIO_AGUA, precioCompraHarina, precioVentaHarina } from '../data/preciosHarina'
import type { TipoHarina } from '../types'

const TIPOS: TipoHarina[] = ['Blanca', 'Integral', 'Centeno']

const mercado = computed(() => store.estado!.market)
const temperatura = computed(() => store.estado!.environment.temperatura_actual)
</script>

<template>
  <section class="panel bolsa-harinas">
    <h3>Bolsa de Harinas</h3>
    <ul class="lista-bolsa-harinas">
      <li v-for="tipo in TIPOS" :key="tipo" class="lote">
        <div class="recursos">
          <span class="recurso">
            <span class="icono"><IconoHarina :tipo="tipo" /></span>
            {{ tipo }} — visor {{ mercado.posiciones_harina[tipo] }}/5
          </span>
          <span class="precio">
            Compra <span class="icono-mini"><IconoMonedas /></span>{{ precioCompraHarina(tipo, mercado.posiciones_harina[tipo]) }}
          </span>
          <span class="precio">
            Venta <span class="icono-mini"><IconoMonedas /></span>{{ precioVentaHarina(tipo, mercado.posiciones_harina[tipo]) }}
          </span>
        </div>
      </li>
      <li class="lote">
        <div class="recursos">
          <span class="recurso">
            <span class="icono"><IconoAgua /></span>
            Agua @ {{ temperatura }}°C
          </span>
          <span v-for="lote in LOTES_AGUA_VALIDOS" :key="lote" class="precio">
            {{ lote }}% <span class="icono-mini"><IconoMonedas /></span>{{ PRECIO_AGUA[temperatura]?.[lote] ?? '—' }}
          </span>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.bolsa-harinas h3 {
  margin-top: 0;
}

.lista-bolsa-harinas {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.lote {
  background: var(--color-fondo);
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
}

.recursos {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6rem;
  font-size: 0.8rem;
}

.recurso {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.precio {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  color: var(--color-texto-tenue);
}

.icono {
  width: 16px;
  height: 16px;
}

.icono-mini {
  width: 12px;
  height: 12px;
  display: inline-flex;
}
</style>
