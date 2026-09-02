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
import type { Grado, Recipe } from '../types'
import IconoPan from './IconoPan.vue'
import IconoHarina from './IconoHarina.vue'
import IconoMonedas from './IconoMonedas.vue'
import IconoAgua from './IconoAgua.vue'
import { PCT_POR_TOKEN_HARINA, fmtTokensHarina, tokensHarina } from '../data/unidades'
import EscalaAcidez from './EscalaAcidez.vue'
import TablaRendimiento from './TablaRendimiento.vue'
import { PRECIO_RECETA } from '../data/preciosReceta'
import { tieneZonaAmpliada, zonasDe } from '../data/zonasReceta'
import PistaMedida, { type BandaPista } from './PistaMedida.vue'
import Tooltip from './Tooltip.vue'

// Que imprime cada grado. El grado no se elige: lo deriva models.py del reparto
// de harinas (`_grado_desde_harinas`), y las dos formas legales -- 100% y 50+50 --
// son exactamente las dos que la Bolsa de Harinas sabe vender.
const REGLA_GRADO: Record<Grado, string> = {
  'Básica': 'una bolsa entera de Blanca',
  'Intermedia': 'media bolsa de dos harinas distintas',
  'Avanzada': 'una bolsa entera de harina especial',
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
const zonas = computed(() => zonasDe(props.receta))
const ampliada = computed(() => tieneZonaAmpliada(props.receta))

const bandas = computed<BandaPista[]>(() => {
  const z = zonas.value
  // `etiqueta`/`rango` viajan CON la banda: PistaMedida las posiciona con la misma
  // aritmetica que usa para dibujarla, asi que el nombre no puede desalinearse de la
  // zona que nombra. Los rangos salen de `zonasDe`, o sea de las zonas EFECTIVAS:
  // con Modulo Analitico instalado, la optima se etiqueta ya ensanchada.
  return [
    {
      desde: z.crecimiento[0] - 1,
      hasta: z.crecimiento[1],
      tono: 'crecimiento',
      etiqueta: 'Crecimiento',
      rango: `${z.crecimiento[0]}–${z.crecimiento[1]}`,
    },
    {
      desde: z.preFermento[0] - 1,
      hasta: z.preFermento[1],
      tono: 'baja',
      etiqueta: 'Pre-fermento',
      rango: `${z.preFermento[0]}–${z.preFermento[1]}`,
    },
    {
      desde: z.optima[0] - 1,
      hasta: z.optima[1],
      tono: 'optima',
      etiqueta: 'Óptima',
      rango: `${z.optima[0]}–${z.optima[1]}`,
    },
    {
      desde: z.colapso[0] - 1,
      hasta: TRACK_MAX,
      tono: 'sobre',
      etiqueta: 'Colapso',
      rango: `${z.colapso[0]}–${z.colapso[1]}`,
    },
  ]
})

// 100% = una bolsa entera (10 tokens); 50% = media bolsa (5), la unidad que la
// Accion C ya vende con `comprar_media`.
function etiquetaBolsa(pct: number): string {
  return pct === 100 ? 'una bolsa entera' : 'media bolsa'
}

const textoHarinas = computed(() =>
  props.receta.harinas
    .map(([tipo, pct]) => `${fmtTokensHarina(pct)} de Harina ${tipo} (${pct}%)`)
    .join(' + '),
)

// Precio de adquisicion IMPRESO en la carta, como la esquina de coste de una carta
// fisica: se muestra siempre, tambien en las que ya son tuyas. Es deliberadamente
// distinto de `.requisitos` / "Formula Base", que son el coste de INICIAR la receta
// (harina y agua): otro momento, otra moneda, y nunca se pagan a la vez. De ahi que
// viva en la cabecera y no en la fila de insumos.
const precioAdquisicion = computed(() => PRECIO_RECETA[props.receta.grado])
const tituloPrecio = computed(
  () => `Adquirir esta receta cuesta ${precioAdquisicion.value} Monedas (Acción G)`,
)

const centroExacto = computed(() =>
  Math.floor((props.receta.zona_optima[0] + props.receta.zona_optima[1]) / 2),
)

const detalleAbierto = ref(false)
</script>

<template>
  <!-- Dos raices en vez de una: la carta compacta tiene tooltip y por tanto ES
       el ancla (Tooltip.vue detecta el hover sobre su propia raiz); la completa
       no tiene, y se queda como un div normal. -->
  <Tooltip
    v-if="compacta"
    class="receta-card compacta"
    :fijado="detalleAbierto"
    @cerrar="detalleAbierto = false"
  >
    <div class="cabecera">
      <div class="ico-m icono-pan-envoltorio"><IconoPan :id="receta.id" /></div>
      <div class="titulo">
        <span class="nombre">{{ receta.nombre }}</span>
        <span class="grado" :class="`grado-${receta.grado.toLowerCase()}`">{{ receta.grado }}</span>
      </div>
      <span class="precio-carta" :title="tituloPrecio">
        <span class="ico-xs"><IconoMonedas /></span><span class="dato">{{ precioAdquisicion }}</span>
      </span>
      <button
        type="button"
        class="boton-info"
        :aria-expanded="detalleAbierto"
        aria-label="Ver todos los detalles"
        @click="detalleAbierto = !detalleAbierto"
      >
        ⓘ
      </button>
    </div>

    <div class="requisitos">
      <span
        v-for="[tipo, pct] in receta.harinas"
        :key="tipo"
        class="req"
        :title="`${fmtTokensHarina(pct)} de Harina ${tipo} del ${PCT_POR_TOKEN_HARINA}% = ${pct}% (${etiquetaBolsa(pct)})`"
      >
        <span class="ico-xs"><IconoHarina :tipo="tipo" /></span> {{ tokensHarina(pct) }}
        <span class="unidad-secundaria">({{ pct }}%)</span>
      </span>
      <span class="req" :title="`${receta.tokens_agua} tokens de Agua = ${receta.hidratacion_pct}% de hidratación`">
        <span class="ico-xs"><IconoAgua /></span> {{ receta.tokens_agua }}
        <span class="unidad-secundaria">({{ receta.hidratacion_pct }}%)</span>
      </span>
    </div>

    <div class="escala-puntos">
      <PistaMedida :valor="null" :max="TRACK_MAX" :bandas="bandas" modo="posicion" lectura="" compacta />
      <div class="etiquetas-puntos">
        <span class="pts baja dato">{{ receta.puntos_pre_fermento }}</span>
        <span class="pts optima dato">{{ receta.puntos_optimos }}</span>
        <span class="pts sobre dato">{{ receta.penalizacion_colapso }}</span>
      </div>
    </div>

    <template #contenido>
      <p>
        Requiere: {{ textoHarinas }} +
        {{ receta.tokens_agua }} tokens de Agua ({{ receta.hidratacion_pct }}% hidratación)
      </p>
      <p>Bono de sabor: Acidez ∈ {{ receta.acidez_diana.join(', ') }} al iniciar → +{{ receta.bono_sabor_pts }} pts</p>
      <p>
        Zona Óptima {{ zonas.optima[0] }}–{{ zonas.optima[1] }}: +1 Dato (+1 más con Módulo
        Analítico, y +1 más en el centro exacto {{ centroExacto }})
      </p>
      <p>
        Colapso desde {{ zonas.colapso[0] }}: horneado automático con penalización. Crecimiento 1–{{ zonas.crecimiento[1] }}: la masa aún no es pan, no se puede hornear.<template v-if="ampliada">
          Zona ensanchada por tu Módulo Analítico.</template
        >
      </p>
    </template>
  </Tooltip>

  <div v-else class="receta-card completa">
    <div class="cabecera-completa">
      <h4 class="titulo-completo">Receta de Protocolo: <strong>{{ receta.nombre }}</strong></h4>
      <span class="esquina-carta">
        <span class="precio-carta" :title="tituloPrecio">
          <span class="ico-xs"><IconoMonedas /></span><span class="dato">{{ precioAdquisicion }}</span>
        </span>
        <span class="harinas-cabecera">
          <span v-for="[tipo] in receta.harinas" :key="tipo" class="ico-s"><IconoHarina :tipo="tipo" /></span>
        </span>
      </span>
    </div>
    <p class="grado-linea">
      Grado: <span class="grado" :class="`grado-${receta.grado.toLowerCase()}`">{{ receta.grado }}</span>
      <span class="unidad-secundaria"> · {{ REGLA_GRADO[receta.grado] }}</span>
    </p>

    <div class="formula-base">
      <div class="eyebrow">Fórmula Base</div>
      <div class="formula-cuerpo">
        <div class="ico-l"><IconoPan :id="receta.id" /></div>
        <div class="formula-datos">
          <div v-for="[tipo, pct] in receta.harinas" :key="tipo" class="dato-formula">
            <span class="ico-xs"><IconoHarina :tipo="tipo" /></span>
            {{ fmtTokensHarina(pct) }} de Harina {{ tipo }}
            <span class="unidad-secundaria">({{ pct }}% — {{ etiquetaBolsa(pct) }})</span>
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
      </div>
    </div>

    <div class="seccion">
      <div class="eyebrow">Rendimiento</div>
      <TablaRendimiento :receta="receta" />
    </div>
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

/* El grado se diferencia por PESO tipografico, no por color: el sistema reserva
   --cobre (lo tuyo/interactivo) y --verdin (estado de mercado) para significados
   propios, y los colores de estado nunca se usan decorativamente. */
.grado {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.grado-básica {
  font-weight: 400;
}

.grado-intermedia {
  font-weight: 600;
}

.grado-avanzada {
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--tinta);
}

.harinas-cabecera {
  display: inline-flex;
  gap: var(--e1);
  flex: 0 0 auto;
}

/* Esquina de coste: el precio de adquisicion, separado de la fila de insumos
   (que es el coste de INICIAR). Sin acento propio -- el sistema reserva --cobre
   y --verdin para "lo tuyo" y "estado de mercado", y esto no es ninguno de los
   dos: es un dato impreso en la carta. */
.esquina-carta {
  display: inline-flex;
  align-items: center;
  gap: var(--e2);
  flex: 0 0 auto;
}

.precio-carta {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex: 0 0 auto;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
  white-space: nowrap;
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

</style>
