<script setup lang="ts">
// Modal obligatorio al inicio de cada dia. Anuncia las DOS cartas que revela
// la Fase I -- el clima y la tendencia de mercado -- en una sola pasada, en
// vez de encadenar dos modales bloqueantes cada dia.
//
// Mismo tratamiento que FermentationReportModal.vue le da a los colapsos: algo
// que se le dice explicitamente al jugador, no algo que tenga que notar por su
// cuenta en MazoClimaPanel.vue / MazoTendenciasPanel.vue. A diferencia de ese
// modal, este se arma a partir del estado actual (no del registro de eventos),
// ya que environment.ultima_carta_clima y market.tendencia_pendiente siempre
// reflejan lo de "hoy".
//
// La diferencia clave entre ambas cartas: el clima rige HOY, la tendencia NO
// -- se aplica al final de este dia y rige los precios de MAÑANA (ver
// engine.py: robar_tendencia / aplicar_tendencia_pendiente). Eso lo dice ahora
// la MAQUETA, no solo un parrafo en negrita: dos columnas rotuladas "rige hoy"
// / "rige mañana", una carta en cada una. La tabla de precios cruza las dos por
// debajo porque es justamente donde se ve la consecuencia -- el antes/despues
// concreto en monedas, no el modificador crudo.
import { computed } from 'vue'
import { reconocerInicioDia, store } from '../store'
import { efectoBiologicoTexto as bioTexto, efectoPasivoTexto as pasivoTexto } from '../climaTexto'
import { textoTendencia } from '../tendenciaTexto'
import { precioCompraHarina, precioVentaHarina } from '../data/preciosHarina'
import type { TipoHarina } from '../types'
import CartaClima from './CartaClima.vue'
import CartaTendencia from './CartaTendencia.vue'
import ModalObligatorio from './ModalObligatorio.vue'

const TIPOS: TipoHarina[] = ['Blanca', 'Integral', 'Centeno']
const POSICION_MIN = 1
const POSICION_MAX = 5

const env = computed(() => store.estado!.environment)
const mercado = computed(() => store.estado!.market)
const carta = computed(() => env.value.ultima_carta_clima!)
const avanceBase = computed(() => Math.floor(env.value.temperatura_actual / 5))

const efectoBiologicoTexto = computed(() => bioTexto(carta.value))
const efectoPasivoTexto = computed(() => pasivoTexto(carta.value) ?? 'Ninguno — desgaste y costos normales hoy.')

const tendencia = computed(() => mercado.value.tendencia_pendiente)

/** Precios de hoy y los que dejará la tendencia al aplicarse esta noche.
 * El desplazamiento replica engine.py: Market.aplicar_tendencia -- los 3
 * visores se mueven a la vez, cada uno con su propio tope [1, 5]. */
const preciosComparados = computed(() => {
  const modificador = tendencia.value ?? 0
  return TIPOS.map((tipo) => {
    const hoy = mercado.value.posiciones_harina[tipo]
    const manana = Math.max(POSICION_MIN, Math.min(POSICION_MAX, hoy + modificador))
    return {
      tipo,
      compraHoy: precioCompraHarina(tipo, hoy),
      compraManana: precioCompraHarina(tipo, manana),
      ventaHoy: precioVentaHarina(tipo, hoy),
      ventaManana: precioVentaHarina(tipo, manana),
      cambia: manana !== hoy,
    }
  })
})
</script>

<template>
  <ModalObligatorio
    :ceja="`Fase I · Día ${env.dia_actual}`"
    titulo="Inicio del Día"
    ancho="l"
    etiqueta-boton="Entendido"
    @reconocer="reconocerInicioDia"
  >
    <div class="rejilla">
      <section class="columna">
        <header class="cabecera-columna hoy">
          <p class="eyebrow">🌦️ Rige hoy</p>
          <h3>Evento Climático</h3>
        </header>

        <div class="carta-envoltorio">
          <CartaClima :carta="carta" />
        </div>

        <ul class="lista">
          <li>
            Modificador térmico
            <span class="dato">{{ carta.modificador_termico >= 0 ? '+' : '' }}{{ carta.modificador_termico }}°C</span>
            → temperatura hoy <span class="dato">{{ env.temperatura_actual }}°C</span>
          </li>
          <li>
            Avance base de fermentación: <span class="dato">{{ avanceBase }}</span> casillas
            <span class="matiz">(antes del dado de inóculo y la incubadora)</span>
          </li>
          <li v-if="efectoBiologicoTexto">🧪 {{ efectoBiologicoTexto }}</li>
          <li>⚙️ Efecto pasivo vigente: {{ efectoPasivoTexto }}</li>
        </ul>
      </section>

      <section class="columna">
        <header class="cabecera-columna manana">
          <p class="eyebrow">📈 Rige mañana</p>
          <h3>Tendencia de Mercado</h3>
        </header>

        <div class="carta-envoltorio">
          <CartaTendencia :modificador="tendencia" />
        </div>

        <template v-if="tendencia !== null">
          <p class="aviso-timing">
            <strong>Los precios de hoy NO cambian.</strong>
            Esta carta se aplica al <strong>final del día</strong>, así que fija los precios de la Bolsa de
            Harinas para <strong>mañana</strong>. Tienes todo el día de hoy para comprar o vender sabiendo
            hacia dónde van.
          </p>

          <ul class="lista">
            <li>{{ textoTendencia(tendencia) }}</li>
          </ul>
        </template>

        <p v-else class="lista sin-tendencia">
          Mazo de tendencias agotado — los precios de la Bolsa no se moverán esta noche.
        </p>
      </section>

      <!-- Cruza las dos columnas: es donde el "hoy vs mañana" de arriba se
           vuelve un numero que el jugador puede usar para decidir hoy. -->
      <section v-if="tendencia !== null" class="bolsa">
        <p class="eyebrow">Bolsa de Harinas — efecto de la tendencia</p>

        <table class="tabla-precios">
          <thead>
            <tr>
              <th>Harina</th>
              <th colspan="2">Comprar</th>
              <th colspan="2">Vender</th>
            </tr>
            <tr class="sub">
              <th></th>
              <th>hoy</th>
              <th>mañana</th>
              <th>hoy</th>
              <th>mañana</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fila in preciosComparados" :key="fila.tipo">
              <td class="tipo">{{ fila.tipo }}</td>
              <td class="dato">{{ fila.compraHoy }}</td>
              <td class="dato" :class="{ cambia: fila.cambia }">{{ fila.compraManana }}</td>
              <td class="dato">{{ fila.ventaHoy }}</td>
              <td class="dato" :class="{ cambia: fila.cambia }">{{ fila.ventaManana }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </ModalObligatorio>
</template>

<style scoped>
.rejilla {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--e4) var(--e3);
}

.columna {
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  min-width: 0;
}

/* La regla superior de color es lo que separa las dos columnas de un vistazo:
   cobre = lo tuyo/lo activo (hoy), verdin = estado de mercado compartido
   (mañana). Ver el sistema de acentos en App.vue. */
.cabecera-columna {
  border-top: 2px solid var(--borde);
  padding-top: var(--e2);
}

.cabecera-columna.hoy {
  border-top-color: var(--cobre);
}

.cabecera-columna.manana {
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

.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--e2);
  font-size: var(--t-s);
  line-height: 1.4;
}

.matiz {
  color: var(--tinta-tenue);
}

.sin-tendencia {
  color: var(--tinta-tenue);
  font-style: italic;
}

.aviso-timing {
  margin: 0;
  padding: var(--e2) var(--e3);
  border: 1px solid var(--cobre);
  border-radius: var(--r-carta);
  background: var(--lavado-cobre);
  font-size: var(--t-s);
  line-height: 1.45;
}

.bolsa {
  grid-column: 1 / -1;
  border-top: 1px solid var(--borde);
  padding-top: var(--e3);
}

.tabla-precios {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--t-s);
  margin-top: var(--e2);
}

.tabla-precios th,
.tabla-precios td {
  padding: var(--e1) var(--e2);
  text-align: center;
  border-bottom: 1px solid var(--borde);
}

.tabla-precios tbody tr:last-child td {
  border-bottom: none;
}

.tabla-precios thead th {
  color: var(--tinta-tenue);
  font-weight: 600;
}

.tabla-precios .sub th {
  font-weight: 400;
  font-size: var(--t-xs);
  padding-top: 0;
}

.tabla-precios .tipo {
  text-align: left;
}

.tabla-precios .cambia {
  color: var(--cobre);
  font-weight: 600;
}

/* Mismo punto de corte que el resto del sistema. Al apilar se recupera el
   orden narrativo de siempre: clima -> tendencia -> precios. */
@media (max-width: 720px) {
  .rejilla {
    grid-template-columns: 1fr;
  }
}
</style>
