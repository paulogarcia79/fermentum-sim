<script setup lang="ts">
// Bolsa de Harinas + Suministro Hídrico Global (GDD v0.0.2) -- ahora
// muestra la pista de precio COMPLETA (las 5 posiciones posibles del visor
// de cada harina, y las 5 filas de temperatura x 4 lotes de agua) con la
// posicion/fila actual resaltada, en vez de solo el precio vigente como
// texto -- ver reference_images/market_example.jpeg. PistaPrecioHarina.vue
// y TablaPrecioAgua.vue hacen el trabajo real; este panel solo los agrupa
// y los reusa tambien ModalC.vue (Accion C) para dar contexto al transactar.
import { computed } from 'vue'
import { store } from '../store'
import PistaPrecioHarina from './PistaPrecioHarina.vue'
import TablaPrecioAgua from './TablaPrecioAgua.vue'
import TermometroAgua from './TermometroAgua.vue'
import type { TipoHarina } from '../types'

const TIPOS: TipoHarina[] = ['Blanca', 'Integral', 'Centeno']

const temperatura = computed(() => store.estado!.environment.temperatura_actual)
</script>

<template>
  <section class="panel bolsa-harinas">
    <h3>Bolsa de Harinas</h3>
    <div class="cuerpo-bolsa">
      <div class="seccion-harinas">
        <PistaPrecioHarina v-for="tipo in TIPOS" :key="tipo" :tipo="tipo" />
      </div>

      <div class="seccion-agua">
        <h4>Suministro Hídrico @ {{ temperatura }}°C</h4>
        <div class="fila-agua">
          <TermometroAgua :temperatura="temperatura" />
          <TablaPrecioAgua />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bolsa-harinas h3 {
  margin-top: 0;
}

.cuerpo-bolsa {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.seccion-harinas {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 2 1 260px;
}

.seccion-agua {
  flex: 1 1 220px;
}

.seccion-agua h4 {
  margin: 0 0 0.4rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-texto-tenue);
}

.fila-agua {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 640px) {
  .cuerpo-bolsa {
    flex-direction: column;
  }
}
</style>
