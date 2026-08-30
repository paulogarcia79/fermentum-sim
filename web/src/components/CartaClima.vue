<script setup lang="ts">
// Carta de clima como objeto fisico -- inspirada en
// reference_images/climate_card_example.jpeg (barra de titulo, numero de
// temperatura grande, nombre de protocolo, recuadro rayado con el efecto,
// insignia de riesgo). Un mismo componente cubre tres usos: la carta
// revelada a tamaño completo, las miniaturas de la pila de descarte
// (`compacta`), y el dorso boca-abajo del mazo (`bocaAbajo`, sin `carta` --
// la identidad de las cartas del mazo esta oculta).
import { computed } from 'vue'
import type { ClimateCard } from '../types'
import { efectoBiologicoTexto, efectoPasivoTexto } from '../climaTexto'
import IconoClima from './IconoClima.vue'

const props = defineProps<{
  carta?: ClimateCard | null
  compacta?: boolean
  bocaAbajo?: boolean
}>()

const signoClase = computed(() => {
  const mod = props.carta?.modificador_termico ?? 0
  if (mod > 0) return 'calido'
  if (mod < 0) return 'frio'
  return 'neutro'
})

const signoTexto = computed(() => ((props.carta?.modificador_termico ?? 0) >= 0 ? '+' : ''))

const bioTexto = computed(() => (props.carta ? efectoBiologicoTexto(props.carta) : null))
const pasivoTexto = computed(() => (props.carta ? efectoPasivoTexto(props.carta) : null))
const tieneEfecto = computed(() => bioTexto.value !== null || pasivoTexto.value !== null)
</script>

<template>
  <div class="carta-clima" :class="{ compacta, 'boca-abajo': bocaAbajo, vacia: !bocaAbajo && !carta }">
    <div v-if="bocaAbajo" class="dorso">
      <div class="dorso-marca">
        <svg viewBox="0 0 24 24" class="dorso-icono" aria-hidden="true">
          <path
            d="M10 3 H14 V9.5 L18.5 18 A2.5 2.5 0 0 1 16.2 21.5 H7.8 A2.5 2.5 0 0 1 5.5 18 Z"
            fill="none"
            stroke="currentColor"
            stroke-width="1.3"
            stroke-linejoin="round"
          />
          <path d="M9 14 H15" stroke="currentColor" stroke-width="1" />
        </svg>
        <span class="dorso-texto">FERMENTUM</span>
      </div>
    </div>

    <template v-else-if="carta">
      <div class="cabecera-carta">
        <span class="titulo-set">Fermentum</span>
        <span class="titulo-sub">Protocolo Climático</span>
      </div>

      <div class="cuerpo-carta">
        <div class="icono-envoltorio"><IconoClima :id="carta.id" /></div>
        <div class="numero-temp" :class="signoClase">{{ signoTexto }}{{ carta.modificador_termico }}°</div>
        <span v-if="tieneEfecto" class="insignia-riesgo" title="Esta carta tiene un efecto adicional">!</span>
      </div>

      <p class="nombre-protocolo">{{ carta.nombre }}</p>

      <div class="efecto-caja" :class="{ neutra: !tieneEfecto }">
        <p v-if="bioTexto">🧪 {{ bioTexto }}</p>
        <p v-if="pasivoTexto">⚙️ {{ pasivoTexto }}</p>
        <p v-if="!tieneEfecto">Sin efecto adicional.</p>
      </div>
    </template>

    <div v-else class="vacio-contenido">—</div>
  </div>
</template>

<style scoped>
.carta-clima {
  width: 200px;
  min-height: 270px;
  display: flex;
  flex-direction: column;
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-zona);
  padding: var(--e2) var(--e3);
  box-shadow: var(--sombra-carta);
}

.carta-clima.compacta {
  width: 108px;
  min-height: 148px;
  padding: var(--e2) var(--e2);
  border-radius: var(--r-carta);
}

.carta-clima.vacia {
  align-items: center;
  justify-content: center;
  border-style: dashed;
  box-shadow: none;
}

.vacio-contenido {
  color: var(--tinta-tenue);
  font-size: var(--t-xl);
}

/* -- Cabecera -- */
.cabecera-carta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--e2);
  border-bottom: 1px solid var(--borde);
  padding-bottom: var(--e2);
  margin-bottom: var(--e2);
}

.titulo-set {
  font-size: var(--t-micro);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.titulo-sub {
  font-size: 0.6rem;
  color: var(--tinta-tenue);
  text-align: right;
}

.compacta .cabecera-carta {
  display: none;
}

/* -- Cuerpo: icono + numero de temperatura -- */
.cuerpo-carta {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--e2);
  padding: var(--e1) 0;
}

.icono-envoltorio {
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
}

.compacta .icono-envoltorio {
  width: 18px;
  height: 18px;
}

.numero-temp {
  font-size: var(--t-display);
  font-weight: 800;
  line-height: 1;
}

.compacta .numero-temp {
  font-size: var(--t-l);
}

.numero-temp.calido {
  color: var(--calido);
}

.numero-temp.frio {
  color: var(--frio);
}

.numero-temp.neutro {
  color: var(--tinta);
}

.insignia-riesgo {
  position: absolute;
  top: -0.3rem;
  right: -0.1rem;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 3px;
  transform: rotate(45deg);
  background: var(--riesgo);
  color: var(--tinta-sobre-acento);
  font-weight: 800;
  font-size: var(--t-micro);
  display: flex;
  align-items: center;
  justify-content: center;
}

.insignia-riesgo::before {
  content: '!';
  transform: rotate(-45deg);
}

.compacta .insignia-riesgo {
  width: 0.85rem;
  height: 0.85rem;
  font-size: 0.55rem;
}

/* -- Nombre de protocolo -- */
.nombre-protocolo {
  margin: var(--e2) 0 var(--e2);
  font-size: var(--t-s);
  font-weight: 700;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.compacta .nombre-protocolo {
  font-size: 0.6rem;
  margin: var(--e1) 0 var(--e2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* -- Recuadro de efecto (rayado, como la referencia) -- */
.efecto-caja {
  margin-top: auto;
  border: 1px solid var(--cobre);
  border-radius: var(--r-control);
  padding: var(--e2) var(--e2);
  background: repeating-linear-gradient(
    45deg,
    var(--lavado-cobre),
    var(--lavado-cobre) 5px,
    transparent 5px,
    transparent 10px
  );
}

.efecto-caja p {
  margin: 0;
  font-size: var(--t-micro);
  line-height: 1.3;
}

.efecto-caja p + p {
  margin-top: var(--e1);
}

.efecto-caja.neutra {
  border-color: var(--borde);
  background: none;
}

.efecto-caja.neutra p {
  color: var(--tinta-tenue);
  font-style: italic;
}

.compacta .efecto-caja {
  padding: var(--e1) var(--e2);
}

.compacta .efecto-caja p {
  font-size: 0.55rem;
}

/* -- Dorso (mazo boca-abajo) -- */
.dorso {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-carta);
  background: repeating-linear-gradient(
    45deg,
    var(--carta),
    var(--carta) 6px,
    var(--borde) 6px,
    var(--borde) 7px
  );
}

.dorso-marca {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--e2);
  color: var(--cobre);
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: 50%;
  width: 64%;
  aspect-ratio: 1;
  justify-content: center;
}

.dorso-icono {
  width: 40%;
  height: 40%;
}

.dorso-texto {
  font-size: 0.5rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.compacta .dorso-texto {
  font-size: 0.4rem;
}
</style>
