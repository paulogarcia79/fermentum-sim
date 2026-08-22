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
  `serialization.snapshot()` with the one redaction that matters — `Environment.mazo_clima` /
  `Market.mazo_recetas` (the hidden future decks) become counts, since everything else in this
  game is public information — plus `disponibilidad.acciones_disponibles` per player and
  `puntos_maestria_final`/`calcular_ranking_final` (both `@property`/methods, not dataclass
  fields, so `dataclasses.asdict` wouldn't include them — computed here instead of in the
  frontend, same reasoning as action availability: don't duplicate `CORE_MECHANICS.md` §3's
  scoring formula in TypeScript). `app.py` wires it all into routes and maps the `FermentumError` /
  `server/errors.py` `RoomError` hierarchies to HTTP status codes via one `isinstance` walk.
  Nothing in `models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`
  imports anything from `server/` — the dependency only goes one way.
- **`web/`** — the frontend (Vue 3 + TypeScript + Vite; see `web/README.md`). One reactive store
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

  **Board-game-style layout and per-player color**: the UI is split into a shared "Mesa Común"
  region (`GameView.vue`: `MercadoPanel.vue`'s recipe cards, `SuministrosPanel.vue`'s supply
  lots, and `BarraAcciones.vue`'s action buttons restyled as board-tile "Espacios de Acción" —
  same click-to-open-modal behavior, purely repositioned/restyled) versus each player's own,
  richer board (`MiTablero.vue`, reorganized into labeled zones: resources as icon tiles,
  0-6 pip Vitalidad/Acidez tracks matching the PA-pip visual language, an Incubadora/Cámara
  B/Módulo Analítico upgrade-slot row showing locked/unlocked state, and the hand/stations as
  `RecetaCard`s). `RecetaCard.vue` (superseding the earlier `RecetaDetalle.vue`) renders a recipe
  as a small card — a per-recipe bread icon (`IconoPan.vue`, one hand-authored flat SVG shape per
  recipe `id`, generic fallback for any future recipe without one yet), a flour/water requirement
  row (`IconoHarina.vue`, `IconoAgua.vue`), and a point-scale strip across the 1-20 track (same
  zone-banding math as `EstacionCard.vue`) labeling each zone's points directly — with the
  remaining text detail (`acidez_diana`, `req_tecnologico`, hydration%) in a tooltip
  (hover *and* tap-toggle via a `ⓘ` button, so it also works on touch, unlike a pure `:hover`
  tooltip). Used identically in the market, the hand (`MiTablero.vue`), and own stations
  (`EstacionCard.vue`) for one consistent recipe representation everywhere.

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
