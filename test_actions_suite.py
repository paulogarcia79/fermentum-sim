"""
test_actions_suite.py — Suite de integración para actions.py

Cubre rutas felices y rutas de fallo (Fail-Fast / excepciones semánticas)
para las 11 acciones implementadas en ActionManager.
"""
import sys

from models import (
    Player, FermentationSlot, TecnologiaID, TipoHarina,
    Grado, RECIPE_CATALOG, Environment,
)
from engine import GameEngine, Market
from actions import ActionManager
from exceptions import (
    NotEnoughActionPointsError, MissingResourceError,
    StationBlockedError, CarpetaFullError,
    RuleViolationError, InvalidActionError,
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
receta_av = next(r for r in RECIPE_CATALOG.values() if r.grado == Grado.AVANZADA)

# ========================================================================
print("--- A: Alimentar ---")
p1.reserva_harina = {"Blanca": 100, "Centeno": 0, "Integral": 0}
p1.reserva_agua = 10
p1.puntos_accion = 2
p1.accion_alimentar_usada = False
v0, a0 = p1.vitalidad, p1.acidez

manager.accion_A_alimentar(p1, tipo_harina="Blanca")
check("A full: +1 vit", lambda: None if p1.vitalidad == v0 + 1 else (_ for _ in ()).throw(AssertionError()))
check("A full: +1 acid", lambda: None if p1.acidez == a0 + 1 else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "A doble uso en mismo dia", lambda: manager.accion_A_alimentar(p1, tipo_harina="Blanca"))

p1.accion_alimentar_usada = False
xraises(InvalidActionError, "A sin recursos", lambda: manager.accion_A_alimentar(p1, usar_harina=False, usar_agua=False))

# Accion A es gratuita (0 PA, ACTIONS_REGISTRY.md SS3) -- debe funcionar incluso sin PA.
p1.puntos_accion = 0
manager.accion_A_alimentar(p1, tipo_harina="Blanca")
check("A funciona con 0 PA (accion gratuita)", lambda: None if p1.accion_alimentar_usada else (_ for _ in ()).throw(AssertionError()))

p1.accion_alimentar_usada = False
p1.reserva_agua = 0
xraises(MissingResourceError, "A agua insuficiente", lambda: manager.accion_A_alimentar(p1, usar_harina=False, usar_agua=True))

# ========================================================================
print("--- B: Iniciar Receta ---")
p1.vitalidad = 3
p1.acidez = 3
p1.puntos_accion = 2
p1.dados_inoculo = 3
p1.carpeta_proyectos = [receta_b]
p1.reserva_harina = {"Blanca": 0, "Centeno": 0, "Integral": 0}
p1.reserva_harina[receta_b.harina_base.value] = 100
p1.reserva_agua = receta_b.tokens_agua + 5
p1.estaciones_fermentacion = [None, None, None]

slot = manager.accion_B_iniciar_receta(p1, receta_b)
check("B: slot en estación 0", lambda: None if p1.estaciones_fermentacion[0] is not None else (_ for _ in ()).throw(AssertionError()))
check("B: dado sellado = 3", lambda: None if slot.dado_inoculo == 3 else (_ for _ in ()).throw(AssertionError()))
check("B: receta removida de carpeta", lambda: None if receta_b not in p1.carpeta_proyectos else (_ for _ in ()).throw(AssertionError()))
check("B: dados_inoculo -= 1 (ahora 2)", lambda: None if p1.dados_inoculo == 2 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
xraises(RuleViolationError, "B receta no en carpeta", lambda: manager.accion_B_iniciar_receta(p1, receta_b))

p1.carpeta_proyectos = [receta_b]
p1.reserva_harina = {"Blanca": 0, "Centeno": 0, "Integral": 0}
p1.reserva_harina[receta_b.harina_base.value] = 100
p1.reserva_agua = 200
p1.estaciones_fermentacion = [slot, slot, slot]
p1.puntos_accion = 2
xraises(StationBlockedError, "B estaciones llenas", lambda: manager.accion_B_iniciar_receta(p1, receta_b))

p1.carpeta_proyectos = [receta_av]
p1.estaciones_fermentacion = [None, None, None]
p1.puntos_accion = 2
xraises(RuleViolationError, "B avanzada sin Modulo Analitico", lambda: manager.accion_B_iniciar_receta(p1, receta_av))

p1.vitalidad = 0
p1.en_estado_contaminacion = True
p1.carpeta_proyectos = [receta_b]
p1.puntos_accion = 2
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
monedas_antes2 = p1.monedas
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "Blanca", "operacion": "vender"}])
check("C vender harina: -100 Blanca", lambda: None if p1.reserva_harina["Blanca"] == 100 else (_ for _ in ()).throw(AssertionError()))
check("C vender harina: monedas recibidas", lambda: None if p1.monedas > monedas_antes2 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
agua_antes = p1.reserva_agua
manager.accion_C_visitar_mercado(p1, transacciones=[{"tipo_recurso": "agua", "operacion": "comprar", "lote_pct": 10}])
check("C comprar agua: tokens recibidos", lambda: None if p1.reserva_agua > agua_antes else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
xraises(InvalidActionError, "C exclusividad: mismo recurso dos veces", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[
        {"tipo_recurso": "Blanca", "operacion": "comprar"},
        {"tipo_recurso": "Blanca", "operacion": "vender"},
    ]
))
xraises(InvalidActionError, "C sin transacciones", lambda: manager.accion_C_visitar_mercado(p1, transacciones=[]))

p1.puntos_accion = 2
p1.monedas = 0
xraises(MissingResourceError, "C monedas insuficientes", lambda: manager.accion_C_visitar_mercado(
    p1, transacciones=[{"tipo_recurso": "Centeno", "operacion": "comprar"}]
))

# ========================================================================
print("--- Pedido de Urgencia ---")
ph = p1.reserva_harina["Blanca"]
p1.datos_investigacion = 5
manager.accion_auxiliar_pedido_urgencia(p1, harina_urgencia=TipoHarina.BLANCA)
check("Pedido Urgencia: +100 Blanca", lambda: None if p1.reserva_harina["Blanca"] == ph + 100 else (_ for _ in ()).throw(AssertionError()))
check("Pedido Urgencia: -1 dato", lambda: None if p1.datos_investigacion == 4 else (_ for _ in ()).throw(AssertionError()))
check("Pedido Urgencia: no consume PA", lambda: None if p1.puntos_accion == 2 else (_ for _ in ()).throw(AssertionError()))

xraises(InvalidActionError, "Pedido Urgencia sin recurso", lambda: manager.accion_auxiliar_pedido_urgencia(p1))
xraises(InvalidActionError, "Pedido Urgencia doble recurso", lambda: manager.accion_auxiliar_pedido_urgencia(p1, harina_urgencia=TipoHarina.BLANCA, agua_tokens_urgencia=10))

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

p1.puntos_accion = 2
manager.accion_D_implementar_mejora(p1, TecnologiaID.CAMARA_B)
check("D: una segunda mejora DISTINTA sí se permite (GDD v0.0.2)", lambda: None if p1.tecnologias.camara_b else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 2
manager.accion_D_implementar_mejora(p1, TecnologiaID.CRIOPRESERVACION)
check("D: Criopreservación (3ra mejora distinta)", lambda: None if p1.tecnologias.criopreservacion else (_ for _ in ()).throw(AssertionError()))

# ========================================================================
print("--- E: Pliegues ---")
p1.estaciones_fermentacion = [slot, None, None]
p1.puntos_accion = 3
pos0 = slot.posicion_track

manager.accion_E_tecnica_pliegues(p1, slot_index=0)
check("E avanzar: +1 posicion", lambda: None if slot.posicion_track == pos0 + 1 else (_ for _ in ()).throw(AssertionError()))

p1.tecnologias.camara_b = True
p1.puntos_accion = 2
v_e = p1.vitalidad
manager.accion_E_tecnica_pliegues(p1, slot_index=0, opcion_camara_b="recuperar_vitalidad")
check("E recuperar_vit: vitalidad incrementada", lambda: None if p1.vitalidad >= v_e else (_ for _ in ()).throw(AssertionError()))

p1.tecnologias.camara_b = False
p1.puntos_accion = 1
xraises(RuleViolationError, "E recuperar_vit sin CamaraB", lambda: manager.accion_E_tecnica_pliegues(p1, slot_index=0, opcion_camara_b="recuperar_vitalidad"))
xraises(InvalidActionError, "E opcion invalida", lambda: manager.accion_E_tecnica_pliegues(p1, slot_index=0, opcion_camara_b="volar"))

xraises(RuleViolationError, "E slot vacio", lambda: manager.accion_E_tecnica_pliegues(p1, slot_index=1))

# ========================================================================
print("--- F: Hornear ---")
p1.estaciones_fermentacion = [slot, None, None]
slot.posicion_track = 5
p1.puntos_accion = 2

rec = manager.accion_F_hornear(p1, slot_index=0)
check("F: HorneadoRecord devuelto", lambda: None if rec is not None else (_ for _ in ()).throw(AssertionError()))
check("F: estacion liberada", lambda: None if p1.estaciones_fermentacion[0] is None else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 0
xraises(NotEnoughActionPointsError, "F sin PA", lambda: manager.accion_F_hornear(p1, slot_index=0))
p1.puntos_accion = 1
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
p1.puntos_accion = 2
market.protocolo_refresco()
idx_r2 = next((i for i, r in enumerate(market.recetas_visibles) if r is not None), None)
if idx_r2 is not None:
    xraises(CarpetaFullError, "G carpeta llena sin descarte", lambda: manager.accion_G_investigar_protocolo(p1, idx_r2))
    manager.accion_G_investigar_protocolo(p1, idx_r2, indice_descartar=0)
    check("G carpeta llena con descarte: size=3", lambda: None if len(p1.carpeta_proyectos) == 3 else (_ for _ in ()).throw(AssertionError()))

p1.puntos_accion = 1
xraises(InvalidActionError, "G indice mercado invalido", lambda: manager.accion_G_investigar_protocolo(p1, 99))

# ========================================================================
print("--- Simposio Tecnico ---")
p1.carpeta_proyectos = list(RECIPE_CATALOG.values())[:2]
p1.puntos_accion = 2
datos_s = p1.datos_investigacion

manager.accion_simposio_tecnico(p1, "carpeta", 0)
check("Simposio carpeta: +1 dato", lambda: None if p1.datos_investigacion == datos_s + 1 else (_ for _ in ()).throw(AssertionError()))
check("Simposio carpeta: size=1", lambda: None if len(p1.carpeta_proyectos) == 1 else (_ for _ in ()).throw(AssertionError()))

fslot = FermentationSlot(recipe=receta_b, dado_inoculo=2, posicion_track=3, bono_sabor=False, modificador_incubadora=0)
p1.estaciones_fermentacion = [fslot, None, None]
p1.puntos_accion = 2
p1.dados_inoculo = 1
datos_s2 = p1.datos_investigacion

manager.accion_simposio_tecnico(p1, "estacion", 0)
check("Simposio estacion: +1 dato", lambda: None if p1.datos_investigacion == datos_s2 + 1 else (_ for _ in ()).throw(AssertionError()))
check("Simposio estacion: slot liberado", lambda: None if p1.estaciones_fermentacion[0] is None else (_ for _ in ()).throw(AssertionError()))
check("Simposio estacion: dado recuperado (1->2)", lambda: None if p1.dados_inoculo == 2 else (_ for _ in ()).throw(AssertionError(f"dados={p1.dados_inoculo}")))

p1.puntos_accion = 1
xraises(InvalidActionError, "Simposio origen invalido", lambda: manager.accion_simposio_tecnico(p1, "horno", 0))
xraises(RuleViolationError, "Simposio estacion vacia", lambda: manager.accion_simposio_tecnico(p1, "estacion", 0))

# ========================================================================
print("--- Horas Extras ---")
p1.horas_extras_usadas = False
p1.datos_investigacion = 5
pa_he = p1.puntos_accion

manager.accion_auxiliar_horas_extras(p1)
check("HE: +1 PA", lambda: None if p1.puntos_accion == pa_he + 1 else (_ for _ in ()).throw(AssertionError()))
check("HE: -1 dato", lambda: None if p1.datos_investigacion == 4 else (_ for _ in ()).throw(AssertionError()))
check("HE: flag seteado", lambda: None if p1.horas_extras_usadas else (_ for _ in ()).throw(AssertionError()))
xraises(InvalidActionError, "HE doble uso en mismo dia", lambda: manager.accion_auxiliar_horas_extras(p1))

p1.datos_investigacion = 0
p1.horas_extras_usadas = False
xraises(MissingResourceError, "HE sin datos", lambda: manager.accion_auxiliar_horas_extras(p1))

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
check("H: harina consumida (-50%)", lambda: None if sum(p1.reserva_harina.values()) == 0 else (_ for _ in ()).throw(AssertionError()))
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
xraises(MissingResourceError, "I datos insuficientes", lambda: manager.accion_I_inoculo_emergencia(p2))

# ========================================================================
print()
print(f"Resultado: {ok} OK / {fail} FAIL")
sys.exit(0 if fail == 0 else 1)
