<script setup lang="ts">
/**
 * Registro de la partida: un solo hilo cronologico con TODO lo que pasa en la
 * mesa -- los movimientos de cada jugador (store.estado.registro_acciones,
 * espejo de server/sessions.py:EntradaRegistro) intercalados con los eventos
 * automaticos del motor (store.eventos).
 *
 * Antes solo mostraba los eventos del motor, de los que exactamente una accion
 * de jugador (la F, via su HORNEADO) formaba parte: los otros 13 movimientos
 * sonaban por el canal efimero de avisos y no dejaban rastro alguno.
 *
 * Ordenacion sin marcas de tiempo: cada entrada guarda `pos_eventos` =
 * `len(engine.eventos)` en el instante ANTES de su mutacion, asi que va
 * despues del evento `pos_eventos - 1` y antes del `pos_eventos`. Eso hace que
 * "Horneo X" se lea justo por delante del HORNEADO que la propia accion emitio.
 * Depende de que store.eventos[i] sea el evento i del motor, que es lo que
 * garantiza el deduplicado por seq de store.ts.
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { store } from '../store'
import { hexDeColor } from '../data/coloresJugador'
import type { IdMovimiento } from '../data/descripcionesAcciones'
import type { GameEventView, RegistroAccionView } from '../types'

const ICONOS: Record<string, string> = {
  jefe_asignado: '👑',
  clima_revelado: '⛅',
  tendencia_anunciada: '📣',
  tendencia_mercado: '📈',
  mercado_refrescado: '🔄',
  receta_descartada: '🗑',
  masa_avanzo: '📈',
  horneado: '🍞',
  desgaste: '💧',
  renta_panaderia: '🥖',
  rendimiento_molino: '🌾',
  contaminacion: '☣',
  fin_de_partida: '🏁',
}

/**
 * Un glifo por movimiento. Tipado como Record exhaustivo sobre IdMovimiento
 * (no Record<string, string>) para que anadir una accion nueva sin su icono
 * sea un error de compilacion, igual que hace SONIDOS_ACCION.
 */
const ICONOS_ACCION: Record<IdMovimiento, string> = {
  A: '🌾',
  B: '🧫',
  C: '🛒',
  D: '🔧',
  E: '🤲',
  descarte: '💧',
  F: '🍞',
  G: '📋',
  simposio: '🎓',
  jefatura: '👑',
  H: '🧹',
  I: '💉',
  horas_extras: '⏳',
  pedido_urgencia: '📦',
  pasar: '⏭',
  deshacer: '↩',
  pase_forzado: '⏱',
}

type Linea =
  | { clase: 'dia'; clave: string; dia: number }
  | { clase: 'evento'; clave: string; ev: GameEventView }
  | { clase: 'accion'; clave: string; entrada: RegistroAccionView }

const lineas = computed<Linea[]>(() => {
  const eventos = store.eventos
  const acciones = store.estado?.registro_acciones ?? []
  const salida: Linea[] = []
  let i = 0
  let j = 0
  let diaEnCurso: number | null = null

  const empujar = (dia: number, linea: Linea) => {
    if (dia !== diaEnCurso) {
      salida.push({ clase: 'dia', clave: `d${dia}`, dia })
      diaEnCurso = dia
    }
    salida.push(linea)
  }

  while (i < eventos.length || j < acciones.length) {
    // Las acciones ya vienen en orden de `seq`, que es el orden de anexado:
    // eso desempata a las que comparten `pos_eventos` (lo normal, porque casi
    // ninguna accion emite eventos). Si la lista de eventos del cliente va por
    // detras del estado, las acciones restantes se emiten igual.
    const tocaAccion = j < acciones.length && (i >= eventos.length || acciones[j].pos_eventos <= i)
    if (tocaAccion) {
      empujar(acciones[j].dia, { clase: 'accion', clave: `a${acciones[j].seq}`, entrada: acciones[j] })
      j++
    } else {
      empujar(eventos[i].dia, { clase: 'evento', clave: `e${i}`, ev: eventos[i] })
      i++
    }
  }
  return salida
})

function jugadorNombre(idx: number | null): string {
  if (idx === null || !store.estado) return ''
  return store.estado.players[idx]?.nombre ?? ''
}

function colorJugador(idx: number | null): string | undefined {
  if (idx === null || !store.estado) return undefined
  const color = store.estado.players[idx]?.color
  return color ? hexDeColor(color) : undefined
}

function esMio(idx: number | null): boolean {
  return idx !== null && idx === store.sesion?.playerIndex
}

// --- Auto-scroll pegado al final -------------------------------------------
// El hilo se lee de arriba abajo (lo mas nuevo abajo), asi que la vista util
// es el final. Se sigue solo si el usuario ya estaba abajo: si subio a leer
// algo, una accion de un rival no debe arrancarle la lectura.
const lista = ref<HTMLElement | null>(null)
let pegadoAbajo = true // no reactivo: solo lo leen el handler y el watcher
const UMBRAL_PX = 8

function alDesplazar(): void {
  const el = lista.value
  if (!el) return
  pegadoAbajo = el.scrollTop + el.clientHeight >= el.scrollHeight - UMBRAL_PX
}

async function bajarDelTodo(): Promise<void> {
  await nextTick()
  const el = lista.value
  if (el && pegadoAbajo) el.scrollTop = el.scrollHeight
}

// Limitacion conocida: el panel se oculta con v-show (ver DockPaneles), y un
// elemento en display:none no puede desplazarse. Al volver a mostrarse se
// queda donde estaba en vez de saltar al final.
watch(() => lineas.value.length, bajarDelTodo)
onMounted(bajarDelTodo)
</script>

<template>
  <section class="panel eventos">
    <h3>Registro</h3>
    <ul ref="lista" @scroll="alDesplazar">
      <template v-for="linea in lineas" :key="linea.clave">
        <li v-if="linea.clase === 'dia'" class="separador-dia eyebrow">Día {{ linea.dia }}</li>

        <li
          v-else-if="linea.clase === 'accion'"
          class="fila"
          :class="{
            propia: esMio(linea.entrada.jugador_idx),
            deshecha: linea.entrada.deshecha,
            forzada: linea.entrada.accion === 'pase_forzado',
          }"
        >
          <span class="icono">{{ ICONOS_ACCION[linea.entrada.accion as IdMovimiento] ?? '•' }}</span>
          <span class="texto">
            <span class="quien" :style="{ color: colorJugador(linea.entrada.jugador_idx) }">
              {{ jugadorNombre(linea.entrada.jugador_idx) }}:
            </span>
            {{ linea.entrada.mensaje }}
          </span>
        </li>

        <li v-else class="fila sistema">
          <span class="icono">{{ ICONOS[linea.ev.tipo] ?? '•' }}</span>
          <span class="texto">
            <span
              v-if="linea.ev.jugador_idx !== null"
              class="quien"
              :style="{ color: colorJugador(linea.ev.jugador_idx) }"
            >
              {{ jugadorNombre(linea.ev.jugador_idx) }}:
            </span>
            {{ linea.ev.mensaje }}
          </span>
        </li>
      </template>
      <li v-if="lineas.length === 0" class="vacio">Sin movimientos todavía.</li>
    </ul>
  </section>
</template>

<style scoped>
.eventos h3 {
  margin-top: 0;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  max-height: min(45vh, 30rem);
  overflow-y: auto;
}

.fila {
  display: flex;
  gap: var(--e2);
  font-size: var(--t-s);
  align-items: flex-start;
  padding: 2px var(--e2);
  border-radius: var(--r-control);
  border-left: 2px solid transparent;
}

.propia {
  background: var(--lavado-cobre);
  border-left-color: var(--cobre);
}

.sistema {
  color: var(--tinta-tenue);
}

.deshecha {
  text-decoration: line-through;
  color: var(--tinta-tenue);
  opacity: 0.75;
}

.forzada {
  color: var(--riesgo);
}

.quien {
  font-weight: 600;
}

.icono {
  flex: none;
}

.separador-dia {
  border-top: 1px solid var(--borde);
  padding-top: var(--e2);
  margin-top: var(--e1);
}

.separador-dia:first-child {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

.vacio {
  color: var(--tinta-tenue);
  font-style: italic;
}
</style>
