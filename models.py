"""
models.py — Motor Lógico de Fermentum
======================================
Define todas las entidades de datos puras del simulador del juego de mesa Fermentum.

Contenido:
  · Enumeraciones de dominio (Grado, TipoHarina, TecnologiaID, …)
  · Entidades inmutables del catálogo (Recipe, ClimateCard)
  · Entidades mutables de estado de partida (FermentationSlot, HorneadoRecord,
    Technologies, Player, Environment)
  · Catálogos maestros constantes (RECIPE_CATALOG, CLIMATE_CATALOG)
  · Funciones de utilidad para el setup inicial

Estándares aplicados (ARCHITECTURE.md):
  · Strict type hinting en todos los atributos, métodos y retornos (PEP 484)
  · @dataclass para todas las entidades; frozen=True en entidades de catálogo
  · Inmutabilidad del catálogo: RECIPE_CATALOG y CLIMATE_CATALOG son constantes
  · Separación de responsabilidades: sólo datos puros, sin lógica de turnos
  · Excepciones semánticas pertenecen a exceptions.py (fuera del alcance aquí)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional, Tuple
from types import MappingProxyType


# ===========================================================================
# SECCIÓN 1: ENUMERACIONES DE DOMINIO
# ===========================================================================


class Grado(str, Enum):
    """Nivel de complejidad de una receta de panificación."""

    BASICA = "Básica"
    AVANZADA = "Avanzada"


class TipoHarina(str, Enum):
    """Tipos de token de harina disponibles en el mercado central."""

    BLANCA = "Blanca"
    CENTENO = "Centeno"
    INTEGRAL = "Integral"


class TecnologiaID(str, Enum):
    """
    Identificadores de las mejoras de laboratorio (Zona 4 del tablero personal).
    Los valores de cadena coinciden con los nombres de atributo en Technologies.
    """

    INCUBADORA = "incubadora"
    CAMARA_B = "camara_b"
    MODULO_ANALITICO = "modulo_analitico"


class EfectoClimatico(str, Enum):
    """
    Efectos pasivos que una carta de clima puede activar durante la Fase III.
    Solo los efectos que alteran la resolución automática tienen entrada aquí.
    """

    NINGUNO = "ninguno"
    ALTA_HUMEDAD = "Alta Humedad"
    ALETARGAMIENTO_INVERNAL = "Aletargamiento Invernal"


class EfectoBiologico(str, Enum):
    """
    Efectos biológicos inmediatos de las cartas de clima, aplicados a todos
    los jugadores durante la Fase I (antes de las acciones).
    """

    NINGUNO = "ninguno"
    GANANCIA_VITALIDAD = "Ganancia Vitalidad"  # +1 Vitalidad a todos (máx 6)
    GANANCIA_ACIDEZ = "Ganancia Acidez"  # +1 Acidez a todos (máx 6)


# ===========================================================================
# SECCIÓN 2: ENTIDADES DE CATÁLOGO INMUTABLES
# ===========================================================================


@dataclass(frozen=True)
class Recipe:
    """
    Representa una carta de receta del catálogo maestro.

    Inmutable (frozen=True): todas las instancias son referencias de solo lectura
    compartidas entre el catálogo, las carpetas de jugadores y las estaciones.

    Attributes:
        id: Identificador único de la receta (snake_case, ej. "pan_de_campo").
        nombre: Nombre legible para mostrar en la interfaz.
        grado: Nivel de complejidad (Básica / Avanzada).
        harina_base: Tipo de token de harina que consume la receta.
        hidratacion_pct: Porcentaje total de hidratación de la masa.
        tokens_agua: Cantidad de tokens de agua (5% c/u) requeridos para iniciarla.
        acidez_diana: Conjunto de niveles de acidez que activan el Bono de Sabor.
        bono_sabor_pts: Puntos de Maestría del bono de acidez impresos en la carta.
            NOTA: No especificado en la tabla de RECIPE_DATABASE.md; se asignan
            valores coherentes con el balance: +2 pts (Básica) / +3-4 pts (Avanzada).
        zona_baja: Rango [inicio, fin] del track donde la masa está cruda (pocos puntos).
        zona_optima: Rango [inicio, fin] objetivo (puntos máximos y posible Dato extra).
        zona_sobrefermentada: Rango [inicio, fin] donde la masa colapsa automáticamente.
        puntos_optimos: Puntos de Maestría al hornear dentro de zona_optima.
        penalizacion_colapso: Puntos negativos aplicados en un horneado de emergencia.
        req_tecnologico: Mejora de laboratorio necesaria para iniciar la receta
            si es Avanzada (None para las Básicas).
    """

    id: str
    nombre: str
    grado: Grado
    harina_base: TipoHarina
    hidratacion_pct: int
    tokens_agua: int
    acidez_diana: Tuple[int, ...]
    bono_sabor_pts: int
    zona_baja: Tuple[int, int]
    zona_optima: Tuple[int, int]
    zona_sobrefermentada: Tuple[int, int]
    puntos_optimos: int
    penalizacion_colapso: int  # Valor negativo, ej. -2
    req_tecnologico: Optional[TecnologiaID]

    # ------------------------------------------------------------------
    # Métodos de consulta de zona (sin efectos secundarios)
    # ------------------------------------------------------------------

    def esta_en_zona_baja(self, posicion: int) -> bool:
        """Retorna True si la posición está dentro del rango de masa cruda."""
        return self.zona_baja[0] <= posicion <= self.zona_baja[1]

    def esta_en_zona_optima(self, posicion: int) -> bool:
        """Retorna True si la posición está dentro del rango de horneado óptimo."""
        return self.zona_optima[0] <= posicion <= self.zona_optima[1]

    def esta_sobrefermentada(self, posicion: int) -> bool:
        """
        Retorna True si la posición alcanzó el colapso estructural.
        Gatilla un horneado automático de emergencia en la Fase III.
        """
        return posicion >= self.zona_sobrefermentada[0]

    def es_centro_exacto(self, posicion: int) -> bool:
        """
        Retorna True si la posición es el punto central exacto de la zona óptima.
        El centro exacto activa el bono del Módulo Analítico (+1 Dato de Investigación).
        """
        inicio, fin = self.zona_optima
        return posicion == (inicio + fin) // 2

    def acidez_activa_bono(self, acidez_actual: int) -> bool:
        """
        Comprueba si el nivel de acidez dado coincide con la acidez_diana de la receta.
        Se invoca al sellar el Cubo de Laboratorio en la Acción B (Iniciar Receta).
        """
        return acidez_actual in self.acidez_diana


@dataclass(frozen=True)
class ClimateCard:
    """
    Representa un tipo de carta del mazo de Clima.

    Inmutable: funciona como plantilla. El mazo construido contiene referencias
    a estas instancias (ver build_climate_deck()).

    Attributes:
        id: Identificador único del tipo de carta (snake_case).
        nombre: Nombre del evento climático para mostrar.
        cantidad: Número de copias de esta carta en el mazo maestro (30 total).
        modificador_termico: Variación de temperatura en °C aplicada al entorno.
        efecto_biologico: Efecto instantáneo aplicado en Fase I a todos los jugadores.
        efecto_pasivo: Condición especial vigente durante la resolución de Fase III.
    """

    id: str
    nombre: str
    cantidad: int
    modificador_termico: int
    efecto_biologico: EfectoBiologico
    efecto_pasivo: EfectoClimatico


# ===========================================================================
# SECCIÓN 3: ENTIDADES DE ESTADO DE PARTIDA (MUTABLES)
# ===========================================================================


@dataclass
class FermentationSlot:
    """
    Masa activa en una estación de fermentación (Zona 2 del tablero personal).
    Creada al ejecutar la Acción B (Iniciar Receta) y destruida al hornear.

    Attributes:
        recipe: Referencia a la carta de receta del catálogo (solo lectura).
        dado_inoculo: Valor sellado del dado = Vitalidad del jugador al iniciar (1–6).
            Determina la velocidad de fermentación de esta masa específica.
        posicion_track: Posición acumulada en el track de fermentación (inicia en 0).
        bono_sabor: True si la acidez al iniciar estaba dentro de acidez_diana.
            Se sella el Cubo de Laboratorio en la carta si es True.
        modificador_incubadora: Ajuste de avance local (-1 / 0 / +1).
            Solo aplicable si el jugador tiene la tecnología Incubadora instalada.
    """

    recipe: Recipe
    dado_inoculo: int  # Campo requerido — debe ser 1-6 (= Vitalidad al iniciar)
    posicion_track: int = 0
    bono_sabor: bool = False
    modificador_incubadora: int = 0  # -1, 0 o +1

    def __post_init__(self) -> None:
        # Validaciones de integridad de datos en el origen.
        # Las violaciones de regla de negocio (ej. PA insuficientes) se
        # gestionan en engine.py mediante excepciones de exceptions.py.
        if not (1 <= self.dado_inoculo <= 6):
            raise ValueError(
                f"dado_inoculo debe estar entre 1 y 6 (= Vitalidad al iniciar). "
                f"Recibido: {self.dado_inoculo}"
            )
        if self.modificador_incubadora not in (-1, 0, 1):
            raise ValueError(
                f"modificador_incubadora debe ser -1, 0 o 1. "
                f"Recibido: {self.modificador_incubadora}"
            )

    def calcular_avance(self, temperatura_actual: int) -> int:
        """
        Calcula el avance de la masa durante la Fase III (Cinética Biológica).

        Fórmula (CLIMATE_LOGIC.md §3):
            Avance_Final = (temperatura_actual // 5) + dado_inoculo + modificador_incubadora

        Args:
            temperatura_actual: Temperatura del laboratorio en el turno actual (°C).

        Returns:
            Número de casillas que avanza esta masa en su track de fermentación.
        """
        return (temperatura_actual // 5) + self.dado_inoculo + self.modificador_incubadora


@dataclass(frozen=True)
class HorneadoRecord:
    """
    Registro inmutable de una receta completada (horneado exitoso o colapso).
    Almacenado en `archivo_horneado_exitoso` o `archivo_colapsos` del jugador.

    Attributes:
        recipe: Carta de receta completada.
        posicion_final: Posición del track en el momento del horneado.
        puntos_base: Puntos de Maestría obtenidos por la zona del track.
            Positivos si zona óptima/baja, negativo (penalizacion_colapso) si colapso.
        bono_sabor_aplicado: True si el Cubo de Laboratorio estaba sellado en la carta.
        fue_colapso: True si el horneado fue de emergencia (masa sobrefermentada).
        datos_obtenidos: Datos de Investigación recibidos al hornear.
            0 si fue colapso o si la posición no es zona óptima.
    """

    recipe: Recipe
    posicion_final: int
    puntos_base: int
    bono_sabor_aplicado: bool
    fue_colapso: bool
    datos_obtenidos: int = 0

    @property
    def puntos_totales(self) -> int:
        """Suma de puntos base y bono de sabor para este horneado."""
        bonus = self.recipe.bono_sabor_pts if self.bono_sabor_aplicado else 0
        return self.puntos_base + bonus


@dataclass
class Technologies:
    """
    Estado de las mejoras de laboratorio instaladas (Zona 4 del tablero personal).

    Regla de negocio (validada en engine.py): solo se puede instalar UNA mejora
    por partida; esta clase únicamente registra qué está instalado.

    Attributes:
        incubadora: Permite ajuste local de temperatura ±5°C en la Fase III
            para una masa específica (modificador_incubadora = ±1).
        camara_b: Desbloquea la Estación 03 (índice 2) y mejora la Acción E (Pliegues):
            recupera +1 Vitalidad o afecta dos masas simultáneamente.
        modulo_analitico: Genera +1 Dato al hornear en centro exacto y
            habilita el inicio de recetas de grado Avanzado.
    """

    incubadora: bool = False
    camara_b: bool = False
    modulo_analitico: bool = False

    def esta_activa(self, tecnologia: TecnologiaID) -> bool:
        """Retorna True si la tecnología especificada está instalada."""
        return bool(getattr(self, tecnologia.value))

    def activar(self, tecnologia: TecnologiaID) -> None:
        """Marca una tecnología como instalada. Sin validaciones: responsabilidad del engine."""
        setattr(self, tecnologia.value, True)

    @property
    def cantidad_instaladas(self) -> int:
        """Número de mejoras actualmente instaladas (máximo 1 por partida)."""
        return sum([self.incubadora, self.camara_b, self.modulo_analitico])


@dataclass
class Player:
    """
    Estado completo del tablero personal de un investigador (jugador).

    Cubre:
      · Zona 1: Cultivo Base (Masa Madre) — vitalidad y acidez
      · Zona 2: Estaciones de Fermentación — hasta 3 masas activas
      · Zona 4: Tecnologías de Laboratorio
      · Archivos de Cartas: carpeta de proyectos y archivos de resultados
      · Recursos económicos: datos de investigación, tokens de insumos
      · Seguimiento de turno: PA disponibles, uso de horas extras

    Inicialización recomendada:
        player = Player.crear_dia_1(nombre="Investigador 1", receta_inicial=receta)
    """

    nombre: str

    # ------------------------------------------------------------------
    # Zona 1: Cultivo Base (Masa Madre)
    # ------------------------------------------------------------------

    vitalidad: int = 0
    """Nivel de actividad de la levadura. Rango estricto: [0, 6]."""

    acidez: int = 0
    """Perfil ácido del cultivo base. Rango estricto: [0, 6]."""

    en_estado_contaminacion: bool = False
    """
    True si la vitalidad llegó a 0 y aún no se ejecutó un Protocolo de Emergencia
    (Acción H o I). Mientras está activo, algunas acciones pueden bloquearse.
    """

    # ------------------------------------------------------------------
    # Atributos Operativos y Económicos
    # ------------------------------------------------------------------

    puntos_accion: int = 0
    """
    PA disponibles en la Fase II actual.
    Se reinician a 2 al inicio de cada Fase II; pueden subir a 3 con Horas Extras.
    """

    datos_investigacion: int = 0
    """Moneda virtual para comprar mejoras de laboratorio y PA adicionales."""

    reserva_harina: Dict[str, int] = field(
        default_factory=lambda: {"Blanca": 0, "Centeno": 0, "Integral": 0}
    )
    """
    Reserva de harina por tipo. Las claves son los nombres de los tipos
    ("Blanca", "Centeno", "Integral") y los valores son porcentajes en
    múltiplos de 10 (ej. 100 = una bolsa completa, 0 = sin reserva).
    """

    accion_alimentar_usada: bool = False
    """
    True si la Acción A (Alimentar) ya fue ejecutada este turno de Fase II.
    Se reinicia a False al inicio de cada Fase II.
    """

    reserva_agua: int = 0
    """
    Total de tokens de hidratación disponibles.
    Cada unidad representa un 5% de hidratación (ej. 12 tokens = 60%).
    """

    # ------------------------------------------------------------------
    # Zona 2: Estaciones de Fermentación (3 ranuras)
    # ------------------------------------------------------------------

    estaciones_fermentacion: List[Optional[FermentationSlot]] = field(
        default_factory=lambda: [None, None, None]
    )
    """
    Lista de 3 ranuras de fermentación [estacion_01, estacion_02, estacion_03].
    · Índices 0 y 1: siempre disponibles.
    · Índice 2 (Estación 03): bloqueada hasta que tecnologias.camara_b == True.
    None indica estación libre; FermentationSlot indica masa en curso.
    """

    dados_inoculo: int = 0
    """
    Cantidad de dados físicos disponibles para iniciar nuevas masas (máximo 3).
    Se consume 1 al ejecutar Acción B (Iniciar Receta).
    Se recupera 1 al ejecutar Acción F (Hornear).
    """

    # ------------------------------------------------------------------
    # Zona 4: Tecnologías de Laboratorio
    # ------------------------------------------------------------------

    tecnologias: Technologies = field(default_factory=Technologies)

    # ------------------------------------------------------------------
    # Archivos de Cartas
    # ------------------------------------------------------------------

    carpeta_proyectos: List[Recipe] = field(default_factory=list)
    """
    Recetas investigadas pendientes de iniciar (estado inactivo).
    Límite estricto: máximo 3 cartas. Acción G (Investigar Protocolo) las agrega.
    """

    archivo_horneado_exitoso: List[HorneadoRecord] = field(default_factory=list)
    """
    Registros de recetas horneadas con puntuación positiva.
    Gatillo de fin de partida: len(archivo_horneado_exitoso) >= 5.
    """

    archivo_colapsos: List[HorneadoRecord] = field(default_factory=list)
    """
    Registros de recetas retiradas de emergencia (sobrefermentadas) con puntuación negativa.
    No cuenta para el gatillo de fin de partida.
    """

    # ------------------------------------------------------------------
    # Seguimiento de Turno (se resetea al inicio de cada Fase II)
    # ------------------------------------------------------------------

    horas_extras_usadas: bool = False
    """
    Indica si ya se usó la acción auxiliar 'Horas Extras' en el día actual.
    Solo se puede usar una vez por día. Se resetea en resetear_puntos_accion().
    """

    # ------------------------------------------------------------------
    # Seguimiento de Penalizaciones Acumuladas
    # ------------------------------------------------------------------

    contador_contaminaciones: int = 0
    """
    Número de episodios en los que la Vitalidad llegó a 0 durante la partida.
    Cada episodio aplica -3 Puntos de Maestría al final del juego.
    """

    # ==================================================================
    # FACTORY METHOD — Inicialización correcta para el Día 1
    # ==================================================================

    @classmethod
    def crear_dia_1(
        cls,
        nombre: str,
        receta_inicial: Recipe,
        player_index: int = 0,
    ) -> "Player":
        """
        Crea e inicializa un jugador con el estado exacto descrito en PLAYER_STATE.md §2.

        Valores fijados en el Día 1:
          · vitalidad = 1, acidez = 1
          · dados_inoculo = 3, puntos_accion = 0
          · carpeta_proyectos = [receta_inicial]
          · todas las tecnologías inactivas
          · recursos asimétricos según player_index (PLAYER_STATE.md §2):
              Índice 0 → harina=[Blanca], agua=0,  datos=1
              Índice 1 → harina=[Blanca], agua=10, datos=1
              Índice 2 → harina=[Blanca], agua=20, datos=1
              Índice 3 → harina=[Blanca], agua=20, datos=2

        Args:
            nombre: Nombre o identificador del investigador.
            receta_inicial: Carta de receta de grado 'Básica' asignada aleatoriamente
                (usar seleccionar_receta_inicial() para elección automática).
            player_index: Posición en el orden de turno (0 = primero, 3 = último).
                Determina los recursos iniciales asimétricos.

        Returns:
            Instancia de Player completamente configurada para el inicio de partida.

        Raises:
            ValueError: Si receta_inicial no es de grado Básica (regla del setup).
            ValueError: Si player_index está fuera del rango 0-3.
        """
        if receta_inicial.grado != Grado.BASICA:
            raise ValueError(
                f"La receta inicial del Día 1 debe ser de grado '{Grado.BASICA.value}'. "
                f"Recibido: '{receta_inicial.grado.value}' (id='{receta_inicial.id}')."
            )
        if player_index not in range(4):
            raise ValueError(
                f"player_index debe estar en el rango 0-3. Recibido: {player_index}."
            )
        player = cls(nombre=nombre)
        player._aplicar_setup_dia_1(receta_inicial, player_index)
        return player

    def _aplicar_setup_dia_1(self, receta_inicial: Recipe, player_index: int = 0) -> None:
        """Aplica los valores de inicialización del Día 1 (PLAYER_STATE.md §2)."""
        # --- Recursos asimétricos según orden de turno (PLAYER_STATE.md §2) ---
        _recursos: Dict[int, Tuple[int, int, int]] = {
            0: (0,  0, 1),
            1: (0, 10, 1),
            2: (0, 20, 1),
            3: (0, 20, 2),
        }
        _, agua_inicial, datos_iniciales = _recursos[player_index]

        self.vitalidad = 1
        self.acidez = 1
        self.datos_investigacion = datos_iniciales
        self.dados_inoculo = 3
        self.puntos_accion = 0  # Se asignan 2 al llegar a la Fase II del primer día
        self.reserva_harina = {"Blanca": 100, "Centeno": 0, "Integral": 0}
        self.reserva_agua = agua_inicial
        self.tecnologias = Technologies()
        self.estaciones_fermentacion = [None, None, None]
        self.carpeta_proyectos = [receta_inicial]
        self.archivo_horneado_exitoso = []
        self.archivo_colapsos = []
        self.horas_extras_usadas = False
        self.en_estado_contaminacion = False
        self.contador_contaminaciones = 0
        self.accion_alimentar_usada = False

    # ==================================================================
    # MÉTODOS DE MODIFICACIÓN DE ESTADO (con clamping y efectos secundarios)
    # ==================================================================

    def ajustar_vitalidad(self, delta: int) -> None:
        """
        Modifica la vitalidad aplicando el clamp [0, 6].

        Si el resultado es 0 y el jugador no estaba ya contaminado, activa el
        estado de contaminación e incrementa el contador de penalizaciones.
        El motor debe ofrecer al jugador los Protocolos de Emergencia (H o I).

        Args:
            delta: Incremento (positivo) o decremento (negativo) de vitalidad.
        """
        nuevo_valor: int = max(0, min(6, self.vitalidad + delta))
        self.vitalidad = nuevo_valor
        if self.vitalidad == 0 and not self.en_estado_contaminacion:
            self.en_estado_contaminacion = True
            self.contador_contaminaciones += 1

    def ajustar_acidez(self, delta: int) -> None:
        """
        Modifica la acidez aplicando el clamp [0, 6].

        Args:
            delta: Incremento (positivo) o decremento (negativo) de acidez.
        """
        self.acidez = max(0, min(6, self.acidez + delta))

    def resetear_puntos_accion(self) -> None:
        """
        Reinicia los PA a 2 al comienzo de la Fase II del turno del jugador.
        También resetea el uso de Horas Extras para el día.
        """
        self.puntos_accion = 2
        self.horas_extras_usadas = False

    def consumir_punto_accion(self) -> None:
        """
        Decrementa 1 PA del jugador.
        Precondición: el engine debe verificar puntos_accion >= 1 ANTES de llamar.
        """
        self.puntos_accion -= 1

    def otorgar_punto_accion_extra(self) -> None:
        """
        Aplica el efecto de la acción auxiliar 'Horas Extras' (+1 PA).
        Precondición: el engine debe verificar que horas_extras_usadas == False
        y que datos_investigacion >= 1 antes de llamar.
        """
        self.puntos_accion += 1
        self.horas_extras_usadas = True

    # ==================================================================
    # PROPIEDADES DE CONSULTA DE ESTADO (solo lectura)
    # ==================================================================

    @property
    def indice_estacion_disponible(self) -> Optional[int]:
        """
        Retorna el índice de la primera estación de fermentación libre disponible,
        o None si todas están ocupadas o bloqueadas.

        La Estación 03 (índice 2) requiere tecnologias.camara_b == True.
        """
        for i, slot in enumerate(self.estaciones_fermentacion):
            if slot is None:
                if i == 2 and not self.tecnologias.camara_b:
                    continue  # Estación 03 bloqueada sin Cámara B
                return i
        return None

    @property
    def masas_activas(self) -> List[Tuple[int, FermentationSlot]]:
        """
        Retorna lista de (índice_estación, slot) de todas las masas en fermentación.
        Útil para iterar en la Fase III sin filtrar None manualmente.
        """
        return [
            (i, slot)
            for i, slot in enumerate(self.estaciones_fermentacion)
            if slot is not None
        ]

    @property
    def total_tokens_recursos(self) -> int:
        """
        Total de tokens de insumos sin utilizar (harina + agua).
        Usado para el cálculo de la penalización por desperdicio al final del juego.
        """
        return sum(v // 10 for v in self.reserva_harina.values()) + self.reserva_agua

    @property
    def puntos_penalizacion_contaminacion(self) -> int:
        """Puntos negativos acumulados por episodios de vitalidad = 0 (-3 por c/u)."""
        return self.contador_contaminaciones * -3

    @property
    def puntos_maestria_final(self) -> int:
        """
        Calcula el total de Puntos de Maestría al final de la partida.

        Componentes (CORE_MECHANICS.md §3):
          1. Puntos Base   : suma de puntos de todas las recetas horneadas (positivos + negativos)
          2. Puntos de Sabor: suma de bono_sabor_pts de registros con bono_sabor_aplicado == True
          3. Madurez del Cultivo: ceil((vitalidad + acidez) / 2)
          4. Penalización Desperdicio: -1 pt por cada 3 tokens de insumos sin usar
          5. Penalización Contaminación: -3 pts × contador_contaminaciones

        Debe invocarse únicamente al final del día que termina la partida.
        """
        todos_los_horneados: List[HorneadoRecord] = (
            self.archivo_horneado_exitoso + self.archivo_colapsos
        )

        # 1. Puntos base de recetas
        puntos_base: int = sum(r.puntos_base for r in todos_los_horneados)

        # 2. Puntos de sabor (bono de acidez sellado en cada carta)
        puntos_sabor: int = sum(
            r.recipe.bono_sabor_pts
            for r in todos_los_horneados
            if r.bono_sabor_aplicado
        )

        # 3. Madurez del cultivo base al final de la partida
        madurez: int = math.ceil((self.vitalidad + self.acidez) / 2)

        # 4. Penalización por desperdicio de insumos (-1 por cada 3 tokens)
        penalizacion_desperdicio: int = -(self.total_tokens_recursos // 3)

        # 5. Penalización por episodios de contaminación
        penalizacion_contaminacion: int = self.puntos_penalizacion_contaminacion

        return (
            puntos_base
            + puntos_sabor
            + madurez
            + penalizacion_desperdicio
            + penalizacion_contaminacion
        )

    def __repr__(self) -> str:
        return (
            f"Player(nombre={self.nombre!r}, "
            f"vitalidad={self.vitalidad}, acidez={self.acidez}, "
            f"PA={self.puntos_accion}, datos={self.datos_investigacion}, "
            f"masas_activas={len(self.masas_activas)}, "
            f"horneados={len(self.archivo_horneado_exitoso)})"
        )


@dataclass
class Environment:
    """
    Estado global del tablero central (compartido entre todos los jugadores).

    Gestiona la temperatura del laboratorio, el mazo de clima y el avance base
    de fermentación (Ábaco). El Investigador Jefe (jugador con mayor vitalidad)
    lidera la Fase I que modifica este estado.

    Inicialización recomendada:
        env = Environment.crear_inicial()
    """

    temperatura_actual: int = 20
    """Temperatura del laboratorio en °C. Inicia en 20°C; modificada cada Fase I."""

    dia_actual: int = 1
    """Ronda/día de laboratorio en curso. Incrementa al finalizar cada ciclo completo."""

    efecto_pasivo_activo: EfectoClimatico = EfectoClimatico.NINGUNO
    """
    Efecto pasivo de la carta de clima del día vigente.
    Modifica la resolución de la Fase III (ej. Aletargamiento Invernal → -2 Vitalidad).
    Se sobrescribe con cada nueva carta revelada en la Fase I.
    """

    mazo_clima: List[ClimateCard] = field(default_factory=list)
    """Cartas de clima restantes por revelar. Vaciar este mazo es un gatillo de fin de juego."""

    descarte_clima: List[ClimateCard] = field(default_factory=list)
    """Cartas ya reveladas. Se barajan de vuelta al mazo si este se agota."""

    ultima_carta_clima: Optional[ClimateCard] = field(default=None)
    """Última carta de clima revelada en la Fase I. Usada por la CLI para mostrar el evento."""

    # ==================================================================
    # FACTORY METHOD — Estado Inicial del Juego
    # ==================================================================

    @classmethod
    def crear_inicial(cls) -> "Environment":
        """
        Crea el entorno con el estado exacto de inicio de partida:
          · Temperatura base: 20°C
          · Mazo de clima completo (30 cartas) barajado aleatoriamente
          · Sin efectos pasivos activos
          · Día 1

        Returns:
            Instancia de Environment lista para el inicio de la partida.
        """
        env = cls()
        env.temperatura_actual = 20
        env.dia_actual = 1
        env.efecto_pasivo_activo = EfectoClimatico.NINGUNO
        env.mazo_clima = build_climate_deck()
        random.shuffle(env.mazo_clima)
        env.descarte_clima = []
        env.ultima_carta_clima = None
        return env

    # ==================================================================
    # PROPIEDADES DE CONSULTA
    # ==================================================================

    @property
    def avance_base(self) -> int:
        """
        Casillas base de avance térmico (Ábaco de Fermentación).
        Fórmula (CLIMATE_LOGIC.md §1): temperatura_actual // 5
        Ejemplos: 20°C → 4, 25°C → 5, 30°C → 6, 15°C → 3
        """
        return self.temperatura_actual // 5

    @property
    def mazo_agotado(self) -> bool:
        """
        Retorna True si el mazo de clima se ha vaciado.
        Agotar el mazo es uno de los dos gatillos de fin de partida.
        """
        return len(self.mazo_clima) == 0

    @property
    def desgaste_vitalidad_fase_3(self) -> int:
        """
        Retorna el decremento de Vitalidad que se aplica al cultivo base en la Fase III.
        Estándar: -1. Con Aletargamiento Invernal activo: -2.
        """
        if self.efecto_pasivo_activo == EfectoClimatico.ALETARGAMIENTO_INVERNAL:
            return -2
        return -1

    # ==================================================================
    # MÉTODOS DE MODIFICACIÓN DE ESTADO
    # ==================================================================

    def aplicar_carta_clima(self, carta: ClimateCard) -> None:
        """
        Aplica el modificador térmico de una carta al entorno y activa su efecto pasivo.
        Llamar DESPUÉS de resetear la temperatura a la base si el diseño lo requiere.

        Args:
            carta: Carta de clima revelada durante la Fase I.
        """
        self.ultima_carta_clima = carta
        self.temperatura_actual += carta.modificador_termico
        self.efecto_pasivo_activo = carta.efecto_pasivo

    def resetear_temperatura_base(self) -> None:
        """
        Resetea la temperatura al valor base de 20°C antes de aplicar la carta del día.
        Invocar al inicio de cada Fase I, antes de aplicar_carta_clima().
        """
        self.temperatura_actual = 20

    def __repr__(self) -> str:
        return (
            f"Environment(día={self.dia_actual}, "
            f"temp={self.temperatura_actual}°C, "
            f"avance_base={self.avance_base}, "
            f"efecto_pasivo={self.efecto_pasivo_activo.value!r}, "
            f"cartas_restantes={len(self.mazo_clima)})"
        )


# ===========================================================================
# SECCIÓN 4: CATÁLOGO MAESTRO DE RECETAS (CONSTANTE INMUTABLE)
# ===========================================================================

_RECIPE_CATALOG_DATA: Dict[str, Recipe] = {
    "pan_de_campo": Recipe(
        id="pan_de_campo",
        nombre="Pan de Campo",
        grado=Grado.BASICA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=60,
        tokens_agua=12,
        acidez_diana=(3,),
        bono_sabor_pts=2,
        zona_baja=(1, 11),
        zona_optima=(12, 14),
        zona_sobrefermentada=(15, 20),
        puntos_optimos=10,
        penalizacion_colapso=-2,
        req_tecnologico=None,
    ),
    "focaccia": Recipe(
        id="focaccia",
        nombre="Focaccia",
        grado=Grado.BASICA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=75,
        tokens_agua=15,
        acidez_diana=(1, 2),
        bono_sabor_pts=2,
        zona_baja=(1, 9),
        zona_optima=(10, 14),
        zona_sobrefermentada=(15, 20),
        puntos_optimos=12,
        penalizacion_colapso=-3,
        req_tecnologico=None,
    ),
    "baguette": Recipe(
        id="baguette",
        nombre="Baguette",
        grado=Grado.BASICA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=65,
        tokens_agua=13,
        acidez_diana=(2,),
        bono_sabor_pts=2,
        zona_baja=(1, 13),
        zona_optima=(14, 15),
        zona_sobrefermentada=(16, 20),
        puntos_optimos=11,
        penalizacion_colapso=-2,
        req_tecnologico=None,
    ),
    "pizza_napolitana": Recipe(
        id="pizza_napolitana",
        nombre="Pizza Napolitana",
        grado=Grado.AVANZADA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=62,
        tokens_agua=13,
        acidez_diana=(3,),
        bono_sabor_pts=3,
        zona_baja=(1, 10),
        zona_optima=(11, 13),
        zona_sobrefermentada=(14, 20),
        puntos_optimos=14,
        penalizacion_colapso=-4,
        req_tecnologico=TecnologiaID.MODULO_ANALITICO,
    ),
    "brioche": Recipe(
        id="brioche",
        nombre="Brioche",
        grado=Grado.AVANZADA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=52,
        tokens_agua=11,
        acidez_diana=(1,),
        bono_sabor_pts=3,
        zona_baja=(1, 16),
        zona_optima=(17, 18),
        zona_sobrefermentada=(19, 20),
        puntos_optimos=16,
        penalizacion_colapso=-6,
        req_tecnologico=TecnologiaID.MODULO_ANALITICO,
    ),
    "hogaza_centeno": Recipe(
        id="hogaza_centeno",
        nombre="Hogaza Centeno",
        grado=Grado.AVANZADA,
        harina_base=TipoHarina.CENTENO,
        hidratacion_pct=67,
        tokens_agua=14,
        acidez_diana=(4, 5),
        bono_sabor_pts=3,
        zona_baja=(1, 14),
        zona_optima=(15, 18),
        zona_sobrefermentada=(19, 20),
        puntos_optimos=15,
        penalizacion_colapso=-5,
        req_tecnologico=TecnologiaID.MODULO_ANALITICO,
    ),
    "pan_semillas": Recipe(
        id="pan_semillas",
        nombre="Pan Semillas",
        grado=Grado.AVANZADA,
        harina_base=TipoHarina.INTEGRAL,
        hidratacion_pct=78,
        tokens_agua=16,
        acidez_diana=(3, 4),
        bono_sabor_pts=3,
        zona_baja=(1, 12),
        zona_optima=(13, 15),
        zona_sobrefermentada=(16, 20),
        puntos_optimos=17,
        penalizacion_colapso=-5,
        req_tecnologico=TecnologiaID.MODULO_ANALITICO,
    ),
    "panettone": Recipe(
        id="panettone",
        nombre="Panettone",
        grado=Grado.AVANZADA,
        harina_base=TipoHarina.BLANCA,
        hidratacion_pct=47,
        tokens_agua=10,
        acidez_diana=(1,),
        bono_sabor_pts=4,
        zona_baja=(1, 17),
        zona_optima=(18, 19),
        zona_sobrefermentada=(20, 20),
        puntos_optimos=20,
        penalizacion_colapso=-8,
        req_tecnologico=TecnologiaID.MODULO_ANALITICO,
    ),
}

RECIPE_CATALOG: Mapping[str, Recipe] = MappingProxyType(_RECIPE_CATALOG_DATA)
"""
Catálogo maestro de recetas. Solo lectura en tiempo de ejecución (MappingProxyType).
Contiene las 8 recetas del juego: 3 Básicas + 5 Avanzadas.
Todas las referencias a recetas en el estado del juego apuntan a estas instancias.
"""


# ===========================================================================
# SECCIÓN 5: CATÁLOGO DEL MAZO DE CLIMA (CONSTANTE INMUTABLE)
# ===========================================================================

_CLIMATE_CATALOG_DATA: Dict[str, ClimateCard] = {
    "estabilidad_termica": ClimateCard(
        id="estabilidad_termica",
        nombre="Estabilidad Térmica",
        cantidad=10,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "fallo_refrigeracion": ClimateCard(
        id="fallo_refrigeracion",
        nombre="Fallo Refrigeración",
        cantidad=4,
        modificador_termico=5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "ola_de_calor": ClimateCard(
        id="ola_de_calor",
        nombre="Ola de Calor",
        cantidad=2,
        modificador_termico=10,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "corriente_de_aire": ClimateCard(
        id="corriente_de_aire",
        nombre="Corriente de Aire",
        cantidad=4,
        modificador_termico=-5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "fallo_calefaccion": ClimateCard(
        id="fallo_calefaccion",
        nombre="Fallo Calefacción",
        cantidad=2,
        modificador_termico=-10,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "alta_humedad": ClimateCard(
        id="alta_humedad",
        nombre="Alta Humedad",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.ALTA_HUMEDAD,
    ),
    "explosion_levaduras": ClimateCard(
        id="explosion_levaduras",
        nombre="Explosión de Levaduras",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.GANANCIA_VITALIDAD,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "acidificacion_acelerada": ClimateCard(
        id="acidificacion_acelerada",
        nombre="Acidificación Acelerada",
        cantidad=2,
        modificador_termico=0,
        efecto_biologico=EfectoBiologico.GANANCIA_ACIDEZ,
        efecto_pasivo=EfectoClimatico.NINGUNO,
    ),
    "aletargamiento_invernal": ClimateCard(
        id="aletargamiento_invernal",
        nombre="Aletargamiento Invernal",
        cantidad=2,
        modificador_termico=-5,
        efecto_biologico=EfectoBiologico.NINGUNO,
        efecto_pasivo=EfectoClimatico.ALETARGAMIENTO_INVERNAL,
    ),
}

CLIMATE_CATALOG: Mapping[str, ClimateCard] = MappingProxyType(_CLIMATE_CATALOG_DATA)
"""
Catálogo maestro del mazo de Clima. Solo lectura en tiempo de ejecución.
9 tipos de carta · 30 instancias totales en el mazo (según campo `cantidad`).
"""


# ===========================================================================
# SECCIÓN 6: FUNCIONES DE UTILIDAD PARA EL SETUP
# ===========================================================================


def build_climate_deck() -> List[ClimateCard]:
    """
    Construye el mazo de clima completo expandiendo cada carta según su `cantidad`.

    Retorna la lista sin barajar (30 cartas); el orden aleatorio lo aplica
    Environment.crear_inicial() con random.shuffle().

    Returns:
        Lista de 30 referencias a ClimateCard del catálogo inmutable.

    Raises:
        AssertionError: Si el total no suma exactamente 30 cartas (integridad del catálogo).
    """
    deck: List[ClimateCard] = []
    for card in CLIMATE_CATALOG.values():
        deck.extend([card] * card.cantidad)
    assert len(deck) == 30, (
        f"El mazo de clima debe tener exactamente 30 cartas, "
        f"el catálogo actual genera {len(deck)}."
    )
    return deck


def get_recetas_basicas() -> List[Recipe]:
    """
    Retorna todas las recetas de grado 'Básica' del catálogo maestro.
    Usada en el setup del Día 1 para obtener el mazo de recetas iniciales.

    Returns:
        Lista de Recipe con grado == Grado.BASICA.
    """
    return [r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA]


def get_recetas_avanzadas() -> List[Recipe]:
    """
    Retorna todas las recetas de grado 'Avanzada' del catálogo maestro.
    Usada para construir el mazo del mercado central.

    Returns:
        Lista de Recipe con grado == Grado.AVANZADA.
    """
    return [r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA]


def seleccionar_receta_inicial() -> Recipe:
    """
    Selecciona aleatoriamente una receta de grado 'Básica' para el inicio de partida.

    Abstrae el azar para facilitar el mocking en pruebas unitarias:
    en tests, reemplazar esta función con un stub determinista.

    Returns:
        Una Recipe de grado Básica elegida al azar del catálogo.

    Raises:
        RuntimeError: Si el catálogo no contiene recetas básicas (error de configuración).
    """
    basicas: List[Recipe] = get_recetas_basicas()
    if not basicas:
        raise RuntimeError(
            "No hay recetas de grado 'Básica' disponibles en RECIPE_CATALOG. "
            "Verificar la integridad del catálogo."
        )
    return random.choice(basicas)
