<script setup lang="ts">
import { computed, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import {
  DATOS_SIMPOSIO,
  MAX_DATOS_PONENCIA,
  PRECIO_DATO_SIMPOSIO,
  RENTA_POR_GRADO,
} from '../../data/datosSimposio'
import ModalShell from '../ModalShell.vue'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const archivo = computed(() => yo.value.archivo_horneado_exitoso)

/** Los dos modos comparten espacio, PA y la puerta del archivo; sólo cambia
 * cómo se paga. La exclusividad entre ellos no necesita lógica aquí: el
 * espacio de acción es uno por día. */
const modo = ref<'sacrificar' | 'ponencia'>('sacrificar')
const indice = ref(0)
const datos = ref(1)
const enviando = ref(false)
const error = ref<string | null>(null)

const coste = computed(() => datos.value * PRECIO_DATO_SIMPOSIO)
const puedePagar = computed(() => yo.value.monedas >= coste.value)

/** Lo que cuesta cada fila, calculado por registro para que el jugador compare
 * antes de elegir. Los puntos y la renta salen del registro; el escalón de
 * Variedad hay que derivarlo porque sólo se pierde si era la ÚLTIMA copia de
 * esa receta en el archivo. */
const opciones = computed(() =>
  archivo.value.map((record, i) => {
    const grado = record.recipe.grado
    const otrasCopias = archivo.value.some((r, j) => j !== i && r.recipe.id === record.recipe.id)
    return {
      i,
      nombre: record.recipe.nombre,
      grado,
      datos: DATOS_SIMPOSIO[grado],
      puntos: record.puntos_totales,
      renta: RENTA_POR_GRADO[grado],
      pierdeVariedad: !otrasCopias,
    }
  }),
)

const elegida = computed(() => opciones.value.find((o) => o.i === indice.value) ?? null)

function sumar() {
  if (datos.value < MAX_DATOS_PONENCIA) datos.value += 1
}

function restar() {
  if (datos.value > 1) datos.value -= 1
}

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    // Parámetros discriminados por `modo`, como el `recurso` del Pedido de
    // Urgencia: el parámetro del modo contrario no viaja nunca.
    await despacharAccion(
      'simposio',
      modo.value === 'ponencia'
        ? { modo: 'ponencia', datos: datos.value }
        : { modo: 'sacrificar', indice: indice.value },
    )
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo completar el Simposio Técnico.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <ModalShell titulo="Simposio Técnico (1 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Presentas uno de tus panes en el simposio. Eliges un modo por visita:
      <strong>sacrificarlo</strong> a cambio de Datos según su grado, o pagar una
      <strong>ponencia</strong> en Monedas sin tocar el Archivo.
    </p>

    <p v-if="archivo.length === 0" class="aviso-vacio">
      Todavía no tienes ningún horneado exitoso en el Archivo. El Simposio exige uno,
      sea para sacrificarlo o para presentar una ponencia sobre él.
    </p>

    <template v-else>
      <div class="opciones-radio">
        <label
          ><input type="radio" value="sacrificar" v-model="modo" /> Sacrificar un pan
          <span class="dato">+1 a +3 Datos</span></label
        >
        <label
          ><input type="radio" value="ponencia" v-model="modo" /> Presentar una ponencia
          <span class="dato">{{ PRECIO_DATO_SIMPOSIO }} Monedas</span> por Dato</label
        >
      </div>

      <template v-if="modo === 'sacrificar'">
        <label class="campo">
          Horneado a sacrificar
          <select v-model.number="indice">
            <option v-for="o in opciones" :key="o.i" :value="o.i">
              {{ o.nombre }} ({{ o.grado }}) → +{{ o.datos }} Datos
            </option>
          </select>
        </label>

        <div v-if="elegida" class="balance">
          <div class="ganas">
            <span class="eyebrow">Ganas</span>
            <p class="dato">+{{ elegida.datos }} Datos de Investigación</p>
          </div>
          <div class="pierdes">
            <span class="eyebrow">Pierdes</span>
            <ul>
              <li class="dato">−{{ elegida.puntos }} Puntos de Maestría</li>
              <li class="dato">−{{ elegida.renta }} Monedas cada noche</li>
              <li>Un paso del Archivo ({{ archivo.length }}/5 → {{ archivo.length - 1 }}/5)</li>
              <li v-if="elegida.pierdeVariedad" class="grave">
                Un escalón de Variedad de Recetas ({{ yo.recetas_distintas_horneadas }} →
                {{ yo.recetas_distintas_horneadas - 1 }} tipos)
              </li>
            </ul>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="campo-ponencia">
          <span class="eyebrow">Datos a comprar</span>
          <div class="stepper">
            <button type="button" :disabled="datos <= 1" @click="restar">−</button>
            <span class="dato">{{ datos }}</span>
            <button type="button" :disabled="datos >= MAX_DATOS_PONENCIA" @click="sumar">+</button>
          </div>
        </div>

        <p class="info-linea" :class="{ falta: !puedePagar }">
          Cuesta {{ coste }} Monedas · tienes {{ yo.monedas }}.
        </p>

        <p class="intacto">
          Ganas <span class="dato">+{{ datos }} Datos</span> · el Archivo no se toca: conservas
          sus puntos, su renta y su paso hacia el 5/5.
        </p>
      </template>
    </template>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || archivo.length === 0 || (modo === 'ponencia' && !puedePagar)"
        @click="confirmar"
      >
        {{ modo === 'ponencia' ? 'Comprar Datos' : 'Sacrificar' }}
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.aviso-vacio {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  padding: var(--e3) 0;
}

.falta {
  color: var(--riesgo);
}

.campo-ponencia {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--e3);
  margin-top: var(--e3);
}

.stepper {
  display: flex;
  align-items: center;
  gap: var(--e2);
}

.stepper button {
  width: 1.75rem;
  height: 1.75rem;
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-control);
  background: var(--zona);
  color: var(--tinta);
  font-size: var(--t-s);
  line-height: 1;
  cursor: pointer;
}

.stepper button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.intacto {
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  margin: var(--e2) 0 0;
}

.intacto .dato {
  color: var(--vital);
}

.balance {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--e3);
  margin-top: var(--e3);
  padding: var(--e3);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--zona);
}

.ganas p {
  color: var(--vital);
  margin: var(--e1) 0 0;
}

.pierdes ul {
  list-style: none;
  margin: var(--e1) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
}

.pierdes li {
  color: var(--riesgo);
  font-size: var(--t-s);
}

.pierdes li.grave {
  font-weight: 600;
}

@media (max-width: 720px) {
  .balance {
    grid-template-columns: 1fr;
  }
}
</style>
