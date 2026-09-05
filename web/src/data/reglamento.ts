// El reglamento completo (RULEBOOK.html, en la raiz del repo) leido como
// texto en tiempo de compilacion y despiezado una sola vez para que
// ReglamentoView.vue lo pinte dentro de la app.
//
// Por que se importa el fichero en vez de reescribir las reglas en Vue: son
// las MISMAS reglas que tests/test_reglamento_al_dia.py ya vigila celda a
// celda contra el codigo. Una quinta superficie escrita a mano seria una
// quinta cosa que puede contradecir a las otras cuatro (ver CLAUDE.md, "Every
// rules change MUST update the rulebooks"). Asi, un cambio de regla llega al
// cliente solo con editar el reglamento, que es obligatorio de todas formas.
//
// El `?raw` necesita `server.fs.allow` en vite.config.ts -- ver el comentario
// largo de ahi. Y este modulo debe tener UN SOLO importador
// (ReglamentoView.vue): asi una edicion del reglamento en caliente vuelve a
// ejecutar el setup de ese componente en vez de recargar la app entera.
import html from '../../../RULEBOOK.html?raw'

export interface SeccionReglamento {
  /** El id del `<section class="rule">`: s1 … s12. */
  id: string
  /** El ordinal impreso, "01" … "12". */
  numero: string
  /** El `<h2>` de la seccion. */
  titulo: string
}

// Se despieza al cargar el modulo, no en un `computed` ni en el `setup`: la
// entrada es una constante de compilacion, asi que hacerlo por instancia seria
// repetir el mismo trabajo para obtener el mismo resultado.
const documento = new DOMParser().parseFromString(html, 'text/html')
const cuerpo = documento.querySelector('main')

if (!cuerpo) {
  // No deberia poder pasar: tests/test_reglamento_al_dia.py exige un unico
  // <main> en el fichero. El mensaje esta aqui para que, si alguien
  // reestructura el reglamento, el fallo diga que se rompio y no una
  // excepcion de null a media pagina.
  throw new Error('RULEBOOK.html no tiene <main>: ReglamentoView no puede renderizarlo.')
}

/**
 * El indice se RECONSTRUYE a partir de las secciones, no se copia el
 * `<nav class="rail">` del fichero. Asi el indice de la app no puede
 * desincronizarse de las secciones que realmente existen, y ademas es
 * marcado de Vue normal: puede llevar `@click`, `aria-current` y el
 * `<details>` de movil sin operar sobre un subarbol de `v-html`.
 */
export const SECCIONES: SeccionReglamento[] = [...cuerpo.querySelectorAll('section.rule')].map(
  (seccion) => ({
    id: seccion.id,
    numero: seccion.querySelector('.section-head .n')?.textContent?.trim() ?? '',
    titulo: seccion.querySelector('h2')?.textContent?.trim() ?? '',
  }),
)

// Los enlaces internos del reglamento (`href="#s7"`, `href="#unidades"`) se
// reescriben a `#reglamento/<id>`: en modo pagina esa es la URL que App.vue
// entiende, asi que copiar el enlace o abrirlo en otra pestaña sigue
// funcionando. Los clicks normales igualmente los intercepta el componente y
// hace scroll dentro de su contenedor, sin tocar el hash.
for (const enlace of cuerpo.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')) {
  enlace.setAttribute('href', `#reglamento/${enlace.getAttribute('href')!.slice(1)}`)
}

/**
 * El interior del `<main>`, listo para `v-html`.
 *
 * Se toma `innerHTML` y no el elemento entero a proposito: App.vue ya envuelve
 * todo en `<main class="app-shell">`, y un segundo `<main>` anidado seria un
 * segundo landmark para un lector de pantalla.
 *
 * No se sanea, y no hace falta: esto es un fichero del repositorio incrustado
 * en tiempo de compilacion, con el mismo nivel de confianza que cualquier otro
 * fuente. Nada de aqui viene del servidor ni de otro jugador.
 * `tests/test_reglamento_al_dia.py` fija ademas que dentro del `<main>` no hay
 * `<script>`, `<style>` ni manejadores `on*`.
 */
export const CUERPO_HTML: string = cuerpo.innerHTML

/** La cabecera del reglamento suelto no se usa: la app pone la suya. */
export const REVISION = 'Revisión de reglas GDD v0.0.2'
