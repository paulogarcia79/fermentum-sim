<script setup lang="ts">
// Carta de Tendencia de Mercado como objeto fisico -- mismo patron que
// CartaClima.vue (3 usos: revelada a tamaño completo, miniatura en la pila
// de descarte/`compacta`, dorso boca-abajo del mazo/`bocaAbajo`), pero para
// un modificador entero simple (-2..+2, ver engine.py: Market.mazo_tendencias)
// en vez de un objeto de carta con id/nombre/efectos -- no hay identidad de
// carta que ocultar salvo el propio numero, asi que no hace falta un
// IconoTendencia.vue por id: la flecha arriba/abajo/plana se dibuja inline.
import { computed } from 'vue'
import { textoTendencia } from '../tendenciaTexto'

const props = defineProps<{
  modificador?: number | null
  compacta?: boolean
  bocaAbajo?: boolean
}>()

const signoClase = computed(() => {
  const mod = props.modificador ?? 0
  if (mod > 0) return 'calido'
  if (mod < 0) return 'frio'
  return 'neutro'
})

const signoTexto = computed(() => ((props.modificador ?? 0) >= 0 ? '+' : ''))

const texto = computed(() => (props.modificador !== null && props.modificador !== undefined ? textoTendencia(props.modificador) : null))
</script>

<template>
  <div class="carta-tendencia" :class="{ compacta, 'boca-abajo': bocaAbajo, vacia: !bocaAbajo && (modificador === null || modificador === undefined) }">
    <div v-if="bocaAbajo" class="dorso">
      <div class="dorso-marca">
        <svg viewBox="0 0 24 24" class="dorso-icono" aria-hidden="true">
          <circle cx="12" cy="12" r="7.5" fill="none" stroke="currentColor" stroke-width="1.3" />
          <path d="M12 8 V16 M9.5 9.7 A3 2 0 0 1 14.5 9.7" stroke="currentColor" stroke-width="1.1" fill="none" stroke-linecap="round" />
        </svg>
        <span class="dorso-texto">FERMENTUM</span>
      </div>
    </div>

    <template v-else-if="modificador !== null && modificador !== undefined">
      <div class="cabecera-carta">
        <span class="titulo-set">Fermentum</span>
        <span class="titulo-sub">Tendencia de Mercado</span>
      </div>

      <div class="cuerpo-carta">
        <svg v-if="modificador > 0" viewBox="0 0 24 24" class="flecha calido" aria-hidden="true">
          <path d="M12 4 L19 14 H14 V20 H10 V14 H5 Z" fill="currentColor" />
        </svg>
        <svg v-else-if="modificador < 0" viewBox="0 0 24 24" class="flecha frio" aria-hidden="true">
          <path d="M12 20 L5 10 H10 V4 H14 V10 H19 Z" fill="currentColor" />
        </svg>
        <svg v-else viewBox="0 0 24 24" class="flecha neutro" aria-hidden="true">
          <rect x="5" y="10.5" width="14" height="3" rx="1.5" fill="currentColor" />
        </svg>
        <div class="numero-modificador" :class="signoClase">{{ signoTexto }}{{ modificador }}</div>
      </div>

      <div class="efecto-caja" :class="{ neutra: modificador === 0 }">
        <p>{{ texto }}</p>
      </div>
    </template>

    <div v-else class="vacio-contenido">—</div>
  </div>
</template>

<style scoped>
.carta-tendencia {
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

.carta-tendencia.compacta {
  width: 108px;
  min-height: 148px;
  padding: var(--e2) var(--e2);
  border-radius: var(--r-carta);
}

.carta-tendencia.vacia {
  align-items: center;
  justify-content: center;
  border-style: dashed;
  box-shadow: none;
}

.vacio-contenido {
  color: var(--tinta-tenue);
  font-size: var(--t-xl);
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

.cuerpo-carta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--e2);
  padding: var(--e2) 0;
}

.flecha {
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
}

.compacta .flecha {
  width: 16px;
  height: 16px;
}

.flecha.calido {
  color: var(--calido);
}

.flecha.frio {
  color: var(--frio);
}

.flecha.neutro {
  color: var(--tinta-tenue);
}

.numero-modificador {
  font-size: var(--t-display);
  font-weight: 800;
  line-height: 1;
}

.compacta .numero-modificador {
  font-size: var(--t-l);
}

.numero-modificador.calido {
  color: var(--calido);
}

.numero-modificador.frio {
  color: var(--frio);
}

.numero-modificador.neutro {
  color: var(--tinta);
}

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
