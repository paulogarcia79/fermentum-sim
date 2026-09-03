<script setup lang="ts">
// El tercer overlay a nivel de body, despues de los modales y las pilas de
// descarte. Motivo: en GameView cada .region es un contenedor de scroll
// (`overflow-y: auto`, y .region-acciones ademas tope de 40vh), asi que un
// tooltip `position: absolute` que se abre hacia ARRIBA desde su ancla se sale
// del rectangulo de la region y lo recorta. El z-index no arregla nada porque
// el problema es recorte, no apilado -- por eso la caja se teletransporta al
// body y se posiciona con `fixed`, igual que hacen ModalShell y compañia.
//
// El API es de envoltorio: el ancla va en el slot por defecto (asi el hover y
// el foco se detectan sobre TODO el bloque, incluido un boton `disabled`, que
// no emite eventos de raton propios) y el contenido de la caja en #contenido.
// La raiz es un <div> simple para que la clase del consumidor
// (`envoltorio-boton`, `mejora-slot`, `receta-card`) caiga por atributos y sus
// estilos scoped le sigan aplicando.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ fijado?: boolean }>(), { fijado: false })
const emit = defineEmits<{ cerrar: [] }>()

/** Separacion entre el ancla y la caja, y margen minimo contra el borde de la
 * ventana. Es --e1 (0.25rem) en pixeles: el estilo no puede leerlo desde JS. */
const HUECO = 4

const ancla = ref<HTMLElement | null>(null)
const caja = ref<HTMLElement | null>(null)

const hover = ref(false)
const foco = ref(false)
const abierto = computed(() => hover.value || foco.value || props.fijado)

const pos = ref<{ top: string; left: string } | null>(null)

/** Coloca la caja a partir del rectangulo real del ancla y del suyo propio.
 * Preferencia arriba (es donde estaba historicamente); si no cabe, abajo. En
 * horizontal se centra sobre el ancla y se recorta contra la ventana, que es
 * lo que salva a los espacios de accion de los extremos de la barra. */
function colocar() {
  const a = ancla.value?.getBoundingClientRect()
  const c = caja.value?.getBoundingClientRect()
  if (!a || !c) return

  const cabeArriba = a.top - c.height - HUECO >= HUECO
  const top = cabeArriba ? a.top - c.height - HUECO : a.bottom + HUECO

  const centrado = a.left + a.width / 2 - c.width / 2
  const maxIzq = window.innerWidth - c.width - HUECO
  const left = Math.max(HUECO, Math.min(centrado, Math.max(HUECO, maxIzq)))

  pos.value = { top: `${Math.max(HUECO, top)}px`, left: `${left}px` }
}

/** Cierra de verdad: limpia el estado propio y avisa al consumidor para que
 * suelte su `fijado` (si no, la caja volveria a abrirse sola). */
function cerrar() {
  hover.value = false
  foco.value = false
  emit('cerrar')
}

/** Una caja `fixed` queda obsoleta en cuanto su ancla se mueve, y aqui las
 * regiones hacen scroll por dentro: mas vale ocultarla que dejarla flotando
 * lejos de su espacio de accion. */
function alDesplazar() {
  cerrar()
}

function alPulsarFuera(e: PointerEvent) {
  const destino = e.target as Node
  if (ancla.value?.contains(destino) || caja.value?.contains(destino)) return
  cerrar()
}

function alTeclear(e: KeyboardEvent) {
  if (e.key === 'Escape') cerrar()
}

/** focusout burbujea tambien cuando el foco solo salta de un hijo a otro
 * dentro del ancla; sin este filtro la caja parpadearia al tabular. */
function alPerderFoco(e: FocusEvent) {
  const siguiente = e.relatedTarget as Node | null
  if (siguiente && ancla.value?.contains(siguiente)) return
  foco.value = false
}

function escuchar(activar: boolean) {
  const metodo = activar ? window.addEventListener : window.removeEventListener
  metodo('scroll', alDesplazar, true)
  metodo('resize', alDesplazar)
  metodo('pointerdown', alPulsarFuera as EventListener, true)
  metodo('keydown', alTeclear as EventListener)
}

watch(abierto, async (activo) => {
  escuchar(activo)
  if (!activo) {
    pos.value = null
    return
  }
  // La caja se monta invisible (pos === null -> opacidad 0) y solo aparece una
  // vez medida, para que no se vea un fotograma en la esquina superior.
  await nextTick()
  colocar()
})

onBeforeUnmount(() => escuchar(false))
</script>

<template>
  <div
    ref="ancla"
    @mouseenter="hover = true"
    @mouseleave="hover = false"
    @focusin="foco = true"
    @focusout="alPerderFoco"
  >
    <slot />

    <Teleport to="body">
      <div
        v-if="abierto"
        ref="caja"
        class="tooltip"
        role="tooltip"
        :class="{ colocado: pos !== null, interactiva: fijado }"
        :style="pos ?? undefined"
      >
        <slot name="contenido" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Tier elevado, como un modal: la caja esta POR ENCIMA de la mesa, no impresa
   en ella. z-index por debajo del velo de los modales (40) para que un modal
   abierto tape siempre una caja que se haya quedado colgada. */
.tooltip {
  position: fixed;
  top: 0;
  left: 0;
  width: 16rem;
  max-width: 70vw;
  background: var(--carta);
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-carta);
  padding: var(--e2);
  font-size: var(--t-xs);
  line-height: 1.35;
  color: var(--tinta);
  box-shadow: var(--sombra-flotante);
  z-index: 35;
  opacity: 0;
  transition: opacity var(--transicion);
  /* La caja de hover no se traga clics de lo que tiene debajo; la fijada si
     es interactiva, para poder seleccionar su texto y para que el cierre por
     pulsacion-fuera no se dispare al pulsar dentro de ella. */
  pointer-events: none;
}

.tooltip.interactiva {
  pointer-events: auto;
}

.tooltip.colocado {
  opacity: 1;
}

.tooltip :deep(p) {
  margin: 0 0 var(--e1);
}

.tooltip :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
