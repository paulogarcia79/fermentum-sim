<script setup lang="ts">
// Tarjeta visual de una receta -- "compacta" (icono + nombre + track con
// numeros, todo el detalle en un tooltip) es el diseño historico, usado
// hoy solo anidado dentro de EstacionCard.vue donde el espacio es
// reducido. El modo por defecto (sin `compacta`) es la carta de protocolo
// completa al estilo de un juego de mesa fisico
// (reference_images/recipe_card_example.jpeg): Formula Base, Perfil de
// Acidez, el track biologico con las zonas nombradas, y una tabla de
// Rendimiento por zona -- usada en el Mercado y en la Carpeta de Proyectos.
// `acidezInicial`/`bonoSellado` (de FermentationSlot, ver EstacionCard.vue y
// DetalleRecetaModal.vue) son opcionales: cuando estan presentes (una
// receta ya iniciada) la Escala de Acidez muestra el Registro de pH real en
// vez de solo la diana objetivo.
import { computed, ref } from 'vue'
import type { Recipe, TecnologiaID } from '../types'
import IconoPan from './IconoPan.vue'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'
import { PCT_POR_TOKEN_HARINA, fmtTokensHarina, tokensHarina } from '../data/unidades'
import EscalaAcidez from './EscalaAcidez.vue'
import TablaRendimiento from './TablaRendimiento.vue'

const NOMBRE_TECNOLOGIA: Record<TecnologiaID, string> = {
  incubadora: 'Incubadora',
  camara_b: 'Cámara B',
  modulo_analitico: 'Módulo Analítico',
  criopreservacion: 'Criopreservación',
}

const props = defineProps<{
  receta: Recipe
  compacta?: boolean
  acidezInicial?: number | null
  bonoSellado?: boolean
}>()

const TRACK_MAX = 20
function pct(posicion: number): number {
  return Math.min(100, Math.max(0, (posicion / TRACK_MAX) * 100))
}

const bandas = computed(() => {
  const r = props.receta
  const baja = [pct(r.zona_baja[0] - 1), pct(r.zona_baja[1])]
  const optima = [pct(r.zona_optima[0] - 1), pct(r.zona_optima[1])]
  const sobre = [pct(r.zona_sobrefermentada[0] - 1), pct(TRACK_MAX)]
  return { baja, optima, sobre }
})

const centroExacto = computed(() =>
  Math.floor((props.receta.zona_optima[0] + props.receta.zona_optima[1]) / 2),
)

const detalleAbierto = ref(false)
</script>

<template>
  <div class="receta-card" :class="{ compacta, completa: !compacta, abierta: detalleAbierto }">
    <template v-if="compacta">
      <div class="cabecera">
        <div class="icono-pan-envoltorio"><IconoPan :id="receta.id" /></div>
        <div class="titulo">
          <span class="nombre">{{ receta.nombre }}</span>
          <span class="grado">{{ receta.grado }}</span>
        </div>
        <button
          type="button"
          class="boton-info"
          :aria-expanded="detalleAbierto"
          title="Ver todos los detalles"
          @click="detalleAbierto = !detalleAbierto"
        >
          ⓘ
        </button>
      </div>

      <div class="requisitos">
        <span
          class="req"
          :title="`${fmtTokensHarina(100)} de Harina ${receta.harina_base} del ${PCT_POR_TOKEN_HARINA}% = 100% (una bolsa entera)`"
        >
          <span class="icono-req"><IconoHarina :tipo="receta.harina_base" /></span> {{ tokensHarina(100) }}
          <span class="unidad-secundaria">(100%)</span>
        </span>
        <span class="req" :title="`${receta.tokens_agua} tokens de Agua = ${receta.hidratacion_pct}% de hidratación`">
          <span class="icono-req"><IconoAgua /></span> {{ receta.tokens_agua }}
          <span class="unidad-secundaria">({{ receta.hidratacion_pct }}%)</span>
        </span>
      </div>

      <div class="escala-puntos">
        <div class="pista">
          <div class="banda baja" :style="{ left: bandas.baja[0] + '%', width: bandas.baja[1] - bandas.baja[0] + '%' }" />
          <div
            class="banda optima"
            :style="{ left: bandas.optima[0] + '%', width: bandas.optima[1] - bandas.optima[0] + '%' }"
          />
          <div class="banda sobre" :style="{ left: bandas.sobre[0] + '%', width: bandas.sobre[1] - bandas.sobre[0] + '%' }" />
        </div>
        <div class="etiquetas-puntos">
          <span class="pts baja">{{ receta.puntos_baja }}</span>
          <span class="pts optima">{{ receta.puntos_optimos }}</span>
          <span class="pts sobre">{{ receta.penalizacion_colapso }}</span>
        </div>
      </div>

      <div class="tooltip" role="tooltip">
        <p>
          Requiere: {{ fmtTokensHarina(100) }} de Harina {{ receta.harina_base }} (100%) +
          {{ receta.tokens_agua }} tokens de Agua ({{ receta.hidratacion_pct }}% hidratación)<template
            v-if="receta.req_tecnologico"
          >
            · Requiere {{ receta.req_tecnologico }}</template
          >
        </p>
        <p>Bono de sabor: Acidez ∈ {{ receta.acidez_diana.join(', ') }} al iniciar → +{{ receta.bono_sabor_pts }} pts</p>
        <p>
          Zona Óptima {{ receta.zona_optima[0] }}–{{ receta.zona_optima[1] }}: +1 Dato (centro exacto
          {{ centroExacto }}: +1 extra con Módulo Analítico)
        </p>
        <p>Sobrefermentada desde {{ receta.zona_sobrefermentada[0] }}: colapso automático.</p>
      </div>
    </template>

    <template v-else>
      <div class="cabecera-completa">
        <h4 class="titulo-completo">Receta de Protocolo: <strong>{{ receta.nombre }}</strong></h4>
        <span class="icono-cabecera-trigo"><IconoHarina :tipo="receta.harina_base" /></span>
      </div>
      <p class="grado-linea">
        Grado: {{ receta.grado
        }}<span v-if="receta.req_tecnologico"> · requiere {{ NOMBRE_TECNOLOGIA[receta.req_tecnologico] }}</span>
      </p>

      <div class="formula-base">
        <div class="formula-titulo">Fórmula Base</div>
        <div class="formula-cuerpo">
          <div class="ilustracion-pan"><IconoPan :id="receta.id" /></div>
          <div class="formula-datos">
            <div class="dato-formula">
              <span class="icono-dato"><IconoHarina :tipo="receta.harina_base" /></span>
              {{ fmtTokensHarina(100) }} de Harina {{ receta.harina_base }}
              <span class="unidad-secundaria">(100%)</span>
            </div>
            <div class="dato-formula">
              <span class="icono-dato"><IconoAgua /></span>
              {{ receta.tokens_agua }} tokens de Agua
              <span class="unidad-secundaria">({{ receta.hidratacion_pct }}% de hidratación)</span>
            </div>
            <div class="pips-agua">
              <span v-for="n in receta.tokens_agua" :key="n" class="pip-agua" />
            </div>
          </div>
        </div>
      </div>

      <div class="seccion">
        <div class="seccion-titulo">Perfil de Acidez Requerido</div>
        <EscalaAcidez
          :diana="[...receta.acidez_diana]"
          :bono-pts="receta.bono_sabor_pts"
          :registrada="acidezInicial"
          :bono-sellado="bonoSellado"
        />
      </div>

      <div class="seccion">
        <div class="seccion-titulo">Track Biológico (Fermentación)</div>
        <div class="escala-puntos">
          <div class="pista">
            <div class="banda baja" :style="{ left: bandas.baja[0] + '%', width: bandas.baja[1] - bandas.baja[0] + '%' }" />
            <div
              class="banda optima"
              :style="{ left: bandas.optima[0] + '%', width: bandas.optima[1] - bandas.optima[0] + '%' }"
            />
            <div
              class="banda sobre"
              :style="{ left: bandas.sobre[0] + '%', width: bandas.sobre[1] - bandas.sobre[0] + '%' }"
            />
          </div>
          <div class="etiquetas-zona">
            <span class="baja">Baja</span>
            <span class="optima">Óptima</span>
            <span class="sobre">Sobre-fermentada</span>
          </div>
        </div>
      </div>

      <div class="seccion">
        <div class="seccion-titulo">Rendimiento</div>
        <TablaRendimiento :receta="receta" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.receta-card {
  position: relative;
  background: var(--color-fondo);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.receta-card.completa {
  border-radius: 10px;
  padding: 0.7rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.3);
}

/* -- Modo completo: cabecera -- */
.cabecera-completa {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem;
  border-bottom: 1px solid var(--color-borde);
  padding-bottom: 0.4rem;
}

.titulo-completo {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--color-texto-tenue);
}

.titulo-completo strong {
  color: var(--color-texto);
  font-weight: 700;
  text-transform: uppercase;
}

.icono-cabecera-trigo {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
}

.grado-linea {
  margin: -0.3rem 0 0;
  font-size: 0.72rem;
  color: var(--color-texto-tenue);
}

/* -- Modo completo: Formula Base -- */
.formula-base {
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.4rem 0.5rem;
}

.formula-titulo {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-texto-tenue);
  margin-bottom: 0.3rem;
}

.formula-cuerpo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.ilustracion-pan {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
}

.formula-datos {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1 1 auto;
  min-width: 0;
}

.dato-formula {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
}

.icono-dato {
  width: 14px;
  height: 14px;
  flex: 0 0 auto;
}

.pips-agua {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 0.1rem;
}

.pip-agua {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #5b8dd9;
  opacity: 0.75;
  flex: 0 0 auto;
}

/* -- Modo completo: secciones genericas -- */
.seccion-titulo {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-texto-tenue);
  margin-bottom: 0.3rem;
}

.etiquetas-zona {
  display: flex;
  justify-content: space-between;
  font-size: 0.62rem;
  color: var(--color-texto-tenue);
  margin-top: 0.2rem;
}

.etiquetas-zona .optima {
  color: var(--color-bien);
}

.etiquetas-zona .sobre {
  color: var(--color-mal);
}

.cabecera {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.icono-pan-envoltorio {
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
}

.receta-card.compacta .icono-pan-envoltorio {
  width: 20px;
  height: 20px;
}

.titulo {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
}

.nombre {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grado {
  font-size: 0.7rem;
  color: var(--color-texto-tenue);
}

.boton-info {
  flex: 0 0 auto;
  background: none;
  border: none;
  color: var(--color-texto-tenue);
  font-size: 0.9rem;
  padding: 0 0.2rem;
  cursor: pointer;
}

.boton-info:hover {
  color: var(--color-texto);
}

.requisitos {
  display: flex;
  gap: 0.75rem;
  margin: 0.4rem 0;
}

.req {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
}

.icono-req {
  width: 16px;
  height: 16px;
}

.escala-puntos {
  margin-top: 0.3rem;
}

.pista {
  position: relative;
  height: 8px;
  background: #2a231d;
  border-radius: 4px;
  overflow: visible;
}

.banda {
  position: absolute;
  top: 0;
  height: 100%;
}

.banda.baja {
  background: #4a4038;
}

.banda.optima {
  background: var(--color-bien);
  opacity: 0.55;
}

.banda.sobre {
  background: var(--color-mal);
  opacity: 0.55;
}

.etiquetas-puntos {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: var(--color-texto-tenue);
  margin-top: 0.15rem;
}

.pts.optima {
  color: var(--color-bien);
}

.pts.sobre {
  color: var(--color-mal);
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + 0.4rem);
  left: 50%;
  transform: translateX(-50%);
  width: 260px;
  max-width: 70vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--color-texto);
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

.receta-card.compacta:hover .tooltip,
.receta-card.compacta:focus-within .tooltip,
.receta-card.compacta.abierta .tooltip {
  visibility: visible;
  opacity: 1;
}
</style>
