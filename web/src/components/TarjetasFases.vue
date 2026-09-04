<script setup lang="ts">
// Las tres fases del Dia de Laboratorio como tres tarjetas.
//
// Vive en su propio componente porque se pinta en DOS sitios: la portada
// (LandingView) y la sala de espera (SalaEsperaView). Que sean literalmente el
// mismo componente es el punto -- lo que lees mientras esperas a que entren
// los demas es lo mismo que te explico el juego antes de entrar, y no dos
// redacciones que pueden separarse.
import { FASES } from '../data/copyLanding'
import IconoClima from './IconoClima.vue'
import IconoPeon from './IconoPeon.vue'
import IconoPan from './IconoPan.vue'

// Compacto = version de la sala de espera: mismo texto, menos aire.
withDefaults(defineProps<{ compacto?: boolean }>(), { compacto: false })
</script>

<template>
  <ol class="fases" :class="{ compacto }">
    <li v-for="fase in FASES" :key="fase.numero" class="fase">
      <div class="marca">
        <span class="dato ordinal">{{ fase.numero }}</span>
        <span class="ico-s icono" aria-hidden="true">
          <!-- Un icono por fase, reutilizando los que ya dibuja el tablero:
               el clima que se revela, el peon que actua, el pan que sale. -->
          <IconoClima v-if="fase.numero === 'I'" id="estabilidad_termica" />
          <IconoPeon v-else-if="fase.numero === 'II'" color="var(--cobre)" />
          <IconoPan v-else id="hogaza_centeno" />
        </span>
      </div>
      <h3>{{ fase.titulo }}</h3>
      <p>{{ fase.texto }}</p>
    </li>
  </ol>
</template>

<style scoped>
.fases {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--e3);
}

.fase {
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  padding: var(--e3) var(--e4) var(--e4);
}

.compacto .fase {
  padding: var(--e3);
}

.marca {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e2);
  margin-bottom: var(--e2);
}

.ordinal {
  color: var(--cobre);
  font-size: var(--t-l);
  font-weight: 600;
  line-height: 1;
}

.icono {
  opacity: 0.85;
}

.fase h3 {
  margin: 0 0 var(--e1);
  font-size: var(--t-m);
}

.fase p {
  margin: 0;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
  line-height: 1.5;
}

.compacto .fase p {
  font-size: var(--t-xs);
}
</style>
