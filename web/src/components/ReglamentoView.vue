<script setup lang="ts">
// El reglamento completo dentro de la app.
//
// El contenido NO se reescribe aqui: se importa RULEBOOK.html tal cual (ver
// data/reglamento.ts) y se le quita su hoja de estilos para repintarlo con
// los tokens del tablero. Asi la app no es una quinta superficie de reglas
// que pueda contradecir a las otras cuatro.
//
// Dos anfitriones, un solo componente:
//   - modo="pagina": App.vue, con el hash #reglamento. Se lee como documento.
//   - modo="superpuesto": GameView, a pantalla completa por encima del
//     tablero, que sigue montado detras (no se pierde el scroll de un panel
//     ni un tooltip abierto por consultar una regla).
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { CUERPO_HTML, REVISION, SECCIONES } from '../data/reglamento'

const props = defineProps<{ modo: 'pagina' | 'superpuesto'; seccion?: string }>()
const emit = defineEmits<{ cerrar: [] }>()

const raiz = ref<HTMLElement | null>(null)
const desplazador = ref<HTMLElement | null>(null)
const botonCerrar = ref<HTMLButtonElement | null>(null)
const indiceMovil = ref<HTMLDetailsElement | null>(null)
const seccionActual = ref<string | null>(null)

const esSuperpuesto = computed(() => props.modo === 'superpuesto')

// --- Navegacion entre secciones ------------------------------------------
//
// Los enlaces internos del reglamento ya vienen reescritos a
// `#reglamento/<id>` (data/reglamento.ts), asi que copiarlos o abrirlos en
// otra pestaña funciona. Pero un click normal NO se deja navegar: se
// intercepta y se hace scroll dentro del contenedor. Si se dejara pasar,
// dispararia el `hashchange` que App.vue escucha para decidir la vista, y en
// modo superpuesto ademas cambiaria la URL de una partida en curso.
function irA(id: string, actualizarUrl: boolean) {
  const destino = raiz.value?.querySelector(`#${CSS.escape(id)}`)
  if (!destino) return
  destino.scrollIntoView({ block: 'start' })
  seccionActual.value = id
  if (indiceMovil.value) indiceMovil.value.open = false
  // La URL solo se toca en modo pagina, y con replace: un `push` por titulo
  // convertiria el boton Atras en un paseo por doce encabezados.
  if (actualizarUrl && props.modo === 'pagina') {
    history.replaceState(null, '', `#reglamento/${id}`)
  }
}

function alPulsar(e: MouseEvent) {
  // Respetar ctrl/cmd/shift-click y el boton central: son "abrir en otra
  // pestaña", y para eso el href reescrito ya es correcto.
  if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
  const enlace = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#reglamento/"]')
  if (!enlace) return
  e.preventDefault()
  irA(enlace.getAttribute('href')!.slice('#reglamento/'.length), true)
}

// --- Seccion activa en el indice -----------------------------------------
let observador: IntersectionObserver | undefined

function observarSecciones() {
  const secciones = raiz.value?.querySelectorAll('section.rule')
  if (!secciones?.length) return
  const visibles = new Set<string>()
  observador = new IntersectionObserver(
    (entradas) => {
      for (const entrada of entradas) {
        if (entrada.isIntersecting) visibles.add(entrada.target.id)
        else visibles.delete(entrada.target.id)
      }
      // La primera en orden de documento, no la ultima que notifico: si dos
      // secciones se solapan en pantalla, la de arriba es la que se esta
      // leyendo.
      seccionActual.value = SECCIONES.find((s) => visibles.has(s.id))?.id ?? seccionActual.value
    },
    // El margen inferior deja "activa" la seccion cuyo encabezado esta en el
    // cuarto superior, que es donde mira la vista.
    { root: esSuperpuesto.value ? desplazador.value : null, rootMargin: '0px 0px -75% 0px' },
  )
  for (const seccion of secciones) observador.observe(seccion)
}

// --- Modo superpuesto: teclado y foco -------------------------------------
//
// Se captura AQUI, en el cuerpo del setup, y no en `onMounted`: para entonces
// este componente ya ha movido el foco (al boton de cerrar), y guardar
// `document.activeElement` despues significa guardar un elemento del propio
// superpuesto, que se destruye al cerrarlo -- el foco acababa en el <body> en
// vez de volver al boton de la cabecera desde el que se abrio.
const focoPrevio = document.activeElement as HTMLElement | null

function alTeclear(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('cerrar')
}

onMounted(async () => {
  await nextTick()
  observarSecciones()
  if (props.seccion) irA(props.seccion, false)

  if (esSuperpuesto.value) {
    botonCerrar.value?.focus()
    window.addEventListener('keydown', alTeclear)
    // Bloquear el scroll de detras: por debajo de 1100px la pagina si
    // desplaza, y sin esto se mueve el tablero al llegar al final del texto.
    document.body.style.overflow = 'hidden'
  }
})

onBeforeUnmount(() => {
  observador?.disconnect()
  if (esSuperpuesto.value) {
    window.removeEventListener('keydown', alTeclear)
    document.body.style.overflow = ''
    focoPrevio?.focus?.()
  }
})
</script>

<template>
  <Teleport to="body" :disabled="modo === 'pagina'">
    <div
      class="reglamento"
      :class="modo"
      :role="esSuperpuesto ? 'dialog' : undefined"
      :aria-modal="esSuperpuesto ? 'true' : undefined"
      aria-label="Reglamento de Fermentum"
    >
      <div class="barra">
        <a v-if="modo === 'pagina'" class="volver" href="#" @click.prevent="emit('cerrar')">← Volver</a>
        <p class="eyebrow">Reglamento · {{ REVISION }}</p>
        <button
          v-if="esSuperpuesto"
          ref="botonCerrar"
          class="cerrar"
          aria-label="Cerrar el reglamento"
          @click="emit('cerrar')"
        >
          ✕
        </button>
      </div>

      <div ref="desplazador" class="desplazador" tabindex="-1">
        <div ref="raiz" class="cuerpo" @click="alPulsar">
          <!-- El indice se reconstruye desde las secciones (data/reglamento.ts):
               marcado de Vue normal, con aria-current y plegado en movil. -->
          <nav class="indice-escritorio" aria-label="Índice del reglamento">
            <p class="eyebrow">Índice</p>
            <ol>
              <li v-for="seccion in SECCIONES" :key="seccion.id">
                <a
                  :href="`#reglamento/${seccion.id}`"
                  :aria-current="seccionActual === seccion.id ? 'true' : undefined"
                >
                  <span class="dato num">{{ seccion.numero }}</span>
                  {{ seccion.titulo }}
                </a>
              </li>
            </ol>
          </nav>

          <details ref="indiceMovil" class="indice-movil">
            <summary>Índice</summary>
            <ol>
              <li v-for="seccion in SECCIONES" :key="seccion.id">
                <a :href="`#reglamento/${seccion.id}`">
                  <span class="dato num">{{ seccion.numero }}</span>
                  {{ seccion.titulo }}
                </a>
              </li>
            </ol>
          </details>

          <!-- eslint-disable-next-line vue/no-v-html -- Es un fichero del
               repositorio incrustado en compilacion, no entrada de usuario ni
               del servidor; ver data/reglamento.ts. -->
          <div class="texto" v-html="CUERPO_HTML" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<!-- NO es `scoped`, y eso es deliberado.

     Cuando la raiz de la plantilla es un `<Teleport>`, Vue no estampa el
     atributo `data-v-*` en el contenido teletransportado, asi que en modo
     superpuesto NINGUNA regla con scope llegaba a aplicarse: el reglamento
     salia sin posicionar, empujando el tablero hacia abajo. En modo pagina
     funcionaba (ahi el teleport esta desactivado y el elemento se queda en su
     sitio), que es justo lo que hacia el fallo facil de no ver.

     A cambio, TODO selector de aqui abajo cuelga de `.reglamento`. Es
     obligatorio, no una convencion: sin scope, un `.cuerpo` o un `.cerrar`
     sueltos pisarian los de GameView.vue y ModalShell.vue. -->
<style>
/* Los cinco `style=` en linea que sobreviven en el cuerpo del reglamento
   apuntan a los nombres de variable del fichero suelto. Sin estos alias los
   cuatro `.dot` de las tarjetas se quedarian transparentes. */
.reglamento {
  --accent-vitalidad: var(--calido);
  --accent-acidez: var(--verdin);
  --accent-agua: var(--frio);
  --accent-datos: var(--frio);
  --accent-monedas: var(--cobre);
  --ink-muted: var(--tinta-tenue);
  font-family: var(--fuente);
  font-size: var(--t-m);
  line-height: 1.6;
  color: var(--tinta);
  text-align: left;
}

.reglamento.superpuesto {
  position: fixed;
  inset: 0;
  /* Opaco, no un velo: esto se lee, no se ojea por encima del tablero. */
  background: var(--mesa);
  /* Nivel de ModalShell. Los modales obligatorios (50) siguen ganando, que es
     lo correcto: el informe de Fase III no puede quedar debajo. */
  z-index: 40;
  display: flex;
  flex-direction: column;
}

.reglamento .barra {
  display: flex;
  align-items: center;
  gap: var(--e3);
  padding: var(--e2) var(--e3);
  border-bottom: 1px solid var(--borde);
  background: var(--zona);
}

.reglamento.superpuesto .barra {
  flex: 0 0 auto;
}

.reglamento .barra .eyebrow {
  margin: 0;
  margin-right: auto;
}

.reglamento .volver {
  color: var(--cobre);
  font-size: var(--t-s);
  font-weight: 600;
}

.reglamento .cerrar {
  background: none;
  border: none;
  color: var(--tinta-tenue);
  font-size: var(--t-l);
  padding: 0 var(--e1);
  cursor: pointer;
}

.reglamento .desplazador {
  scroll-behavior: smooth;
}

.reglamento.superpuesto .desplazador {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

/* La regla global de App.vue solo anula transiciones y animaciones: un scroll
   suave por JS/CSS queda fuera de esa red y hay que apagarlo aqui. */
@media (prefers-reduced-motion: reduce) {
  .reglamento .desplazador {
    scroll-behavior: auto;
  }
}

.reglamento .cuerpo {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: var(--e5);
  padding: var(--e4);
  max-width: 1100px;
  margin: 0 auto;
}

/* En modo pagina el ancho y el padding ya los pone `.app-shell.centrado` de
   App.vue; repetirlos aqui daria un doble margen. */
.reglamento.pagina .cuerpo {
  padding: var(--e4) 0 var(--e6);
  max-width: none;
}

/* La barra tambien se estira de lado a lado en superpuesto, pero en pagina
   vive dentro de la columna del documento. */
.reglamento.pagina .barra {
  margin: 0 calc(-1 * var(--e4));
  padding-left: var(--e4);
  padding-right: var(--e4);
}

.reglamento .indice-escritorio {
  position: sticky;
  top: var(--e4);
  align-self: start;
  max-height: calc(100dvh - 2 * var(--e4));
  overflow-y: auto;
}

.reglamento .indice-escritorio ol,
.reglamento .indice-movil ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.reglamento .indice-escritorio a,
.reglamento .indice-movil a {
  display: flex;
  gap: var(--e2);
  padding: var(--e1) var(--e2);
  border-radius: var(--r-control);
  color: var(--tinta-tenue);
  font-size: var(--t-s);
  line-height: 1.3;
  text-decoration: none;
}

.reglamento .indice-escritorio a:hover,
.reglamento .indice-movil a:hover {
  background: var(--zona);
  color: var(--tinta);
}

.reglamento .indice-escritorio a[aria-current] {
  background: var(--lavado-cobre);
  color: var(--cobre);
}

.reglamento .num {
  color: var(--tinta-tenue);
  min-width: 1.6em;
  flex: 0 0 auto;
}

.reglamento .indice-escritorio a[aria-current] .num {
  color: var(--cobre);
}

.reglamento .indice-movil {
  display: none;
}

.reglamento .indice-movil summary {
  cursor: pointer;
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
  padding: var(--e2) 0;
}

.reglamento .indice-movil ol {
  flex-direction: row;
  flex-wrap: wrap;
  gap: var(--e1);
  padding-bottom: var(--e3);
}

.reglamento .indice-movil a {
  background: var(--zona);
  font-size: var(--t-xs);
}

@media (max-width: 1100px) {
  .reglamento .cuerpo {
    grid-template-columns: 1fr;
    gap: var(--e3);
  }

  .reglamento .indice-escritorio {
    display: none;
  }

  .reglamento .indice-movil {
    display: block;
  }
}

/* --- El reglamento importado -------------------------------------------- */
/* Todo lo de aqui abajo repinta las clases de RULEBOOK.html con los tokens
   del tablero. La hoja de estilos original (Fraunces, paleta clara) se
   descarta entera en data/reglamento.ts. */

.reglamento .texto .prose {
  max-width: 720px;
}

.reglamento .texto section.rule {
  margin-bottom: var(--e6);
  scroll-margin-top: var(--e4);
}

.reglamento .texto .section-head {
  display: flex;
  align-items: baseline;
  gap: var(--e3);
  margin-bottom: var(--e4);
  padding-bottom: var(--e2);
  border-bottom: 1px solid var(--borde-fuerte);
}

.reglamento .texto .section-head .n {
  font-family: var(--fuente-dato);
  font-variant-numeric: tabular-nums;
  font-size: var(--t-l);
  font-weight: 600;
  color: var(--cobre);
}

.reglamento .texto .section-head h2 {
  font-family: var(--fuente-titulo);
  font-size: var(--t-xl);
  margin: 0;
}

.reglamento .texto h3.sub {
  font-family: var(--fuente-titulo);
  font-size: var(--t-l);
  margin: var(--e5) 0 var(--e2);
}

.reglamento .texto h4.sub-sub {
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
  margin: var(--e4) 0 var(--e2);
}

.reglamento .texto p {
  max-width: 68ch;
  margin: 0 0 var(--e3);
}

.reglamento .texto ul.rules-list,
.reglamento .texto ol.rules-list {
  max-width: 68ch;
  margin: 0 0 var(--e3);
  padding-left: var(--e5);
}

.reglamento .texto .rules-list li {
  margin-bottom: var(--e2);
}

.reglamento .texto em.aside,
.reglamento .texto p.note {
  color: var(--tinta-tenue);
}

.reglamento .texto a {
  color: var(--cobre);
}

.reglamento .texto .callout {
  background: var(--zona);
  border-left: 3px solid var(--cobre);
  border-radius: 0 var(--r-control) var(--r-control) 0;
  padding: var(--e3) var(--e4);
  margin: var(--e3) 0 var(--e4);
  max-width: 68ch;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.reglamento .texto .callout strong {
  color: var(--tinta);
}

.reglamento .texto .formula {
  font-family: var(--fuente-dato);
  background: var(--mesa);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  padding: var(--e3) var(--e4);
  margin: var(--e3) 0 var(--e4);
  font-size: var(--t-s);
  max-width: 68ch;
  overflow-x: auto;
}

.reglamento .texto .chip {
  display: inline-flex;
  align-items: center;
  gap: var(--e1);
  font-family: var(--fuente-dato);
  font-size: var(--t-xs);
  font-weight: 500;
  padding: 1px var(--e2) 1px var(--e1);
  border-radius: 999px;
  white-space: nowrap;
}

.reglamento .texto .chip::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex: none;
}

.reglamento .texto .chip.datos {
  color: var(--frio);
  background: color-mix(in srgb, var(--frio) 14%, transparent);
}

.reglamento .texto .chip.monedas {
  color: var(--cobre);
  background: var(--lavado-cobre);
}

.reglamento .texto .legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  margin: var(--e1) 0 var(--e4);
}

.reglamento .texto .card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: var(--e3);
  margin: var(--e3) 0 var(--e4);
}

.reglamento .texto .card {
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
  box-shadow: var(--sombra-carta);
  padding: var(--e3) var(--e4);
}

.reglamento .texto .card h5 {
  display: flex;
  align-items: center;
  gap: var(--e2);
  margin: 0 0 var(--e1);
  font-family: var(--fuente);
  font-size: var(--t-m);
  font-weight: 600;
}

.reglamento .texto .card h5 .dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
}

.reglamento .texto .card p {
  margin: 0;
  font-size: var(--t-s);
  color: var(--tinta-tenue);
}

.reglamento .texto .card .cost {
  display: block;
  margin-top: var(--e2);
  font-family: var(--fuente-dato);
  font-size: var(--t-xs);
  color: var(--tinta-tenue);
}

.reglamento .texto .table-wrap {
  overflow-x: auto;
  margin: var(--e2) 0 var(--e5);
  border: 1px solid var(--borde);
  border-radius: var(--r-carta);
}

.reglamento .texto table {
  border-collapse: collapse;
  width: 100%;
  min-width: 560px;
  background: var(--zona);
  font-size: var(--t-s);
}

.reglamento .texto table caption {
  caption-side: top;
  text-align: left;
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--tinta-tenue);
  padding: var(--e3) var(--e4) 0;
  background: var(--zona);
}

.reglamento .texto thead th {
  text-align: left;
  font-size: var(--t-xs);
  font-weight: 600;
  color: var(--tinta-tenue);
  background: var(--carta);
  padding: var(--e2) var(--e3);
  border-bottom: 1px solid var(--borde-fuerte);
  white-space: nowrap;
}

.reglamento .texto tbody td {
  padding: var(--e2) var(--e3);
  border-bottom: 1px solid var(--borde);
  font-family: var(--fuente-dato);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.reglamento .texto tbody td.name {
  font-family: var(--fuente);
  font-weight: 500;
  white-space: normal;
}

.reglamento .texto tbody td.wrap {
  font-family: var(--fuente);
  color: var(--tinta-tenue);
  white-space: normal;
}

.reglamento .texto tbody tr:last-child td {
  border-bottom: none;
}

.reglamento .texto tbody tr:nth-child(even) td {
  background: var(--banda-tenue);
}

/* Las cuatro zonas de fermentacion. Los nombres `baja`/`sobre` son los
   ANTIGUOS (hoy Pre-fermento y Colapso) y sobreviven solo como selectores,
   igual que en el fichero original. Van con --banda-* y no con --lavado-*:
   estas celdas son franjas pequeñas sobre --zona, donde un 12% no se ve. */
.reglamento .texto tbody td.z-crecimiento {
  background: var(--banda-tenue) !important;
  color: var(--tinta-tenue);
}

.reglamento .texto tbody td.z-baja {
  background: color-mix(in srgb, var(--calido) 22%, transparent) !important;
  color: var(--calido);
  font-weight: 600;
}

.reglamento .texto tbody td.z-optima {
  background: var(--banda-vital) !important;
  color: var(--tinta);
  font-weight: 600;
}

.reglamento .texto tbody td.z-sobre {
  background: var(--banda-riesgo) !important;
  color: var(--tinta);
  font-weight: 600;
}

.reglamento .texto .zone-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  margin: var(--e1) 0 var(--e3);
  font-family: var(--fuente-dato);
  font-size: var(--t-xs);
}

.reglamento .texto .zone-legend span {
  display: inline-flex;
  align-items: center;
  gap: var(--e1);
  padding: var(--e1) var(--e3);
  border-radius: var(--r-control);
}

.reglamento .texto .zone-legend .lc {
  background: var(--banda-tenue);
  color: var(--tinta-tenue);
}

.reglamento .texto .zone-legend .lb {
  background: color-mix(in srgb, var(--calido) 22%, transparent);
  color: var(--calido);
}

.reglamento .texto .zone-legend .lo {
  background: var(--banda-vital);
  color: var(--tinta);
}

.reglamento .texto .zone-legend .ls {
  background: var(--banda-riesgo);
  color: var(--tinta);
}
</style>
