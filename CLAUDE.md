# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A simulation of **Fermentum**, a 1-4 player Eurogame about resource management and
engine-building (fermenting bread), being ported from a single-process CLI to an online
multiplayer web app: the Python rules engine is kept as-is and a thin HTTP layer + a Vue 3
frontend are added on top, rather than porting the rules to another stack. The core simulation
(`models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`/
`disponibilidad.py`/`main.py`) has zero external dependencies — everything is stdlib Python 3.12.
The optional `server/` package (headless HTTP backend) needs `starlette`+`uvicorn`, kept in its
own `pyproject.toml` dependency group so a CLI-only checkout never has to install a web
framework. `pytest`+`httpx` are dev-only. `web/` (Vue 3 + TypeScript + Vite, see `web/README.md`)
is a fully separate npm project with its own dependencies — nothing in the Python side depends on
it or on Node being installed.

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

# Run the web client (separate terminal, needs the backend above already running) — see
# web/README.md. vite.config.ts proxies /games/* to :8000 so no CORS setup is needed in dev.
cd web && npm install && npm run dev

# Type-check + production build the web client
cd web && npm run build
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

`tests/test_disponibilidad.py` covers `disponibilidad.acciones_disponibles` — Day-1 defaults,
0-PA disabling costed actions but not free ones, emergency-protocol availability by resource, and
already-used actions reporting disabled.

`tests/test_sse.py` covers the SSE push mechanism (Milestone 5, `GET /games/{id}/events/stream`):
error paths (missing token, room not found, game not started) via a plain non-streaming `.get()`,
and — the actual load-bearing test — `GameSession.difundir_evento` fanning out to every
subscriber queue, plus `RoomManager.iniciar` correctly wiring it as the engine's `event_sink`.
Starlette's `TestClient` cannot exercise the endpoint end-to-end: it hangs on a genuinely
open-ended `StreamingResponse` generator regardless of whether a concurrent action is involved
(confirmed experimentally). Confirmed working live in a real browser (Milestone 5 follow-up): an
action from one player updates another player's screen without waiting for a poll tick.

`tests/test_avisos_accion.py` covers the ephemeral per-action channel (`AvisoAccion`, see
Architecture below): the frame format (`event: accion` and, load-bearing, **no `id:` line**,
contrasted against a numbered log frame), `difundir_accion` fanning out to every subscriber, the
four routes that broadcast (`/actions`, `/pass`, `/force-pass`, `/undo`), a fail-fast-rejected
action broadcasting nothing, and — the guardrail — a free action plus an undo leaving
`len(engine.eventos)` unchanged, which is the invariant that forced this to be a separate channel
instead of a new `EventoTipo`. Same `TestClient` limitation as `test_sse.py`, so the stream is
not consumed end-to-end; it hooks a fake queue onto the live `GameSession` (reachable via
`app.state.salas`) instead. The end-to-end wire format was verified separately against a real
`uvicorn` with a second client on the stream, and the audio confirmed by ear in a browser.

`tests/test_robustness.py` covers the three Milestone 6 additions: force-pass (rejects before the
inactivity threshold, succeeds after it, rejects with no active turn), `RoomManager.limpiar_inactivas`
(removes only genuinely idle rooms, respects the longer EN_CURSO threshold, deletes the matching
disk snapshot), and the persistence round-trip (`server/persistence.py`: save → `cargar_todas()` →
the restored session is still genuinely playable, not just readable — confirmed with a real
`pasar_turno()` call after reload — plus a corrupted/version-mismatched file being discarded
cleanly). `tests/conftest.py` has an autouse fixture redirecting `persistence.DATA_DIR` to a temp
path per test, since `RoomManager` now persists to disk on every mutation — without it, the test
suite would write real files into the repo's own `data/games/`. The full persist → kill process →
start a new process → reload → keep playing cycle was also verified against two real `uvicorn`
processes, not just in-process.

The `web/` frontend was confirmed working in a real browser after Milestone 4 (room creation
through to actual gameplay) — the only environment issue hit was a Node version mismatch (Vite 8
needs Node ≥20.19/≥22.12; fixed via `web/.nvmrc` + `nvm alias default`, see git history). It has
no automated tests of its own; verification is `vue-tsc -b` + a clean production build plus that
manual browser confirmation.

## Architecture

Strict separation enforced by `context/ARCHITECTURE.md`, and followed by the four modules:

- **`models.py`** — pure data: `Player`, `Recipe`, `ClimateCard`, `FermentationSlot`,
  `HorneadoRecord`, `Technologies`, `Environment`, plus the `RECIPE_CATALOG` /
  `build_climate_deck()` constant data. No game-flow logic lives here beyond small mutators
  (e.g. `Player.ajustar_vitalidad`) that enforce the [0, 6] clamps.
- **`engine.py`** — turn/phase orchestration: `GameEngine` runs the three-phase Day of Lab loop,
  plus `Market` (recipe market with refresh protocol, the 3-track Bolsa de Harinas, and the
  Mercado de Tendencias deck — see the GDD v0.0.2 note above; there is no supply-lot market
  anymore) and endgame/scoring (`resolver_horneado`, `calcular_ranking_final`). Two ways to drive
  Phase II, sharing one
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
  `ACTIONS_REGISTRY.md` (A: Alimentar, B: Iniciar Receta, C: Visitar el Mercado, D: Implementar
  Mejora, E: Técnica/Pliegues, F: Hornear y Vender, G: Investigar Protocolo, H: Re-cultivo Manual, I:
  Inóculo de Emergencia, plus Simposio Técnico, Horas Extras, and Pedido de Urgencia). Every method
  validates preconditions and raises before mutating state (fail-fast). **GDD v0.0.2 rules
  overhaul** (branch `rules-gdd-0.0.2`): introduces a `Player.monedas` economy — Acción C
  (`accion_C_visitar_mercado`) replaced the old random-lot Acción C (Adquirir Insumos, now removed
  along with `SupplyLote`/`Market.suministros`) with priced buy/sell of flour against a shared,
  3-track `Market.posiciones_harina` "Bolsa de Harinas" (moved by both player transactions and the
  daily Mercado de Tendencias — announced in Fase I, applied in Fase III, see below) plus
  temperature-priced water lots
  (`engine.PRECIO_AGUA`); Acción F now pays out Monedas per zone on top of the existing
  points/Datos logic (`Recipe.monedas_baja/optima/sobre`, flat `+2` Monedas Bono de Sabor); setup
  (`bootstrap.create_game`) now deals from an 8-card `PATROCINIO_CATALOG` instead of a hardcoded
  4-slot `player_index` table, driving both Día 1 turn order (`GameEngine`'s new `orden_inicial`
  param) and starting resources; the lab-upgrade cap (Acción D) is now per-technology, not a
  single "one upgrade per game" total, with a 4th tech (Criopreservación) added; and endgame
  scoring gained a "Conversión de riqueza" term. Recipe zone/point/Monedas values were rebalanced
  across the board — see `context/RECIPE_DATABASE.md`.
- **`main.py`** — CLI only: rendering (`mostrar_estado_jugador`, `mostrar_mercado`, colored
  output helpers), prompting (`_pedir_int`, `_pedir_opcion`, `_params_accion_*`), and the
  `main()` entrypoint / `setup_game()`. Contains no rules logic — it calls into `engine`/
  `actions` and displays the result.
- **`events.py`** — `GameEvent`/`EventoTipo`/`EventSink`: a structured log of automatic,
  no-player-input state changes (chief-researcher assignment, climate reveal, market refresh,
  end-of-day discard of the market's oldest recipe, mass advance, structural collapse, every
  bake — manual or auto-collapse, both go through `resolver_horneado` — metabolic decay,
  contamination onset, game over with its reason).
  `GameEngine` always keeps the full log (`engine.eventos`) and optionally forwards each event,
  at emission time, to an injected `event_sink` — this is what `server/sessions.py`'s
  `GameSession.difundir_evento` plugs into (Milestone 5) to push events to connected SSE clients
  live, with no polling needed on the happy path. `main.py`'s `_reporte_fermentacion` is built
  entirely from
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
- **`disponibilidad.py`** — `acciones_disponibles(engine, player) -> List[{id, habilitada, motivo}]`:
  cheap per-action checks (PA, contamination gate, empty carpeta/stations, market emptiness, tech
  already installed) so a remote client can enable/disable its own buttons without reimplementing
  `ActionManager`'s rules. Not authoritative — an action reported "enabled" can still fail at
  submit time for reasons this module doesn't check (e.g. exact recipe resource cost);
  `ActionManager` remains the only real validation.
- **`server/`** — the headless HTTP backend (Starlette + uvicorn; see `server/app.py`'s module
  docstring for the transport/concurrency reasoning). `sessions.py` holds `RoomManager`/
  `GameSession`/`Seat` — in-memory rooms, no accounts, a room code + a per-player secret token is
  the entire identity/reconnect mechanism. `Seat.last_seen` is bumped on every authenticated
  request (in `GameSession.asiento_por_token`, the one choke point every route passes through) and
  backs two Milestone 6 features: any seated player can `POST /games/{id}/force-pass` to pass the
  active player's turn once they've been silent for `UMBRAL_INACTIVIDAD_SEGUNDOS` (90s — the
  server decides eligibility, the client just offers the button), and
  `RoomManager.limpiar_inactivas()` (run on a background loop from `app.py`'s lifespan) drops
  rooms idle longer than a per-status threshold (LOBBY/EN_CURSO/TERMINADA get very different
  grace periods — an active game is kept for hours, an unstarted lobby for 30 minutes).
  `persistence.py` pickles each `GameSession` to `data/games/{id}.pkl` after every mutation
  (`RoomManager.guardar`) and reloads them at process startup (`app.py`'s lifespan again) — chosen
  over hand-written JSON because `GameEngine`'s internal turn-state (`Fase`, order, cursor, nonce,
  who's already passed) has no serialization-oriented accessors, and `pickle` round-trips the
  whole object graph — including the circular `GameEngine._event_sink → GameSession.difundir_evento`
  reference — with no custom code; confirmed by actually restarting a live `uvicorn` process
  mid-game and continuing to play. `GameSession.__getstate__`/`__setstate__` exclude `lock` and
  `suscriptores` from the pickle and rebuild them fresh on load, since neither an `asyncio.Lock`
  nor an SSE client's `asyncio.Queue` means anything outside the process/event loop that created
  them. Accepted limitation, stated rather than hidden: a pickle is fragile across class-shape
  changes, so a version mismatch on load discards that one file with a log message instead of
  crashing startup — a deploy that changes `Player`/`GameSession`'s fields can end in-progress
  games. `GameSession.difundir_evento` (Milestone 5) fans out
  each emitted event to every SSE subscriber for that room; it's registered as the engine's
  `event_sink` in `RoomManager.iniciar`, and registration + backlog-read happen under the same
  session lock that guards all engine mutation, so there's no race between "just subscribed" and
  "already emitted" — see `GET /games/{id}/events/stream` in `app.py`, which resumes from
  `Last-Event-ID` or `?since=N`/`?player_token=` (the browser's native `EventSource` can't send
  custom headers, so this one route accepts the token as a query param too — every other route
  stays strictly header-only). Polling (`GET /games/{id}/events?since=N`) remains the permanent
  reconnect/catch-up path, not replaced by SSE. `commands.py` holds `resolver_comando`, which maps a
  wire action id + params to the right `ActionManager` call (resolving what HTTP can't carry
  directly — Acción B's recipe via `carpeta_index`, `TecnologiaID`/`TipoHarina` from plain
  strings) and **owns `ACCIONES_QUE_TERMINAN_TURNO`**, the per-action turn-ending table the
  turn-economy rule above deferred to this layer. `views.py` builds the client-facing state via
  `serialization.snapshot()` with the redaction that matters — `Environment.mazo_clima` /
  `Market.mazo_recetas` / `Market.mazo_tendencias` (the hidden future decks) become counts, since
  everything else in this game is public information (including `Market.posiciones_harina`, the
  Bolsa de Harinas price tracks, which are left untouched) — plus `disponibilidad.acciones_disponibles` per player and
  `puntos_maestria_final`/`calcular_ranking_final` (both `@property`/methods, not dataclass
  fields, so `dataclasses.asdict` wouldn't include them — computed here instead of in the
  frontend, same reasoning as action availability: don't duplicate `CORE_MECHANICS.md` §3's
  scoring formula in TypeScript) — plus the engine turn/phase fields `fase_actual`,
  `turno_nonce`, `jugador_en_turno_idx`, `jefe_investigador_idx` and `turno_orden`
  (`GameEngine.turno_orden`: the full day's play-order list of player indices, `[0]` = Jefe;
  public, unredacted; holds the last day's order after game over). `app.py` wires it all into routes and maps the `FermentumError` /
  `server/errors.py` `RoomError` hierarchies to HTTP status codes via one `isinstance` walk.
  Nothing in `models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`
  imports anything from `server/` — the dependency only goes one way.
- **`web/`** — the frontend (Vue 3 + TypeScript + Vite; see `web/README.md`).

  **Design system (`App.vue`'s global `<style>`) — read this before writing any CSS here.**
  The UI grew panel by panel and ended up with no system at all: 30 distinct `font-size` values
  (twelve of them inside the 0.62–0.82rem band, differing by fractions of a pixel), 48 distinct
  `padding` declarations, 11 border radii, three alphas of the same amber wash, `#1a1410`
  copy-pasted into 8 files, and five breakpoints with no shared token. `App.vue` now owns the only
  token layer and **no component should write a raw hex, font size, spacing value or radius
  again**:
  - **Three surfaces**, the load-bearing idea — `--mesa` (the ground), `--zona` (printed board
    regions), `--carta` (what is raised off the table). Panels rendered *inside* a region are
    flattened by `GameView.vue`'s `.region :deep(.panel)` rule (transparent, no border, no
    padding) precisely so there are never two concentric rectangles of the same color per module;
    only cards carry `--sombra-carta`, and regions carry an inset hairline frame instead.
    A **modal is the raised tier, not a printed zone**: the eight overlay roots use the global
    `.modal` rule (`--carta` + `--borde-fuerte` + `--sombra-flotante`), never `.panel`, and each
    wraps its `.fondo-modal` root in `<Teleport to="body">`. Both halves are load-bearing:
    `:deep()` compiles to a plain descendant selector, so before the teleport every modal opened
    from inside a region (all 11 action modals via `ModalShell`, `DetalleRecetaModal`, both
    `PilaDescarte*Modal`) was flattened to a transparent, padding-less box you could read the
    board through — and teleporting also puts every modal's `z-index` on one body-level scale
    instead of competing inside each region's subtree.
  - **Two accents with meaning**: `--cobre` = yours / interactive / active turn, `--verdin` =
    shared market state. Everything else (`--vital`, `--riesgo`, `--calido`, `--frio`) is game
    state and is never used decoratively. `--lavado-*` gives one alpha per color;
    `--tinta-sobre-acento` replaces the 8 copies of `#1a1410`; `--velo-modal` the 8 modal scrims.
  - **Type**: Bricolage Grotesque (titles — the bakery half), IBM Plex Sans (body — the lab half),
    IBM Plex Mono for **every number that sits on a scale**, via the global `.dato` class. Loaded
    from Google Fonts in `web/index.html`. Seven sizes, `--t-micro` … `--t-display`. The global
    `.eyebrow` class replaced five differently-valued copies of the same section-label idea.
  - **Native chrome**: `:root` sets `color-scheme: dark` plus `scrollbar-width`/`scrollbar-color`
    (thumb `--borde-fuerte`, transparent track so the bar sits on whatever surface is under it).
    Both inherit, so all eight scrolling containers are covered from one place — no component
    styles its own scrollbar, and `::-webkit-scrollbar` is deliberately unused (Chrome ignores it
    once the standard properties apply).
  - **Space/radius**: `--e1`…`--e6` and `--r-control`/`--r-carta`/`--r-zona`. Icon boxes are
    `.ico-xs/-s/-m/-l` (the eight `Icono*.vue` already declare `width:100%`, so consumers only
    pick a box). Two breakpoints, **720px** and **1100px**.
  - The old `--color-*` names remain as aliases pointing at the new tokens, so any component not
    yet migrated keeps working; they are safe to delete once nothing reads them.

  **`PistaMedida.vue` — the instrument, and the visual signature.** Everything measurable in
  Fermentum is a reading on a banded scale (Vitalidad 0–6, Acidez 0–6, fermentación 1–20, precio
  1–5). Each of those used to draw itself differently (pips, an 8px bar, a 10px bar, a table
  visor). `PistaMedida` now draws all of them: ruled track + zone bands + a **solid bracket at the
  current value and a dashed bracket at the projected one** + a Plex Mono readout. The dashed
  bracket generalizes what `PistaPrecioHarina.vue` had invented for tonight's price move, and it
  is what the contamination warning now uses — `vitalidad_prevista` is rendered *as part of the
  reading* rather than as a badge bolted beside it. `valor: null` draws bands with no needle
  (a recipe card shows its zones but has no position yet); `tonoPrevisto` lets the dashed bracket
  differ in color from the solid one (`EstacionCard` colors it by the zone the dough will land in).
  Call sites: `MiTablero`, `EstacionCard`, `RecetaCard`.

  **Layout — one screen, regions scroll internally.** `GameView.vue` is a `100dvh` flex board, not
  a scrolling document: a header rail, then `.cuerpo` = [left block: Mesa Común over Mi Tablero]
  + a full-height side rail, then the action bar pinned as the bottom region. Every region sets
  `min-height: 0` and `overflow-y: auto`, so no region can push another off screen. `.app-shell`'s
  `max-width: 1100px` centering now applies only via the `centrado` class (`App.vue` binds it when
  *not* in a game) — the lobby and ranking are documents and keep a measure limit; the board fills
  the monitor. The action bar keeps its footprint on an opponent's turn (showing whose turn it is
  plus force-pass) so the layout never jumps mid-round. At ≤1100px the rails unstack and the page
  scrolls again; at ≤720px the order flips so the action bar and your own board come first.
  `MiTablero` is correspondingly wide-and-short: its content is a `flex-wrap` row of sub-zones
  (cultivo / estaciones+mejoras / carpeta / archivo), not one tall column.

  One reactive store
  (`src/store.ts`) updated wholesale from the server's full-snapshot responses — no Pinia/Vuex,
  no optimistic updates (submit an action, wait for the response, render it; the server is the
  only rules authority and a turn-based game has no latency budget worth spending complexity on).
  `iniciarPolling()` opens an `EventSource` against `/events/stream` (Milestone 5) — each pushed
  event immediately triggers a state refetch — plus slow fallback polling (state every 4s, events
  every 15s) in case the SSE connection silently fails; `EventSource`'s own auto-reconnect with
  `Last-Event-ID` handles the common disconnect case already, so the fallback poll is a safety net,
  not the primary path. `src/types.ts` hand-mirrors the `server/views.py` JSON shape — there's no
  shared schema, so a backend field rename needs a matching edit there. `src/components/acciones/`
  has one component per player action, mirroring `main.py`'s `_params_accion_*` functions, reading
  `acciones_disponibles` from the state to decide what's clickable rather than reimplementing
  `ActionManager`'s rules. The Phase III report renders as a mandatory dismissible modal
  (`FermentationReportModal.vue`), not a log line — an automatic structural collapse can cost a
  player several points with no action on their part, and they need to be told, not left to infer
  it from state changing between polls.

  **Start-of-day modal**: `InicioDiaModal.vue` (formerly `EventoClimaticoModal.vue`) gives both
  cards revealed by Fase I — the climate card *and* the announced Mercado de Tendencias card — one
  mandatory-modal treatment, explaining their concrete effects in plain language (translated from
  the raw `efecto_biologico`/`efecto_pasivo` enum values — e.g. "Iniciar Receta costará 1 token de
  Agua menos hoy," not just "Alta Humedad") rather than leaving them to the board panels to be
  noticed. Both are covered by one modal, not two chained ones, so a player dismisses a single
  thing per day. The load-bearing distinction the modal has to make unmistakable is that the
  climate card governs **today** while the trend governs **tomorrow**: it says so outright and
  then shows a concrete today-vs-tomorrow buy/sell price table for all three flours, computed
  client-side from `web/src/data/preciosHarina.ts` (the existing mirror of `engine.PRECIOS_HARINA`)
  by clamping `posiciones_harina[tipo] + tendencia_pendiente` to [1, 5]. Unlike the Fase III
  report, this one is built straight from current state
  (`environment.ultima_carta_clima`/`temperatura_actual` and `market.tendencia_pendiente`, already
  present, not event-log filtering) — deliberately more robust across the
  return-to-lobby/second-game reset (a fresh game's event `seq` restarts at 0). `store.ts` tracks a
  non-reactive `ultimaCartaClimaId` (module-level, per tab) to detect when the day actually turned
  over, seeded `undefined` so Day 1 triggers it too, not just later days; reset alongside the other
  per-game flags in `cerrarSesion()`/`volverAVistaDeLobby()`. It keys off the *climate* card even
  though it gates both halves, because the climate card is the only one of the two with a stable
  `id` — trend modifiers are ints in -2..+2 that repeat, so two "+1" days in a row would defeat a
  value-identity guard. Reconnecting or loading into an already-started game shows the current
  day's cards once for that tab even if others already dismissed them — deliberate (it's "here's
  today's situation," unlike the Fase III report, which is about a past transition and is
  suppressed on reconnect). `GameView.vue` sequences it after `FermentationReportModal`
  (`v-else-if`) since both can go pending from the same day-transition state push, and the Fase III
  report is the more consequential one to see first.

  The trend's persistent, all-day counterpart lives in `MazoTendenciasPanel.vue`, which now
  distinguishes three things that used to be conflated: `market.tendencia_pendiente` (revealed this
  morning, applies tonight — the prominent slot), the last entry of `descarte_tendencias` (applied
  last night, so it is what sets *today's* prices), and the rest of the discard (history). Before
  this change `robar_tendencia()` pushed straight to the discard, so that panel derived "today's
  card" as the discard's last element and `PilaDescarteTendenciasModal.vue` had to `slice(0, -1)`
  it back off; both assumptions are gone. `PistaPrecioHarina.vue` additionally marks the cell each
  visor will move to tonight with a dashed outline, next to the solid `.actual` bracket.

  **Session persistence / reconnect**: `store.ts` saves `Sesion` (room id + player token) to
  `localStorage` on every `establecerSesion` call. Without this, closing the browser mid-game was
  a dead end — the backend was already designed for reconnect (per-player tokens valid for the
  room's lifetime, state independent of any live connection), but `join` only works while a room
  is still in `lobby`, so a player who lost their in-memory session had no way back into a game
  already in progress. `App.vue` calls `intentarReconectar()` once on mount, before deciding
  which view to show: it verifies the saved room still exists and the token is still accepted by
  the server (never trusts the cached copy blindly), and either restores just `store.sesion` (room
  still in `lobby` — `LobbyView.vue`'s own `onMounted` then resumes the waiting-room view from
  that) or restores the full game state and starts SSE/polling (room already started — lands
  straight in `GameView`). Any failure at any step (room gone, token rejected) just clears the
  stored session and falls back to the normal create/join form.

  **Contamination alert (opt-in)**: hitting Vitalidad 0 in Fase III is one of the harshest swings
  in the game (-3 PM, a lower Madurez term, Acción B locked until an emergency protocol) and used
  to be invisible until after it happened. `GameEngine.vitalidad_prevista`/`riesgo_colapso`
  (`engine.py`) predict tonight's outcome; both share `_delta_desgaste` with the real
  `_aplicar_desgaste_metabolico`, so the warning can't drift from the actual rule (it already
  accounts for the Criopreservación exemption and Aletargamiento Invernal's -2). The prediction is
  exact rather than a guess because the climate card is resolved in Fase I and nothing else in
  Fase III touches vitality before the decay. `riesgo_colapso` returns False for an
  already-contaminated player — staying at 0 is not a new episode, the same
  transition-only rule `Player.ajustar_vitalidad` and `EventoTipo.CONTAMINACION` follow.
  `server/views.py` ships both as per-player fields from the same zip loop that adds
  `puntos_maestria_final`/`color` — computed server-side deliberately, since the decay formula is
  a `CLIMATE_LOGIC.md` rule that must not be duplicated in TypeScript (and it's a `@property`, so
  `dataclasses.asdict` wouldn't include it). Injected in `views.py`, **not** `serialization.py`,
  so the golden-game snapshot stays untouched. The alert is opt-in per player, chosen by a
  checkbox in `LobbyView.vue`'s create/join form (the one screen every player passes through —
  only the host has a start button) and stored in `store.preferencias` under its own
  `'fermentum-preferencias'` localStorage key, separate from the session key because
  `cerrarSesion()` deletes the session and a durable preference should outlive it; for the same
  reason it is *not* reset in `cerrarSesion()`/`volverAVistaDeLobby()`, unlike the per-game
  module-level guards. When enabled it drives two things: `MiTablero.vue` paints the Vitalidad
  pips red plus a `⚠` badge in the previously-unused third column of `.medidor`, and the
  pass-advice modal (below) additionally shows a red collapse-warning block.

  **Pass-advice modal**: passing is a total forfeit of the rest of the day (PA *and* unused free
  actions), so `BarraAcciones.vue` gates "Pasar turno" behind a `ModalShell.vue`-based
  confirmation whenever **any** of the local player's `acciones_disponibles` entries is still
  `habilitada` — not gated by any preference (this superseded the earlier contamination-only
  inline `.confirmacion-pase` strip; the opt-in part is now just the danger block inside it). The
  modal lists the remaining actions by filtering the component's own `BOTONES` table through the
  server-shipped availability — deliberately reusing already-shipped data instead of
  reimplementing enablement rules (e.g. "could Acción A actually save me" needs ≥10 of a *single*
  flour type, or Pedido de Urgencia, and under Aletargamiento a single +1 isn't enough); each row
  is a shortcut that closes the confirmation and calls the existing `abrir(id)`, dropping into
  that action's normal modal flow, and the footer offers "Seguir jugando" / "Pasar de todos
  modos". Since Pedido de Urgencia is enabled whenever the player holds ≥1 Dato, the modal
  appears on most passes — accepted deliberately: over-warning is the right failure mode for a
  safety net; getting the rule subtly wrong is not.

  **Undo (visit-scope)**: `POST /games/{id}/undo` restores the game to the state at the start of
  the active player's **current visit** — available only to that player, only while the visit is
  open, unlimited (always back to the same point). Mechanism: `GameSession.tomar_checkpoint()`
  pickles the engine right before the visit's *first free action* (`enviar_accion` takes it lazily;
  A / Horas Extras / Pedido de Urgencia don't end the visit, so several can share one checkpoint),
  detaching `engine._event_sink` around the dump — it's a bound method of the session, so pickling
  it would drag a full `GameSession` clone along — and `restaurar_checkpoint()` re-wires
  `difundir_evento` on the restored engine so SSE keeps flowing. A PA action, a pass, or a
  force-pass **closes** the visit and discards the checkpoint (cleared *after* the mutating call
  succeeds, never before — fail-fast rejections must not destroy a live checkpoint); the key is
  `(dia_actual, turno_nonce, player_index)` because the nonce alone doesn't mark visit boundaries
  (free actions don't bump it). Snapshot-restore was chosen over inverse commands because several
  mutations are lossy at their clamps (`mover_visor_harina`'s [1,5], `dados_inoculo`'s `min(3,…)`)
  — an "inverse action" would be wrong exactly at the boundaries. It is safe because every Fase II
  action is deterministic over public information (`actions.py` imports no `random` and never
  touches a hidden deck; all reveals live in `fase_I_ambiente`), and inside the undo window only
  free actions occur, **none of which emit events** — so `engine.eventos` is byte-identical across
  an undo and client `since` pointers never dangle (no epoch counter needed). The hidden-info rule
  ("revealed information can never be un-revealed; undo restores from the reveal point") is
  vacuously true today but wired for the future: `server/commands.py:ACCIONES_QUE_REVELAN` (all
  `False`) forces a checkpoint re-take right *after* a flagged action resolves — the reveal
  becomes the new undo floor — and its UI mirror in `web/src/data/descripcionesAcciones.ts` adds
  a "no se puede deshacer" tooltip warning to flagged actions. The client gets
  `puede_deshacer` in the state view and shows an "↩ Deshacer" button beside "Pasar turno"
  (`BarraAcciones.vue`). Checkpoint bytes ride in the persistence pickle (undo survives a
  restart); `VERSION_FORMATO` bumped to 8 for the `GameSession` shape change, and
  `reiniciar_a_lobby` clears the checkpoint with the engine. Tests: `tests/test_undo.py`.

  **Live score and bake archive**: `puntos_maestria_final` always shipped but was rendered only
  on the endgame `RankingView` — during play the score existed nowhere on screen. Now
  `MiTablero.vue` carries a score strip under the header (`IconoMaestria` glyph +
  `puntos_horneados`, the new "points from bakes so far" number, with the projected final PM
  beside it and a tooltip explaining the projection moves for reasons other than baking), and the
  old one-line archive count is a real "Archivo de Horneados (X/5)" zone — `/5` because the fifth
  successful bake ends the game — listing each record's recipe, zone, `puntos_totales` (marking the
  sabor bonus) and monedas, with collapses appended in `--color-mal` since their negative points
  count toward the score. `TablerosOponentes.vue` shows every opponent's `🍞 X/5` and Maestría
  (public info). Server side, `Player.puntos_horneados` (models.py, exactly the Puntos
  Base + Sabor terms of `puntos_maestria_final` expressed per record) and the two
  `HorneadoRecord` `@property`s `asdict` drops (`puntos_totales`, `zona_resultado`) are injected
  per player / per record in `server/views.py`'s existing loop — view layer, not
  `serialization.py`, so the golden snapshot is untouched (tests: `tests/test_puntos_horneados.py`).
  After a voluntary bake, `ModalF.vue` no longer closes silently: it stores the freshly-applied
  snapshot's last `archivo_horneado_exitoso` record in `store.resultadoHorneado` and
  `GameView.vue` shows `ResultadoHorneadoModal.vue` (first in the modal chain). The record must
  live in the store, not a ModalF ref: Acción F ends the turn, so the response snapshot unmounts
  `BarraAcciones` (`v-if="esMiTurno"`) — and ModalF with it — before any local state could render.

  **Board-game-style layout and per-player color**: the UI is split into a shared "Mesa Común"
  region (`GameView.vue`: `MercadoPanel.vue`'s recipe cards, `SuministrosPanel.vue`'s supply
  lots, and `BarraAcciones.vue`'s action buttons restyled as board-tile "Espacios de Acción" —
  same click-to-open-modal behavior, purely repositioned/restyled) versus each player's own,
  richer board (`MiTablero.vue`, reorganized into labeled zones: resources as icon tiles,
  0-6 pip Vitalidad/Acidez tracks matching the PA-pip visual language, an Incubadora/Cámara
  B/Módulo Analítico upgrade-slot row showing locked/unlocked state, and the hand/stations as
  `RecetaCard`s). The side column also carries `OrdenTurnoPanel.vue` — a vertical "Track de
  Orden de Turno" (numbered rows, a per-player-color meeple via `IconoPeon.vue`, `👑 Jefe` on
  row 1, the active player's row accented) built straight from the state view's `turno_orden`,
  mirroring the physical board component. `RecetaCard.vue` (superseding the earlier `RecetaDetalle.vue`) renders a recipe
  as a small card — a per-recipe bread icon (`IconoPan.vue`, one hand-authored flat SVG shape per
  recipe `id`, generic fallback for any future recipe without one yet), a flour/water requirement
  row (`IconoHarina.vue`, `IconoAgua.vue`), and a point-scale strip across the 1-20 track (same
  zone-banding math as `EstacionCard.vue`) labeling each zone's points directly — with the
  remaining text detail (`acidez_diana`, `req_tecnologico`, hydration%) in a tooltip
  (hover *and* tap-toggle via a `ⓘ` button, so it also works on touch, unlike a pure `:hover`
  tooltip). Used identically in the market, the hand (`MiTablero.vue`), and own stations
  (`EstacionCard.vue`) for one consistent recipe representation everywhere.

  The 12 action spaces are split into the three families `context/ACTIONS_REGISTRY.md` itself
  defines, each its own bordered zone with a header, a cost badge and an accent color:
  **Principales** (`B C D E F G simposio`, 1 PA, end your turn), **Gratuitas**
  (`A horas_extras pedido_urgencia`, 0 PA, chainable) and **Protocolos de Emergencia** (`H I`).
  Principales and Gratuitas sit side by side (`2fr 1fr`), Emergencia spans the full width below,
  and all three stack under 800px — the same breakpoint `.columnas` uses. The easy mistake this
  layout must not make: the emergency zone's badge says **1 PA, not 0 PA** — `H`/`I` are reactive
  by *availability* (they need active contamination), not by cost, and they charge a PA and end
  the turn exactly like the main actions. That zone is always rendered and merely greys out when
  there is no contamination (`disponibilidad.py` already returns them disabled with a `motivo`, so
  no backend involvement) — the layout never jumps and a player learns the rescue exists before
  needing it — and only lights up red when actually contaminated. The group table lives in
  `web/src/data/descripcionesAcciones.ts` as `GRUPOS_ACCION`, next to the `IdAccion` type it
  already owns, so `BarraAcciones.vue` keeps no parallel catalog; its pass-confirmation modal
  flattens that same table rather than a second list.

  Every player picks a color from a fixed 6-entry palette (`data/coloresJugador.ts`, mirroring
  `server/sessions.py:COLORES_DISPONIBLES`) in `LobbyView.vue` before creating/joining — needed
  for opponent identification (`TablerosOponentes.vue`'s color dot, `MiTablero.vue`'s accent
  border) and as groundwork for a deferred future feature (pawns on action spaces showing what
  each player did that round — not built yet; needs its own new backend state, since nothing
  today tracks which action space a player used on a given day). Joining live-checks
  `GET /games/{id}` (public, no token) to grey out already-taken colors as the room code is typed;
  the server's `color_ya_tomado`/`color_invalido` errors are the authoritative fallback for any
  race or stale check. `color` lives on `server/sessions.py`'s `Seat` (a session/lobby concept),
  not on the domain `Player` — `server/views.py:game_state_view` takes the whole `GameSession`
  (not just the `engine`) specifically so it can attach `color` (and the early-end vote tally
  below) to the view without threading extra parameters through every call site.

  **Mutual early-end vote and return-to-lobby**: any seated player can `POST
  /games/{id}/confirm-end` at any point while `EN_CURSO` (not gated by whose turn it is, like
  force-pass isn't either) — a one-way confirmation, no retracting a vote once cast. Once every
  seat has confirmed, the server calls the new `engine.forzar_fin_de_partida()`
  (`engine.py`) — sets `_partida_terminada`/`_fase` directly to the exact same terminal state a
  natural ending (deck exhaustion, 5th bake) produces, skipping the wait for the next
  `resolver_fase_III()`. This works cleanly because `calcular_ranking_final()` was already
  documented as callable "at any moment" (partial results otherwise) — so `RankingView.vue` needs
  zero special-casing for an early end vs. a natural one. From that ranking screen, only the host
  can `POST /games/{id}/return-to-lobby` (`GameSession.reiniciar_a_lobby`, same host-token check
  `iniciar_sala` already does) — resets `status`/`engine`/the vote set but **keeps `seats`**
  (names/tokens/colors), so the same room can start a fresh game immediately. Every other
  connected player picks this up on their own without any extra signal: `store.ts`'s
  `refrescarEstado()` already polls `GET /games/{id}/state`, and once the room resets that route
  starts returning `sala_no_disponible` (the engine is gone) — this specific error code is treated
  as "the room went back to lobby," not a generic failure, resetting `store.estado` (keeping
  `store.sesion`) the same way `volverALobby()` does for the host, which is what actually flips
  `App.vue` back to `LobbyView` (its `enPartida` computed already keys off `estado !== null`) and
  lets `LobbyView.vue`'s existing reconnect-resume logic pick the waiting room back up with no
  changes needed there. `server/persistence.py:VERSION_FORMATO` was bumped to 2 for this — a
  `GameSession`/`Seat` shape change (this and last session's `color` field) should invalidate old
  on-disk pickles per the module's own documented policy, rather than loading a stale object that
  crashes the first time new code touches a field it doesn't have.

  **Per-action sound effects**: every player move plays a distinct sound in *every* connected
  tab (including the actor's), so a player can tell by ear what someone else just did.
  `web/src/sonido.ts` (which already held the turn chime) now exposes a `tocarTonos(Tono[])`
  primitive plus a `Sonido` union — `{clase:'sintetizado'}` today, `{clase:'archivo', url}`
  implemented but unexercised, so one recipe can become an `.ogg` without touching the trigger.
  The recipes live in `web/src/data/sonidosAccion.ts`, keyed by
  `IdSonido = IdAccion | 'pasar' | 'deshacer'` so a missing action is a compile error (same trick
  as `GrupoAccion.id: IdAccion`). Everything is synthesized rather than shipped as files, for the
  same reason `Icono*.vue` hand-authors every SVG: this repo has no binary assets and no asset
  pipeline. Design is **timbre per family, pitch per action** — the three action zones share a
  waveform (Principales an ascending `triangle` pair, Gratuitas a short quiet high `sine` tick,
  Emergencia a descending low `sawtooth`), so the family is instantly readable and the specific
  action is learnable; Hornear breaks family with a three-note arpeggio. Toggle is
  `store.preferencias.sonido` (default **on**, unlike `alertaContaminacion`), driven by a 🔊/🔇
  button in `GameView.vue`'s header — deliberately not in `BarraAcciones.vue`, which unmounts on
  `v-if="esMiTurno"`, i.e. precisely when someone else is the one making noise. The turn chime
  now takes a delay argument and fires 0.35 s late so it doesn't collide with the action sound of
  the opponent who just ceded the turn.

  **Action broadcast (`AvisoAccion`) — why it is not a `GameEvent`**: the engine's event log only
  covers automatic, no-player-input changes, so of the 12 actions only F emitted anything
  (`HORNEADO`, via `resolver_horneado`). The other 11 produced no SSE frame at all — opponents'
  boards lagged behind by up to one 4 s backup poll. A new `EventoTipo` per action is not merely
  inelegant, it is **unsound**: the free actions (`A`, `horas_extras`, `pedido_urgencia`) happen
  inside the undo window, and `GameSession.restaurar_checkpoint` does `pickle.loads` of the whole
  engine, so `engine.eventos` would *shrink* on an undo and every client's `since` /
  `Last-Event-ID` pointer would sit past the end of the server's list — `engine.eventos[desde:]`
  returning `[]` forever. That is exactly the invariant `server/sessions.py`'s checkpoint comment
  already spelled out. So an action broadcast rides a **separate ephemeral channel over the same
  SSE connection**: `server/sessions.py:AvisoAccion` (a frozen dataclass next to `Seat`, kept out
  of `events.py` for the same reason `server/errors.py` is kept out of `exceptions.py`),
  fanned out by `GameSession.difundir_accion` over the same `suscriptores` queues (widened to
  `Queue[Union[GameEvent, AvisoAccion]]`), and written by `server/app.py:_formatear_sse_aviso` as
  `event: accion` + `data:` with **no `id:` line**. The missing `id:` is load-bearing: a browser
  only advances `Last-Event-ID` on frames that carry one, so an aviso cannot disturb the event
  log's resume pointer (an index into `engine.eventos`, which an aviso never enters) — and since
  it is never in the log, an undo cannot dangle it. A sound already played is not state: there is
  no backlog and nothing replays on reconnect, which is the wanted behaviour. Unlike
  `difundir_evento` it is **not** registered as the engine's `event_sink` — the engine doesn't
  know the HTTP action ids, so `app.py` calls it, in the four routes that represent a move
  (`/actions`, `/pass`, `/force-pass`, `/undo`), always *after* the mutation succeeded so a
  fail-fast rejection never makes a sound, and *before* `_avanzar_fase_si_corresponde` so the
  action's frame precedes the Fase III events it triggered. No `VERSION_FORMATO` bump: no
  persisted field changed (`suscriptores` was already excluded from `__getstate__`).
  `forzar_pase_por_inactividad` now returns the passed player's index instead of `None`, so the
  route doesn't recompute who was active. Client side, `store.ts`'s `iniciarEventSource` adds an
  `addEventListener('accion', …)` — named frames never reach the existing `onmessage`, so the
  event log is untouched — which plays the sound *and* calls `refrescarEstado()`; that refetch is
  the part that makes opponents' boards update in step with the sound instead of up to 4 s later.
  `crear_app()` now hangs its `RoomManager` on `app.state.salas`, purely so tests can reach the
  live `GameSession` and attach a fake subscriber. Tests: `tests/test_avisos_accion.py`, whose
  last case is the guardrail for the invariant above (a free action + an undo must leave
  `len(engine.eventos)` unchanged).

  **Show/hide panels (floating dock)**: the nine persistent modules `GameView.vue` renders —
  `MazoClimaPanel`, `MercadoPanel`, `BolsaHarinasPanel`, `MazoTendenciasPanel`, the "Espacios de
  Acción" panel, `MiTablero`, `OrdenTurnoPanel`, `TablerosOponentes`, `RegistroEventos` — can each
  be hidden and brought back from `DockPaneles.vue`, a strip of one icon chip per panel (lit =
  shown, dimmed = hidden) in the header rail, plus a hover ✕ on each panel via the generic
  `PanelOcultable.vue` wrapper. It lived as a floating right-edge column while the game view was a
  scrolling document; once the board became viewport-locked (see the layout section above) a
  floating rail was redundant chrome — there is no scrolling for it to survive — so the chips moved
  into the header and the 1220px gutter hack went away with them. The catalog (`IdPanel` union + `PANELES` table) lives in `web/src/data/panelesTablero.ts`,
  following the `GRUPOS_ACCION` precedent — the table sits next to the id type it indexes, so
  `GameView` keeps no parallel list. Hiding uses **`v-show`, not `v-if`**: the panels stay mounted
  and keep their local state (the Registro's scroll position, an open `ⓘ` recipe tooltip); only
  the *regions* (`.region-mesa`, `.region-medio`, `.region-tablero`, `.region-lateral`, and the
  wrappers around them) use `v-if`, collapsing when every panel inside them is hidden — in a
  viewport-locked board, hiding a module has to hand its space back to its neighbours rather than
  leave a gap. Three rules keep the feature from stranding anyone: the dock itself is never
  hideable, it carries a "Restaurar todos" (⟳), and **"Espacios de Acción" force-shows whenever
  `esMiTurno`** — hiding it mid-turn would leave a player unable to act while the
  `UMBRAL_INACTIVIDAD_SEGUNDOS` force-pass clock runs against them. That override is deliberately
  *temporary*: `visible()` returns true without touching `panelesOcultos`, so the panel hides
  again when the turn ends and the player's stated preference is never silently overwritten.
  State is `store.preferencias.panelesOcultos`, persisted in the existing `'fermentum-preferencias'`
  localStorage key and, like `sonido`/`alertaContaminacion`, deliberately **not** cleared by
  `cerrarSesion()`/`volverAVistaDeLobby()` — a layout preference outlives a session. Default is
  all nine visible, i.e. exactly the pre-existing screen for anyone who ignores the dock. Below
  800px (the same breakpoint `.columnas` uses) the dock collapses to a single ☰ button with a
  The chips are rendered only while the game is in progress, so the ranking screen never shows a
  row of dead controls. Deliberately *not* included: the mandatory modals (`InicioDiaModal`,
  `FermentationReportModal`, `ResultadoHorneadoModal`, `FinAnticipadoModal`) are not togglable —
  they exist so an automatic collapse can't go unseen — and hidden chips carry no "something
  changed" badge, since the state view is refetched wholesale and a per-panel diff would be a
  feature of its own.

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
Investigador Jefe, *announce* the day's Mercado de Tendencias card without applying it —
`Market.robar_tendencia`, emits `TENDENCIA_ANUNCIADA`, refill the recipe market back to
`NUM_RECIPE_SLOTS`=4 — `Market.protocolo_refresco`,
refill-only, no discard) → Phase II (round-robin, 2 PA per player, one action per
visit until no player has PA or an unused free action — see the turn-economy rule above) → Phase
III (every active `FermentationSlot` advances by
`temperatura_actual/5 + dado_inoculo + modificador_incubadora`; overshoot into
`zona_sobrefermentada` auto-bakes at 0 PA cost with a penalty; then all players lose 1 vitality,
2 if "Aletargamiento Invernal" is active; then the market's oldest visible recipe is discarded —
`Market.descartar_receta_mas_antigua`, emits `RECETA_DESCARTADA`; then this morning's announced
trend is finally applied to the three flour price tracks —
`Market.aplicar_tendencia_pendiente`, emits `TENDENCIA_MERCADO` — so it governs *tomorrow's*
prices). The game ends when the climate deck is exhausted or
any player successfully bakes their 5th recipe (collapsed bakes don't count), then scores per
`CORE_MECHANICS.md` §3.
