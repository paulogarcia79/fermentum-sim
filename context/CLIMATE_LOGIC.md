# CLIMATE_LOGIC (Fermentum)
**Descripción General:** Este archivo define las reglas termodinámicas y biológicas del tablero central. Contiene el algoritmo matemático que dicta el avance automático de las masas en fermentación y la base de datos de los eventos climáticos.

## 1. Variables de Entorno (Estado Global)
Para la simulación, el entorno (`Environment`) debe mantener un registro de las siguientes variables durante cada ronda (Día de Laboratorio):
* `temperatura_actual` (Integer): Temperatura del laboratorio. Inicia siempre en 20°C en la preparación del juego.
* `avance_base` (Integer): Resultado del Ábaco de Fermentación. Se calcula como `temperatura_actual / 5`. (Ej: 20°C = 4 casillas).
* `efecto_pasivo_activo` (String / None): Registra si hay una condición especial vigente para la ronda (ej. "Alta Humedad" o "Aletargamiento").

---

## 2. Catálogo del Mazo de Clima (Dataset de 30 Cartas)
Este mazo actúa como temporizador del juego (se roba una carta al inicio de cada Fase I) y altera el entorno.

*Nota:* el Mercado de Tendencias (mazo de 21 cartas que fija el precio de la Bolsa de Harinas) es un mazo independiente, robado también en Fase I pero después del Clima — ver CORE_MECHANICS.md §2 y ACTIONS_REGISTRY.md §2C. No interactúa con la temperatura ni con este mazo.

| ID Evento (Cantidad) | Modificador Térmico | Efecto Biológico Inmediato (Fase I) | Efecto Pasivo / Impacto en Fase III |
| :--- | :--- | :--- | :--- |
| **Estabilidad Térmica** (x10) | 0°C | Ninguno | Ninguno. Avance normal. |
| **Fallo Refrigeración** (x4) | +5°C | Ninguno | Ninguno. (Acelera avance base en +1). |
| **Ola de Calor** (x2) | +10°C | Ninguno | Ninguno. (Acelera avance base en +2). |
| **Corriente de Aire** (x4) | -5°C | Ninguno | Ninguno. (Ralentiza avance base en -1). |
| **Fallo Calefacción** (x2) | -10°C | Ninguno | Ninguno. (Ralentiza avance base en -2). |
| **Alta Humedad** (x2) | 0°C | Ninguno | Iniciar Receta (Acción B) cuesta 1 Token de Agua menos este turno. |
| **Explosión Levaduras** (x2) | 0°C | Todos los jugadores ganan +1 Vitalidad (Máx 6). | Ninguno. |
| **Acidificación Acelerada** (x2)| 0°C | Todos los jugadores ganan +1 Acidez (Máx 6). | Ninguno. |
| **Aletargamiento Invernal** (x2)| -5°C | Ninguno | Desgaste masivo: En Fase III, el cultivo base sufre -2 Vitalidad (en lugar del -1 normal). |

---

## 3. Algoritmo de Cinética Biológica (Fase III)
Durante la Fase III (Fermentación), todas las masas activas en las estaciones de trabajo de los jugadores deben avanzar de forma simultánea. El motor de juego debe calcular el avance exacto de cada carta usando la siguiente ecuación:

`Avance_Final = (temperatura_actual / 5) + valor_dado_inoculo + modificador_incubadora`

* **`temperatura_actual / 5`**: Representa la inercia térmica global (Ábaco de Fermentación).
* **`valor_dado_inoculo`**: Es el valor numérico (del 1 al 6) que se selló en la masa al momento de ejecutar la Acción B (Iniciar Receta).
* **`modificador_incubadora`**: Si el jugador posee la tecnología "Incubadora", puede inyectar un valor de `+1`, `-1` o `0` a esta masa específica para mitigar el clima.

### Reglas de Ejecución del Algoritmo
1. **Independencia del Cultivo:** El cálculo utiliza el valor del `dado_inoculo` guardado en la carta de la masa, NO el nivel de Vitalidad actual del frasco base del jugador.
2. **Límite de Colapso:** Después de aplicar el `Avance_Final` a la posición actual de la masa, el sistema evalúa si la nueva posición es mayor o igual al límite inferior de la `zona_sobrefermentada` de esa receta.
3. **Trigger de Emergencia:** Si entra en sobre-fermentación, se gatilla inmediatamente una acción automática de Horneado con 0 costo de PA, aplicando la penalización correspondiente.

---

## 4. Desgaste Metabólico (Final de Fase III)
Tras procesar el avance de todas las masas, el entorno aplica el consumo de energía a los cultivos base (Masa Madre) de todos los jugadores:
* **Desgaste Estándar:** La Vitalidad del cultivo base se reduce en `-1`.
* **Modificador Aletargamiento:** Si el evento climático vigente es "Aletargamiento Invernal", la reducción de Vitalidad es `-2`.
* **Límite Suelo:** La Vitalidad nunca puede descender por debajo de `0`. (Si llega a 0, el jugador queda penalizado y requiere Protocolos de Emergencia).