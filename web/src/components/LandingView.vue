<script setup lang="ts">
// La portada: lo que ve alguien que abre la URL sin sesion guardada.
//
// Antes esto eran tres bloques apilados dentro de una columna de 480px (un
// h1 con un emoji, un parrafo y tres viñetas con emoji) encima del
// formulario. Ahora es una rejilla de dos columnas: el relato a la izquierda,
// la tarjeta de sala a la derecha. La decision de fondo es que no hay una
// pantalla de "landing" separada de la de entrar -- crear o unirse esta
// siempre a la vista, sin un scroll ni un click de por medio.
import { CEJA, DESCRIPTOR, ENLACE_REGLAMENTO, FICHA, LEMA, PILARES, RELATO, TITULO } from '../data/copyLanding'
import FormularioSala from './FormularioSala.vue'
import TarjetasFases from './TarjetasFases.vue'
import IconoPan from './IconoPan.vue'
import IconoDatos from './IconoDatos.vue'
import IconoMaestria from './IconoMaestria.vue'

defineProps<{ codigoInvitacion: string | null }>()
const emit = defineEmits<{ entrar: [{ roomId: string; hostToken: string; nombre: string }] }>()

// El relato lleva **negritas** en copyLanding.ts en vez de HTML: asi ese
// fichero se puede leer como texto y no como plantilla. Se parte aqui en
// trozos alternos (normal, fuerte, normal, ...) porque `v-html` para poner un
// <strong> seria desproporcionado.
const trozosRelato = RELATO.split('**')
</script>

<template>
  <div class="portada">
    <section class="relato">
      <div class="ceja-titulo">
        <span class="ico-l marca" aria-hidden="true"><IconoPan id="pan_de_campo" /></span>
        <div>
          <p class="eyebrow">{{ CEJA }}</p>
          <h1>{{ TITULO }}</h1>
        </div>
      </div>

      <p class="lema">{{ LEMA }}</p>
      <p class="descriptor">{{ DESCRIPTOR }}</p>

      <ul class="ficha">
        <li v-for="dato in FICHA" :key="dato">{{ dato }}</li>
      </ul>

      <p class="cuerpo-relato">
        <template v-for="(trozo, i) in trozosRelato" :key="i">
          <strong v-if="i % 2 === 1">{{ trozo }}</strong>
          <template v-else>{{ trozo }}</template>
        </template>
      </p>

      <div class="bloque">
        <p class="eyebrow">Cómo se juega · un Día de Laboratorio</p>
        <TarjetasFases />
      </div>

      <div class="bloque">
        <p class="eyebrow">Lo que gestionas</p>
        <ul class="pilares">
          <li v-for="(pilar, i) in PILARES" :key="pilar.titulo">
            <span class="ico-m icono-pilar" aria-hidden="true">
              <IconoDatos v-if="i === 0" />
              <IconoPan v-else-if="i === 1" id="baguette" />
              <IconoMaestria v-else />
            </span>
            <span>
              <strong>{{ pilar.titulo }}</strong>
              {{ pilar.texto }}
            </span>
          </li>
        </ul>
      </div>

      <p class="pie">
        <a href="#reglamento">{{ ENLACE_REGLAMENTO }} →</a>
        <span class="revision">Reglas GDD v0.0.2</span>
      </p>
    </section>

    <FormularioSala :codigo-invitacion="codigoInvitacion" @entrar="emit('entrar', $event)" />
  </div>
</template>

<style scoped>
.portada {
  display: grid;
  /* Dos columnas solo cuando caben de verdad: el relato quiere ~60ch y la
     tarjeta de sala tiene un ancho minimo real (swatches + botones). */
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 400px);
  gap: var(--e6);
  align-items: start;
  text-align: left;
}

.relato {
  min-width: 0;
}

.ceja-titulo {
  display: flex;
  align-items: center;
  gap: var(--e3);
}

.marca {
  flex: 0 0 auto;
}

.ceja-titulo h1 {
  /* Fuera de la escala de tokens a proposito: --t-display (34px) esta
     calibrado para numeros de carta dentro del tablero, no para el titulo de
     una portada. Es el unico sitio de la app con un tamaño de heroe. */
  font-size: clamp(2.4rem, 5vw, 3.4rem);
  line-height: 1.02;
  letter-spacing: -0.02em;
  margin: 0;
}

.lema {
  font-family: var(--fuente-titulo);
  font-size: var(--t-xl);
  font-weight: 700;
  color: var(--cobre);
  margin: var(--e4) 0 var(--e2);
  text-wrap: balance;
}

.descriptor {
  color: var(--tinta-tenue);
  margin: 0 0 var(--e4);
  max-width: 58ch;
}

.ficha {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: var(--e2);
  padding: 0;
  margin: 0 0 var(--e5);
}

.ficha li {
  font-family: var(--fuente-dato);
  font-size: var(--t-xs);
  color: var(--tinta);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  padding: var(--e1) var(--e2);
  background: var(--zona);
}

.cuerpo-relato {
  max-width: 60ch;
  line-height: 1.6;
  margin: 0 0 var(--e5);
}

.cuerpo-relato strong {
  color: var(--cobre);
  font-weight: 600;
}

.bloque {
  margin-bottom: var(--e5);
}

.bloque .eyebrow {
  margin-bottom: var(--e2);
}

.pilares {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e3);
}

.pilares li {
  display: flex;
  align-items: flex-start;
  gap: var(--e3);
  font-size: var(--t-s);
  color: var(--tinta-tenue);
  line-height: 1.5;
}

.icono-pilar {
  flex: 0 0 auto;
  margin-top: -2px;
}

.pilares strong {
  color: var(--tinta);
  font-weight: 600;
  display: block;
}

.pie {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--e2);
  margin: 0;
  padding-top: var(--e4);
  border-top: 1px solid var(--borde);
}

.pie a {
  color: var(--cobre);
  font-weight: 600;
  font-size: var(--t-s);
}

.revision {
  font-family: var(--fuente-dato);
  font-size: var(--t-micro);
  color: var(--tinta-tenue);
}

@media (max-width: 1100px) {
  .portada {
    grid-template-columns: 1fr;
    gap: var(--e5);
  }
}

@media (max-width: 720px) {
  /* En movil el formulario va primero: quien llega por un enlace de
     invitacion viene a entrar, no a leer la contraportada. */
  .portada > :last-child {
    order: -1;
  }

  .ceja-titulo h1 {
    font-size: 2.2rem;
  }
}
</style>
