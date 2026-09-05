"""
test_actions_suite.py — Suite de integración para actions.py

Cubre rutas felices y rutas de fallo (Fail-Fast / excepciones semánticas)
para las 11 acciones implementadas en ActionManager.
"""
import sys

from models import (
    Player, FermentationSlot, HorneadoRecord, TecnologiaID, TipoHarina,
    Grado, RECIPE_CATALOG, Environment,
)
from engine import GameEngine, Market, MAX_DATOS_PONENCIA, MONEDAS_MOSTRADOR, PRECIO_DATO_SIMPOSIO, PRECIO_RECETA_MAZO
from actions import ActionManager, AGUA_PEDIDO_URGENCIA, HARINA_PEDIDO_URGENCIA
from exceptions import (
    NotEnoughActionPointsError, MissingResourceError,
    StationBlockedError, CarpetaFullError,
    RuleViolationError, InvalidActionError,
    EspacioAccionYaUsadoError,
)

ok = 0
fail = 0


def check(desc, fn):
    global ok, fail
    try:
        fn()
        print(f"  OK  {desc}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {desc}: {e}")
        fail += 1


def xraises(exc, desc, fn):
    global ok, fail
    try:
        fn()
        print(f"  FAIL {desc}: expected {exc.__name__}, got nothing")
        fail += 1
    except exc:
        print(f"  OK  {desc}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {desc}: expected {exc.__name__}, got {type(e).__name__}: {e}")
        fail += 1


# ---- Setup común -------------------------------------------------------
env = Environment.crear_inicial()
p1 = Player.crear_dia_1("Alba", list(RECIPE_CATALOG.values())[0])
p2 = Player.crear_dia_1("Bruno", list(RECIPE_CATALOG.values())[1])
market = Market.crear_inicial()
engine = GameEngine([p1, p2], env, market)
manager = ActionManager(engine)

receta_b = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA)
receta_int = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.INTERMEDIA)
receta_av = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA)


def stock_harinas(player, receta, extra=0):
    """Deja en la reserva exactamente lo que la receta pide (mas `extra` de cada tipo)."""
    player.reserva_harina = {"Blanca": 0, "Centeno": 0, "Integral": 0}
    for tipo, pct in receta.requisito_harina.items():
        player.reserva_harina[tipo] = pct + extra

# ========================================================================
print("--- A: Alimentar ---")
p1.reserva_harina = {"Blanca": 100, "Centeno": 0, "Integral": 0}
p1.reserva_agua = 10
p1.puntos_accion = 2
p1.accion_alimentar_usada = False
v0, a0 = p1.vitalidad, p1.acidez

manager.accion_A_alimentar(p1, harina={"Blanca": 10})
check("A: +1 vit", lambda: None if p1.vitalidad == v0 + 1 else (_ for _ in ()).throw(AssertionError()))
# La Accion A ya NO toca la Acidez: todo el control voluntario vive en «Descarte».
check("A: no toca acidez", lambda: None if p1.acidez == a0 else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "A doble uso en mismo dia", lambda: manager.accion_A_alimentar(p1, harina={"Blanca": 10}))

p1.accion_alimentar_usada = False
xraises(InvalidActionError, "A sin tipo de harina", lambda: manager.accion_A_alimentar(p1))

# Accion A es gratuita (0 PA, ACTIONS_REGISTRY.md SS3) -- debe funcionar incluso sin PA.
p1.puntos_accion = 0
manager.accion_A_alimentar(p1, harina={"Blanca": 10})
check("A funciona con 0 PA (accion gratuita)", lambda: None if p1.accion_alimentar_usada else (_ for _ in ()).throw(AssertionError()))

p1.accion_alimentar_usada = False
p1.reserva_harina["Blanca"] = 0
xraises(MissingResourceError, "A harina insuficiente", lambda: manager.accion_A_alimentar(p1, harina={"Blanca": 10}))
p1.reserva_harina["Blanca"] = 100

# ========================================================================
print("--- Descarte: control bidireccional de Acidez ---")
p1.accion_alimentar_usada = False
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
p1.acidez = 3
p1.reserva_agua = 20
p1.monedas = 20

manager.accion_descarte_acidez(p1, operacion="subir", niveles=3)
check("Descarte subir 3: acidez 3->6", lambda: None if p1.acidez == 6 else (_ for _ in ()).throw(AssertionError()))
check("Descarte subir 3: cuesta 9 agua", lambda: None if p1.reserva_agua == 11 else (_ for _ in ()).throw(AssertionError()))
check("Descarte no gasta PA", lambda: None if p1.puntos_accion == 2 else (_ for _ in ()).throw(AssertionError()))
check("Descarte ocupa su espacio", lambda: None if "descarte" in p1.acciones_pa_usadas_hoy else (_ for _ in ()).throw(AssertionError()))

xraises(EspacioAccionYaUsadoError, "Descarte 2x mismo dia", lambda: manager.accion_descarte_acidez(p1, operacion="bajar", niveles=1))

p1.acciones_pa_usadas_hoy = []
manager.accion_descarte_acidez(p1, operacion="bajar", niveles=2)
check("Descarte bajar 2: acidez 6->4", lambda: None if p1.acidez == 4 else (_ for _ in ()).throw(AssertionError()))
check("Descarte bajar 2: cuesta 3 monedas", lambda: None if p1.monedas == 17 else (_ for _ in ()).throw(AssertionError()))

p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "Descarte operacion invalida", lambda: manager.accion_descarte_acidez(p1, operacion="mezclar", niveles=1))
xraises(InvalidActionError, "Descarte niveles fuera de escalera", lambda: manager.accion_descarte_acidez(p1, operacion="subir", niveles=4))

p1.reserva_agua = 1
xraises(MissingResourceError, "Descarte subir sin agua", lambda: manager.accion_descarte_acidez(p1, operacion="subir", niveles=1))
p1.monedas = 0
xraises(MissingResourceError, "Descarte bajar sin monedas", lambda: manager.accion_descarte_acidez(p1, operacion="bajar", niveles=1))
check("Descarte rechazado no ocupa el espacio", lambda: None if "descarte" not in p1.acciones_pa_usadas_hoy else (_ for _ in ()).throw(AssertionError()))

# ========================================================================
print("--- B: Iniciar Receta ---")
p1.vitalidad = 3
p1.acidez = 3
p1.puntos_accion = 2
p1.dados_inoculo = 3
p1.carpeta_proyectos = [receta_b]
stock_harinas(p1, receta_b)
p1.reserva_agua = receta_b.tokens_agua + 5
p1.estaciones_fermentacion = [None, None, None]

slot = manager.accion_B_iniciar_receta(p1, receta_b)
check("B: slot en estación 0", lambda: None if p1.estaciones_fermentacion[0] is not None else (_ for _ in ()).throw(AssertionError()))
check("B: dado sellado = 3", lambda: None if slot.dado_inoculo == 3 else (_ for _ in ()).throw(AssertionError()))
check("B: receta removida de carpeta", lambda: None if receta_b not in p1.carpeta_proyectos else (_ for _ in ()).throw(AssertionError()))
check("B: dados_inoculo -= 1 (ahora 2)", lambda: None if p1.dados_inoculo == 2 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(RuleViolationError, "B receta no en carpeta", lambda: manager.accion_B_iniciar_receta(p1, receta_b))

p1.carpeta_proyectos = [receta_b]
stock_harinas(p1, receta_b)
p1.reserva_agua = 200
p1.estaciones_fermentacion = [slot, slot, slot]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(StationBlockedError, "B estaciones llenas", lambda: manager.accion_B_iniciar_receta(p1, receta_b))

# Una Avanzada se inicia SIN ninguna tecnologia instalada: el freno son los
# insumos, no una mejora de laboratorio.
p1.carpeta_proyectos = [receta_av]
p1.estaciones_fermentacion = [None, None, None]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.dados_inoculo = 3
p1.tecnologias.modulo_analitico = False
stock_harinas(p1, receta_av)
p1.reserva_agua = receta_av.tokens_agua + 5
manager.accion_B_iniciar_receta(p1, receta_av)
check("B avanzada sin ninguna tecnologia", lambda: None if p1.estaciones_fermentacion[0] is not None else (_ for _ in ()).throw(AssertionError()))

# Receta Intermedia: cobra media bolsa de CADA uno de sus dos tipos.
p1.carpeta_proyectos = [receta_int]
p1.estaciones_fermentacion = [None, None, None]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.dados_inoculo = 3
stock_harinas(p1, receta_int)
p1.reserva_agua = receta_int.tokens_agua + 5
manager.accion_B_iniciar_receta(p1, receta_int)
check("B intermedia: cobra las dos harinas", lambda: None if all(p1.reserva_harina[t] == 0 for t in receta_int.requisito_harina) else (_ for _ in ()).throw(AssertionError()))

# Con una sola de las dos mitades en reserva, la Intermedia se rechaza.
p1.carpeta_proyectos = [receta_int]
p1.estaciones_fermentacion = [None, None, None]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
stock_harinas(p1, receta_int)
p1.reserva_harina[list(receta_int.requisito_harina)[1]] = 0
xraises(MissingResourceError, "B intermedia con solo una harina", lambda: manager.accion_B_iniciar_receta(p1, receta_int))

p1.vitalidad = 0
p1.en_estado_contaminacion = True
p1.carpeta_proyectos = [receta_b]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(RuleViolationError, "B vitalidad=0 bloquea inicio", lambda: manager.accion_B_iniciar_receta(p1, receta_b))
p1.vitalidad = 2
p1.en_estado_contaminacion = False

# ========================================================================
print("--- C: Visitar el Mercado ---")
p1.puntos_accion = 3
p1.monedas = 50
p1.reserva_harina = {"Blanca": 100, "Centeno": 0, "Integral": 0}

pa_antes = p1.puntos_accion
monedas_antes = p1.monedas
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "Blanca", "operacion": "comprar"}])
check("C comprar harina: PA consumido", lambda: None if p1.puntos_accion == pa_antes - 1 else (_ for _ in ()).throw(AssertionError()))
check("C comprar harina: +100 Blanca", lambda: None if p1.reserva_harina["Blanca"] == 200 else (_ for _ in ()).throw(AssertionError()))
check("C comprar harina: monedas descontadas", lambda: None if p1.monedas < monedas_antes else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
monedas_antes2 = p1.monedas
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "Blanca", "operacion": "vender"}])
check("C vender harina: -100 Blanca", lambda: None if p1.reserva_harina["Blanca"] == 100 else (_ for _ in ()).throw(AssertionError()))
check("C vender harina: monedas recibidas", lambda: None if p1.monedas > monedas_antes2 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
agua_antes = p1.reserva_agua
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": 10}])
check("C comprar agua: tokens recibidos", lambda: None if p1.reserva_agua > agua_antes else (_ for _ in ()).throw(AssertionError()))

# --- Media bolsa (5 tokens / 50%): compra al alza, venta a la baja ---
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.monedas = 50
p1.reserva_harina["Integral"] = 100
market.posiciones_harina[TipoHarina.INTEGRAL] = 2  # compra 5 / venta 3
monedas_antes3 = p1.monedas
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "Integral", "operacion": "comprar_media"}])
check("C comprar_media: +50 Integral", lambda: None if p1.reserva_harina["Integral"] == 150 else (_ for _ in ()).throw(AssertionError(p1.reserva_harina["Integral"])))
check("C comprar_media: paga ceil(5/2)=3", lambda: None if p1.monedas == monedas_antes3 - 3 else (_ for _ in ()).throw(AssertionError(p1.monedas)))
check("C comprar_media: visor +1 igual que bolsa entera", lambda: None if market.posiciones_harina[TipoHarina.INTEGRAL] == 3 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
market.posiciones_harina[TipoHarina.INTEGRAL] = 2  # venta 3
monedas_antes4 = p1.monedas
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "Integral", "operacion": "vender_media"}])
check("C vender_media: -50 Integral", lambda: None if p1.reserva_harina["Integral"] == 100 else (_ for _ in ()).throw(AssertionError(p1.reserva_harina["Integral"])))
check("C vender_media: cobra floor(3/2)=1", lambda: None if p1.monedas == monedas_antes4 + 1 else (_ for _ in ()).throw(AssertionError(p1.monedas)))
check("C vender_media: visor -1", lambda: None if market.posiciones_harina[TipoHarina.INTEGRAL] == 1 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "C operacion desconocida", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[{"tipo_recurso": "Blanca", "operacion": "comprar_cuarto"}]
))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.reserva_harina["Centeno"] = 0
xraises(MissingResourceError, "C vender_media sin harina", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[{"tipo_recurso": "Centeno", "operacion": "vender_media"}]
))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "C exclusividad: mismo recurso dos veces", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[
        {"tipo_recurso": "Blanca", "operacion": "comprar"},
        {"tipo_recurso": "Blanca", "operacion": "vender"},
    ]
))
p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "C sin transacciones", lambda: manager.accion_C_visitar_mercado(p1, transacciones=[]))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.monedas = 0
xraises(MissingResourceError, "C monedas insuficientes", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[{"tipo_recurso": "Centeno", "operacion": "comprar"}]
))

# ========================================================================
print("--- Pedido de Urgencia ---")
ph = p1.reserva_harina["Blanca"]
p1.datos_investigacion = 5
manager.accion_auxiliar_pedido_urgencia(p1, recurso="harina", harina=TipoHarina.BLANCA)
check("Pedido Urgencia: +media bolsa Blanca", lambda: None if p1.reserva_harina["Blanca"] == ph + HARINA_PEDIDO_URGENCIA else (_ for _ in ()).throw(AssertionError()))
check("Pedido Urgencia: -1 dato", lambda: None if p1.datos_investigacion == 4 else (_ for _ in ()).throw(AssertionError()))
check("Pedido Urgencia: no consume PA", lambda: None if p1.puntos_accion == 2 else (_ for _ in ()).throw(AssertionError()))

pa_agua = p1.reserva_agua
manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua")
check("Pedido Urgencia: +lote fijo de agua", lambda: None if p1.reserva_agua == pa_agua + AGUA_PEDIDO_URGENCIA else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "Pedido Urgencia recurso invalido", lambda: manager.accion_auxiliar_pedido_urgencia(p1, recurso="datos"))
xraises(InvalidActionError, "Pedido Urgencia harina sin tipo", lambda: manager.accion_auxiliar_pedido_urgencia(p1, recurso="harina"))
xraises(InvalidActionError, "Pedido Urgencia doble recurso", lambda: manager.accion_auxiliar_pedido_urgencia(p1, recurso="agua", harina=TipoHarina.BLANCA))

# ========================================================================
print("--- D: Implementar Mejora ---")
p1.puntos_accion = 2
p1.datos_investigacion = 10
p1.tecnologias.incubadora = False
p1.tecnologias.camara_b = False
p1.tecnologias.modulo_analitico = False

manager.accion_D_implementar_mejora(p1, TecnologiaID.INCUBADORA)
check("D: Incubadora activa", lambda: None if p1.tecnologias.incubadora else (_ for _ in ()).throw(AssertionError()))
check("D: -3 datos (10-3=7)", lambda: None if p1.datos_investigacion == 7 else (_ for _ in ()).throw(AssertionError(f"datos={p1.datos_investigacion}")))

p1.puntos_accion = 2
xraises(RuleViolationError, "D misma mejora dos veces bloqueada", lambda: manager.accion_D_implementar_mejora(p1, TecnologiaID.INCUBADORA))

# Nueva regla: el espacio D queda bloqueado el resto del día tras instalar
# CUALQUIER mejora, incluso una DISTINTA (un visita por espacio por día).
p1.puntos_accion = 2
xraises(EspacioAccionYaUsadoError, "D bloqueado el mismo día para una mejora distinta", lambda: manager.accion_D_implementar_mejora(p1, TecnologiaID.CAMARA_B))

# Simular el día siguiente (el espacio se libera en engine.py:_preparar_fase_II).
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
manager.accion_D_implementar_mejora(p1, TecnologiaID.CAMARA_B)
check("D: una segunda mejora DISTINTA al día siguiente sí se permite (GDD v0.0.2)", lambda: None if p1.tecnologias.camara_b else (_ for _ in ()).throw(AssertionError()))

p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
manager.accion_D_implementar_mejora(p1, TecnologiaID.CRIOPRESERVACION)
check("D: Criopreservación (3ra mejora distinta, otro día)", lambda: None if p1.tecnologias.criopreservacion else (_ for _ in ()).throw(AssertionError()))

# ========================================================================
print("--- E: Pliegues ---")
p1.estaciones_fermentacion = [slot, None, None]
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 0  # E ya no cuesta PA: se paga en Monedas
p1.monedas = 20
pos0 = slot.posicion_track

manager.accion_E_tecnica_pliegues(p1, reparto={0: 1})
check("E avanzar 1: +1 posicion", lambda: None if slot.posicion_track == pos0 + 1 else (_ for _ in ()).throw(AssertionError()))
check("E avanzar 1: cuesta 1 Moneda", lambda: None if p1.monedas == 19 else (_ for _ in ()).throw(AssertionError()))
check("E avanzar: no consume PA", lambda: None if p1.puntos_accion == 0 else (_ for _ in ()).throw(AssertionError()))
check("E ocupa el espacio del dia", lambda: None if "E" in p1.acciones_pa_usadas_hoy else (_ for _ in ()).throw(AssertionError()))
xraises(EspacioAccionYaUsadoError, "E dos veces el mismo dia", lambda: manager.accion_E_tecnica_pliegues(p1, reparto={0: 1}))

p1.acciones_pa_usadas_hoy = []
pos1 = slot.posicion_track
manager.accion_E_tecnica_pliegues(p1, reparto={0: 3})
check("E avanzar 3: +3 posiciones", lambda: None if slot.posicion_track == pos1 + 3 else (_ for _ in ()).throw(AssertionError()))
check("E avanzar 3: cuesta 6 Monedas", lambda: None if p1.monedas == 13 else (_ for _ in ()).throw(AssertionError()))

p1.tecnologias.camara_b = True
p1.acciones_pa_usadas_hoy = []
v_e = p1.vitalidad
manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad")
check("E recuperar_vit: vitalidad incrementada", lambda: None if p1.vitalidad >= v_e else (_ for _ in ()).throw(AssertionError()))
check("E recuperar_vit: cuesta 6 Monedas", lambda: None if p1.monedas == 7 else (_ for _ in ()).throw(AssertionError()))

p1.tecnologias.camara_b = False
p1.acciones_pa_usadas_hoy = []
xraises(RuleViolationError, "E recuperar_vit sin CamaraB", lambda: manager.accion_E_tecnica_pliegues(p1, opcion="recuperar_vitalidad"))
xraises(RuleViolationError, "E reparto en 2 masas sin CamaraB", lambda: manager.accion_E_tecnica_pliegues(p1, reparto={0: 1, 1: 1}))
xraises(InvalidActionError, "E opcion invalida", lambda: manager.accion_E_tecnica_pliegues(p1, opcion="volar"))
xraises(InvalidActionError, "E sin reparto", lambda: manager.accion_E_tecnica_pliegues(p1))
xraises(InvalidActionError, "E total fuera de la escalera", lambda: manager.accion_E_tecnica_pliegues(p1, reparto={0: 4}))
xraises(RuleViolationError, "E slot vacio", lambda: manager.accion_E_tecnica_pliegues(p1, reparto={1: 1}))

monedas_antes_e = p1.monedas
p1.monedas = 0
xraises(MissingResourceError, "E sin Monedas", lambda: manager.accion_E_tecnica_pliegues(p1, reparto={0: 1}))
check("E rechazada no ocupa el espacio", lambda: None if "E" not in p1.acciones_pa_usadas_hoy else (_ for _ in ()).throw(AssertionError()))
p1.monedas = monedas_antes_e

# ========================================================================
print("--- F: Hornear ---")
p1.estaciones_fermentacion = [slot, None, None]
# Una masa en CRECIMIENTO no se puede hornear: la masa todavia no es pan.
slot.posicion_track = receta_b.zona_crecimiento[1]
p1.puntos_accion = 2
xraises(RuleViolationError, "F rechaza una masa en crecimiento", lambda: manager.accion_F_hornear(p1, slot_index=0))
check("F rechazada no ocupa el espacio", lambda: None if "F" not in p1.acciones_pa_usadas_hoy else (_ for _ in ()).throw(AssertionError()))
check("F rechazada no gasta PA", lambda: None if p1.puntos_accion == 2 else (_ for _ in ()).throw(AssertionError()))

# Una casilla mas adelante ya es pre-fermento y si hornea.
slot.posicion_track = receta_b.zona_pre_fermento[0]
p1.acciones_pa_usadas_hoy = []

rec = manager.accion_F_hornear(p1, slot_index=0)
check("F: HorneadoRecord devuelto", lambda: None if rec is not None else (_ for _ in ()).throw(AssertionError()))
check("F: estacion liberada", lambda: None if p1.estaciones_fermentacion[0] is None else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 0
xraises(NotEnoughActionPointsError, "F sin PA", lambda: manager.accion_F_hornear(p1, slot_index=0))
p1.puntos_accion = 1
p1.acciones_pa_usadas_hoy = []
xraises(RuleViolationError, "F estacion vacia", lambda: manager.accion_F_hornear(p1, slot_index=0))

# ========================================================================
print("--- G: Investigar Protocolo ---")
market.protocolo_refresco()
p1.puntos_accion = 3
p1.carpeta_proyectos = []

idx_r = next((i for i, r in enumerate(market.recetas_visibles) if r is not None), None)
if idx_r is not None:
    manager.accion_G_investigar_protocolo(p1, idx_r)
    check("G: receta en carpeta", lambda: None if len(p1.carpeta_proyectos) == 1 else (_ for _ in ()).throw(AssertionError()))

p1.carpeta_proyectos = list(RECIPE_CATALOG.values())[:3]
receta_desplazada = p1.carpeta_proyectos[0]
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
market.protocolo_refresco()
idx_r2 = next((i for i, r in enumerate(market.recetas_visibles) if r is not None), None)
if idx_r2 is not None:
    xraises(CarpetaFullError, "G carpeta llena sin descarte", lambda: manager.accion_G_investigar_protocolo(p1, idx_r2))
    manager.accion_G_investigar_protocolo(p1, idx_r2, indice_descartar=0)
    check("G carpeta llena con descarte: size=3", lambda: None if len(p1.carpeta_proyectos) == 3 else (_ for _ in ()).throw(AssertionError()))
    check("G carpeta llena con descarte: va al descarte del mercado", lambda: None if receta_desplazada in market.descarte_recetas else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 1
p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "G indice mercado invalido", lambda: manager.accion_G_investigar_protocolo(p1, 99))

# Investigacion a ciegas: la carta de arriba del mazo por PRECIO_RECETA_MAZO.
p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
p1.carpeta_proyectos = []
p1.monedas = 10
_cima = market.mazo_recetas[0]
_mazo_antes = len(market.mazo_recetas)
_monedas_antes = p1.monedas
manager.accion_G_investigar_protocolo(p1, origen="mazo")
check("G ciegas: roba la cima del mazo", lambda: None if p1.carpeta_proyectos == [_cima] else (_ for _ in ()).throw(AssertionError()))
check("G ciegas: el mazo baja una carta", lambda: None if len(market.mazo_recetas) == _mazo_antes - 1 else (_ for _ in ()).throw(AssertionError()))
check("G ciegas: cuesta el precio plano", lambda: None if _monedas_antes - p1.monedas == PRECIO_RECETA_MAZO else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
p1.acciones_pa_usadas_hoy = []
xraises(InvalidActionError, "G origen invalido", lambda: manager.accion_G_investigar_protocolo(p1, origen="ciegas"))
xraises(InvalidActionError, "G ciegas con indice de mercado", lambda: manager.accion_G_investigar_protocolo(p1, 0, origen="mazo"))
xraises(InvalidActionError, "G mercado sin indice", lambda: manager.accion_G_investigar_protocolo(p1))

# ========================================================================
print("--- Simposio Tecnico ---")
# El Simposio ya no descarta de carpeta ni de estacion: se paga sacrificando un
# horneado exitoso del archivo, y paga Datos segun el grado de la carta (1/2/3).
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 1
p1.archivo_horneado_exitoso = []
xraises(RuleViolationError, "Simposio archivo vacio", lambda: manager.accion_simposio_tecnico(p1, "sacrificar", indice=0))

receta_basica = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.BASICA)
receta_avanzada = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA)

def _record(recipe):
    return HorneadoRecord(
        recipe=recipe,
        posicion_final=recipe.zona_optima[0],
        puntos_base=recipe.puntos_optimos,
        bono_sabor_aplicado=False,
        fue_colapso=False,
        datos_obtenidos=1,
        monedas_obtenidos=recipe.monedas_optima,
        ampliacion_aplicada=0,
    )

p1.archivo_horneado_exitoso = [_record(receta_basica), _record(receta_avanzada)]
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
datos_s = p1.datos_investigacion

manager.accion_simposio_tecnico(p1, "sacrificar", indice=0)
check("Simposio Basica: +1 dato", lambda: None if p1.datos_investigacion == datos_s + 1 else (_ for _ in ()).throw(AssertionError(f"datos={p1.datos_investigacion}")))
check("Simposio: registro fuera del archivo", lambda: None if len(p1.archivo_horneado_exitoso) == 1 else (_ for _ in ()).throw(AssertionError()))
check("Simposio: carta va al descarte del mercado", lambda: None if receta_basica in market.descarte_recetas else (_ for _ in ()).throw(AssertionError()))

p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
datos_s2 = p1.datos_investigacion
manager.accion_simposio_tecnico(p1, "sacrificar", indice=0)
check("Simposio Avanzada: +3 datos", lambda: None if p1.datos_investigacion == datos_s2 + 3 else (_ for _ in ()).throw(AssertionError(f"datos={p1.datos_investigacion}")))
check("Simposio: archivo vaciado", lambda: None if not p1.archivo_horneado_exitoso else (_ for _ in ()).throw(AssertionError()))

p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 1
p1.archivo_horneado_exitoso = [_record(receta_basica)]
xraises(InvalidActionError, "Simposio indice fuera de rango", lambda: manager.accion_simposio_tecnico(p1, "sacrificar", indice=5))

# Modo ponencia: paga PRECIO_DATO_SIMPOSIO Monedas por Dato y NO toca el archivo.
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
p1.monedas = 30
datos_p = p1.datos_investigacion
manager.accion_simposio_tecnico(p1, "ponencia", datos=2)
check("Ponencia: +2 datos", lambda: None if p1.datos_investigacion == datos_p + 2 else (_ for _ in ()).throw(AssertionError(f"datos={p1.datos_investigacion}")))
check("Ponencia: cobra 5 Monedas por dato", lambda: None if p1.monedas == 30 - 2 * PRECIO_DATO_SIMPOSIO else (_ for _ in ()).throw(AssertionError(f"monedas={p1.monedas}")))
check("Ponencia: el archivo sigue intacto", lambda: None if len(p1.archivo_horneado_exitoso) == 1 else (_ for _ in ()).throw(AssertionError()))

p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 1
p1.monedas = 4
xraises(MissingResourceError, "Ponencia sin monedas", lambda: manager.accion_simposio_tecnico(p1, "ponencia", datos=1))
xraises(InvalidActionError, "Ponencia por encima del tope", lambda: manager.accion_simposio_tecnico(p1, "ponencia", datos=MAX_DATOS_PONENCIA + 1))
xraises(InvalidActionError, "Simposio modo desconocido", lambda: manager.accion_simposio_tecnico(p1, "congreso", datos=1))
xraises(InvalidActionError, "Simposio parametros cruzados", lambda: manager.accion_simposio_tecnico(p1, "ponencia", datos=1, indice=0))

p1.archivo_horneado_exitoso = []
p1.acciones_pa_usadas_hoy = []
p1.puntos_accion = 2
p1.monedas = 30
xraises(RuleViolationError, "Ponencia sin pan en el archivo", lambda: manager.accion_simposio_tecnico(p1, "ponencia", datos=1))

# ========================================================================
print("--- Horas Extras ---")
p1.horas_extras_usadas = False
p1.datos_investigacion = 5
pa_he = p1.puntos_accion

manager.accion_auxiliar_horas_extras(p1)
check("HE: +1 PA", lambda: None if p1.puntos_accion == pa_he + 1 else (_ for _ in ()).throw(AssertionError()))
check("HE: -1 dato", lambda: None if p1.datos_investigacion == 4 else (_ for _ in ()).throw(AssertionError()))
check("HE: flag seteado", lambda: None if p1.horas_extras_usadas else (_ for _ in ()).throw(AssertionError()))
check("HE: entrega el marcador neutral", lambda: None if p1.marcador_neutral_disponible else (_ for _ in ()).throw(AssertionError()))
check("HE: el marcador nace sin gastar", lambda: None if p1.espacio_repetido_hoy is None else (_ for _ in ()).throw(AssertionError()))
xraises(InvalidActionError, "HE doble uso en mismo dia", lambda: manager.accion_auxiliar_horas_extras(p1))

p1.datos_investigacion = 0
p1.horas_extras_usadas = False
xraises(MissingResourceError, "HE sin datos", lambda: manager.accion_auxiliar_horas_extras(p1))

# ========================================================================
print("--- Estasis Biologica ---")
p1.tecnologias.criopreservacion = False
p1.estasis_suspendida = False
xraises(RuleViolationError, "Estasis sin Criopreservacion", lambda: manager.accion_auxiliar_estasis(p1, suspender=True))

p1.tecnologias.criopreservacion = True
pa_est = p1.puntos_accion
espacios_est = list(p1.acciones_pa_usadas_hoy)

manager.accion_auxiliar_estasis(p1, suspender=True)
check("Estasis: bandera suspendida", lambda: None if p1.estasis_suspendida else (_ for _ in ()).throw(AssertionError()))
check("Estasis: no gasta PA", lambda: None if p1.puntos_accion == pa_est else (_ for _ in ()).throw(AssertionError()))
check("Estasis: no ocupa espacio", lambda: None if p1.acciones_pa_usadas_hoy == espacios_est else (_ for _ in ()).throw(AssertionError()))

manager.accion_auxiliar_estasis(p1, suspender=False)
check("Estasis: interruptor de dos sentidos", lambda: None if not p1.estasis_suspendida else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "Estasis con parametro no booleano", lambda: manager.accion_auxiliar_estasis(p1, suspender=1))

p1.tecnologias.criopreservacion = False

# ========================================================================
print("--- Incubadora (dial de avance) ---")
p1.tecnologias.incubadora = False
_slot_inc = FermentationSlot(
    recipe=RECIPE_CATALOG["pan_de_molde"],
    dado_inoculo=1,
    posicion_track=3,
    bono_sabor=False,
    acidez_inicial=1,
)
p1.estaciones_fermentacion[0] = _slot_inc
xraises(RuleViolationError, "Incubadora sin la tecnologia", lambda: manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1))

p1.tecnologias.incubadora = True
pa_inc = p1.puntos_accion
espacios_inc = list(p1.acciones_pa_usadas_hoy)

manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=-1)
check("Incubadora: dial escrito en la masa", lambda: None if _slot_inc.modificador_incubadora == -1 else (_ for _ in ()).throw(AssertionError()))
check("Incubadora: no gasta PA", lambda: None if p1.puntos_accion == pa_inc else (_ for _ in ()).throw(AssertionError()))
check("Incubadora: no ocupa espacio", lambda: None if p1.acciones_pa_usadas_hoy == espacios_inc else (_ for _ in ()).throw(AssertionError()))

manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=0)
check("Incubadora: dial de dos sentidos", lambda: None if _slot_inc.modificador_incubadora == 0 else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "Incubadora con modificador fuera de rango", lambda: manager.accion_auxiliar_incubadora(p1, slot_index=0, modificador=2))
xraises(RuleViolationError, "Incubadora sobre estacion vacia", lambda: manager.accion_auxiliar_incubadora(p1, slot_index=1, modificador=-1))

p1.estaciones_fermentacion[0] = None
p1.tecnologias.incubadora = False

# ========================================================================
print("--- Turno de Mostrador ---")
p1.puntos_accion = 2
p1.monedas = 0
p1.acciones_pa_usadas_hoy = []

manager.accion_turno_mostrador(p1)
check("Mostrador: paga MONEDAS_MOSTRADOR", lambda: None if p1.monedas == MONEDAS_MOSTRADOR else (_ for _ in ()).throw(AssertionError(f"monedas={p1.monedas}")))
check("Mostrador: gasta 1 PA", lambda: None if p1.puntos_accion == 1 else (_ for _ in ()).throw(AssertionError()))
check("Mostrador: NO ocupa espacio", lambda: None if p1.acciones_pa_usadas_hoy == [] else (_ for _ in ()).throw(AssertionError(f"usados={p1.acciones_pa_usadas_hoy}")))

# El invariante que justifica la accion: se repite mientras queden PA, porque
# el hueco que viene a tapar puede darse dos veces el mismo dia.
manager.accion_turno_mostrador(p1)
check("Mostrador: repetible el mismo dia", lambda: None if p1.monedas == 2 * MONEDAS_MOSTRADOR and p1.puntos_accion == 0 else (_ for _ in ()).throw(AssertionError()))

xraises(NotEnoughActionPointsError, "Mostrador sin PA", lambda: manager.accion_turno_mostrador(p1))

# ========================================================================
print("--- Protocolo H: Re-cultivo Manual ---")
p1.vitalidad = 0
p1.acidez = 0
p1.en_estado_contaminacion = True
p1.puntos_accion = 2
p1.reserva_harina = {"Blanca": 50, "Centeno": 0, "Integral": 0}
p1.reserva_agua = 5

manager.accion_H_recultivo_manual(p1)
check("H: vitalidad=1", lambda: None if p1.vitalidad == 1 else (_ for _ in ()).throw(AssertionError()))
check("H: acidez=1", lambda: None if p1.acidez == 1 else (_ for _ in ()).throw(AssertionError()))
check("H: contaminacion limpia", lambda: None if not p1.en_estado_contaminacion else (_ for _ in ()).throw(AssertionError()))
check("H: harina consumida (-30%)", lambda: None if sum(p1.reserva_harina.values()) == 20 else (_ for _ in ()).throw(AssertionError(f"quedan {sum(p1.reserva_harina.values())}")))
check("H: agua NO consumida (sin costo de agua en GDD v0.0.2)", lambda: None if p1.reserva_agua == 5 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 1
xraises(InvalidActionError, "H sin contaminacion", lambda: manager.accion_H_recultivo_manual(p1))

# ========================================================================
print("--- Protocolo I: Inoculo de Emergencia ---")
p2.vitalidad = 0
p2.acidez = 0
p2.en_estado_contaminacion = True
p2.puntos_accion = 2
p2.datos_investigacion = 4

manager.accion_I_inoculo_emergencia(p2)
check("I: vitalidad=2", lambda: None if p2.vitalidad == 2 else (_ for _ in ()).throw(AssertionError()))
check("I: acidez=2", lambda: None if p2.acidez == 2 else (_ for _ in ()).throw(AssertionError()))
check("I: contaminacion limpia", lambda: None if not p2.en_estado_contaminacion else (_ for _ in ()).throw(AssertionError()))
check("I: datos=3 (4-1, GDD v0.0.2)", lambda: None if p2.datos_investigacion == 3 else (_ for _ in ()).throw(AssertionError(f"datos={p2.datos_investigacion}")))

p2.puntos_accion = 1
xraises(InvalidActionError, "I sin contaminacion", lambda: manager.accion_I_inoculo_emergencia(p2))

p2.en_estado_contaminacion = True
p2.puntos_accion = 1
p2.datos_investigacion = 0
p2.acciones_pa_usadas_hoy = []
xraises(MissingResourceError, "I datos insuficientes", lambda: manager.accion_I_inoculo_emergencia(p2))

# ========================================================================
print()
print(f"Resultado: {ok} OK / {fail} FAIL")
sys.exit(0 if fail == 0 else 1)
