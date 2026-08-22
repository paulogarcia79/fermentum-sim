<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import EstacionCard from './EstacionCard.vue'
import RecetaDetalle from './RecetaDetalle.vue'

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
</script>

<template>
  <section class="panel mi-tablero">
    <div class="cabecera-tablero">
      <h2>{{ yo.nombre }} <span v-if="yo.en_estado_contaminacion" class="badge-contaminado">◉ CONTAMINADO</span></h2>
      <div class="pa-pips">
        <span v-for="i in 3" :key="i" class="pip" :class="{ activo: i <= yo.puntos_accion }">●</span>
      </div>
    </div>

    <div class="medidores">
      <div class="medidor">
        <span class="etiqueta">Vitalidad</span>
        <div class="barra"><div class="relleno vitalidad" :style="{ width: (yo.vitalidad / 6) * 100 + '%' }" /></div>
        <span class="valor">{{ yo.vitalidad }}/6</span>
      </div>
      <div class="medidor">
        <span class="etiqueta">Acidez</span>
        <div class="barra"><div class="relleno acidez" :style="{ width: (yo.acidez / 6) * 100 + '%' }" /></div>
        <span class="valor">{{ yo.acidez }}/6</span>
      </div>
    </div>

    <div class="reservas">
      <span>Harina — Blanca: {{ yo.reserva_harina.Blanca }}% Centeno: {{ yo.reserva_harina.Centeno }}% Integral: {{ yo.reserva_harina.Integral }}%</span>
      <span>Agua: {{ yo.reserva_agua }} tokens</span>
      <span>Datos: {{ yo.datos_investigacion }}</span>
      <span>Dados de inóculo: {{ yo.dados_inoculo }}</span>
    </div>

    <div class="tecnologias" v-if="yo.tecnologias.incubadora || yo.tecnologias.camara_b || yo.tecnologias.modulo_analitico">
      <span v-if="yo.tecnologias.incubadora" class="tech">🌡 Incubadora</span>
      <span v-if="yo.tecnologias.camara_b" class="tech">🚪 Cámara B</span>
      <span v-if="yo.tecnologias.modulo_analitico" class="tech">📊 Módulo Analítico</span>
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
    <ul class="carpeta">
      <li v-for="(receta, i) in yo.carpeta_proyectos" :key="i">
        {{ receta.nombre }} <span class="detalle">({{ receta.grado }})</span>
        <RecetaDetalle :receta="receta" />
      </li>
      <li v-if="yo.carpeta_proyectos.length === 0" class="vacio">— vacía —</li>
    </ul>

    <div class="archivo">
      Archivo: {{ yo.archivo_horneado_exitoso.length }} exitosos · {{ yo.archivo_colapsos.length }} colapsos
    </div>
  </section>
</template>

<style scoped>
.cabecera-tablero {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cabecera-tablero h2 {
  margin: 0;
  font-size: 1.15rem;
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

.barra {
  height: 8px;
  background: var(--color-fondo);
  border-radius: 4px;
  overflow: hidden;
}

.relleno {
  height: 100%;
}

.relleno.vitalidad {
  background: var(--color-bien);
}

.relleno.acidez {
  background: #7fa8d9;
}

.reservas {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.8rem;
  color: var(--color-texto-tenue);
  margin-bottom: 0.5rem;
}

.tecnologias {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.tech {
  background: var(--color-fondo);
  border-radius: 4px;
  padding: 0.15rem 0.4rem;
  font-size: 0.75rem;
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
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.carpeta .detalle {
  color: var(--color-texto-tenue);
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
