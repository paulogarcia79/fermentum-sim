<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import RecetaCard from './RecetaCard.vue'
import { PRECIO_RECETA_MAZO } from '../data/preciosReceta'

const mercado = computed(() => store.estado!.market)
const cartasEnMazo = computed(() => mercado.value.mazo_recetas_restantes)
const cartasEnDescarte = computed(() => mercado.value.descarte_recetas.length)
// Un mazo vacio con descarte sigue dando carta: robar lo rebaraja primero.
const mazoAgotado = computed(() => cartasEnMazo.value === 0 && cartasEnDescarte.value === 0)
</script>

<template>
  <section class="panel mercado">
    <h3>Mercado Central</h3>

    <!-- El mazo va en la cabecera, no como quinta carta de la lista: la lista
         envuelve y se va por debajo del pliegue de scroll de la region, y una
         carta que hay que buscar no es una carta que se pueda comprar. Ademas
         no es una estacion: es la pila de robo, y leerla junto al titulo es
         justo donde antes vivia el recuento. -->
    <div class="cabecera-recetas">
      <span class="sub-titulo">Recetas</span>
      <div class="mazo" :class="{ agotado: mazoAgotado }">
        <span class="dorso" aria-hidden="true"></span>
        <span v-if="mazoAgotado" class="estado-mazo">Mazo agotado</span>
        <span v-else class="estado-mazo">
          Mazo: <span class="dato">{{ cartasEnMazo }}</span>
          <template v-if="cartasEnMazo === 0 && cartasEnDescarte > 0">
            — se baraja el descarte (<span class="dato">{{ cartasEnDescarte }}</span
            >)
          </template>
        </span>
        <span v-if="!mazoAgotado" class="precio-ciega">
          A ciegas <span class="dato">{{ PRECIO_RECETA_MAZO }}</span> Monedas
        </span>
      </div>
    </div>
    <ul class="lista-recetas">
      <li v-for="(receta, i) in mercado.recetas_visibles" :key="i" class="slot">
        <RecetaCard v-if="receta" :receta="receta" />
        <span v-else class="vacio">— vacía —</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.mercado h3 {
  margin-top: 0;
}

.sub-titulo {
  font-size: var(--t-xs);
  text-transform: uppercase;
  color: var(--tinta-tenue);
  margin: var(--e3) 0 var(--e2);
}

.lista-recetas {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
}

.lista-recetas .slot {
  flex: 1 1 260px;
  min-width: 240px;
  max-width: 320px;
}

.slot .vacio {
  display: block;
  padding: var(--e2) var(--e2);
}

.vacio {
  color: var(--tinta-tenue);
  font-style: italic;
}

.cabecera-recetas {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--e2);
  margin: var(--e3) 0 var(--e2);
}

.cabecera-recetas .sub-titulo {
  margin: 0;
}

/* La pila de robo. No es un slot vacio ni una quinta estacion: es la carta que
   se puede comprar sin verla (Accion G, origen mazo), y el dorso rayado en
   miniatura es lo que la distingue de las cuatro expuestas de un vistazo. */
.mazo {
  display: flex;
  align-items: center;
  gap: var(--e1);
  padding: var(--e1) var(--e2);
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-control);
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.mazo .dorso {
  width: 0.75rem;
  height: 1rem;
  border: 1px solid var(--borde-fuerte);
  border-radius: 2px;
  background: repeating-linear-gradient(
    45deg,
    var(--carta),
    var(--carta) 3px,
    var(--borde) 3px,
    var(--borde) 4px
  );
}

.mazo.agotado {
  opacity: 0.6;
}

.precio-ciega {
  color: var(--verdin);
}
</style>
