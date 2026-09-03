<script setup lang="ts">
// Estasis Biológica: el interruptor de la Criopreservación. A diferencia de las
// otras gratuitas no gasta nada, así que el modal no confirma un coste -- enseña
// las DOS Vitalidades de esta noche y deja elegir. Ninguna de las dos cifras se
// calcula aquí: `vitalidad_prevista` y `vitalidad_prevista_alterna` llegan del
// servidor (server/views.py), porque el desgaste con su -2 de Aletargamiento es
// una regla de CLIMATE_LOGIC.md y duplicarla en TypeScript sería deriva segura.
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const suspendida = computed(() => yo.value.estasis_suspendida)

/** Vitalidad de esta noche con la Estasis ACTIVA (el cultivo ignora el desgaste). */
const conEstasis = computed(() =>
  suspendida.value ? yo.value.vitalidad_prevista_alterna : yo.value.vitalidad_prevista,
)
/** Vitalidad de esta noche con la Estasis SUSPENDIDA (desgaste normal). */
const sinEstasis = computed(() =>
  suspendida.value ? yo.value.vitalidad_prevista : yo.value.vitalidad_prevista_alterna,
)

/** Suspender llevaría el cultivo a 0: contaminación (-3 PM y Acción B bloqueada). */
const peligro = computed(() => sinEstasis.value === 0 && !yo.value.en_estado_contaminacion)

const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    await despacharAccion('estasis', { suspender: !suspendida.value })
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo ajustar la Estasis.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Estasis Biológica (0 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Tu Criopreservación mantiene el cultivo en estasis: ignora el desgaste metabólico cada noche.
      Aquí decides si lo dejas desgastarse <strong>esta noche</strong>, para bajar la Vitalidad a
      voluntad. Importa porque la Acción B sella el <strong>Dado de Inóculo</strong> con tu Vitalidad
      del día: cuanto más alta, más avanzan tus masas cada noche, y las recetas Avanzadas tienen la
      zona óptima más estrecha del catálogo.
    </p>

    <div class="opciones">
      <div class="opcion" :class="{ vigente: !suspendida }">
        <span class="eyebrow">Estasis activa</span>
        <span class="dato cifra">{{ yo.vitalidad }} → {{ conEstasis }}</span>
        <span class="pie">Vitalidad intacta</span>
      </div>
      <div class="opcion" :class="{ vigente: suspendida, riesgo: peligro }">
        <span class="eyebrow">Estasis suspendida</span>
        <span class="dato cifra">{{ yo.vitalidad }} → {{ sinEstasis }}</span>
        <span class="pie">Desgaste normal de esta noche</span>
      </div>
    </div>

    <p v-if="peligro" class="aviso-riesgo">
      ⚠ Suspender la Estasis esta noche te dejaría en Vitalidad 0: entrarías en Contaminación
      (−3 Puntos de Maestría y no podrás iniciar recetas hasta ejecutar un Protocolo de Emergencia).
    </p>

    <p class="info-nota">
      Dura una sola noche: la Fase III reactiva la Estasis por sí sola. Puedes cambiar de idea las
      veces que quieras mientras sea tu turno — no cuesta PA ni ocupa espacio de acción.
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button class="confirmar" :disabled="enviando" @click="confirmar">
        {{ suspendida ? 'Reactivar la Estasis' : 'Suspender esta noche' }}
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.opciones {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--e2);
  margin: var(--e3) 0;
}

.opcion {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  padding: var(--e2);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--zona);
}

.opcion.vigente {
  border-color: var(--cobre);
  box-shadow: inset 0 0 0 1px var(--cobre);
}

.opcion.riesgo .cifra {
  color: var(--riesgo);
}

.cifra {
  font-size: var(--t-xl);
}

.pie {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.aviso-riesgo {
  margin: 0 0 var(--e3);
  padding: var(--e2);
  border: 1px solid var(--riesgo);
  border-radius: var(--r-control);
  background: var(--lavado-riesgo);
  font-size: var(--t-micro);
  color: var(--riesgo);
}

.info-nota {
  margin: 0;
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}
</style>
