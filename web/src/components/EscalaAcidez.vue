<script setup lang="ts">
// Perfil de Acidez Requerido de una receta: fila de 6 casillas (1-6, mismo
// lenguaje visual que el track de precio de harina -- casilla resaltada =
// valor objetivo) marcando `diana` (recipe.acidez_diana). Cuando la receta
// ya fue iniciada (`registrada` viene de FermentationSlot.acidez_inicial),
// se marca ademas esa casilla como sellada (bono activo) o fallida.
import { computed } from 'vue'

const props = defineProps<{
  diana: number[]
  bonoPts: number
  registrada?: number | null
  bonoSellado?: boolean
}>()

const tieneRegistro = computed(() => props.registrada !== null && props.registrada !== undefined)
</script>

<template>
  <div class="escala-acidez">
    <div class="fila-pips">
      <div
        v-for="n in 6"
        :key="n"
        class="pip"
        :class="{
          diana: diana.includes(n),
          sellado: tieneRegistro && n === registrada && bonoSellado,
          fallido: tieneRegistro && n === registrada && !bonoSellado,
        }"
      >
        {{ n }}
      </div>
    </div>
    <p class="nota">
      <template v-if="tieneRegistro">
        Registro de pH: <strong>{{ registrada }}</strong>
        <span v-if="bonoSellado" class="sellado-texto">— Bono sellado (+{{ bonoPts }} Maestría, +2 Monedas)</span>
        <span v-else class="fallido-texto">— Sin bono (fuera de la diana)</span>
      </template>
      <template v-else>
        Diana {{ diana.join(', ') }} al iniciar → +{{ bonoPts }} Maestría, +2 Monedas
      </template>
    </p>
  </div>
</template>

<style scoped>
.escala-acidez {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.fila-pips {
  display: flex;
  gap: 0.25rem;
}

.pip {
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  color: var(--color-texto-tenue);
  flex: 0 0 auto;
}

.pip.diana {
  border-color: var(--color-acento);
  background: rgba(217, 154, 63, 0.16);
  color: var(--color-texto);
  font-weight: 700;
}

.pip.sellado {
  box-shadow: 0 0 0 2px var(--color-bien) inset;
  color: var(--color-bien);
}

.pip.fallido {
  box-shadow: 0 0 0 2px var(--color-mal) inset;
}

.nota {
  margin: 0;
  font-size: 0.68rem;
  color: var(--color-texto-tenue);
}

.nota strong {
  color: var(--color-texto);
}

.sellado-texto {
  color: var(--color-bien);
}

.fallido-texto {
  color: var(--color-mal);
}
</style>
