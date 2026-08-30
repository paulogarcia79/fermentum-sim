<script setup lang="ts">
import { computed, ref } from 'vue'
import { store } from '../store'
import EstacionCard from './EstacionCard.vue'
import RecetaCard from './RecetaCard.vue'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'
import IconoDatos from './IconoDatos.vue'
import IconoMonedas from './IconoMonedas.vue'
import IconoMaestria from './IconoMaestria.vue'
import PistaMedida from './PistaMedida.vue'
import { hexDeColor } from '../data/coloresJugador'
import { TECNOLOGIAS } from '../data/tecnologias'
import { fmtTokensAgua, fmtTokensHarina, pctAgua, tokensHarina } from '../data/unidades'
import type { HorneadoRecord, TecnologiaID, TipoHarina } from '../types'

const TIPOS_HARINA: TipoHarina[] = ['Blanca', 'Centeno', 'Integral']

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const colorHex = computed(() => hexDeColor(yo.value.color))

// Espejo de la penalizacion por desperdicio de models.py
// (puntos_maestria_final: -(total_tokens_recursos // 3)). El conteo en si lo
// hace el servidor; aqui solo se divide para mostrar el coste ya acumulado.
const penalizacionDesperdicio = computed(() => -Math.floor(yo.value.total_tokens_recursos / 3))

const EMOJI_TECNOLOGIA: Record<TecnologiaID, string> = {
  incubadora: '🌡',
  camara_b: '🚪',
  modulo_analitico: '📊',
  criopreservacion: '❄',
}

const tecAbierta = ref<TecnologiaID | null>(null)

/** Aviso de colapso: opt-in por jugador (se elige en el lobby). `en_riesgo_colapso`
 * lo calcula el servidor -- ya contempla la exencion por Criopreservacion y el
 * -2 de Aletargamiento Invernal. */
const avisoColapso = computed(
  () => store.preferencias.alertaContaminacion && yo.value.en_riesgo_colapso,
)

/** Archivo completo, exitosos primero y colapsos despues -- ambos suman al
 * marcador (los colapsos en negativo), pero solo los exitosos cuentan para
 * el gatillo de quinta receta. */
const registrosArchivo = computed<{ registro: HorneadoRecord; colapso: boolean }[]>(() => [
  ...yo.value.archivo_horneado_exitoso.map((registro) => ({ registro, colapso: false })),
  ...yo.value.archivo_colapsos.map((registro) => ({ registro, colapso: true })),
])

/** Termino «Variedad de Recetas» (CORE_MECHANICS.md 3), tal como llega del
 * servidor. La curva triangular NO se replica aqui: `puntos_variedad` viaja
 * dentro de `desglose_maestria`, y el valor marginal de la proxima clase
 * nueva es simplemente "una clase mas", no la formula. */
const variedad = computed(() => {
  const distintas = yo.value.recetas_distintas_horneadas
  return {
    distintas,
    puntos: yo.value.desglose_maestria['Variedad de Recetas'] ?? 0,
    // Incremento de la curva al pasar de n a n+1 clases: n+1.
    proxima: distintas + 1,
  }
})

const ETIQUETA_ZONA: Record<HorneadoRecord['zona_resultado'], string> = {
  optima: 'Zona Óptima',
  pre_fermento: 'Pre-fermento',
  colapso: 'Colapso',
}
</script>

<template>
  <section class="panel mi-tablero" :style="{ borderLeftColor: colorHex }">
    <header class="cabecera-tablero">
      <h2>
        <span class="punto-color" :style="{ background: colorHex }" />
        {{ yo.nombre }}
      </h2>
      <span v-if="yo.en_estado_contaminacion" class="badge-contaminado">◉ CONTAMINADO</span>

      <span class="marcador">
        <span class="ico-s"><IconoMaestria /></span>
        <strong class="dato">{{ yo.puntos_horneados }}</strong> pts horneados
        <span
          class="proyeccion"
          title="Puntuación si la partida terminara ahora: horneados + madurez del cultivo + conversión de riqueza − penalizaciones (desperdicio, contaminación). Cambia también sin hornear."
        >
          · proyección <span class="dato">{{ yo.puntos_maestria_final }}</span> PM
        </span>
      </span>

      <span class="pa" title="Puntos de Acción disponibles">
        <span class="eyebrow">PA</span>
        <span class="pa-pips">
          <span v-for="i in 3" :key="i" class="pip" :class="{ activo: i <= yo.puntos_accion }">●</span>
        </span>
      </span>
    </header>

    <div class="zonas-tablero">
      <!-- Estado del cultivo: las dos lecturas que deciden la partida. -->
      <section class="sub-zona zona-estado">
        <h3 class="eyebrow">Cultivo</h3>
        <PistaMedida
          etiqueta="Vitalidad"
          :valor="yo.vitalidad"
          :max="6"
          :previsto="avisoColapso ? yo.vitalidad_prevista : null"
          :tono="avisoColapso ? 'riesgo' : 'vital'"
        />
        <p
          v-if="avisoColapso"
          class="aviso-colapso"
          :title="`Vitalidad ${yo.vitalidad} → ${yo.vitalidad_prevista} esta noche: entrarás en Contaminación (-3 Puntos de Maestría y no podrás Iniciar Receta). Alimenta el cultivo (Acción A, 0 PA) antes de terminar el día.`"
        >
          ⚠ Colapsa esta noche si no lo alimentas
        </p>
        <PistaMedida etiqueta="Acidez" :valor="yo.acidez" :max="6" tono="frio" />

        <h3 class="eyebrow">Recursos</h3>
        <div class="recursos-grid">
          <div
            v-for="tipo in TIPOS_HARINA"
            :key="tipo"
            class="recurso-tile"
            :title="`Harina ${tipo}: ${fmtTokensHarina(yo.reserva_harina[tipo])} del 10% = ${yo.reserva_harina[tipo]}%`"
          >
            <span class="ico-s"><IconoHarina :tipo="tipo" /></span>
            <span class="dato">{{ tokensHarina(yo.reserva_harina[tipo]) }}</span>
            <span class="unidad-secundaria">({{ yo.reserva_harina[tipo] }}%)</span>
          </div>
          <div
            class="recurso-tile"
            :title="`Agua: ${fmtTokensAgua(yo.reserva_agua)} del 5% = ${pctAgua(yo.reserva_agua)}% de hidratación`"
          >
            <span class="ico-s"><IconoAgua /></span>
            <span class="dato">{{ yo.reserva_agua }}</span>
            <span class="unidad-secundaria">({{ pctAgua(yo.reserva_agua) }}%)</span>
          </div>
          <div class="recurso-tile" title="Datos de Investigación">
            <span class="ico-s"><IconoDatos /></span><span class="dato">{{ yo.datos_investigacion }}</span>
          </div>
          <div class="recurso-tile" title="Monedas">
            <span class="ico-s"><IconoMonedas /></span><span class="dato">{{ yo.monedas }}</span>
          </div>
          <div class="recurso-tile" title="Dados de inóculo en reserva">
            <span class="ico-s emoji">🎲</span><span class="dato">{{ yo.dados_inoculo }}</span>
          </div>
        </div>
        <p
          class="linea-desperdicio"
          :class="{ penaliza: penalizacionDesperdicio < 0 }"
          title="Al final de la partida pierdes 1 Punto de Maestría por cada 3 tokens de insumo sin usar. Un token de harina (10%) y uno de agua (5%) cuentan igual aquí."
        >
          <span class="dato">{{ yo.total_tokens_recursos }}</span> tokens sin usar
          <span v-if="penalizacionDesperdicio < 0">→ {{ penalizacionDesperdicio }} PM al final</span>
          <span v-else>→ sin penalización todavía</span>
        </p>
      </section>

      <section class="sub-zona zona-estaciones">
        <h3 class="eyebrow">Estaciones de fermentación</h3>
        <div class="estaciones">
          <EstacionCard :slot="yo.estaciones_fermentacion[0]" :indice="0" mostrar-fantasma />
          <EstacionCard :slot="yo.estaciones_fermentacion[1]" :indice="1" mostrar-fantasma />
          <EstacionCard
            :slot="yo.estaciones_fermentacion[2] ?? null"
            :indice="2"
            :bloqueada="!yo.tecnologias.camara_b"
            mostrar-fantasma
          />
        </div>

        <h3 class="eyebrow">Mejoras de laboratorio</h3>
        <div class="mejoras-grid">
          <div
            v-for="tec in TECNOLOGIAS"
            :key="tec.id"
            class="mejora-slot"
            :class="{ activa: yo.tecnologias[tec.id], abierta: tecAbierta === tec.id }"
          >
            {{ EMOJI_TECNOLOGIA[tec.id] }} {{ tec.nombre }}
            <button
              type="button"
              class="boton-info"
              :aria-expanded="tecAbierta === tec.id"
              title="Ver detalles"
              @click="tecAbierta = tecAbierta === tec.id ? null : tec.id"
            >
              ⓘ
            </button>
            <div class="tooltip" role="tooltip">
              <p>{{ tec.descripcion }}</p>
              <p v-if="!yo.tecnologias[tec.id]">Costo: {{ tec.costo }} Datos</p>
            </div>
          </div>
        </div>
      </section>

      <section class="sub-zona zona-carpeta">
        <h3 class="eyebrow">Carpeta de Proyectos ({{ yo.carpeta_proyectos.length }}/3)</h3>
        <div class="carpeta">
          <RecetaCard v-for="(receta, i) in yo.carpeta_proyectos" :key="i" :receta="receta" />
          <p v-if="yo.carpeta_proyectos.length === 0" class="vacio">— vacía —</p>
        </div>
      </section>

      <section class="sub-zona zona-archivo">
        <h3 class="eyebrow">
          Archivo de Horneados ({{ yo.archivo_horneado_exitoso.length }}/5)
          <span
            class="variedad"
            :title="`Variedad de Recetas: ${variedad.distintas} receta(s) distinta(s) horneada(s) con éxito = +${variedad.puntos} PM al final. La próxima receta NUEVA suma +${variedad.proxima} PM; repetir una ya horneada no suma nada.`"
          >
            · <span class="dato">{{ variedad.distintas }}</span> tipos
            <span class="dato">+{{ variedad.puntos }}</span> PM
          </span>
        </h3>
        <ul class="archivo-lista">
          <li
            v-for="({ registro, colapso }, i) in registrosArchivo"
            :key="i"
            class="registro-horneado"
            :class="{ colapso }"
          >
            <span class="nombre-registro">
              <template v-if="colapso">⚠ </template>{{ registro.recipe.nombre }}
            </span>
            <span class="detalle-registro">
              {{ ETIQUETA_ZONA[registro.zona_resultado] }} ·
              <span class="dato">{{ registro.puntos_totales }}</span> pts<template
                v-if="registro.bono_sabor_aplicado"
              >
                (con Bono de Sabor)</template
              >
              · <span class="dato">{{ registro.monedas_obtenidos }}</span>₥
            </span>
          </li>
          <p v-if="registrosArchivo.length === 0" class="vacio">— todavía nada horneado —</p>
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.mi-tablero {
  border-left: 3px solid transparent;
  padding: var(--e3);
}

/* --- Cabecera ------------------------------------------------------------ */
.cabecera-tablero {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--e1) var(--e3);
  margin-bottom: var(--e3);
}

.cabecera-tablero h2 {
  display: flex;
  align-items: center;
  gap: var(--e1);
}

.punto-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.badge-contaminado {
  color: var(--riesgo);
  font-size: var(--t-micro);
  font-weight: 600;
  letter-spacing: 0.06em;
}

.marcador {
  display: flex;
  align-items: center;
  gap: var(--e1);
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.marcador strong {
  color: var(--tinta);
}

.proyeccion {
  cursor: help;
}

.pa {
  display: flex;
  align-items: center;
  gap: var(--e1);
  margin-left: auto;
}

.pa-pips {
  letter-spacing: 0.12em;
  font-size: var(--t-xs);
}

.pip {
  color: var(--borde-fuerte);
}

.pip.activo {
  color: var(--cobre);
}

/* --- Sub-zonas ----------------------------------------------------------- */
/* El tablero propio es ancho y bajo dentro de su region, asi que se reparte
   en columnas que envuelven, en vez de una sola pila muy alta. */
.zonas-tablero {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e3);
  align-items: flex-start;
}

.sub-zona {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  min-width: 0;
}

.zona-estado {
  flex: 1 1 17rem;
}
.zona-estaciones {
  flex: 2 1 26rem;
}
.zona-carpeta {
  flex: 1 1 18rem;
}
.variedad {
  color: var(--cobre);
  text-transform: none;
  letter-spacing: normal;
}

.zona-archivo {
  flex: 1 1 15rem;
}

.aviso-colapso {
  margin: 0;
  font-size: var(--t-micro);
  color: var(--riesgo);
  cursor: help;
}

/* --- Recursos ------------------------------------------------------------ */
.recursos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(5.5rem, 1fr));
  gap: var(--e1);
}

.recurso-tile {
  display: flex;
  align-items: center;
  gap: var(--e1);
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  padding: var(--e1);
  font-size: var(--t-xs);
}

.emoji {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--t-s);
}

.linea-desperdicio {
  margin: 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.linea-desperdicio.penaliza span:not(.dato) {
  color: var(--riesgo);
}

/* --- Mejoras ------------------------------------------------------------- */
.mejoras-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e1);
}

.mejora-slot {
  position: relative;
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--carta);
  border: 1px dashed var(--borde);
  border-radius: var(--r-control);
  padding: 2px var(--e2);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.mejora-slot.activa {
  border-style: solid;
  border-color: var(--cobre);
  color: var(--tinta);
}

.mejora-slot .boton-info {
  flex: 0 0 auto;
  background: none;
  border: none;
  color: inherit;
  font-size: var(--t-xs);
  line-height: 1;
  padding: 0 0 0 2px;
  opacity: 0.8;
}

.mejora-slot .boton-info:hover {
  opacity: 1;
}

.mejora-slot .tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + var(--e1));
  left: 50%;
  transform: translateX(-50%);
  width: 14rem;
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
  white-space: normal;
}

.mejora-slot .tooltip p {
  margin: 0 0 var(--e1);
}

.mejora-slot .tooltip p:last-child {
  margin-bottom: 0;
}

.mejora-slot:hover .tooltip,
.mejora-slot:focus-within .tooltip,
.mejora-slot.abierta .tooltip {
  visibility: visible;
  opacity: 1;
}

/* --- Estaciones y carpeta ------------------------------------------------ */
.estaciones {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--e2);
}

.carpeta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
}

.carpeta > :deep(.receta-card) {
  flex: 1 1 14rem;
}

.vacio {
  margin: 0;
  color: var(--tinta-tenue);
  font-style: italic;
  font-size: var(--t-xs);
}

/* --- Archivo ------------------------------------------------------------- */
.archivo-lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
}

.registro-horneado {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px var(--e2);
  font-size: var(--t-xs);
  padding: var(--e1) var(--e2);
  border: 1px solid var(--borde);
  border-left: 2px solid var(--vital);
  border-radius: var(--r-control);
}

.registro-horneado .nombre-registro {
  font-weight: 600;
}

.registro-horneado .detalle-registro {
  color: var(--tinta-tenue);
  font-size: var(--t-micro);
}

.registro-horneado.colapso {
  border-color: var(--riesgo);
  border-left-color: var(--riesgo);
}

.registro-horneado.colapso .nombre-registro,
.registro-horneado.colapso .detalle-registro {
  color: var(--riesgo);
}

@media (max-width: 720px) {
  .estaciones {
    grid-template-columns: 1fr;
  }
}
</style>
