# ACTIONS_REGISTRY (Fermentum)
**Descripción General:** Este registro define todas las operaciones válidas que un jugador (o agente) puede ejecutar durante la Fase II: Acción del Día de Laboratorio.

## 1. Reglas Generales de Operación
* Cada jugador dispone de 2 Puntos de Acción (PA) por Día de Laboratorio.
* Al ejecutar una acción, el jugador debe desplazar un Cubo de Laboratorio a su "Checklist de Protocolo" (Zona 5 del tablero) para indicar el consumo del punto.
* Algunas acciones requieren el gasto adicional de tokens (Harina/Agua) o Datos de Investigación.

---

## 2. Catálogo de Acciones Principales (Costo: 1 PA)
*(Nota: La Acción A original se mueve a auxiliares. La Acción B ahora requiere restar 100 unidades de la harina específica en el diccionario).*

### B. Iniciar Receta
* **Costo:** 1 PA + 1 Token de Harina (100% base) + Tokens de Agua (pago exacto según porcentaje de hidratación de la receta).
* **Memoria Biológica:** Se sella el Dado de Inóculo (con la Vitalidad actual) y el Cubo de Laboratorio (con la Acidez actual) en la carta de receta.
* **Condición:** El Cubo de Acidez solo se sella si la acidez del cultivo base se encuentra dentro del rango con bonificación de sabor exigido por la receta.

### C. Adquirir Insumos
* **Costo:** 1 PA.
* **Efecto:** Toma un lote del mercado central. Cada lote es un diccionario aleatorio de recursos (Harina Blanca, Centeno, Integral y Agua) que sumados dan exactamente 150%.
* **Pedido de urgencia:** Pagando +1 Dato, el jugador ignora el mercado y recibe 150% en recursos elegidos a su medida.

### D. Implementar Mejora de Laboratorio
* **Costo:** 1 PA + Datos de Investigación.
    * *Incubadora:* 3 Datos. Permite ajustar temperatura local en +/- 5°C.
    * *Cámara B:* 4 Datos. Desbloquea Estación 03 y mejora la acción de Pliegue.
    * *Módulo Analítico:* 3 Datos. Genera +1 Dato extra al hornear en centro exacto y habilita recetas avanzadas.
* **Reglas:** El beneficio se activa inmediatamente y se marca con un Cubo de Laboratorio en la Zona 4. Solo se puede adquirir una mejora por partida.

### E. Técnica (Pliegues)
* **Costo:** 1 PA.
* **Efecto:** Avanza el marcador de Inóculo de una masa 1 casilla.
* **Sinergia:** Con la mejora Cámara B, el jugador puede optar por recuperar +1 de Vitalidad en su cultivo base o afectar a dos masas simultáneamente.

### F. Hornear (Finalización de Protocolo)
* **Costo:** 1 PA.
* **Efecto:** El jugador obtiene Puntos de Maestría según la zona en la que se encuentre el marcador. Si está en Zona Óptima, también recibe Datos de Investigación.
* **Resolución:** Se suma el Bono de Acidez si la carta tiene el Cubo sellado, se recuperan los componentes, y la carta se guarda en la zona de puntuación. Las masas en Zona Baja o Sobre-fermentada no generan Datos de Investigación.

### G. Investigar Protocolo
* **Costo:** 1 PA.
* **Efecto:** Selecciona 1 Carta de Receta del Mercado Central y la coloca boca arriba en la "Carpeta de Proyectos" (estado inactivo).
* **Límites:** Máximo 3 recetas inactivas. Si está llena, debe descartar una previa.
* **Mercado:** El espacio central queda vacío hasta el "Protocolo de Refresco" del día siguiente.

### Simposio Técnico (Generación de Datos)
* **Costo:** 1 PA.
* **Efecto:** Descartar una Carta de Receta de la carpeta de proyectos o de la estación de fermentación para ganar 1 Dato de Investigación inmediatamente.

---

## 3. Acciones Auxiliares y de Emergencia (Costo: 0 PA)

### A. Mantenimiento del Cultivo (Alimentación)
* **Costo:** 0 PA.
* **Límite:** 1 vez por ronda (valida `accion_alimentar_usada == False`).
* **Efecto Modular:** * Restar 10% de Harina (cualquiera) = +1 Vitalidad (Máx 6).
    * Restar 10% de Agua = +1 Acidez (Máx 6).
    * (Se puede hacer uno, otro, o ambos en la misma acción).

### Horas Extras
* **Costo:** 1 Token de Datos de Investigación.
* **Tipo:** Acción Gratuita (0 PA).
* **Momento:** En cualquier momento durante el turno del jugador en la Fase II.
* **Efecto:** Otorga inmediatamente +1 Punto de Acción (PA) adicional.
* **Límite:** Solo una (1) vez por ronda, por investigador.

### Protocolos de Emergencia (Rescate de Cultivo)
*Solo pueden ejecutarse si la Vitalidad del cultivo base llega a 0, momento en el cual el jugador recibe una penalización de -3 Puntos de Maestría.*
* **H. Re-cultivo Manual:** Costo 1 PA + 2 Harina + 2 Agua. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 1.
* **I. Inóculo de Emergencia:** Costo 1 PA + 2 Datos. Retira contaminación y sitúa Vitalidad y Acidez en Nivel 2.