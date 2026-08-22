<script setup lang="ts">
import { computed, ref } from 'vue'
import { pasar, store } from '../store'
import ModalA from './acciones/ModalA.vue'
import ModalB from './acciones/ModalB.vue'
import ModalC from './acciones/ModalC.vue'
import ModalD from './acciones/ModalD.vue'
import ModalE from './acciones/ModalE.vue'
import ModalF from './acciones/ModalF.vue'
import ModalG from './acciones/ModalG.vue'
import ModalSimposio from './acciones/ModalSimposio.vue'
import ModalConfirmacion from './acciones/ModalConfirmacion.vue'
import { descripcionesAcciones, type IdAccion } from '../data/descripcionesAcciones'

const BOTONES: { id: IdAccion; etiqueta: string; costo: string }[] = [
  { id: 'B', etiqueta: 'Iniciar Receta', costo: '1 PA' },
  { id: 'C', etiqueta: 'Adquirir Insumos', costo: '1 PA' },
  { id: 'D', etiqueta: 'Implementar Mejora', costo: '1 PA' },
  { id: 'E', etiqueta: 'Pliegues', costo: '1 PA' },
  { id: 'F', etiqueta: 'Hornear', costo: '1 PA' },
  { id: 'G', etiqueta: 'Investigar Protocolo', costo: '1 PA' },
  { id: 'simposio', etiqueta: 'Simposio Técnico', costo: '1 PA' },
  { id: 'H', etiqueta: 'Re-cultivo Manual', costo: '1 PA' },
  { id: 'I', etiqueta: 'Inóculo Emergencia', costo: '1 PA' },
  { id: 'A', etiqueta: 'Alimentar Cultivo', costo: '0 PA' },
  { id: 'horas_extras', etiqueta: 'Horas Extras', costo: '0 PA' },
]

const disponibilidad = computed(() => store.estado!.acciones_disponibles[store.sesion!.playerIndex])

function estado(id: IdAccion) {
  return disponibilidad.value.find((a) => a.id === id) ?? { habilitada: false, motivo: '' }
}

const modalAbierto = ref<IdAccion | null>(null)
function abrir(id: IdAccion) {
  if (!estado(id).habilitada) return
  modalAbierto.value = id
}
function cerrar() {
  modalAbierto.value = null
}

const pasando = ref(false)
async function onPasar() {
  pasando.value = true
  try {
    await pasar()
  } finally {
    pasando.value = false
  }
}
</script>

<template>
  <section class="barra-acciones">
    <div class="grid-botones">
      <div v-for="b in BOTONES" :key="b.id" class="envoltorio-boton">
        <button :disabled="!estado(b.id).habilitada" :title="estado(b.id).motivo" @click="abrir(b.id)">
          {{ b.etiqueta }} <span class="costo">[{{ b.costo }}]</span>
        </button>
        <div class="tooltip" role="tooltip">
          <p>{{ descripcionesAcciones[b.id] }}</p>
          <p v-if="!estado(b.id).habilitada && estado(b.id).motivo" class="tooltip-motivo">
            ⚠ {{ estado(b.id).motivo }}
          </p>
        </div>
      </div>
    </div>

    <button class="pasar" :disabled="pasando" @click="onPasar">Pasar turno (sin más acciones)</button>

    <ModalA v-if="modalAbierto === 'A'" @cerrar="cerrar" />
    <ModalB v-if="modalAbierto === 'B'" @cerrar="cerrar" />
    <ModalC v-if="modalAbierto === 'C'" @cerrar="cerrar" />
    <ModalD v-if="modalAbierto === 'D'" @cerrar="cerrar" />
    <ModalE v-if="modalAbierto === 'E'" @cerrar="cerrar" />
    <ModalF v-if="modalAbierto === 'F'" @cerrar="cerrar" />
    <ModalG v-if="modalAbierto === 'G'" @cerrar="cerrar" />
    <ModalSimposio v-if="modalAbierto === 'simposio'" @cerrar="cerrar" />
    <ModalConfirmacion
      v-if="modalAbierto === 'H'"
      titulo="Re-cultivo Manual (1 PA)"
      :descripcion="descripcionesAcciones.H"
      accion="H"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'I'"
      titulo="Inóculo de Emergencia (1 PA)"
      :descripcion="descripcionesAcciones.I"
      accion="I"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'horas_extras'"
      titulo="Horas Extras (0 PA)"
      :descripcion="descripcionesAcciones.horas_extras"
      accion="horas_extras"
      @cerrar="cerrar"
    />
  </section>
</template>

<style scoped>
.grid-botones {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

.envoltorio-boton {
  position: relative;
}

.envoltorio-boton button {
  width: 100%;
  padding: 0.6rem 0.5rem 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-borde);
  border-top: 3px solid var(--color-acento);
  background: var(--color-fondo);
  color: var(--color-texto);
  font-size: 0.82rem;
  text-align: center;
}

.envoltorio-boton button:disabled {
  border-top-color: var(--color-borde);
}

.tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: calc(100% + 0.4rem);
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  max-width: 60vw;
  background: var(--color-panel);
  border: 1px solid var(--color-borde);
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  font-size: 0.78rem;
  line-height: 1.35;
  color: var(--color-texto);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  z-index: 30;
  pointer-events: none;
  transition: opacity 0.1s ease;
}

.tooltip p {
  margin: 0;
}

.tooltip-motivo {
  margin-top: 0.4rem !important;
  color: var(--color-mal);
}

.envoltorio-boton:hover .tooltip,
.envoltorio-boton:focus-within .tooltip {
  visibility: visible;
  opacity: 1;
}

.costo {
  color: var(--color-texto-tenue);
  font-size: 0.75rem;
  display: block;
}

.pasar {
  width: 100%;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: transparent;
  color: var(--color-texto-tenue);
}
</style>
