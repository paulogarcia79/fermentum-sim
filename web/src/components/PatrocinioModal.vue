<script setup lang="ts">
// Modal obligatorio de arranque: la revelacion de las Cartas de Patrocinio.
//
// El reglamento reparte una carta boca abajo a cada jugador, las revela todas
// a la vez y ordena el Dia 1 por su Iniciativa (RULEBOOK.md §3). En la app
// nada de eso se veia: el jugador arrancaba con unos recursos que no sabia de
// donde salian y en una posicion que OrdenTurnoPanel atribuia a una Jefatura
// que nadie habia podido reclamar. Esto es esa revelacion, una sola vez, ANTES
// del modal del dia (ver la cadena en GameView.vue).
//
// Arriba, como InicioDiaModal, dos mitades: TU carta a la izquierda y la frase
// que importa ("actuas en la posicion N de M") a la derecha. Abajo, a todo el
// ancho, la mesa entera como una fila de cartas en miniatura en el orden del
// Dia 1 -- es informacion publica, la revelacion es simultanea. Una fila de
// cartas y no una tabla: siete columnas con `N (P%)` no caben en los 640px
// del modal y acababan detras de una barra de scroll. La posicion sale de
// `turno_orden`, que ya calculo el motor a partir de las iniciativas; ordenar
// aqui por iniciativa seria una segunda copia de esa regla.
import { computed } from 'vue'
import { reconocerPatrocinio, store } from '../store'
import { hexDeColor } from '../data/coloresJugador'
import CartaPatrocinio from './CartaPatrocinio.vue'
import IconoPeon from './IconoPeon.vue'
import ModalObligatorio from './ModalObligatorio.vue'

const estado = computed(() => store.estado!)
const miIndice = computed(() => store.sesion!.playerIndex)
const yo = computed(() => estado.value.players[miIndice.value])

// Antes del primer iniciar_dia() turno_orden puede venir vacio; en ese caso el
// orden de asiento es la unica aproximacion (mismo criterio que OrdenTurnoPanel).
const orden = computed(() =>
  estado.value.turno_orden.length > 0
    ? estado.value.turno_orden
    : estado.value.players.map((_, i) => i),
)

const miPosicion = computed(() => orden.value.indexOf(miIndice.value) + 1)
const total = computed(() => orden.value.length)
const soyJefe = computed(() => miPosicion.value === 1)
const soyUltimo = computed(() => total.value > 1 && miPosicion.value === total.value)

const filas = computed(() =>
  orden.value.map((idx, pos) => {
    const jugador = estado.value.players[idx]
    return { idx, pos: pos + 1, jugador, carta: jugador.patrocinio }
  }),
)
</script>

<template>
  <ModalObligatorio
    ceja="Preparación · Día 1"
    titulo="Tu Carta de Patrocinio"
    ancho="l"
    etiqueta-boton="Entendido"
    @reconocer="reconocerPatrocinio"
  >
    <div class="rejilla">
      <section class="columna">
        <header class="cabecera-columna tuya">
          <p class="eyebrow">🤝 Tu patrocinador</p>
          <h3>Capital de arranque</h3>
        </header>

        <div class="carta-envoltorio">
          <CartaPatrocinio v-if="yo.patrocinio" :carta="yo.patrocinio" />
          <p v-else class="matiz">Esta partida se armó sin reparto de Patrocinios.</p>
        </div>
      </section>

      <section class="columna">
        <header class="cabecera-columna tuya">
          <p class="eyebrow">📍 Tu posición</p>
          <h3>Día 1</h3>
        </header>

        <p class="posicion" :class="{ jefe: soyJefe }">
          <template v-if="soyJefe">
            👑 Recibes el token de <strong>Investigador Jefe</strong>: abres el Día 1.
          </template>
          <template v-else>
            Actúas en la posición
            <strong class="dato">{{ miPosicion }}</strong> de <span class="dato">{{ total }}</span> en el Día 1<template
              v-if="soyUltimo"
            >
              — cierras la ronda</template
            >.
          </template>
        </p>

        <p class="matiz">
          Los recursos de la carta ya están en tu tablero. Quien actúa más tarde recibe un capital
          mayor, para compensar la ventaja de abrir.
        </p>

        <p class="matiz">
          La Iniciativa solo fija el <strong>Día 1</strong>. Desde mañana abre quien reclame la
          Jefatura durante el día; si nadie la reclama, se queda donde está.
        </p>
      </section>

      <!-- Cruza las dos columnas: la mesa entera, en el orden que las cartas
           acaban de fijar. -->
      <section class="mesa">
        <header class="cabecera-columna compartida">
          <p class="eyebrow">🃏 Revelación simultánea</p>
          <h3>Orden del Día 1</h3>
        </header>

        <ol class="fila-cartas">
          <li v-for="fila in filas" :key="fila.idx" class="puesto" :class="{ propio: fila.idx === miIndice }">
            <p class="puesto-cabecera">
              <span class="recuadro-num dato">{{ fila.pos }}</span>
              <span class="peon"><IconoPeon :color="hexDeColor(fila.jugador.color)" /></span>
              <span class="nombre">
                {{ fila.jugador.nombre }}
                <span v-if="fila.idx === miIndice" class="tu">(tú)</span>
              </span>
              <span v-if="fila.pos === 1" class="tag" title="Investigador Jefe">👑</span>
            </p>
            <CartaPatrocinio v-if="fila.carta" :carta="fila.carta" compacta />
            <p v-else class="matiz">—</p>
          </li>
        </ol>
      </section>
    </div>
  </ModalObligatorio>
</template>

<style scoped>
.rejilla {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--e4) var(--e4);
}

.columna {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  min-width: 0;
}

/* Cobre = lo tuyo; verdin = la mesa compartida. Ver acentos en App.vue. */
.cabecera-columna {
  border-top: 2px solid var(--borde);
  padding-top: var(--e2);
}

.cabecera-columna.tuya {
  border-top-color: var(--cobre);
}

.cabecera-columna.compartida {
  border-top-color: var(--verdin);
}

.cabecera-columna h3 {
  margin: var(--e1) 0 0;
  font-size: var(--t-m);
}

.carta-envoltorio {
  display: flex;
  justify-content: center;
  margin: var(--e2) 0;
}

.posicion {
  margin: 0;
  padding: var(--e2) var(--e3);
  border: 1px solid var(--borde-fuerte);
  border-radius: var(--r-carta);
  font-size: var(--t-s);
  line-height: 1.45;
}

.posicion.jefe {
  border-color: var(--cobre);
  background: var(--lavado-cobre);
}

.matiz {
  margin: 0;
  color: var(--tinta-tenue);
  font-size: var(--t-xs);
  line-height: 1.45;
}

.mesa {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
}

.fila-cartas {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--e3);
}

/* Cada puesto se reparte el ancho: con 2 jugadores las miniaturas crecen, con
   4 se aprietan hasta ~130px sin salirse del modal. */
.puesto {
  flex: 1 1 130px;
  max-width: 200px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e1);
  padding: var(--e1);
  border-radius: var(--r-carta);
}

.puesto.propio {
  background: var(--lavado-cobre);
}

.puesto-cabecera {
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--e1);
  font-size: var(--t-xs);
}

.recuadro-num {
  flex: 0 0 auto;
  width: 1.3rem;
  height: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--carta);
  border: 1px solid var(--borde);
  border-radius: var(--r-control);
  color: var(--tinta-tenue);
}

.puesto.propio .recuadro-num {
  color: var(--cobre);
  border-color: var(--cobre);
}

.peon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.nombre {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tu {
  color: var(--tinta-tenue);
}

.tag {
  flex: 0 0 auto;
}

@media (max-width: 720px) {
  .rejilla {
    grid-template-columns: 1fr;
  }
}
</style>
