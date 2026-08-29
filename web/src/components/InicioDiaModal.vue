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
// La diferencia clave entre ambas cartas, y el motivo de la tabla de precios de
// abajo: el clima rige HOY, la tendencia NO -- se aplica al final de este dia y
// rige los precios de MAÑANA (ver engine.py: robar_tendencia /
// aplicar_tendencia_pendiente). Por eso se muestra el antes/despues concreto en
// monedas y no solo el modificador crudo.
import { computed } from 'vue'
import { reconocerInicioDia, store } from '../store'
import { efectoBiologicoTexto as bioTexto, efectoPasivoTexto as pasivoTexto } from '../climaTexto'
import { textoTendencia } from '../tendenciaTexto'
import { precioCompraHarina, precioVentaHarina } from '../data/preciosHarina'
import type { TipoHarina } from '../types'
import CartaClima from './CartaClima.vue'
import CartaTendencia from './CartaTendencia.vue'

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
  <div class="fondo-modal">
    <div class="modal panel">
      <h2>Inicio del Día {{ env.dia_actual }}</h2>

      <h3 class="seccion">🌦️ Evento Climático — rige hoy</h3>

      <div class="carta-envoltorio">
        <CartaClima :carta="carta" />
      </div>

      <ul class="lista">
        <li>
          Modificador térmico: {{ carta.modificador_termico >= 0 ? '+' : '' }}{{ carta.modificador_termico }}°C →
          Temperatura hoy: {{ env.temperatura_actual }}°C
        </li>
        <li>Avance base de fermentación hoy: {{ avanceBase }} casillas (antes del dado de inóculo y la incubadora)</li>
        <li v-if="efectoBiologicoTexto">🧪 {{ efectoBiologicoTexto }}</li>
        <li>⚙️ Efecto pasivo vigente: {{ efectoPasivoTexto }}</li>
      </ul>

      <template v-if="tendencia !== null">
        <h3 class="seccion">📈 Tendencia de Mercado — rige mañana</h3>

        <div class="carta-envoltorio">
          <CartaTendencia :modificador="tendencia" />
        </div>

        <p class="aviso-timing">
          <strong>Los precios de hoy NO cambian.</strong>
          Esta carta se aplica al <strong>final del día</strong>, así que fija los precios de la Bolsa de
          Harinas para <strong>mañana</strong>. Tienes todo el día de hoy para comprar o vender sabiendo
          hacia dónde van.
        </p>

        <ul class="lista">
          <li>{{ textoTendencia(tendencia) }}</li>
        </ul>

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
              <td>{{ fila.compraHoy }}</td>
              <td :class="{ cambia: fila.cambia }">{{ fila.compraManana }}</td>
              <td>{{ fila.ventaHoy }}</td>
              <td :class="{ cambia: fila.cambia }">{{ fila.ventaManana }}</td>
            </tr>
          </tbody>
        </table>
      </template>

      <button class="primario" @click="reconocerInicioDia">Entendido</button>
    </div>
  </div>
</template>

<style scoped>
.fondo-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 1rem;
}

.modal {
  max-width: 480px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin-top: 0;
}

.seccion {
  font-size: 0.9rem;
  margin: 0 0 0.6rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--color-borde);
  color: var(--color-texto-tenue);
}

.carta-envoltorio {
  display: flex;
  justify-content: center;
  margin-bottom: 0.75rem;
}

.lista {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.88rem;
}

.aviso-timing {
  margin: 0 0 0.75rem;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--color-acento);
  border-radius: 6px;
  background: rgba(217, 154, 63, 0.15);
  font-size: 0.82rem;
  line-height: 1.45;
}

.tabla-precios {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  margin-bottom: 1rem;
}

.tabla-precios th,
.tabla-precios td {
  padding: 0.25rem 0.35rem;
  text-align: center;
  border-bottom: 1px solid var(--color-borde);
}

.tabla-precios thead th {
  color: var(--color-texto-tenue);
  font-weight: 600;
}

.tabla-precios .sub th {
  font-weight: 400;
  font-size: 0.72rem;
  padding-top: 0;
}

.tabla-precios .tipo {
  text-align: left;
}

.tabla-precios .cambia {
  color: var(--color-acento);
  font-weight: 600;
}

button.primario {
  width: 100%;
  padding: 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--color-acento);
  background: var(--color-acento);
  color: #1a1410;
  font-weight: 600;
}
</style>
