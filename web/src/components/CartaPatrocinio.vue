<script setup lang="ts">
// Carta de Patrocinio como objeto fisico, hermana de CartaClima.vue: barra de
// titulo, el numero de Iniciativa grande (es lo unico de la carta que tiene
// efecto -- fija el orden del Dia 1), y debajo el capital de arranque que la
// carta entrego, en la notacion `N (P%)` de data/unidades.ts.
//
// Los recursos de la carta estan YA volcados en el jugador cuando llega el
// primer snapshot; aqui se ensenan como lo que la carta imprime, no como el
// estado actual, para que la lectura sea "esto es lo que te toco".
import type { PatrocinioCard } from '../types'
import { fmtAgua, fmtHarina } from '../data/unidades'
import IconoAgua from './IconoAgua.vue'
import IconoDatos from './IconoDatos.vue'
import IconoHarina from './IconoHarina.vue'
import IconoMonedas from './IconoMonedas.vue'

defineProps<{
  carta: PatrocinioCard
  /** Miniatura para listas; oculta la cabecera y aprieta el cuerpo. */
  compacta?: boolean
}>()
</script>

<template>
  <div class="carta-patrocinio" :class="{ compacta }">
    <div class="cabecera-carta">
      <span class="titulo-set">Fermentum</span>
      <span class="titulo-sub">Carta de Patrocinio</span>
    </div>

    <div class="cuerpo-carta">
      <span class="eyebrow">Iniciativa</span>
      <span class="numero-iniciativa dato">{{ carta.iniciativa }}</span>
    </div>

    <ul class="recursos">
      <li>
        <span class="ico-s"><IconoHarina :tipo="carta.tipo_harina" /></span>
        <span class="dato">{{ fmtHarina(carta.harina_pct) }}</span>
        <span class="etiqueta">{{ carta.tipo_harina }}</span>
      </li>
      <li>
        <span class="ico-s"><IconoAgua /></span>
        <span class="dato">{{ fmtAgua(carta.agua_tokens) }}</span>
        <span class="etiqueta">Agua</span>
      </li>
      <li>
        <span class="ico-s"><IconoMonedas /></span>
        <span class="dato">{{ carta.monedas }}</span>
        <span class="etiqueta">Monedas</span>
      </li>
      <li>
        <span class="ico-s"><IconoDatos /></span>
        <span class="dato">{{ carta.datos }}</span>
        <span class="etiqueta">Datos</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.carta-patrocinio {
  width: 200px;
  display: flex;
  flex-direction: column;
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
  padding: var(--e2) var(--e3);
  box-shadow: var(--sombra-carta);
}

/* La miniatura no fija ancho: lo pone quien la coloca (una fila flexible en
   PatrocinioModal), para que 4 cartas quepan en el modal y 2 lo llenen. */
.carta-patrocinio.compacta {
  width: 100%;
  padding: var(--e2);
  border-radius: var(--r-carta);
}

.cabecera-carta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--e2);
  border-bottom: 1px solid var(--borde);
  padding-bottom: var(--e2);
  margin-bottom: var(--e2);
}

.compacta .cabecera-carta {
  display: none;
}

.titulo-set {
  font-size: var(--t-micro);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.titulo-sub {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  text-align: right;
}

.cuerpo-carta {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--e1) 0 var(--e2);
}

.numero-iniciativa {
  font-size: var(--t-display);
  font-weight: 800;
  line-height: 1;
  color: var(--cobre);
}

.compacta .numero-iniciativa {
  font-size: var(--t-xl);
}

.recursos {
  list-style: none;
  padding: var(--e2) 0 0;
  margin: 0;
  border-top: 1px solid var(--borde);
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  font-size: var(--t-s);
}

.recursos li {
  display: flex;
  align-items: center;
  gap: var(--e2);
}

/* La cifra nunca se parte; si falta sitio, cede la etiqueta. */
.recursos .dato {
  white-space: nowrap;
}

.etiqueta {
  color: var(--tinta-tenue);
  margin-left: auto;
  font-size: var(--t-xs);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
