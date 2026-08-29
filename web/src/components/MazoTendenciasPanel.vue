<script setup lang="ts">
// Mazo de Tendencias de Mercado como objeto fisico -- mismo tratamiento que
// MazoClimaPanel.vue le da al mazo de clima (pila de descarte hojeable a la
// izquierda, mazo boca-abajo en el medio, carta revelada a la derecha).
//
// Aqui hay TRES cosas distintas, porque una tendencia se revela un dia y se
// cobra al final de ese mismo dia (ver engine.py: robar_tendencia /
// aplicar_tendencia_pendiente):
//   · `tendencia_pendiente`: la carta revelada esta mañana. Todavia no movio
//     nada; se aplica esta noche y rige los precios de MAÑANA. Es el aviso
//     permanente que el jugador necesita mientras decide si compra o vende.
//   · ultima de `descarte_tendencias`: la que se aplico anoche, es decir la
//     que fija los precios de HOY.
//   · el resto del descarte: historial.
import { computed, ref } from 'vue'
import { store } from '../store'
import { textoTendencia } from '../tendenciaTexto'
import CartaTendencia from './CartaTendencia.vue'
import PilaDescarteTendenciasModal from './PilaDescarteTendenciasModal.vue'

const mercado = computed(() => store.estado!.market)

// El descarte ya solo contiene cartas APLICADAS: la revelada hoy vive aparte
// en `tendencia_pendiente` hasta que la Fase III la cobra.
const descarte = computed(() => mercado.value.descarte_tendencias)
const topeDescarte = computed(() => descarte.value.slice(-3))
const tendenciaPendiente = computed(() => mercado.value.tendencia_pendiente)
const tendenciaVigente = computed(() =>
  descarte.value.length ? descarte.value[descarte.value.length - 1] : null,
)

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
        <CartaTendencia :modificador="tendenciaPendiente" />
        <span class="etiqueta-pila">Se aplica esta noche</span>
      </div>
    </div>

    <p v-if="tendenciaPendiente !== null" class="aviso-pendiente">
      ⏳ <strong>Anunciada hoy, se cobra esta noche.</strong> No cambia los precios de hoy:
      fija los de mañana. {{ textoTendencia(tendenciaPendiente) }}
    </p>

    <p class="nota-vigente">
      Precios de hoy:
      <template v-if="tendenciaVigente !== null">
        los dejó la tendencia de anoche ({{ tendenciaVigente >= 0 ? '+' : '' }}{{ tendenciaVigente }}).
      </template>
      <template v-else>los de inicio de partida — todavía no se aplicó ninguna tendencia.</template>
    </p>

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

.aviso-pendiente {
  margin: 0.75rem 0 0;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-acento);
  border-radius: 6px;
  background: rgba(217, 154, 63, 0.15);
  font-size: 0.76rem;
  line-height: 1.4;
}

.nota-vigente {
  margin: 0.4rem 0 0;
  font-size: 0.72rem;
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
