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
import PistaMedida, { type BandaPista } from './PistaMedida.vue'

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

// Mismas bandas que dibuja EstacionCard.vue, en unidades del track: la carta
// de la receta y la masa que la esta fermentando se leen como el mismo
// instrumento (ver PistaMedida.vue).
const bandas = computed<BandaPista[]>(() => {
  const r = props.receta
  return [
    { desde: r.zona_baja[0] - 1, hasta: r.zona_baja[1], tono: 'baja' },
    { desde: r.zona_optima[0] - 1, hasta: r.zona_optima[1], tono: 'optima' },
    { desde: r.zona_sobrefermentada[0] - 1, hasta: TRACK_MAX, tono: 'sobre' },
  ]
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
        <div class="ico-m icono-pan-envoltorio"><IconoPan :id="receta.id" /></div>
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
          <span class="ico-xs"><IconoHarina :tipo="receta.harina_base" /></span> {{ tokensHarina(100) }}
          <span class="unidad-secundaria">(100%)</span>
        </span>
        <span class="req" :title="`${receta.tokens_agua} tokens de Agua = ${receta.hidratacion_pct}% de hidratación`">
          <span class="ico-xs"><IconoAgua /></span> {{ receta.tokens_agua }}
          <span class="unidad-secundaria">({{ receta.hidratacion_pct }}%)</span>
        </span>
      </div>

      <div class="escala-puntos">
        <PistaMedida :valor="null" :max="TRACK_MAX" :bandas="bandas" modo="posicion" lectura="" compacta />
        <div class="etiquetas-puntos">
          <span class="pts baja dato">{{ receta.puntos_baja }}</span>
          <span class="pts optima dato">{{ receta.puntos_optimos }}</span>
          <span class="pts sobre dato">{{ receta.penalizacion_colapso }}</span>
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
        <span class="ico-s"><IconoHarina :tipo="receta.harina_base" /></span>
      </div>
      <p class="grado-linea">
        Grado: {{ receta.grado
        }}<span v-if="receta.req_tecnologico"> · requiere {{ NOMBRE_TECNOLOGIA[receta.req_tecnologico] }}</span>
      </p>

      <div class="formula-base">
        <div class="eyebrow">Fórmula Base</div>
        <div class="formula-cuerpo">
          <div class="ico-l"><IconoPan :id="receta.id" /></div>
          <div class="formula-datos">
            <div class="dato-formula">
              <span class="ico-xs"><IconoHarina :tipo="receta.harina_base" /></span>
              {{ fmtTokensHarina(100) }} de Harina {{ receta.harina_base }}
              <span class="unidad-secundaria">(100%)</span>
            </div>
            <div class="dato-formula">
              <span class="ico-xs"><IconoAgua /></span>
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
        <div class="eyebrow">Perfil de Acidez Requerido</div>
        <EscalaAcidez
          :diana="[...receta.acidez_diana]"
          :bono-pts="receta.bono_sabor_pts"
          :registrada="acidezInicial"
          :bono-sellado="bonoSellado"
        />
      </div>

      <div class="seccion">
        <div class="eyebrow">Track Biológico (Fermentación)</div>
        <div class="escala-puntos">
          <PistaMedida :valor="null" :max="TRACK_MAX" :bandas="bandas" modo="posicion" lectura="" />
          <div class="etiquetas-zona">
            <span class="baja">Baja</span>
            <span class="optima">Óptima</span>
            <span class="sobre">Sobre-fermentada</span>
          </div>
        </div>
      </div>

      <div class="seccion">
        <div class="eyebrow">Rendimiento</div>
        <TablaRendimiento :receta="receta" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.receta-card {
  position: relative;
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  padding: var(--e2);
}

/* La carta completa es lo unico que se levanta de la mesa. */
.receta-card.completa {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  padding: var(--e3);
  box-shadow: var(--sombra-carta);
}

/* -- Modo completo: cabecera -- */
.cabecera-completa {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--e1);
  border-bottom: 1px solid var(--borde);
  padding-bottom: var(--e1);
}

.titulo-completo {
  font-family: var(--fuente);
  font-size: var(--t-micro);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
}

.titulo-completo strong {
  display: block;
  font-family: var(--fuente-titulo);
  font-size: var(--t-m);
  letter-spacing: 0;
  color: var(--tinta);
  font-weight: 700;
}

.grado-linea {
  margin: 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

/* -- Modo completo: Formula Base -- */
.formula-base {
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  padding: var(--e2);
}

.formula-cuerpo {
  display: flex;
  align-items: center;
  gap: var(--e2);
  margin-top: var(--e1);
}

.formula-datos {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1 1 auto;
  min-width: 0;
}

.dato-formula {
  display: flex;
  align-items: center;
  gap: var(--e1);
  font-size: var(--t-xs);
}

.pips-agua {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 2px;
}

.pip-agua {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--frio);
  opacity: 0.75;
  flex: 0 0 auto;
}

/* -- Secciones -- */
.seccion > .eyebrow {
  margin-bottom: var(--e1);
}

.formula-base > .eyebrow {
  margin-bottom: var(--e1);
}

.etiquetas-zona {
  display: flex;
  justify-content: space-between;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  margin-top: 2px;
}

.etiquetas-zona .optima {
  color: var(--vital);
}

.etiquetas-zona .sobre {
  color: var(--riesgo);
}

/* -- Modo compacto -- */
.cabecera {
  display: flex;
  align-items: center;
  gap: var(--e1);
}

.receta-card.compacta .icono-pan-envoltorio {
  width: 18px;
  height: 18px;
}

.titulo {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
}

.nombre {
  font-family: var(--fuente-titulo);
  font-weight: 700;
  font-size: var(--t-s);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grado {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.boton-info {
  flex: 0 0 auto;
  background: none;
  border: none;
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  padding: 0 2px;
}

.boton-info:hover {
  color: var(--tinta);
}

.requisitos {
  display: flex;
  gap: var(--e3);
  margin: var(--e1) 0;
}

.req {
  display: flex;
  align-items: center;
  gap: var(--e1);
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.escala-puntos {
  margin-top: var(--e1);
}

.etiquetas-puntos {
  display: flex;
  justify-content: space-between;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  margin-top: 2px;
}

.pts.optima {
  color: var(--vital);
}

.pts.sobre {
  color: var(--riesgo);
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + var(--e1));
  left: 50%;
  transform: translateX(-50%);
  width: 16rem;
  max-width: 70vw;
  background: var(--zona);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  padding: var(--e2);
  font-size: var(--t-xs);
  line-height: 1.35;
  color: var(--tinta);
  box-shadow: var(--sombra-flotante);
  z-index: 30;
  transition: opacity var(--transicion);
}

.tooltip p {
  margin: 0 0 var(--e1);
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
