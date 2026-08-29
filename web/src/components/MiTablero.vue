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

const ETIQUETA_ZONA: Record<HorneadoRecord['zona_resultado'], string> = {
  optima: 'Zona Óptima',
  baja: 'Zona Baja',
  colapso: 'Colapso',
}
</script>

<template>
  <section class="panel mi-tablero" :style="{ borderLeftColor: colorHex }">
    <div class="cabecera-tablero">
      <h2>
        <span class="punto-color" :style="{ background: colorHex }" />
        {{ yo.nombre }}
        <span v-if="yo.en_estado_contaminacion" class="badge-contaminado">◉ CONTAMINADO</span>
      </h2>
      <div class="pa-pips">
        <span v-for="i in 3" :key="i" class="pip" :class="{ activo: i <= yo.puntos_accion }">●</span>
      </div>
    </div>

    <div class="marcador">
      <span class="icono-marcador"><IconoMaestria /></span>
      <span class="puntos-horneados">{{ yo.puntos_horneados }} pts horneados</span>
      <span
        class="proyeccion"
        title="Puntuación si la partida terminara ahora: horneados + madurez del cultivo + conversión de riqueza − penalizaciones (desperdicio, contaminación). Cambia también sin hornear."
      >
        · proyección final: {{ yo.puntos_maestria_final }} PM
      </span>
    </div>

    <div class="medidores">
      <div class="medidor">
        <span class="etiqueta">Vitalidad</span>
        <div class="pips-track">
          <span
            v-for="i in 6"
            :key="i"
            class="pip-track vitalidad"
            :class="{ activo: i <= yo.vitalidad, peligro: avisoColapso }"
            >●</span
          >
        </div>
        <span
          v-if="avisoColapso"
          class="badge-colapso"
          :title="`Vitalidad ${yo.vitalidad} → ${yo.vitalidad_prevista} esta noche: entrarás en Contaminación (-3 Puntos de Maestría y no podrás Iniciar Receta). Alimenta el cultivo (Acción A, 0 PA) antes de terminar el día.`"
          >⚠</span
        >
      </div>
      <div class="medidor">
        <span class="etiqueta">Acidez</span>
        <div class="pips-track">
          <span v-for="i in 6" :key="i" class="pip-track acidez" :class="{ activo: i <= yo.acidez }">●</span>
        </div>
      </div>
    </div>

    <div class="sub-titulo">Recursos</div>
    <div class="recursos-grid">
      <div
        v-for="tipo in TIPOS_HARINA"
        :key="tipo"
        class="recurso-tile"
        :title="`Harina ${tipo}: ${fmtTokensHarina(yo.reserva_harina[tipo])} del 10% = ${yo.reserva_harina[tipo]}%`"
      >
        <span class="icono-recurso"><IconoHarina :tipo="tipo" /></span>{{ tokensHarina(yo.reserva_harina[tipo]) }}
        <span class="unidad-secundaria">({{ yo.reserva_harina[tipo] }}%)</span>
      </div>
      <div
        class="recurso-tile"
        :title="`Agua: ${fmtTokensAgua(yo.reserva_agua)} del 5% = ${pctAgua(yo.reserva_agua)}% de hidratación`"
      >
        <span class="icono-recurso"><IconoAgua /></span>{{ yo.reserva_agua }}
        <span class="unidad-secundaria">({{ pctAgua(yo.reserva_agua) }}%)</span>
      </div>
      <div class="recurso-tile" title="Datos de Investigación">
        <span class="icono-recurso"><IconoDatos /></span>{{ yo.datos_investigacion }}
      </div>
      <div class="recurso-tile" title="Monedas">
        <span class="icono-recurso"><IconoMonedas /></span>{{ yo.monedas }}
      </div>
      <div class="recurso-tile" title="Dados de inóculo en reserva">
        <span class="icono-recurso emoji">🎲</span>{{ yo.dados_inoculo }}
      </div>
    </div>
    <p
      class="linea-desperdicio"
      :class="{ penaliza: penalizacionDesperdicio < 0 }"
      title="Al final de la partida pierdes 1 Punto de Maestría por cada 3 tokens de insumo sin usar. Un token de harina (10%) y uno de agua (5%) cuentan igual aquí."
    >
      {{ yo.total_tokens_recursos }} tokens sin usar
      <span v-if="penalizacionDesperdicio < 0">→ {{ penalizacionDesperdicio }} PM al final</span>
      <span v-else>→ sin penalización todavía</span>
    </p>

    <div class="sub-titulo">Mejoras</div>
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

    <div class="sub-titulo">Estaciones de fermentación</div>
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

    <div class="sub-titulo">Carpeta de Proyectos ({{ yo.carpeta_proyectos.length }}/3)</div>
    <div class="carpeta">
      <RecetaCard v-for="(receta, i) in yo.carpeta_proyectos" :key="i" :receta="receta" />
      <p v-if="yo.carpeta_proyectos.length === 0" class="vacio">— vacía —</p>
    </div>

    <div class="sub-titulo">
      Archivo de Horneados ({{ yo.archivo_horneado_exitoso.length }}/5)
    </div>
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
          {{ registro.puntos_totales }} pts<template v-if="registro.bono_sabor_aplicado">
            (con Bono de Sabor)</template
          >
          · {{ registro.monedas_obtenidos }}₥
        </span>
      </li>
      <p v-if="registrosArchivo.length === 0" class="vacio">— todavía nada horneado —</p>
    </ul>
  </section>
</template>

<style scoped>
.mi-tablero {
  border-left: 4px solid transparent;
}

.cabecera-tablero {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cabecera-tablero h2 {
  margin: 0;
  font-size: 1.15rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.punto-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.badge-contaminado {
  color: var(--color-mal);
  font-size: 0.75rem;
  font-weight: 600;
}

.pa-pips {
  letter-spacing: 0.15em;
}

.pip {
  color: var(--color-borde);
}

.pip.activo {
  color: var(--color-acento);
}

.medidores {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 0.75rem 0;
}

.medidor {
  display: grid;
  grid-template-columns: 70px 1fr 40px;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.medidor .etiqueta {
  color: var(--color-texto-tenue);
}

.pips-track {
  letter-spacing: 0.1em;
  font-size: 0.75rem;
}

.pip-track {
  color: var(--color-borde);
}

.pip-track.activo.vitalidad {
  color: var(--color-bien);
}

.pip-track.activo.acidez {
  color: #7fa8d9;
}

/* Aviso de colapso: la Vitalidad se pinta en rojo en vez de verde para que
   el riesgo se vea sin tener que leer nada. Va despues de .activo.vitalidad
   a proposito -- misma especificidad, gana la ultima regla. */
.pip-track.activo.peligro {
  color: var(--color-mal);
}

.badge-colapso {
  justify-self: end;
  color: var(--color-mal);
  font-size: 0.9rem;
  cursor: help;
}

.linea-desperdicio {
  margin: 0.35rem 0 0;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
}

.linea-desperdicio.penaliza span {
  color: var(--color-mal);
}

.recursos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.recurso-tile {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  background: var(--color-fondo);
  border-radius: 4px;
  padding: 0.3rem 0.4rem;
  font-size: 0.8rem;
}

.icono-recurso {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.icono-recurso.emoji {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
}

.mejoras-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.mejora-slot {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.15rem;
  background: var(--color-fondo);
  border: 1px dashed var(--color-borde);
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
}

.mejora-slot.activa {
  border-style: solid;
  border-color: var(--color-acento);
  color: var(--color-texto);
}

.mejora-slot .boton-info {
  flex: 0 0 auto;
  background: none;
  border: none;
  color: inherit;
  font-size: 0.85rem;
  line-height: 1;
  padding: 0 0 0 0.1rem;
  cursor: pointer;
  opacity: 0.8;
}

.mejora-slot .boton-info:hover {
  opacity: 1;
}

.mejora-slot .tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + 0.4rem);
  left: 50%;
  transform: translateX(-50%);
  width: 220px;
  max-width: 70vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.45rem 0.55rem;
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--color-texto);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  z-index: 30;
  transition: opacity 0.1s ease;
  white-space: normal;
}

.mejora-slot .tooltip p {
  margin: 0 0 0.35rem;
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

.sub-titulo {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--color-texto-tenue);
  margin: 0.75rem 0 0.35rem;
}

.estaciones {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

@media (max-width: 600px) {
  .estaciones {
    grid-template-columns: 1fr;
  }
}

.carpeta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.carpeta > :deep(.receta-card) {
  flex: 1 1 240px;
  max-width: 300px;
}

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}

/* Marcador de puntos en vivo, bajo la cabecera. */
.marcador {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.icono-marcador {
  width: 20px;
  height: 20px;
  display: inline-flex;
}

.icono-marcador :deep(svg) {
  width: 100%;
  height: 100%;
}

.puntos-horneados {
  font-weight: 700;
}

.proyeccion {
  color: var(--color-texto-tenue);
  font-size: 0.78rem;
  cursor: help;
}

/* Archivo de horneados: filas compactas, colapsos en rojo al final. */
.archivo-lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.registro-horneado {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.15rem 0.5rem;
  font-size: 0.8rem;
  padding: 0.3rem 0.45rem;
  border: 1px solid var(--color-borde);
  border-radius: 5px;
}

.registro-horneado .nombre-registro {
  font-weight: 600;
}

.registro-horneado .detalle-registro {
  color: var(--color-texto-tenue);
  font-size: 0.74rem;
}

.registro-horneado.colapso {
  border-color: var(--color-mal);
}

.registro-horneado.colapso .nombre-registro,
.registro-horneado.colapso .detalle-registro {
  color: var(--color-mal);
}
</style>
