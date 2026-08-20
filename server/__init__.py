"""
server/ — Capa de servidor headless de Fermentum (Milestone 3)
==================================================================
Expone la misma partida que juega la CLI (``bootstrap.create_game`` +
``GameEngine``) a través de HTTP, sin modificar ``models.py``/``engine.py``/
``actions.py`` más allá de lo ya hecho en Milestones 0-2. Ningún módulo del
juego (``models``, ``engine``, ``actions``, ``bootstrap``, ``events``,
``serialization``) importa nada de este paquete — la dependencia va en un
solo sentido.

Contenido:
  · ``sessions.py`` — salas/partidas en memoria, asientos, tokens.
  · ``commands.py``  — despacho de comandos de acción hacia ``ActionManager``.
  · ``views.py``     — vistas JSON redactadas (oculta los mazos futuros).
  · ``app.py``       — aplicación Starlette y rutas HTTP.
"""
