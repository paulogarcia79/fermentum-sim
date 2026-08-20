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

type IdAccion = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'simposio' | 'H' | 'I' | 'horas_extras'

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
  <section class="panel barra-acciones">
    <h3>Acciones disponibles</h3>
    <div class="grid-botones">
      <button
        v-for="b in BOTONES"
        :key="b.id"
        :disabled="!estado(b.id).habilitada"
        :title="estado(b.id).motivo"
        @click="abrir(b.id)"
      >
        {{ b.etiqueta }} <span class="costo">[{{ b.costo }}]</span>
      </button>
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
      descripcion="Costo: 2 Harina (10% c/u de cualquier tipo) + 2 Agua. Limpia la Contaminación y fija Vitalidad=1, Acidez=1."
      accion="H"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'I'"
      titulo="Inóculo de Emergencia (1 PA)"
      descripcion="Costo: 2 Datos de Investigación. Limpia la Contaminación y fija Vitalidad=2, Acidez=2."
      accion="I"
      @cerrar="cerrar"
    />
    <ModalConfirmacion
      v-if="modalAbierto === 'horas_extras'"
      titulo="Horas Extras (0 PA)"
      descripcion="Costo: 1 Dato de Investigación. Otorga +1 Punto de Acción inmediato. Una vez por día."
      accion="horas_extras"
      @cerrar="cerrar"
    />
  </section>
</template>

<style scoped>
.barra-acciones h3 {
  margin-top: 0;
}

.grid-botones {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.grid-botones button {
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-borde);
  background: var(--color-fondo);
  color: var(--color-texto);
  font-size: 0.85rem;
  text-align: left;
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
