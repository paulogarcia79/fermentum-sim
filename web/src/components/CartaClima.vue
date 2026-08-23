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
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 10px;
  padding: 0.6rem 0.65rem;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.35);
}

.carta-clima.compacta {
  width: 108px;
  min-height: 148px;
  padding: 0.35rem 0.4rem;
  border-radius: 7px;
}

.carta-clima.vacia {
  align-items: center;
  justify-content: center;
  border-style: dashed;
  box-shadow: none;
}

.vacio-contenido {
  color: var(--color-texto-tenue);
  font-size: 1.4rem;
}

/* -- Cabecera -- */
.cabecera-carta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem;
  border-bottom: 1px solid var(--color-borde);
  padding-bottom: 0.3rem;
  margin-bottom: 0.4rem;
}

.titulo-set {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.titulo-sub {
  font-size: 0.6rem;
  color: var(--color-texto-tenue);
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
  gap: 0.4rem;
  padding: 0.2rem 0;
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
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1;
}

.compacta .numero-temp {
  font-size: 1.25rem;
}

.numero-temp.calido {
  color: var(--color-calido);
}

.numero-temp.frio {
  color: var(--color-frio);
}

.numero-temp.neutro {
  color: var(--color-texto);
}

.insignia-riesgo {
  position: absolute;
  top: -0.3rem;
  right: -0.1rem;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 3px;
  transform: rotate(45deg);
  background: var(--color-mal);
  color: #1a1410;
  font-weight: 800;
  font-size: 0.7rem;
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
  margin: 0.3rem 0 0.4rem;
  font-size: 0.82rem;
  font-weight: 700;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.compacta .nombre-protocolo {
  font-size: 0.6rem;
  margin: 0.2rem 0 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* -- Recuadro de efecto (rayado, como la referencia) -- */
.efecto-caja {
  margin-top: auto;
  border: 1px solid var(--color-acento);
  border-radius: 5px;
  padding: 0.35rem 0.4rem;
  background: repeating-linear-gradient(
    45deg,
    rgba(217, 154, 63, 0.14),
    rgba(217, 154, 63, 0.14) 5px,
    transparent 5px,
    transparent 10px
  );
}

.efecto-caja p {
  margin: 0;
  font-size: 0.68rem;
  line-height: 1.3;
}

.efecto-caja p + p {
  margin-top: 0.25rem;
}

.efecto-caja.neutra {
  border-color: var(--color-borde);
  background: none;
}

.efecto-caja.neutra p {
  color: var(--color-texto-tenue);
  font-style: italic;
}

.compacta .efecto-caja {
  padding: 0.25rem 0.3rem;
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
  border-radius: 6px;
  background: repeating-linear-gradient(
    45deg,
    var(--color-fondo),
    var(--color-fondo) 6px,
    var(--color-borde) 6px,
    var(--color-borde) 7px
  );
}

.dorso-marca {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  color: var(--color-acento);
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
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
