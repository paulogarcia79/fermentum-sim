<script setup lang="ts">
// Icono SVG distinto por carta de clima (silueta plana/geometrica, no
// ilustracion) -- mismo enfoque hecho a mano que IconoPan.vue, con
// fallback generico para cualquier id no mapeado todavia.
defineProps<{ id: string }>()
</script>

<template>
  <svg viewBox="0 0 24 24" class="icono-clima" aria-hidden="true">
    <!-- Estabilidad Termica: balanza en equilibrio -->
    <g v-if="id === 'estabilidad_termica'">
      <path d="M4 17 L20 17" stroke="#8a9a8a" stroke-width="1.4" stroke-linecap="round" />
      <path d="M12 17 L12 6" stroke="#8a9a8a" stroke-width="1.4" stroke-linecap="round" />
      <circle cx="12" cy="5" r="1.6" fill="#8a9a8a" />
      <path d="M6 17 L4 12 L8 12 Z" fill="none" stroke="#8a9a8a" stroke-width="1.2" stroke-linejoin="round" />
      <path d="M18 17 L16 12 L20 12 Z" fill="none" stroke="#8a9a8a" stroke-width="1.2" stroke-linejoin="round" />
    </g>

    <!-- Fallo Refrigeracion: sol pequeño (calor leve) -->
    <g v-else-if="id === 'fallo_refrigeracion'">
      <circle cx="12" cy="12" r="4.2" fill="#e6a94f" stroke="#a9752f" stroke-width="0.6" />
      <path
        d="M12 3.5 L12 6 M12 18 L12 20.5 M3.5 12 L6 12 M18 12 L20.5 12 M6 6 L7.7 7.7 M16.3 16.3 L18 18 M18 6 L16.3 7.7 M7.7 16.3 L6 18"
        stroke="#e6a94f"
        stroke-width="1.2"
        stroke-linecap="round"
      />
    </g>

    <!-- Ola de Calor: llama -->
    <g v-else-if="id === 'ola_de_calor'">
      <path
        d="M12 2.5 C9 7 7.5 9 8 12.5 C8.3 15 10 16 10 14 C10 16.5 12 17.5 13 15.5 C14.5 18 12 21.5 12 21.5 C17 21.5 18 16.5 15.5 12.5 C15 15 13.5 15 14 12.5 C14.5 9.5 13 5 12 2.5 Z"
        fill="#d9612f"
        stroke="#8a3418"
        stroke-width="0.6"
        stroke-linejoin="round"
      />
    </g>

    <!-- Corriente de Aire: remolinos de viento -->
    <g v-else-if="id === 'corriente_de_aire'">
      <path
        d="M3 9 H14 A2.5 2.5 0 1 0 11.5 6.5"
        fill="none"
        stroke="#7fa8c9"
        stroke-width="1.4"
        stroke-linecap="round"
      />
      <path
        d="M3 14.5 H17 A2.5 2.5 0 1 1 14.5 17"
        fill="none"
        stroke="#7fa8c9"
        stroke-width="1.4"
        stroke-linecap="round"
      />
      <path d="M3 19 H10" fill="none" stroke="#7fa8c9" stroke-width="1.4" stroke-linecap="round" />
    </g>

    <!-- Fallo Calefaccion: copo de nieve -->
    <g v-else-if="id === 'fallo_calefaccion'">
      <path
        d="M12 2.5 V21.5 M4 7 L20 17 M20 7 L4 17"
        stroke="#7fb8d9"
        stroke-width="1.3"
        stroke-linecap="round"
      />
      <path
        d="M12 2.5 L10 5 M12 2.5 L14 5 M12 21.5 L10 19 M12 21.5 L14 19 M4 7 L4.3 9.6 M4 7 L6.5 6.3 M20 7 L19.7 9.6 M20 7 L17.5 6.3 M4 17 L4.3 14.4 M4 17 L6.5 17.7 M20 17 L19.7 14.4 M20 17 L17.5 17.7"
        stroke="#7fb8d9"
        stroke-width="1"
        stroke-linecap="round"
      />
    </g>

    <!-- Alta Humedad: gotas de agua -->
    <g v-else-if="id === 'alta_humedad'">
      <path d="M9 4 C9 4 5.5 9.5 5.5 12.3 A3.5 3.5 0 0 0 12.5 12.3 C12.5 9.5 9 4 9 4 Z" fill="#5b8dd9" stroke="#345a8a" stroke-width="0.5" />
      <path d="M16 10 C16 10 13.3 14 13.3 16 A2.7 2.7 0 0 0 18.7 16 C18.7 14 16 10 16 10 Z" fill="#5b8dd9" stroke="#345a8a" stroke-width="0.5" opacity="0.85" />
    </g>

    <!-- Explosion Levaduras: burbujas de fermentacion -->
    <g v-else-if="id === 'explosion_levaduras'">
      <circle cx="12" cy="16" r="5" fill="#c9974f" stroke="#7a4f22" stroke-width="0.6" />
      <circle cx="9" cy="9" r="1.6" fill="#e0c979" stroke="#7a4f22" stroke-width="0.4" />
      <circle cx="14" cy="6" r="1.1" fill="#e0c979" stroke="#7a4f22" stroke-width="0.4" />
      <circle cx="16" cy="10.5" r="1.3" fill="#e0c979" stroke="#7a4f22" stroke-width="0.4" />
    </g>

    <!-- Acidificacion Acelerada: tubo de ensayo con gota acida -->
    <g v-else-if="id === 'acidificacion_acelerada'">
      <path
        d="M9.5 3 H14.5 V13.5 A2.5 2.5 0 0 1 12 16 A2.5 2.5 0 0 1 9.5 13.5 Z"
        fill="none"
        stroke="#8fae5c"
        stroke-width="1.2"
        stroke-linejoin="round"
      />
      <path d="M9.5 11 H14.5 V13.5 A2.5 2.5 0 0 1 12 16 A2.5 2.5 0 0 1 9.5 13.5 Z" fill="#a9d97f" opacity="0.8" />
      <path d="M12 17.5 C12 17.5 10 20 10 21.2 A2 2 0 0 0 14 21.2 C14 20 12 17.5 12 17.5 Z" fill="#8fae5c" stroke="#4a6a2f" stroke-width="0.4" />
    </g>

    <!-- Aletargamiento Invernal: copo de nieve dormido (zzz) -->
    <g v-else-if="id === 'aletargamiento_invernal'">
      <path
        d="M9 4 V17 M4.9 7.2 L13.1 13.8 M13.1 7.2 L4.9 13.8"
        stroke="#7fb8d9"
        stroke-width="1.2"
        stroke-linecap="round"
      />
      <text x="13" y="9" font-size="7" fill="#a89a89" font-family="inherit">z</text>
      <text x="16.5" y="6" font-size="5" fill="#a89a89" font-family="inherit">z</text>
    </g>

    <!-- Generico: cualquier carta futura sin icono propio todavia -->
    <circle v-else cx="12" cy="12" r="7" fill="#8a9a8a" stroke="#5a6a5a" stroke-width="0.6" />
  </svg>
</template>

<style scoped>
.icono-clima {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
