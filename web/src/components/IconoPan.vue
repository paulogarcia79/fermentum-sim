<script setup lang="ts">
// Icono SVG distinto por receta (silueta plana/geometrica, no ilustracion)
// -- primer intento hecho a mano, sin herramienta de generacion de imagenes
// disponible en este entorno; se espera iterar una vez visto renderizado.
defineProps<{ id: string }>()
</script>

<template>
  <svg viewBox="0 0 24 24" class="icono-pan" aria-hidden="true">
    <!-- Pan de Campo: boule redondo con cortes cruzados -->
    <g v-if="id === 'pan_de_campo'">
      <ellipse cx="12" cy="14" rx="8" ry="7" fill="#c9974f" stroke="#7a4f22" stroke-width="0.6" />
      <path
        d="M7 10 L10 7 M11 9 L14 6 M15 10 L18 7"
        stroke="#7a4f22"
        stroke-width="1"
        fill="none"
        stroke-linecap="round"
      />
    </g>

    <!-- Focaccia: oval plano y ancho, con hoyuelos -->
    <g v-else-if="id === 'focaccia'">
      <ellipse cx="12" cy="14" rx="9.5" ry="5" fill="#e0c979" stroke="#a9752f" stroke-width="0.6" />
      <circle cx="7.5" cy="13" r="0.7" fill="#a9752f" />
      <circle cx="10.5" cy="16" r="0.7" fill="#a9752f" />
      <circle cx="13.5" cy="12.5" r="0.7" fill="#a9752f" />
      <circle cx="16.5" cy="15" r="0.7" fill="#a9752f" />
      <circle cx="12" cy="14.5" r="0.7" fill="#a9752f" />
    </g>

    <!-- Baguette: barra larga con cortes diagonales -->
    <g v-else-if="id === 'baguette'">
      <rect x="2.5" y="10.5" width="19" height="5" rx="2.5" fill="#e8c77a" stroke="#a9752f" stroke-width="0.6" />
      <path
        d="M6 10.5 L8 15.5 M10 10.5 L12 15.5 M14 10.5 L16 15.5 M18 10.5 L20 15.5"
        stroke="#a9752f"
        stroke-width="1"
        fill="none"
      />
    </g>

    <!-- Pizza Napolitana: porcion triangular con ingredientes -->
    <g v-else-if="id === 'pizza_napolitana'">
      <path d="M12 4.5 L19.5 19 L4.5 19 Z" fill="#e8b04f" stroke="#a9752f" stroke-width="0.6" stroke-linejoin="round" />
      <circle cx="10" cy="14" r="1.1" fill="#c1443a" />
      <circle cx="14" cy="15.5" r="1.1" fill="#c1443a" />
      <circle cx="12" cy="11" r="1.1" fill="#c1443a" />
      <circle cx="12.5" cy="17" r="1" fill="#5c8a4a" />
    </g>

    <!-- Brioche a la tete: bola grande + bola pequena encima -->
    <g v-else-if="id === 'brioche'">
      <circle cx="12" cy="15.5" r="6" fill="#f0c860" stroke="#a9752f" stroke-width="0.6" />
      <circle cx="12" cy="8" r="3" fill="#f0c860" stroke="#a9752f" stroke-width="0.6" />
    </g>

    <!-- Hogaza Centeno: hogaza oscura con un corte curvo -->
    <g v-else-if="id === 'hogaza_centeno'">
      <ellipse cx="12" cy="14" rx="8" ry="6" fill="#6b4a2f" stroke="#3d2a1a" stroke-width="0.6" />
      <path d="M5 11.5 Q12 7.5 19 11.5" stroke="#3d2a1a" stroke-width="1" fill="none" stroke-linecap="round" />
    </g>

    <!-- Pan Semillas: hogaza con textura de semillas -->
    <g v-else-if="id === 'pan_semillas'">
      <ellipse cx="12" cy="14" rx="8" ry="6" fill="#c9974f" stroke="#7a4f22" stroke-width="0.6" />
      <circle cx="8" cy="12" r="0.5" fill="#3d2a1a" />
      <circle cx="10.5" cy="15.5" r="0.5" fill="#3d2a1a" />
      <circle cx="13" cy="11.5" r="0.5" fill="#3d2a1a" />
      <circle cx="15.5" cy="14.5" r="0.5" fill="#3d2a1a" />
      <circle cx="12" cy="17" r="0.5" fill="#3d2a1a" />
      <circle cx="16" cy="11" r="0.5" fill="#3d2a1a" />
    </g>

    <!-- Panettone: cilindro alto y domado, con corte en cruz -->
    <g v-else-if="id === 'panettone'">
      <path
        d="M7 20 L7 11 Q7 6 12 6 Q17 6 17 11 L17 20 Z"
        fill="#e8c77a"
        stroke="#a9752f"
        stroke-width="0.6"
        stroke-linejoin="round"
      />
      <path d="M12 6 L12 3.2 M9 4.5 L15 7.5" stroke="#7a4f22" stroke-width="1" stroke-linecap="round" />
    </g>

    <!-- Generico: cualquier receta futura sin icono propio todavia -->
    <ellipse v-else cx="12" cy="14" rx="8" ry="6" fill="#c9974f" stroke="#7a4f22" stroke-width="0.6" />
  </svg>
</template>

<style scoped>
.icono-pan {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
