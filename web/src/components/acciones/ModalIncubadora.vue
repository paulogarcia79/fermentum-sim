<script setup lang="ts">
// Incubadora: el dial de avance, masa por masa y noche a noche. Como la Estasis
// Biologica, no gasta nada -- asi que el modal no confirma un coste, sino que
// ensena DONDE va a caer cada masa esta noche y deja mover el dial hasta que la
// proyeccion guste.
//
// La proyeccion no se calcula aqui: `data/proyeccionMasa.ts` la comparte con
// `EstacionCard.vue`, que dibuja el mismo corchete discontinuo en el tablero.
// Dos copias podrian discrepar, y entonces el jugador estaria eligiendo contra
// una cifra que su propio tablero desmiente.
import { computed, reactive, ref } from 'vue'
import { despacharAccion, store } from '../../store'
import ModalShell from '../ModalShell.vue'
import PistaMedida from '../PistaMedida.vue'
import { zonasDe } from '../../data/zonasReceta'
import {
  TRACK_MAX,
  bandasDe,
  posicionProyectada,
  tonoProyectado,
} from '../../data/proyeccionMasa'

const emit = defineEmits<{ cerrar: [] }>()

const yo = computed(() => store.estado!.players[store.sesion!.playerIndex])
const temperatura = computed(() => store.estado!.environment.temperatura_actual)

/** Estaciones con masa, con su indice real: el dial se manda por slot_index. */
const masas = computed(() =>
  yo.value.estaciones_fermentacion
    .map((slot, indice) => ({ slot, indice }))
    .filter((e): e is { slot: NonNullable<typeof e.slot>; indice: number } => e.slot !== null),
)

// Valores que el jugador esta considerando, sembrados con lo que ya hay puesto.
// Se guardan aparte del estado para que la proyeccion se mueva con el dial antes
// de confirmar; al enviar, solo viajan las masas cuyo valor haya cambiado.
const elegido = reactive<Record<number, number>>(
  Object.fromEntries(masas.value.map((m) => [m.indice, m.slot.modificador_incubadora])),
)

function proyeccion(indice: number) {
  const masa = masas.value.find((m) => m.indice === indice)!
  const zonas = zonasDe(masa.slot.recipe)
  const posicion = posicionProyectada(masa.slot, temperatura.value, elegido[indice] ?? 0)
  return {
    zonas,
    posicion,
    bandas: bandasDe(zonas),
    tono: tonoProyectado(zonas, posicion),
    colapsa: posicion >= zonas.colapso[0],
  }
}

const algunColapso = computed(() => masas.value.some((m) => proyeccion(m.indice).colapsa))
const hayCambios = computed(() =>
  masas.value.some((m) => elegido[m.indice] !== m.slot.modificador_incubadora),
)

const enviando = ref(false)
const error = ref<string | null>(null)

async function confirmar() {
  error.value = null
  enviando.value = true
  try {
    // Una llamada por masa cambiada. Son acciones gratuitas y ninguna cierra la
    // visita, asi que van en secuencia sin riesgo de perder el turno a medias.
    for (const masa of masas.value) {
      if (elegido[masa.indice] !== masa.slot.modificador_incubadora) {
        await despacharAccion('incubadora', {
          slot_index: masa.indice,
          modificador: elegido[masa.indice],
        })
      }
    }
    emit('cerrar')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo ajustar la Incubadora.'
  } finally {
    enviando.value = false
  }
}

const OPCIONES = [
  { valor: -1, etiqueta: '−1', pie: 'frena' },
  { valor: 0, etiqueta: '0', pie: 'sin ajuste' },
  { valor: 1, etiqueta: '+1', pie: 'acelera' },
]
</script>

<template>
  <ModalShell titulo="Incubadora (0 PA)" :error="error" @cerrar="emit('cerrar')">
    <p class="info-linea">
      Ajusta la temperatura local de <strong>cada masa</strong> para
      <strong>esta noche</strong>: −1 la frena una casilla, +1 la acelera una. El corchete
      discontinuo enseña dónde caerá tras la Fase III.
    </p>

    <div v-if="masas.length === 0" class="vacio">
      No tienes ninguna masa fermentando. Inicia una receta (Acción B) para poder ajustarla.
    </div>

    <div v-else class="masas">
      <div v-for="masa in masas" :key="masa.indice" class="masa">
        <div class="cabecera">
          <span class="eyebrow">Est-{{ (masa.indice + 1).toString().padStart(2, '0') }}</span>
          <span class="nombre">{{ masa.slot.recipe.nombre }}</span>
          <span class="dato salto">
            {{ masa.slot.posicion_track }} → {{ proyeccion(masa.indice).posicion }}
          </span>
        </div>

        <PistaMedida
          :valor="masa.slot.posicion_track - 0.5"
          :min="0"
          :max="TRACK_MAX"
          :previsto="proyeccion(masa.indice).posicion - 0.5"
          :tono-previsto="proyeccion(masa.indice).tono"
          :bandas="proyeccion(masa.indice).bandas"
          modo="posicion"
          lectura=""
        />

        <div class="dial" role="group" :aria-label="`Ajuste para Est-0${masa.indice + 1}`">
          <button
            v-for="op in OPCIONES"
            :key="op.valor"
            type="button"
            class="opcion"
            :class="{ activa: elegido[masa.indice] === op.valor }"
            @click="elegido[masa.indice] = op.valor"
          >
            <span class="dato">{{ op.etiqueta }}</span>
            <span class="pie">{{ op.pie }}</span>
          </button>
        </div>

        <p v-if="proyeccion(masa.indice).colapsa" class="aviso-colapso">
          ⚠ Con este ajuste la masa entra en <strong>Colapso</strong>: se horneará sola esta
          noche con penalización de puntos.
        </p>
      </div>
    </div>

    <p v-if="algunColapso" class="info-nota riesgo">
      Puedes confirmarlo igualmente — a veces adelantar un colapso es la jugada —, pero conviene
      mirar dos veces.
    </p>

    <p class="info-nota">
      El ajuste dura <strong>una sola noche</strong>: la Fase III lo aplica y devuelve el dial a 0.
      Puedes cambiarlo las veces que quieras mientras sea tu turno — no cuesta PA ni ocupa espacio
      de acción.
    </p>

    <template #acciones>
      <button class="secundario" @click="emit('cerrar')">Cancelar</button>
      <button
        class="confirmar"
        :disabled="enviando || masas.length === 0 || !hayCambios"
        @click="confirmar"
      >
        Aplicar ajustes
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.masas {
  display: flex;
  flex-direction: column;
  gap: var(--e3);
  margin: var(--e3) 0;
}

.masa {
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  padding: var(--e2);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--zona);
}

.cabecera {
  display: flex;
  align-items: baseline;
  gap: var(--e2);
}

.nombre {
  flex: 1 1 auto;
}

.salto {
  flex: 0 0 auto;
}

.dial {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--e1);
}

.opcion {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--e1) 0;
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  background: var(--carta);
  color: var(--tinta);
  font: inherit;
  cursor: pointer;
}

.opcion:hover {
  border-color: var(--borde-fuerte);
}

.opcion.activa {
  border-color: var(--cobre);
  box-shadow: inset 0 0 0 1px var(--cobre);
  color: var(--cobre);
}

.pie {
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.opcion.activa .pie {
  color: var(--cobre);
}

.aviso-colapso {
  margin: 0;
  padding: var(--e1) var(--e2);
  border: 1px solid var(--riesgo);
  border-radius: var(--r-control);
  background: var(--lavado-riesgo);
  font-size: var(--t-micro);
  color: var(--riesgo);
}

.vacio {
  margin: var(--e3) 0;
  color: var(--tinta-tenue);
}

.info-nota {
  margin: 0 0 var(--e2);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

.info-nota.riesgo {
  color: var(--riesgo);
}
</style>
