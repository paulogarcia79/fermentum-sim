<script setup lang="ts">
// Mazo de Tendencias de Mercado como objeto fisico -- mismo tratamiento que
// MazoClimaPanel.vue le da al mazo de clima (pila de descarte hojeable a la
// izquierda, mazo boca-abajo en el medio, carta de hoy revelada a la
// derecha). A diferencia del clima, Market no guarda un campo separado para
// "la carta activa" -- Market.robar_tendencia() empuja el modificador
// robado directo a descarte_tendencias, asi que "la carta de hoy" es
// simplemente la ultima entrada, y la pila de descarte real es todo lo
// demas (misma derivacion que descarte_clima usa en MazoClimaPanel.vue).
import { computed, ref } from 'vue'
import { store } from '../store'
import CartaTendencia from './CartaTendencia.vue'
import PilaDescarteTendenciasModal from './PilaDescarteTendenciasModal.vue'

const mercado = computed(() => store.estado!.market)

const tendencias = computed(() => mercado.value.descarte_tendencias)
const descarte = computed(() => tendencias.value.slice(0, -1))
const topeDescarte = computed(() => descarte.value.slice(-3))
const tendenciaHoy = computed(() => (tendencias.value.length ? tendencias.value[tendencias.value.length - 1] : null))

const pilaDescarteAbierta = ref(false)
</script>

<template>
  <section class="panel mazo-tendencias">
    <div class="cabecera-mazo">
      <h3>Tendencias de Mercado</h3>
      <div class="stats">
        <span>{{ mercado.mazo_tendencias_restantes }} en el mazo</span>
      </div>
    </div>

    <div class="fila-mazo">
      <button
        type="button"
        class="pila pila-descarte"
        :disabled="descarte.length === 0"
        :title="descarte.length ? 'Ver toda la pila de descarte' : 'Todavía no hay cartas descartadas'"
        @click="pilaDescarteAbierta = true"
      >
        <div class="abanico">
          <CartaTendencia v-if="descarte.length === 0" compacta boca-abajo class="carta-abanico" style="--offset: 0" />
          <CartaTendencia
            v-for="(modificador, i) in topeDescarte"
            :key="i"
            :modificador="modificador"
            compacta
            class="carta-abanico"
            :style="{ '--offset': i }"
          />
        </div>
        <span class="etiqueta-pila">Descarte ({{ descarte.length }})</span>
      </button>

      <div class="pila mazo-boca-abajo">
        <div class="abanico">
          <CartaTendencia v-for="n in 3" :key="n" compacta boca-abajo class="carta-abanico" :style="{ '--offset': n - 1 }" />
        </div>
        <span class="etiqueta-pila">Mazo ({{ mercado.mazo_tendencias_restantes }})</span>
      </div>

      <div class="pila carta-revelada">
        <CartaTendencia :modificador="tendenciaHoy" />
        <span class="etiqueta-pila">Carta de hoy</span>
      </div>
    </div>

    <PilaDescarteTendenciasModal v-if="pilaDescarteAbierta" @cerrar="pilaDescarteAbierta = false" />
  </section>
</template>

<style scoped>
.mazo-tendencias h3 {
  margin: 0;
}

.cabecera-mazo {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem 1rem;
  margin-bottom: 0.75rem;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.9rem;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
}

.fila-mazo {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1.5rem;
}

.pila {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  background: none;
  border: none;
  padding: 0;
  color: inherit;
}

.pila-descarte {
  cursor: pointer;
}

.pila-descarte:hover:not(:disabled) .carta-abanico {
  filter: brightness(1.1);
}

.abanico {
  position: relative;
  width: calc(108px + 2 * 12px);
  height: calc(148px + 2 * 6px);
}

.carta-abanico {
  position: absolute;
  left: calc(var(--offset) * 12px);
  top: calc((2 - var(--offset)) * 6px);
  transform: rotate(calc((var(--offset) - 1) * 4deg));
  transition: filter 0.15s ease;
}

.carta-revelada {
  margin-left: 0.5rem;
}

.etiqueta-pila {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-texto-tenue);
}

@media (max-width: 640px) {
  .fila-mazo {
    justify-content: center;
  }
}
</style>
