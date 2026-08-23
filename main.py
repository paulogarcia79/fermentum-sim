"""
main.py — Punto de Entrada y CLI Interactiva de Fermentum
==========================================================
Responsabilidades de este módulo (ARCHITECTURE.md §4):
  · Instanciar el entorno, el mercado y los jugadores (setup_game).
  · Orquestar el bucle principal delegando en GameEngine.
  · Proveer la Interfaz de Línea de Comandos (CLI) para la Fase II:
      – Mostrar el estado del jugador antes de cada acción.
      – Mostrar menú numérico de acciones.
      – Capturar input, ejecutar la acción vía ActionManager.
      – Capturar excepciones semánticas y mostrar mensajes de error
        amigables SIN consumir PA.
  · Imprimir el «Reporte de Fermentación» tras cada Fase III.
  · Mostrar el ranking final al concluir la partida.

Diseño:
  · La lógica de reglas vive exclusivamente en engine.py y actions.py.
  · Este módulo solo lee estado y llama métodos; nunca modifica estado directo.
  · Compatibilidad con terminales sin soporte ANSI: el código ANSI se detecta
    en tiempo de ejecución y se omite silenciosamente si el terminal no lo soporta.
"""

from __future__ import annotations

import math
import os
import sys
from typing import List, Optional, Tuple

from actions import COSTOS_TECNOLOGIA, ActionManager
from bootstrap import create_game
from engine import PRECIO_AGUA, GameEngine
from events import EventoTipo, GameEvent
from exceptions import FermentumError
from models import (
    FermentationSlot,
    Grado,
    HorneadoRecord,
    Player,
    TecnologiaID,
    TipoHarina,
    seleccionar_receta_inicial,
)

# ===========================================================================
# SECCIÓN 1: UTILIDADES DE CONSOLA
# ===========================================================================

# Detección de soporte ANSI para colores (POSIX + Windows 10+)
_ANSI_SUPPORTED: bool = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class _C:
    """Códigos ANSI para colores y estilos de consola."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def _c(code: str, text: str) -> str:
    """Aplica un código de color/estilo solo si el terminal lo soporta."""
    if _ANSI_SUPPORTED:
        return f"{code}{text}{_C.RESET}"
    return text


def _header(title: str, ancho: int = 60) -> None:
    """Imprime una línea de encabezado con separador."""
    linea = "─" * ancho
    print(f"\n{_c(_C.BOLD + _C.CYAN, linea)}")
    print(_c(_C.BOLD + _C.CYAN, f"  {title.upper()}"))
    print(_c(_C.BOLD + _C.CYAN, linea))


def _subheader(title: str) -> None:
    print(_c(_C.BOLD, f"\n  ▶ {title}"))


def _ok(msg: str) -> None:
    print(_c(_C.GREEN, f"  ✔ {msg}"))


def _warn(msg: str) -> None:
    print(_c(_C.YELLOW, f"  ⚠ {msg}"))


def _err(msg: str) -> None:
    print(_c(_C.RED, f"\n  [ERROR] {msg}\n"))


def _barra(valor: int, maximo: int = 6, largo: int = 12) -> str:
    """Genera una barra visual tipo [████░░░░] para valores enteros."""
    lleno = round((valor / maximo) * largo)
    vacio = largo - lleno
    barra = "█" * lleno + "░" * vacio
    color = _C.GREEN if valor >= 4 else (_C.YELLOW if valor >= 2 else _C.RED)
    return f"[{_c(color, barra)}] {valor}/{maximo}"


# ===========================================================================
# SECCIÓN 2: RENDERIZADO DE ESTADO DE JUGADOR
# ===========================================================================

_NOMBRE_ESTACION = {0: "Est-01", 1: "Est-02", 2: "Est-03(B)"}
_NOMBRE_TECNOLOGIA = {
    TecnologiaID.INCUBADORA: "Incubadora",
    TecnologiaID.CAMARA_B: "Cámara B",
    TecnologiaID.MODULO_ANALITICO: "Módulo Analítico",
    TecnologiaID.CRIOPRESERVACION: "Criopreservación",
}


def _render_slot(idx: int, slot: Optional[FermentationSlot]) -> str:
    """Genera una línea descriptiva de una estación de fermentación."""
    nombre = _NOMBRE_ESTACION[idx]
    if slot is None:
        return _c(_C.DIM, f"    {nombre}: — libre —")
    receta = slot.recipe.nombre
    pos = slot.posicion_track
    zo_min, zo_max = slot.recipe.zona_optima
    zsf_min = slot.recipe.zona_sobrefermentada[0]

    # Indicador de zona
    if pos >= zsf_min:
        zona_str = _c(_C.RED + _C.BOLD, f"POS {pos:>2} ⚠ SOBREFERMENTADA")
    elif zo_min <= pos <= zo_max:
        zona_str = _c(_C.GREEN, f"POS {pos:>2} ✔ Zona Óptima [{zo_min}-{zo_max}]")
    else:
        zona_str = _c(_C.YELLOW, f"POS {pos:>2}   Zona Baja")

    dado_str = _c(_C.CYAN, f"D{slot.dado_inoculo}")
    bono_str = _c(_C.MAGENTA, "♦Bono") if slot.bono_sabor else _c(_C.DIM, "○")
    return f"    {nombre}: {receta:<20} {zona_str}  {dado_str} {bono_str}"


def mostrar_estado_jugador(player: Player, dia: int) -> None:
    """Muestra el panel de estado del jugador antes de su turno en Fase II."""
    contam = player.en_estado_contaminacion
    nombre_fmt = _c(_C.BOLD + (_C.RED if contam else _C.WHITE), player.nombre)
    estado_extra = _c(_C.RED, "  ◉ CONTAMINADO") if contam else ""

    print(f"\n  {'─'*56}")
    print(f"  {nombre_fmt}{estado_extra}   Día {dia}")
    print(f"  {'─'*56}")

    # PA
    pa = player.puntos_accion
    pa_str = _c(_C.GREEN if pa > 0 else _C.RED, f"{'●' * pa}{'○' * (2 - min(pa, 2))}  ({pa} PA)")
    print(f"  PA:        {pa_str}")

    # Biológicos
    print(f"  Vitalidad: {_barra(player.vitalidad)}")
    print(f"  Acidez:    {_barra(player.acidez)}")

    # Recursos
    h_partes = [f"{k}: {v}%" for k, v in player.reserva_harina.items()]
    h_str = "  ".join(h_partes)
    agua_str = str(player.reserva_agua) if player.reserva_agua > 0 else _c(_C.DIM, "0")
    print(f"  Harina:    {h_str}")
    print(f"  Agua:      {agua_str} tokens  |  Datos: {player.datos_investigacion}  |  "
          f"Dados: {player.dados_inoculo}  |  {_c(_C.YELLOW, f'Monedas: {player.monedas}')}")

    # Tecnologías activas
    techs = [
        _NOMBRE_TECNOLOGIA[t]
        for t in TecnologiaID
        if player.tecnologias.esta_activa(t)
    ]
    tech_str = ", ".join(techs) if techs else _c(_C.DIM, "ninguna")
    print(f"  Mejoras:   {tech_str}")

    # Carpeta de proyectos
    if player.carpeta_proyectos:
        carpeta_str = ", ".join(
            f"{i}: {r.nombre} ({r.grado.value[0]})"
            for i, r in enumerate(player.carpeta_proyectos)
        )
    else:
        carpeta_str = _c(_C.DIM, "vacía")
    print(f"  Carpeta:   {carpeta_str}")

    # Estaciones de fermentación
    print(f"  Estaciones:")
    for i, slot in enumerate(player.estaciones_fermentacion):
        if i == 2 and not player.tecnologias.camara_b and slot is None:
            print(_c(_C.DIM, f"    Est-03(B): — bloqueada (requiere Cámara B) —"))
        else:
            print(_render_slot(i, slot))

    # Archivo de horneados
    exitosos = len(player.archivo_horneado_exitoso)
    colapsos = len(player.archivo_colapsos)
    print(f"  Archivo:   {_c(_C.GREEN, str(exitosos))} exitosos  {_c(_C.RED, str(colapsos))} colapsos")
    print(f"  {'─'*56}")


def mostrar_mercado(engine: GameEngine) -> None:
    """Muestra el estado actual del mercado central."""
    market = engine.market

    _subheader("MERCADO CENTRAL")

    # Recetas visibles
    print("  Recetas disponibles:")
    for i, receta in enumerate(market.recetas_visibles):
        if receta is None:
            print(_c(_C.DIM, f"    [{i}] — ya tomada —"))
        else:
            grado_c = _C.MAGENTA if receta.grado == Grado.AVANZADA else _C.WHITE
            req = ""
            if receta.req_tecnologico is not None:
                req = _c(_C.DIM, f" [req: {_NOMBRE_TECNOLOGIA[receta.req_tecnologico]}]")
            print(f"    [{i}] {_c(grado_c, receta.nombre):<28} "
                  f"Grado:{receta.grado.value[0]} "
                  f"Opt:[{receta.zona_optima[0]}-{receta.zona_optima[1]}] "
                  f"Pts:{receta.puntos_optimos}{req}")

    # Bolsa de Harinas (Acción C: Visitar el Mercado)
    print("  Bolsa de Harinas (Compra / Venta en Monedas):")
    for tipo in TipoHarina:
        print(f"    {_c(_C.YELLOW, tipo.value):<20} "
              f"Compra: {market.precio_compra_harina(tipo)}  "
              f"Venta: {market.precio_venta_harina(tipo)}  "
              f"(visor: {market.posiciones_harina[tipo]}/5)")

    # Suministro Hídrico Global (precio según temperatura actual)
    temp = engine.environment.temperatura_actual
    fila_agua = PRECIO_AGUA.get(temp, {})
    lotes_str = "  ".join(
        f"{pct}%→{fila_agua[pct]}₥" for pct in (10, 30, 60, 100) if pct in fila_agua
    )
    print(f"  Agua ({temp}°C):        {_c(_C.BLUE, lotes_str) if lotes_str else _c(_C.DIM, 'sin precio para esta temperatura')}")


def _mostrar_evento_climatico(engine: GameEngine) -> None:
    """
    Muestra el evento climático del día con formato destacado.
    Se invoca automáticamente después de la Fase I, antes de la Fase II.
    """
    env = engine.environment
    carta = env.ultima_carta_clima

    sep = "═" * 60
    print(f"\n  {_c(_C.BOLD + _C.YELLOW, sep)}")
    print(_c(_C.BOLD + _C.YELLOW, f"  ⛅  EVENTO CLIMÁTICO DEL DÍA"))
    print(f"  {_c(_C.BOLD + _C.YELLOW, sep)}")

    if carta is not None:
        print(_c(_C.BOLD, f"  ▶ Carta:        {carta.nombre}"))
    else:
        print(_c(_C.DIM, "  ▶ Carta:        (sin carta — mazo agotado)"))

    # Temperatura resultante y avance base
    temp_color = _C.RED if env.temperatura_actual >= 30 else (
        _C.YELLOW if env.temperatura_actual >= 25 else _C.CYAN
    )
    print(f"  ▶ Temperatura:  {_c(temp_color, f'{env.temperatura_actual}°C')}  "
          f"→  Avance base por casilla: {_c(_C.BOLD, str(env.avance_base))} paso(s)")

    # Efecto pasivo
    if env.efecto_pasivo_activo.value != "ninguno":
        print(f"  ▶ Efecto pasivo: {_c(_C.MAGENTA, env.efecto_pasivo_activo.value)}")
    else:
        print(f"  ▶ Efecto pasivo: {_c(_C.DIM, 'ninguno')}")

    # Efecto biológico aplicado
    if carta is not None and carta.efecto_biologico.value != "ninguno":
        print(f"  ▶ Efecto biol.:  {_c(_C.GREEN, carta.efecto_biologico.value)} (ya aplicado a todos)")

    print(f"  {_c(_C.BOLD + _C.YELLOW, sep)}\n")


# ===========================================================================
# SECCIÓN 3: MENÚ DE ACCIONES DE FASE II
# ===========================================================================

_MENU_ACCIONES = """
  ┌─── ACCIONES DISPONIBLES ───────────────────────────────────────┐
  │  B  Iniciar Receta         (colocar masa)           [1PA]       │
  │  C  Visitar el Mercado     (comprar/vender harina,  [1PA]       │
  │                              comprar agua)                      │
  │  D  Implementar Mejora     (tecnología)             [1PA]       │
  │  E  Pliegues               (avanzar masa)           [1PA]       │
  │  F  Hornear y Vender       (finalizar masa)         [1PA]       │
  │  G  Investigar Protocolo   (tomar receta mercado)   [1PA]       │
  │  S  Simposio Técnico       (descartar → +1 Dato)    [1PA]       │
  │  H  Re-cultivo Manual      (emergencia, contamin.)  [1PA]       │
  │  I  Inóculo Emergencia     (emergencia, contamin.)  [1PA]       │
  ├─── AUXILIARES (GRATUITAS) ─────────────────────────────────────┤
  │  A  Alimentar cultivo      (+1 Vit / +1 Acid, 1×)  [0PA]       │
  │  X  Horas Extras           (+1PA a cambio de 1 Dato) [0PA]      │
  │  U  Pedido de Urgencia     (recurso directo × 1 Dato) [0PA]     │
  │  P  Pasar turno            (sin más acciones)                   │
  └────────────────────────────────────────────────────────────────┘
"""


def _pedir_int(prompt: str, minimo: int, maximo: int) -> Optional[int]:
    """Pide un entero al usuario en el rango [minimo, maximo]. None = cancelar."""
    while True:
        raw = input(f"  {prompt} [{minimo}-{maximo}] (Enter=cancelar): ").strip()
        if raw == "":
            return None
        if raw.isdigit() and minimo <= int(raw) <= maximo:
            return int(raw)
        _warn(f"Entrada inválida. Escribe un número entre {minimo} y {maximo}, o Enter para cancelar.")


def _pedir_opcion(prompt: str, opciones: List[str]) -> Optional[str]:
    """Pide al usuario elegir entre un conjunto de opciones. None = cancelar."""
    opts_str = "/".join(opciones)
    while True:
        raw = input(f"  {prompt} ({opts_str}, Enter=cancelar): ").strip().lower()
        if raw == "":
            return None
        if raw in [o.lower() for o in opciones]:
            return raw
        _warn(f"Elige una de: {opts_str}")


# --- Recolectores de parámetros por acción ----------------------------------

def _params_accion_A(player: Player) -> Optional[dict]:
    print("  ¿Qué recursos usar para alimentar el cultivo?")

    # Harina
    usar_h_raw = input("  ¿Usar 10% de harina? (s/n): ").strip().lower()
    usar_h = usar_h_raw == "s"
    tipo_h: Optional[str] = None
    if usar_h:
        disponibles = [(k, v) for k, v in player.reserva_harina.items() if v >= 10]
        if not disponibles:
            _warn("No hay ningún tipo de harina con al menos 10% disponible.")
            return None
        print("  Tipos disponibles:")
        for i, (tipo, pct) in enumerate(disponibles):
            print(f"    [{i}] {tipo}: {pct}%")
        idx = _pedir_int("Tipo de harina a consumir", 0, len(disponibles) - 1)
        if idx is None:
            return None
        tipo_h = disponibles[idx][0]

    # Agua
    usar_a_raw = input("  ¿Usar 10% de agua (2 tokens)? (s/n): ").strip().lower()
    usar_a = usar_a_raw == "s"

    if not usar_h and not usar_a:
        _warn("Debes seleccionar al menos un recurso.")
        return None

    return {"usar_harina": usar_h, "tipo_harina": tipo_h, "usar_agua": usar_a}


def _params_accion_B(player: Player, engine: GameEngine) -> Optional[dict]:
    if not player.carpeta_proyectos:
        _warn("Carpeta de proyectos vacía. Investiga recetas primero (Acción G).")
        return None

    print("  Recetas en carpeta:")
    for i, r in enumerate(player.carpeta_proyectos):
        req = f" [req Módulo Analítico]" if r.grado == Grado.AVANZADA else ""
        print(f"    [{i}] {r.nombre}  {r.grado.value}  Harina:{r.harina_base.value}  "
              f"Agua:{r.tokens_agua}  Óptima:[{r.zona_optima[0]}-{r.zona_optima[1]}]{req}")

    idx = _pedir_int("Índice de receta a iniciar", 0, len(player.carpeta_proyectos) - 1)
    if idx is None:
        return None

    receta = player.carpeta_proyectos[idx]
    mod_inc = 0
    if player.tecnologias.incubadora:
        raw_mod = _pedir_opcion("Modificador incubadora", ["-1", "0", "1"])
        if raw_mod is not None:
            mod_inc = int(raw_mod)

    return {"receta": receta, "modificador_incubadora": mod_inc}


def _params_accion_C(player: Player, engine: GameEngine) -> Optional[dict]:
    mostrar_mercado(engine)
    print("  Arma tu visita: agrega transacciones (una por tipo de recurso), "
          "Enter en blanco para terminar.")

    transacciones: List[dict] = []
    tipos_usados: set = set()
    tipos_harina = list(TipoHarina)

    while True:
        opciones_disponibles = [t.value for t in tipos_harina if t.value not in tipos_usados]
        if "agua" not in tipos_usados:
            opciones_disponibles.append("agua")
        if not opciones_disponibles:
            break

        print(f"  Recursos disponibles para esta visita: {', '.join(opciones_disponibles)}")
        recurso = input(
            "  Tipo de recurso (Enter para terminar la visita): "
        ).strip().capitalize()
        if recurso == "":
            break
        if recurso.lower() == "agua":
            recurso = "agua"
        if recurso not in opciones_disponibles:
            _warn(f"'{recurso}' no es válido o ya fue usado en esta visita.")
            continue

        if recurso == "agua":
            lote = _pedir_int("Tamaño de lote de agua (%)", 10, 100)
            if lote not in (10, 30, 60, 100):
                _warn("El lote debe ser 10, 30, 60 o 100.")
                continue
            transacciones.append({"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": lote})
        else:
            op = _pedir_opcion(f"[c]omprar / [v]ender {recurso}", ["c", "v"])
            if op is None:
                continue
            operacion = "comprar" if op == "c" else "vender"
            transacciones.append({"tipo_recurso": recurso, "operacion": operacion})

        tipos_usados.add(recurso)

    if not transacciones:
        return None
    return {"transacciones": transacciones}


def _params_accion_U(player: Player) -> Optional[dict]:
    """Pedido de Urgencia: recolecta parámetros (harina XOR agua)."""
    tipo_res = _pedir_opcion("Recurso de urgencia: [h]arina / [a]gua", ["h", "a"])
    if tipo_res is None:
        return None
    if tipo_res == "h":
        tipos = list(TipoHarina)
        print("  Tipos de harina:")
        for i, t in enumerate(tipos):
            print(f"    [{i}] {t.value} (+100%)")
        idx_h = _pedir_int("Tipo de harina", 0, len(tipos) - 1)
        if idx_h is None:
            return None
        return {"harina_urgencia": tipos[idx_h]}
    else:
        cant = _pedir_int("Tokens de agua a añadir (5% c/u)", 1, 100)
        if cant is None:
            return None
        return {"agua_tokens_urgencia": cant}


def _params_accion_D(player: Player) -> Optional[dict]:
    tecnologias = list(TecnologiaID)
    print("  Mejoras disponibles:")
    for i, t in enumerate(tecnologias):
        ya = _c(_C.GREEN, " [ya instalada]") if player.tecnologias.esta_activa(t) else ""
        print(f"    [{i}] {_NOMBRE_TECNOLOGIA[t]}  ({COSTOS_TECNOLOGIA[t]} Datos){ya}")
    idx = _pedir_int("Índice de mejora a instalar", 0, len(tecnologias) - 1)
    if idx is None:
        return None
    return {"tecnologia": tecnologias[idx]}


def _params_accion_E(player: Player) -> Optional[dict]:
    masas = player.masas_activas
    if not masas and not player.tecnologias.camara_b:
        _warn("No hay masas activas para plegar.")
        return None

    # Mostrar opción de Cámara B si está activa
    opcion = "avanzar"
    if player.tecnologias.camara_b:
        op = _pedir_opcion(
            "Opción Cámara B: [a]vanzar / [v]italidad / [d]oble masa",
            ["a", "v", "d"]
        )
        if op is None:
            return None
        opcion = {"a": "avanzar", "v": "recuperar_vitalidad", "d": "doble_masa"}[op]

    if opcion == "recuperar_vitalidad":
        return {"slot_index": 0, "opcion_camara_b": "recuperar_vitalidad"}

    if not masas:
        _warn("No hay masas activas para plegar.")
        return None

    print("  Masas activas:")
    for idx, slot in masas:
        print(f"    [{idx}] {slot.recipe.nombre} — pos {slot.posicion_track}")
    slot_idx = _pedir_int("Índice de estación a plegar", 0, 2)
    if slot_idx is None:
        return None

    if opcion == "doble_masa":
        slot_idx_2 = _pedir_int("Índice de segunda estación a plegar", 0, 2)
        if slot_idx_2 is None:
            return None
        return {"slot_index": slot_idx, "opcion_camara_b": "doble_masa", "slot_index_2": slot_idx_2}

    return {"slot_index": slot_idx}


def _params_accion_F(player: Player) -> Optional[dict]:
    masas = player.masas_activas
    if not masas:
        _warn("No hay masas activas para hornear.")
        return None
    print("  Masas activas:")
    for idx, slot in masas:
        print(f"    [{idx}] {slot.recipe.nombre} — pos {slot.posicion_track}")
    idx = _pedir_int("Índice de estación a hornear", 0, 2)
    if idx is None:
        return None
    return {"slot_index": idx}


def _params_accion_G(player: Player, engine: GameEngine) -> Optional[dict]:
    mostrar_mercado(engine)
    num_slots = len(engine.market.recetas_visibles)
    idx = _pedir_int("Índice de receta a investigar", 0, num_slots - 1)
    if idx is None:
        return None

    idx_descartar = None
    if len(player.carpeta_proyectos) >= 3:
        _warn("Carpeta llena (3/3). Debes descartar una receta.")
        print("  Recetas en carpeta:")
        for i, r in enumerate(player.carpeta_proyectos):
            print(f"    [{i}] {r.nombre}")
        idx_descartar = _pedir_int("Índice a descartar", 0, len(player.carpeta_proyectos) - 1)
        if idx_descartar is None:
            return None

    return {"indice_mercado": idx, "indice_descartar": idx_descartar}


def _params_accion_S(player: Player) -> Optional[dict]:
    origen = _pedir_opcion("Origen del descarte: [c]arpeta / [e]stación", ["c", "e"])
    if origen is None:
        return None
    if origen == "c":
        if not player.carpeta_proyectos:
            _warn("Carpeta vacía.")
            return None
        print("  Recetas en carpeta:")
        for i, r in enumerate(player.carpeta_proyectos):
            print(f"    [{i}] {r.nombre}")
        idx = _pedir_int("Índice a descartar", 0, len(player.carpeta_proyectos) - 1)
        if idx is None:
            return None
        return {"origen": "carpeta", "indice": idx}
    else:
        masas = player.masas_activas
        if not masas:
            _warn("No hay masas activas.")
            return None
        print("  Masas activas:")
        for i, slot in masas:
            print(f"    [{i}] {slot.recipe.nombre}")
        idx = _pedir_int("Índice de estación a descartar", 0, 2)
        if idx is None:
            return None
        return {"origen": "estacion", "indice": idx}


# ===========================================================================
# SECCIÓN 4: TURNO INTERACTIVO DE FASE II
# ===========================================================================

def _ejecutar_turno_jugador(engine: GameEngine, player: Player) -> None:
    """
    Callback de turno de jugador para la Fase II con modelo round-robin.
    El engine invoca esta función UNA VEZ por jugador por vuelta del ciclo;
    el jugador debe ejecutar EXACTAMENTE 1 acción (o pasar cediendo sus PA).

    Si la acción falla por regla, se levanta excepción o el jugador cancela
    los parámetros, el menú se vuelve a mostrar (bucle interno) hasta que:
      · La acción se ejecuta con éxito  → break
      · El jugador elige 'P' (Pasar)    → cede sus PA y retorna
    """
    manager = ActionManager(engine)

    while True:
        _header(f"TURNO: {player.nombre}  │  PA restantes: {player.puntos_accion}")
        mostrar_estado_jugador(player, engine.environment.dia_actual)

        if player.en_estado_contaminacion:
            _warn("¡Cultivo CONTAMINADO! Ejecuta el Protocolo H o I para limpiar.")

        print(_MENU_ACCIONES)

        opcion = input("  Tu elección (1 acción o P=pasar turno): ").strip().upper()

        if opcion == "P":
            # El jugador cede todos sus PA restantes y renuncia a cualquier
            # acción gratuita pendiente por el resto del día (engine.py:
            # pasar_turno / _jugador_elegible).
            engine.pasar_turno(player)
            print(_c(_C.DIM, "  → Turno abandonado. Se ceden los PA restantes.\n"))
            return

        try:
            ejecutada = _despachar_accion(opcion, player, engine, manager)
        except FermentumError as exc:
            _err(str(exc))
            continue
        except (ValueError, IndexError) as exc:
            _err(f"Entrada inválida: {exc}")
            continue

        if ejecutada:
            break
        # else: el jugador canceló la recolección de parámetros → reintentar


def _despachar_accion(
    opcion: str,
    player: Player,
    engine: GameEngine,
    manager: ActionManager,
) -> bool:
    """
    Resuelve la opción de menú seleccionada por el jugador, recolecta
    parámetros interactivamente y llama al método correspondiente del
    ActionManager.

    Returns:
        True  si la acción fue despachada con éxito al ActionManager.
        False si el jugador canceló la recolección de parámetros o si
              la opción no es reconocida (se muestra advertencia).

    Raises:
        FermentumError: Cualquier excepción semántica levantada por el
            ActionManager (PA, recursos, reglas). Se propaga al llamador
            para su captura, visualización con _err() y reintento.
    """
    if opcion == "A":
        params = _params_accion_A(player)
        if not params:
            return False
        manager.accion_A_alimentar(player, **params)
        _ok("Cultivo alimentado.")
        return True

    elif opcion == "B":
        params = _params_accion_B(player, engine)
        if not params:
            return False
        slot = manager.accion_B_iniciar_receta(player, **params)
        _ok(f"Masa de '{params['receta'].nombre}' iniciada. Dado={slot.dado_inoculo}, Bono={slot.bono_sabor}.")
        return True

    elif opcion == "C":
        params = _params_accion_C(player, engine)
        if not params:
            return False
        manager.accion_C_visitar_mercado(player, **params)
        _ok("Visita al mercado completada.")
        return True

    elif opcion == "D":
        params = _params_accion_D(player)
        if not params:
            return False
        manager.accion_D_implementar_mejora(player, **params)
        tech = _NOMBRE_TECNOLOGIA[params["tecnologia"]]
        _ok(f"Mejora '{tech}' instalada.")
        return True

    elif opcion == "E":
        params = _params_accion_E(player)
        if not params:
            return False
        manager.accion_E_tecnica_pliegues(player, **params)
        _ok("Pliegue aplicado.")
        return True

    elif opcion == "F":
        params = _params_accion_F(player)
        if not params:
            return False
        record: HorneadoRecord = manager.accion_F_hornear(player, **params)
        _renderizar_resultado_horneado(record)
        return True

    elif opcion == "G":
        params = _params_accion_G(player, engine)
        if not params:
            return False
        manager.accion_G_investigar_protocolo(player, **params)
        _ok("Receta añadida a la Carpeta de Proyectos.")
        return True

    elif opcion == "S":
        params = _params_accion_S(player)
        if not params:
            return False
        manager.accion_simposio_tecnico(player, **params)
        _ok("+1 Dato de Investigación obtenido del Simposio Técnico.")
        return True

    elif opcion == "H":
        manager.accion_H_recultivo_manual(player)
        _ok("Re-cultivo completado. Vitalidad=1, Acidez=1.")
        return True

    elif opcion == "I":
        manager.accion_I_inoculo_emergencia(player)
        _ok("Inóculo de Emergencia aplicado. Vitalidad=2, Acidez=2.")
        return True

    elif opcion == "X":
        manager.accion_auxiliar_horas_extras(player)
        _ok("+1 PA otorgado (Horas Extras).")
        return True

    elif opcion == "U":
        params = _params_accion_U(player)
        if not params:
            return False
        manager.accion_auxiliar_pedido_urgencia(player, **params)
        _ok("Pedido de Urgencia completado.")
        return True

    else:
        _warn(f"Opción '{opcion}' no reconocida. Usa las letras del menú o P para pasar.")
        return False


def _renderizar_resultado_horneado(record: HorneadoRecord) -> None:
    """Imprime el resultado inmediato de un horneado voluntario (Acción F)."""
    pts = record.puntos_totales
    zona = record.zona_resultado
    color = _C.GREEN if pts > 0 else _C.RED

    print()
    print(_c(_C.BOLD, f"  ═══ RESULTADO DE HORNEADO ═══"))
    print(f"  Receta   : {record.recipe.nombre}")
    print(f"  Zona     : {_c(color, zona.upper())}")
    print(f"  Puntos   : {_c(color + _C.BOLD, str(pts))}"
          + (f"  (+{record.puntos_bono_sabor} bono)" if record.puntos_bono_sabor else ""))
    datos = record.datos_generados
    if datos > 0:
        print(f"  Datos +  : {_c(_C.CYAN, str(datos))}")
    print(f"  Monedas + : {_c(_C.YELLOW, str(record.monedas_obtenidos))}")
    if record.fue_colapso:
        _warn("La masa colapsó — horneado de emergencia (0 PA).")
    print()


# ===========================================================================
# SECCIÓN 5: REPORTE DE FERMENTACIÓN (FIN DE DÍA)
# ===========================================================================

def _reporte_fermentacion(
    players: List[Player],
    eventos_dia: List[GameEvent],
    dia: int,
    temp: int,
) -> None:
    """
    Imprime el «Reporte de Fermentación» del día que acaba de concluir,
    construido a partir del registro de eventos que el motor emitió durante
    el día (events.py) — no de un diff de snapshots de estado antes/después
    (ver GameEngine.eventos / GameEngine._emit).

    Args:
        players: Lista de jugadores.
        eventos_dia: Eventos emitidos por el motor durante este día
            (``engine.eventos[idx_antes_del_dia:]``).
        dia: Número de día que acaba de terminar.
        temp: Temperatura final tras aplicar la carta de clima.
    """
    _header(f"REPORTE DE FERMENTACIÓN — Día {dia}")
    avance_base = temp // 5
    print(f"  Temperatura: {temp}°C  →  Avance base por turno: {avance_base} casillas\n")

    for i, player in enumerate(players):
        eventos_jugador = [ev for ev in eventos_dia if ev.jugador_idx == i]
        print(_c(_C.BOLD, f"  {player.nombre}"))

        # Masas horneadas automáticamente durante la Fase III (colapsos),
        # luego horneados exitosos (manuales o en zona óptima) — mismo orden
        # que la implementación anterior basada en archivo_colapsos/archivo_horneado_exitoso.
        for ev in eventos_jugador:
            if ev.tipo == EventoTipo.HORNEADO and ev.datos["fue_colapso"]:
                pts_str = _c(_C.RED, str(ev.datos["puntos_totales"]))
                print(f"    ⚠ COLAPSO: '{ev.datos['receta_nombre']}'  →  {pts_str} pts  (auto-horneado)")

        for ev in eventos_jugador:
            if ev.tipo == EventoTipo.HORNEADO and not ev.datos["fue_colapso"]:
                pts_str = _c(_C.GREEN, str(ev.datos["puntos_totales"]))
                print(f"    ✔ Horneado exitoso: '{ev.datos['receta_nombre']}'  →  {pts_str} pts")

        # Desgaste de vitalidad
        desgaste = next((ev for ev in eventos_jugador if ev.tipo == EventoTipo.DESGASTE), None)
        if desgaste is not None:
            vit_antes = desgaste.datos["vitalidad_antes"]
            vit_despues = desgaste.datos["vitalidad_despues"]
            delta_vit = vit_despues - vit_antes
            delta_str = _c(_C.RED if delta_vit < 0 else _C.GREEN, f"{delta_vit:+d}")
            print(f"    Vitalidad cultivo: {vit_antes} → {vit_despues}  ({delta_str})")

        if any(ev.tipo == EventoTipo.CONTAMINACION for ev in eventos_jugador):
            _warn(f"  ¡{player.nombre} entró en estado de Contaminación!")

        # Masas activas restantes
        masas = player.masas_activas
        if masas:
            avances_por_estacion = {
                ev.datos["estacion_idx"]: ev.datos
                for ev in eventos_jugador
                if ev.tipo == EventoTipo.MASA_AVANZO
            }
            for idx, slot in masas:
                avance = avances_por_estacion.get(idx)
                if avance is not None:
                    print(f"    Est-{idx+1:02d}: '{slot.recipe.nombre}'  "
                          f"pos {avance['posicion_antes']} → {avance['posicion_despues']}  "
                          f"(avanzó +{avance['avance']})")
                else:
                    # Defensivo: Fase III procesa todas las masas activas del
                    # día, así que toda masa activa debería tener un evento
                    # MASA_AVANZO. Respaldo por si ese invariante cambia.
                    print(f"    Est-{idx+1:02d}: '{slot.recipe.nombre}'  "
                          f"nueva → pos {slot.posicion_track}")
        else:
            print(_c(_C.DIM, "    Sin masas activas."))

        print()


# ===========================================================================
# SECCIÓN 6: RANKING FINAL
# ===========================================================================

def _mostrar_ranking_final(engine: GameEngine) -> None:
    """Imprime la tabla de puntuación final y declara el ganador."""
    _header("RESULTADOS FINALES — FIN DE PARTIDA")

    ranking = engine.calcular_ranking_final()

    print(f"  {'Pos':<4} {'Investigador':<20} {'PM Total':>9} {'Vitalidad':>9} {'Datos':>6}")
    print(f"  {'─'*55}")

    medallas = ["🥇", "🥈", "🥉"]
    for pos_0, (puntos, player) in enumerate(ranking):
        medalla = medallas[pos_0] if pos_0 < 3 else "   "
        color = _C.YELLOW if pos_0 == 0 else (_C.WHITE if pos_0 == 1 else "")
        fila = f"  {pos_0+1:<4} {player.nombre:<20} {puntos:>9} {player.vitalidad:>9} {player.datos_investigacion:>6}"
        print(f"{medalla} {_c(color, fila)}")

    print()
    ganador_pts, ganador = ranking[0]
    print(_c(_C.BOLD + _C.YELLOW, f"  ★ Ganador: {ganador.nombre} con {ganador_pts} Puntos de Maestría\n"))

    # Desglose de cada jugador
    _subheader("Desglose de puntuación")
    for _, player in ranking:
        todos = player.archivo_horneado_exitoso + player.archivo_colapsos
        pts_base = sum(r.puntos_base for r in todos)
        pts_sabor = sum(r.puntos_bono_sabor for r in todos)
        madurez = math.ceil((player.vitalidad + player.acidez) / 2)
        desperdicio = -(player.total_tokens_recursos // 3)
        contam = player.puntos_penalizacion_contaminacion
        total = player.puntos_maestria_final
        print(f"\n  {player.nombre}:")
        print(f"    Base:        {pts_base:>4}")
        print(f"    Sabor:       {pts_sabor:>4}")
        print(f"    Madurez:    +{madurez:>3}  (Vit {player.vitalidad} + Acidez {player.acidez})")
        print(f"    Desperdicio: {desperdicio:>4}  ({player.total_tokens_recursos} tokens sin usar)")
        print(f"    Contam.:     {contam:>4}  ({player.contador_contaminaciones}× episodio)")
        print(f"    {'─'*26}")
        print(f"    TOTAL:       {_c(_C.BOLD, str(total)):>4}")


# ===========================================================================
# SECCIÓN 7: SETUP DE LA PARTIDA
# ===========================================================================

def _pedir_nombre(prompt: str, default: str) -> str:
    """Pide un nombre al usuario con un valor por defecto."""
    raw = input(f"  {prompt} [Enter = '{default}']: ").strip()
    return raw if raw else default


def setup_game(nombres: Optional[List[str]] = None) -> GameEngine:
    """
    Inicializa todos los componentes del juego y devuelve un GameEngine listo.

    Wrapper de CLI sobre ``bootstrap.create_game``: su única responsabilidad
    propia es rellenar nombres por defecto cuando el usuario no proporciona
    ninguno. La construcción real de la partida vive en ``bootstrap.py`` para
    que otros llamadores (p. ej. un futuro servidor) no necesiten importar
    este módulo de CLI.

    Args:
        nombres: Lista de nombres de jugadores. Si None se usan defaults.

    Returns:
        GameEngine configurado para el Día 1.
    """
    if nombres is None:
        nombres = ["Investigador α", "Investigador β"]

    return create_game(nombres)


# ===========================================================================
# SECCIÓN 8: BUCLE PRINCIPAL
# ===========================================================================

def main() -> None:
    """Punto de entrada de la simulación interactiva de Fermentum."""
    _header("FERMENTUM — Simulador de Laboratorio de Panadería", ancho=62)
    print("  Bienvenido al simulador del juego de mesa Fermentum.\n")

    # ---- Configuración de jugadores ----
    n_raw = input("  ¿Cuántos investigadores? (1-4) [Enter = 2]: ").strip()
    try:
        n_jugadores = int(n_raw) if n_raw else 2
        n_jugadores = max(1, min(4, n_jugadores))
    except ValueError:
        n_jugadores = 2

    nombres: List[str] = []
    defaults = ["Investigador α", "Investigador β", "Investigador γ", "Investigador δ"]
    for i in range(n_jugadores):
        nombre = _pedir_nombre(f"Nombre del Investigador {i+1}", defaults[i])
        nombres.append(nombre)

    print()
    engine = setup_game(nombres)
    players = engine.players

    _ok(f"Partida iniciada con {len(players)} investigador(es).")
    for p in players:
        _ok(f"  {p.nombre} → receta inicial: {p.carpeta_proyectos[0].nombre}")

    print("\n  Pulsa Enter para comenzar el Día 1...")
    input()

    # ========================================================================
    # BUCLE PRINCIPAL: un ciclo = un Día de Laboratorio
    # ========================================================================
    while not engine.partida_terminada:
        dia = engine.environment.dia_actual
        _header(f"DÍA {dia} DE LABORATORIO")

        # -- Índice del registro de eventos ANTES del día (para el reporte) --
        idx_eventos_inicio = len(engine.eventos)

        # -- Ejecutar el día completo --
        # engine.ejecutar_dia_laboratorio orquesta:
        #   · Fase I (ambiente + mercado) – automática
        #   · Fase II (por jugador, invocando el callback)
        #   · Fase III (fermentación + desgaste) – automática
        try:
            fin = engine.ejecutar_dia_laboratorio(
                ejecutar_turno_jugador=_ejecutar_turno_jugador,
                on_fase_i_complete=_mostrar_evento_climatico,
            )
        except FermentumError as exc:
            # Errores de motor (ej. GameAlreadyOverError) — solo puede ocurrir
            # si hay un bug de integración; se muestra y se detiene la partida.
            _err(f"Error crítico del motor: {exc}")
            break

        # -- Reporte de Fermentación (construido a partir del registro de
        #    eventos del día, no de un diff de snapshots) --
        _reporte_fermentacion(
            players,
            engine.eventos[idx_eventos_inicio:],
            dia=dia,
            temp=engine.environment.temperatura_actual,
        )

        if fin or engine.partida_terminada:
            print(_c(_C.BOLD + _C.YELLOW, "  ► La partida ha terminado.\n"))
            break

        print("  Pulsa Enter para continuar al siguiente día...")
        input()

    # ========================================================================
    # RESULTADOS FINALES
    # ========================================================================
    _mostrar_ranking_final(engine)


if __name__ == "__main__":
    main()
