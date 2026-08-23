<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import EstacionCard from './EstacionCard.vue'
import RecetaCard from './RecetaCard.vue'
import IconoHarina from './IconoHarina.vue'
import IconoAgua from './IconoAgua.vue'
import IconoDatos from './IconoDatos.vue'
import IconoMonedas from './IconoMonedas.vue'
import { hexDeColor } from '../data/coloresJugador'

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const colorHex = computed(() => hexDeColor(yo.value.color))
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

    <div class="medidores">
      <div class="medidor">
        <span class="etiqueta">Vitalidad</span>
        <div class="pips-track">
          <span v-for="i in 6" :key="i" class="pip-track vitalidad" :class="{ activo: i <= yo.vitalidad }">●</span>
        </div>
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
      <div class="recurso-tile" title="Harina Blanca">
        <span class="icono-recurso"><IconoHarina tipo="Blanca" /></span>{{ yo.reserva_harina.Blanca }}%
      </div>
      <div class="recurso-tile" title="Harina Centeno">
        <span class="icono-recurso"><IconoHarina tipo="Centeno" /></span>{{ yo.reserva_harina.Centeno }}%
      </div>
      <div class="recurso-tile" title="Harina Integral">
        <span class="icono-recurso"><IconoHarina tipo="Integral" /></span>{{ yo.reserva_harina.Integral }}%
      </div>
      <div class="recurso-tile" title="Agua">
        <span class="icono-recurso"><IconoAgua /></span>{{ yo.reserva_agua }}
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

    <div class="sub-titulo">Mejoras</div>
    <div class="mejoras-grid">
      <div class="mejora-slot" :class="{ activa: yo.tecnologias.incubadora }">🌡 Incubadora</div>
      <div class="mejora-slot" :class="{ activa: yo.tecnologias.camara_b }">🚪 Cámara B</div>
      <div class="mejora-slot" :class="{ activa: yo.tecnologias.modulo_analitico }">📊 Módulo Analítico</div>
      <div class="mejora-slot" :class="{ activa: yo.tecnologias.criopreservacion }">❄ Criopreservación</div>
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
      <RecetaCard v-for="(receta, i) in yo.carpeta_proyectos" :key="i" :receta="receta" compacta />
      <p v-if="yo.carpeta_proyectos.length === 0" class="vacio">— vacía —</p>
    </div>

    <div class="archivo">
      Archivo: {{ yo.archivo_horneado_exitoso.length }} exitosos · {{ yo.archivo_colapsos.length }} colapsos
    </div>
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
  background: var(--color-fondo);
  border: 1px dashed var(--color-borde);
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-texto-tenue);
  opacity: 0.6;
}

.mejora-slot.activa {
  border-style: solid;
  border-color: var(--color-acento);
  color: var(--color-texto);
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
  flex: 1 1 200px;
  max-width: 260px;
}

.vacio {
  color: var(--color-texto-tenue);
  font-style: italic;
}

.archivo {
  margin-top: 0.6rem;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
}
</style>
