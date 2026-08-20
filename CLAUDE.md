# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A simulation of **Fermentum**, a 1-4 player Eurogame about resource management and
engine-building (fermenting bread), being ported from a single-process CLI to an online
multiplayer web app: the Python rules engine is kept as-is and a thin HTTP layer is added on top,
rather than porting the rules to another stack. The core simulation
(`models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`/`main.py`)
has zero external dependencies — everything is stdlib Python 3.12. The optional `server/` package
(headless HTTP backend) needs `starlette`+`uvicorn`, kept in its own `pyproject.toml` dependency
group so a CLI-only checkout never has to install a web framework. `pytest`+`httpx` are dev-only.

The full game rules live in `context/*.md` and are the source of truth for behavior:

- `context/ARCHITECTURE.md` — coding standards the code must follow (see below)
- `context/CORE_MECHANICS.md` — the Day/Phase loop, fermentation math, endgame/scoring
- `context/ACTIONS_REGISTRY.md` — every player action, its PA/resource cost, and effects
- `context/PLAYER_STATE.md` — the `Player` data schema and per-player setup/validation rules
- `context/CLIMATE_LOGIC.md` — the climate deck and the Phase III fermentation-advance formula
- `context/RECIPE_DATABASE.md` — the recipe catalog (hydration, zones, scoring)

When implementing or changing game logic, check the relevant `context/*.md` file first — it
defines the exact numbers, thresholds, and edge cases the code must match.

## Commands

Core simulation has zero dependencies; dev (`pytest`, `httpx`) and `server` (`starlette`,
`uvicorn`) are separate `pyproject.toml` optional-dependency groups. Use the project venv at
`.venv/` (create with `python3 -m venv .venv && .venv/bin/pip install -e ".[dev,server]"` if it
doesn't exist yet).

```bash
# Run the interactive CLI game
python3 main.py

# Run the legacy integration suite (plain script, not pytest — asserts via print + sys.exit code)
python3 test_actions_suite.py

# Run the pytest suite (tests/ only — pytest is scoped there via testpaths so it never
# collects test_actions_suite.py, whose top-level sys.exit() would abort a pytest session)
.venv/bin/pytest

# Run the headless HTTP backend (single worker only — see server/app.py's concurrency note)
.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1
```

`tests/test_golden_game.py` is a characterization test: it plays a fully deterministic game
(seeded global RNG, two scripted "bot" players from `tests/_bot.py`) through several full
Fase I/II/III cycles using the current `GameEngine.ejecutar_dia_laboratorio` blocking-callback
API, and diffs the final state against `tests/golden/day4_2p_seed1234.json`. Its purpose is to
give behavior-preserving refactors of `engine.py` (e.g. a turn-state-machine refactor) a
regression baseline to check against, since none existed before. If a deliberate rules change
alters this golden game's outcome, regenerate the snapshot rather than hand-editing it.

`test_actions_suite.py` is a hand-rolled suite (`check()` / `xraises()` helpers) that exercises
every `ActionManager` action's happy path and failure path (60/60 passing). It's a standalone
script, not pytest — run it directly.

`tests/test_turn_state_machine.py` exercises the non-blocking `iniciar_dia`/`jugador_activo`/
`terminar_turno_actual`/`pasar_turno` API directly (no callback), including a headless
multi-day driver and targeted tests for the turn-economy rule above.

`tests/test_events.py` covers `GameEngine`'s event emission (see Architecture below): a full
day's global + per-player events, a manual bake vs. an automatic collapse, the
contamination-transition-only rule, and `event_sink` forwarding.

`tests/test_server_api.py` plays a full 2-player game purely over HTTP against `server/app.py`
via Starlette's `TestClient` (real ASGI routing/JSON parsing, no direct calls into
`server/sessions.py`/`server/commands.py`) — room creation, join, start, turn-ownership
rejection, an action, both players passing to trigger the automatic Fase III → next-day Fase I
transition, and polling `/events`. This was the Milestone 3 "de-risk the server before building
any frontend" proof, kept as a permanent regression test rather than a throwaway script.

## Architecture

Strict separation enforced by `context/ARCHITECTURE.md`, and followed by the four modules:

- **`models.py`** — pure data: `Player`, `Recipe`, `ClimateCard`, `FermentationSlot`,
  `HorneadoRecord`, `Technologies`, `Environment`, plus the `RECIPE_CATALOG` /
  `build_climate_deck()` constant data. No game-flow logic lives here beyond small mutators
  (e.g. `Player.ajustar_vitalidad`) that enforce the [0, 6] clamps.
- **`engine.py`** — turn/phase orchestration: `GameEngine` runs the three-phase Day of Lab loop,
  plus `Market` (recipe/supply market with refresh protocol) and endgame/scoring
  (`resolver_horneado`, `calcular_ranking_final`). Two ways to drive Phase II, sharing one
  round-robin implementation (`_preparar_fase_II` / `_avanzar_a_siguiente_elegible`) so they can't
  diverge:
  - **Blocking-callback path** (used by the CLI): `ejecutar_dia_laboratorio(ejecutar_turno_jugador)`
    → `fase_I_ambiente` → `fase_II_accion(callback)` → `resolver_fase_III()`. Runs exactly one day
    and stops (does not auto-chain into the next day's Phase I), preserving `main.py`'s per-day
    pause/report point.
  - **Non-blocking state-machine path** (used by `server/app.py`): `iniciar_dia()` then poll
    `jugador_activo` / call `terminar_turno_actual()` or `pasar_turno(player)` per visit, then
    `resolver_fase_III()`. See `Fase` enum and `GameEngine.turno_nonce`.

  **Turn-economy rule (deliberate, diverges from `ACTIONS_REGISTRY.md`'s literal CLI-original
  behavior)**: Acción A (Alimentar) and Horas Extras do **not** end a player's turn/visit by
  themselves — only a PA-costing action or an explicit `pasar_turno()` does. A player who has
  spent both PA elsewhere stays eligible for further visits solely to use an unused free action
  (`GameEngine.jugador_activo`'s eligibility check: `puntos_accion > 0 or not
  accion_alimentar_usada or not horas_extras_usadas`). An explicit pass is a full forfeiture of
  the rest of the day, including unused free actions — anything that ends a player's turn **must**
  call `engine.pasar_turno(player)`, never assign `player.puntos_accion = 0` directly, or that
  player will be revisited forever (see `main.py`'s `"P"` branch and `tests/_bot.py`'s fallback for
  the required pattern).
- **`actions.py`** — `ActionManager`, one `accion_X_*` method per action in
  `ACTIONS_REGISTRY.md` (A: Alimentar, B: Iniciar Receta, C: Adquirir Insumos, D: Implementar
  Mejora, E: Técnica/Pliegues, F: Hornear, G: Investigar Protocolo, H: Re-cultivo Manual, I:
  Inóculo de Emergencia, plus Simposio Técnico and Horas Extras). Every method validates
  preconditions and raises before mutating state (fail-fast).
- **`main.py`** — CLI only: rendering (`mostrar_estado_jugador`, `mostrar_mercado`, colored
  output helpers), prompting (`_pedir_int`, `_pedir_opcion`, `_params_accion_*`), and the
  `main()` entrypoint / `setup_game()`. Contains no rules logic — it calls into `engine`/
  `actions` and displays the result.
- **`events.py`** — `GameEvent`/`EventoTipo`/`EventSink`: a structured log of automatic,
  no-player-input state changes (chief-researcher assignment, climate reveal, market refresh,
  mass advance, structural collapse, every bake — manual or auto-collapse, both go through
  `resolver_horneado` — metabolic decay, contamination onset, game over with its reason).
  `GameEngine` always keeps the full log (`engine.eventos`) and optionally forwards each event,
  at emission time, to an injected `event_sink` (e.g. for a future server to broadcast to
  clients). `main.py`'s `_reporte_fermentacion` is built entirely from
  `engine.eventos[since_index:]` — there's no before/after snapshot-diffing anywhere in the
  codebase anymore; an automatic event (like a structural collapse costing a player several
  points with no action on their part) is always something the engine explicitly said happened,
  not something a caller has to infer from a state diff. When adding new automatic engine
  behavior, emit an event for it at the point of mutation rather than expecting a caller to
  reconstruct it from before/after state.

- **`bootstrap.py`** — `create_game(nombres: List[str]) -> GameEngine`: the actual game-construction
  logic (shuffled basic-recipe assignment, player setup), with no CLI dependency, so `server/`
  never has to import `main.py`. `main.py:setup_game` is a thin wrapper that only fills in
  default player names for the CLI's convenience, then delegates here.
- **`serialization.py`** — `snapshot(engine) -> dict`: the full, *unredacted* state via
  `dataclasses.asdict`, reused by both `tests/test_golden_game.py` and `server/views.py`. Works
  with no schema library because every domain dataclass already serializes cleanly and every
  domain enum is `str, Enum` (so e.g. `TipoHarina.BLANCA` is already a `str` and needs no
  conversion for `json.dumps`).
- **`server/`** — the headless HTTP backend (Starlette + uvicorn; see `server/app.py`'s module
  docstring for the transport/concurrency reasoning). `sessions.py` holds `RoomManager`/
  `GameSession`/`Seat` — in-memory rooms, no accounts, a room code + a per-player secret token is
  the entire identity/reconnect mechanism. `commands.py` holds `resolver_comando`, which maps a
  wire action id + params to the right `ActionManager` call (resolving what HTTP can't carry
  directly — Acción B's recipe via `carpeta_index`, `TecnologiaID`/`TipoHarina` from plain
  strings) and **owns `ACCIONES_QUE_TERMINAN_TURNO`**, the per-action turn-ending table the
  turn-economy rule above deferred to this layer. `views.py` builds the client-facing state via
  `serialization.snapshot()` with the one redaction that matters — `Environment.mazo_clima` /
  `Market.mazo_recetas` (the hidden future decks) become counts, since everything else in this
  game is public information. `app.py` wires it all into routes and maps the `FermentumError` /
  `server/errors.py` `RoomError` hierarchies to HTTP status codes via one `isinstance` walk.
  Nothing in `models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`
  imports anything from `server/` — the dependency only goes one way.

`agents.py` is currently an empty placeholder file.

### Error handling

All game-rule failures raise semantic exceptions from `exceptions.py` (never bare `Exception`,
`ValueError`, or a boolean return):

- `FermentumError` — base class for `except FermentumError` catch-all
- `ResourceDeficitError` → `NotEnoughActionPointsError`, `MissingResourceError`
- `RuleViolationError` → `StationBlockedError`, `CarpetaFullError`
- `InvalidActionError` — malformed/invalid call parameters
- Engine-flow errors: `PhaseViolationError`, `GameAlreadyOverError`,
  `InsufficientPlayersError`, `MarketSlotEmptyError`, `NotYourTurnError` (server-layer turn
  ownership; the CLI never raises it since its callback only fires for the correct player)

`server/errors.py` holds a second, separate hierarchy (`RoomError` → `RoomNotFoundError`, etc.)
for lobby/session problems that aren't game-rule violations — kept out of `exceptions.py` so that
file stays strictly the rules vocabulary `ActionManager`/`GameEngine` use, independent of whether
a server exists.

`ActionManager` methods validate every precondition (PA, resources, station/carpeta limits,
contamination state) via `_require_*` helpers and raise before touching state — never partially
apply an action.

### Core game loop, in one paragraph

Each "Día de Laboratorio" is Phase I (reveal climate card, adjust `temperatura_actual`, assign
Investigador Jefe, refresh the market) → Phase II (round-robin, 2 PA per player, one action per
visit until no player has PA or an unused free action — see the turn-economy rule above) → Phase
III (every active `FermentationSlot` advances by
`temperatura_actual/5 + dado_inoculo + modificador_incubadora`; overshoot into
`zona_sobrefermentada` auto-bakes at 0 PA cost with a penalty; then all players lose 1 vitality,
2 if "Aletargamiento Invernal" is active). The game ends when the climate deck is exhausted or
any player successfully bakes their 5th recipe (collapsed bakes don't count), then scores per
`CORE_MECHANICS.md` §3.
