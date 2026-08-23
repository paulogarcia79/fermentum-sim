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
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 10px;
  padding: 0.6rem 0.65rem;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.35);
}

.carta-tendencia.compacta {
  width: 108px;
  min-height: 148px;
  padding: 0.35rem 0.4rem;
  border-radius: 7px;
}

.carta-tendencia.vacia {
  align-items: center;
  justify-content: center;
  border-style: dashed;
  box-shadow: none;
}

.vacio-contenido {
  color: var(--color-texto-tenue);
  font-size: 1.4rem;
}

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

.cuerpo-carta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
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
  color: var(--color-calido);
}

.flecha.frio {
  color: var(--color-frio);
}

.flecha.neutro {
  color: var(--color-texto-tenue);
}

.numero-modificador {
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1;
}

.compacta .numero-modificador {
  font-size: 1.25rem;
}

.numero-modificador.calido {
  color: var(--color-calido);
}

.numero-modificador.frio {
  color: var(--color-frio);
}

.numero-modificador.neutro {
  color: var(--color-texto);
}

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
