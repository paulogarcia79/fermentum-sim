<script setup lang="ts">
// Envoltorio de los cuatro modales OBLIGATORIOS -- los que el juego impone
// para contar algo que pasó sin que el jugador lo decidiera: InicioDiaModal,
// FermentationReportModal, ResultadoHorneadoModal y FinAnticipadoModal.
//
// Es un componente aparte de ModalShell.vue a propósito, no una variante suya
// con props. ModalShell sirve a la familia DESCARTABLE (los 11 modales de
// acción + los de pila de descarte): lleva ✕, se cierra al pinchar fuera y
// vive en z-index 40. Aquí nada de eso existe -- no hay forma de salir salvo
// el botón del pie, y el velo tiene que quedar POR ENCIMA de un modal de
// acción que estuviera abierto (z-index 50). Un solo componente con
// `cerrable`/`obligatorio` acabaría siendo dos componentes con un `v-if` en
// medio.
//
// Los cuatro repetían literalmente el mismo bloque: Teleport + .fondo-modal +
// .modal + un button.primario copiado cuatro veces, con cuatro anchos
// distintos (420/460/480/560px) que nadie había elegido. Eso vive aquí ahora,
// una sola vez, con dos anchos con nombre.
//
// El pie usa las clases GLOBALES button.confirmar / button.secundario
// (App.vue), las mismas que ya usaban los 11 modales de acción: el vocabulario
// de botones es uno solo en los 15 modales. Por eso no hay estilos de botón en
// este archivo, y por eso el slot `acciones` funciona sin :slotted() -- el
// contenido del slot se compila en el padre, pero esas clases son globales.
const props = defineProps<{
  /** Título del modal. */
  titulo: string
  /** Línea de contexto sobre el título (día, fase...). Opcional. */
  ceja?: string
  /** 'm' (por defecto) para un aviso corto, 'l' para contenido tabular. */
  ancho?: 'm' | 'l'
  /** Texto del botón del pie por defecto. Ignorado si se usa el slot `acciones`. */
  etiquetaBoton?: string
}>()

const emit = defineEmits<{ reconocer: [] }>()

const anchoClase = () => `ancho-${props.ancho ?? 'm'}`
</script>

<template>
  <!-- A body: un overlay fixed no debe colgar del subarbol de una region
       (GameView aplana lo que hay dentro con :deep, y los z-index de cada
       region compiten entre si). El padre logico no cambia. -->
  <Teleport to="body">
    <!-- `appear` porque estos modales se montan ya visibles (un v-if del
         store), no se abren por interaccion: sin appear no habria entrada.
         El respeto a prefers-reduced-motion lo da la regla global de App.vue,
         que anula toda transition-duration; no hace falta repetirlo aqui. -->
    <Transition appear name="revelado">
      <div class="fondo-modal">
        <div class="modal" :class="anchoClase()" role="dialog" aria-modal="true">
          <header class="cabecera">
            <p v-if="ceja" class="eyebrow">{{ ceja }}</p>
            <h2>{{ titulo }}</h2>
          </header>

          <div class="cuerpo">
            <slot />
          </div>

          <footer class="pie">
            <slot name="acciones">
              <button class="confirmar" @click="emit('reconocer')">
                {{ etiquetaBoton ?? 'Entendido' }}
              </button>
            </slot>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: var(--velo-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: var(--e4);
}

/* .modal (App.vue) pone la superficie --carta con sombra flotante y padding.
   Aqui el padding se anula: las tres bandas (cabecera / cuerpo / pie) ponen el
   suyo, para que las reglas que las separan lleguen de borde a borde. */
.modal {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: 90vh;
  padding: 0;
  /* Recorta el cuerpo scrolleable contra las esquinas redondeadas. */
  overflow: hidden;
}

.ancho-m {
  max-width: 480px;
}

.ancho-l {
  max-width: 640px;
}

.cabecera {
  flex: 0 0 auto;
  padding: var(--e3) var(--e4);
  border-bottom: 1px solid var(--borde);
}

.cabecera h2 {
  margin: 0;
  font-size: var(--t-l);
}

.cabecera .eyebrow {
  margin-bottom: var(--e1);
}

/* min-height:0 para que este sea el que scrollea y no empuje al pie fuera. */
.cuerpo {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--e4);
}

.pie {
  flex: 0 0 auto;
  display: flex;
  gap: var(--e2);
  padding: var(--e3) var(--e4);
  border-top: 1px solid var(--borde);
}

/* Entrada: el velo funde y la carta sube. Salida no hay -- los cuatro se
   desmontan por un v-if del store y encadenan con el siguiente. */
.revelado-enter-active {
  transition: opacity 180ms ease;
}

.revelado-enter-active .modal {
  transition:
    transform 220ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 220ms ease;
}

.revelado-enter-from {
  opacity: 0;
}

.revelado-enter-from .modal {
  transform: translateY(12px);
  opacity: 0;
}
</style>
