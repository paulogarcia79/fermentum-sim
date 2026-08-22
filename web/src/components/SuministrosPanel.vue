<script setup lang="ts">
// Los 3 lotes de suministros del mercado, como su propia seccion (separada
// de MercadoPanel.vue) -- representacion en iconos por tipo de recurso en
// vez de una linea de texto "B:60% C:0%...", con un tooltip que recuerda la
// regla del pedido de urgencia.
import { computed, ref } from 'vue'
import { store } from '../store'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'

const mercado = computed(() => store.estado!.market)

const abierto = ref<number | null>(null)
function alternar(i: number) {
  abierto.value = abierto.value === i ? null : i
}
</script>

<template>
  <section class="panel suministros">
    <h3>Suministros</h3>
    <ul class="lista-suministros">
      <li v-for="(lote, i) in mercado.suministros" :key="i" class="lote" :class="{ abierto: abierto === i }">
        <template v-if="lote">
          <div class="recursos">
            <span class="recurso"><span class="icono"><IconoHarina tipo="Blanca" /></span>{{ lote.recursos.Blanca }}%</span>
            <span class="recurso"><span class="icono"><IconoHarina tipo="Centeno" /></span>{{ lote.recursos.Centeno }}%</span>
            <span class="recurso"><span class="icono"><IconoHarina tipo="Integral" /></span>{{ lote.recursos.Integral }}%</span>
            <span class="recurso"><span class="icono"><IconoAgua /></span>{{ lote.recursos.agua }}%</span>
            <button type="button" class="boton-info" title="¿Cómo funciona?" @click="alternar(i)">ⓘ</button>
          </div>
          <div class="tooltip" role="tooltip">
            <p>
              Acción C: toma este lote entero (1 PA). Suma siempre exactamente 150% en Harina + Agua combinados.
            </p>
            <p>Pedido de urgencia: pagando +1 Dato de Investigación, ignoras el mercado y eliges tú los recursos (también 150%).</p>
          </div>
        </template>
        <span v-else class="vacio">— tomado —</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.suministros h3 {
  margin-top: 0;
}

.lista-suministros {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.lote {
  position: relative;
  background: var(--color-fondo);
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
}

.recursos {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.8rem;
}

.recurso {
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.icono {
  width: 16px;
  height: 16px;
}

.boton-info {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--color-texto-tenue);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0 0.2rem;
}

.boton-info:hover {
  color: var(--color-texto);
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  top: calc(100% + 0.3rem);
  right: 0;
  width: 240px;
  max-width: 70vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  font-size: 0.72rem;
  line-height: 1.35;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  z-index: 30;
  transition: opacity 0.1s ease;
}

.tooltip p {
  margin: 0 0 0.35rem;
}

.tooltip p:last-child {
  margin-bottom: 0;
}

.lote:hover .tooltip,
.lote.abierto .tooltip {
  visibility: visible;
  opacity: 1;
}

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}
</style>
