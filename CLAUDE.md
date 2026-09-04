# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A simulation of **Fermentum**, a 1-4 player Eurogame about resource management and
engine-building (fermenting bread). It began as a single-process CLI and **is now an online
multiplayer web app**: the Python rules engine was kept as-is and a thin HTTP layer + a Vue 3
frontend were added on top, rather than porting the rules to another stack. That port is
finished, and **the CLI has been removed** — `main.py`, `GameEngine.ejecutar_dia_laboratorio`
and `fase_II_accion` are gone, so `server/` is the only way to play and the turn state machine
is the only way to drive the engine. The rules engine
(`models.py`/`engine.py`/`actions.py`/`bootstrap.py`/`events.py`/`serialization.py`/
`disponibilidad.py`) still has zero external dependencies — everything is stdlib Python 3.12 —
and still imports nothing from `server/`; the dependency goes one way. `server/` (Starlette +
uvicorn) is now a **required** dependency rather than an optional group, since without it there
is no application. `pytest`+`httpx` are dev-only. `web/` (Vue 3 + TypeScript + Vite, see `web/README.md`)
is a fully separate npm project with its own dependencies — nothing in the Python side depends on
it or on Node being installed.

The game's rules are written down in **two** places, and both are normative — see
"Every rules change MUST update the rulebooks" below before changing any of them.
`context/*.md` is the implementation spec and the source of truth for behavior:

- `context/ARCHITECTURE.md` — coding standards the code must follow (see below)
- `context/CORE_MECHANICS.md` — the Day/Phase loop, fermentation math, endgame/scoring
- `context/ACTIONS_REGISTRY.md` — every player action, its PA/resource cost, and effects
- `context/PLAYER_STATE.md` — the `Player` data schema and per-player setup/validation rules
- `context/CLIMATE_LOGIC.md` — the climate deck and the Phase III fermentation-advance formula
- `context/RECIPE_DATABASE.md` — the recipe catalog (hydration, zones, scoring)

When implementing or changing game logic, check the relevant `context/*.md` file first — it
defines the exact numbers, thresholds, and edge cases the code must match.

### Every rules change MUST update the rulebooks, in the same commit

There are **two** documentation surfaces, and they serve different readers:

- `context/*.md` — the **spec**, written for whoever implements the code.
- **`RULEBOOK.md` + `RULEBOOK.html`** — the **player-facing reglamento**, in Spanish. These are
  the two halves of one document, **hand-maintained in parallel with no generator script**, so a
  change to one is only half the job. `RULEBOOK.html` is a standalone styled page (its own CSS,
  fonts and table markup); `RULEBOOK.md` is the plain-text twin.

**A commit that changes a rule and does not touch all four files is incomplete.** "Rule" here
means anything a player at the table would notice: a phase step, an action's cost or effect, a
setup value, a scoring term, a tiebreaker, a card's printed numbers, or a capability being
removed. Pure refactors and server/web plumbing do not count.

This is written down because it has already gone wrong twice, silently. `3ff8fc9` (Variedad de
Recetas) added a **7th scoring term and a new first tiebreaker** and never touched the rulebooks,
so for two commits the reglamento told players there were 6 terms and that Vitalidad broke ties.
The Ingresos de Panadería commit repeated it. Nothing caught either one, because no test read
these files and `context/*.md` being correct made the gap invisible from the code side.

**`tests/test_reglamento_al_dia.py` now enforces the mechanical half of this** — every number in
the rulebooks that can be derived from the code, plus `.md`-vs-`.html` agreement. It cannot judge
prose, so the reasoning, the examples and the cross-references are still on you.

Things that are easy to miss when doing this, learned the hard way:
- **Prose, not just tables.** Old rules survive in sentences long after the numbers are fixed —
  a currency's list of sources, the one-line phase summary in §4, a cross-reference telling
  players to use an action that no longer does that thing.
- **Section renumbering.** Inserting a `### 9.4` means the old 9.4 and 9.5 must shift, and the
  `.html` may not even have the same subsections as the `.md`.
- **Verify, don't eyeball.** Diff the 12 recipe rows cell-by-cell against `RECIPE_CATALOG` in
  *both* files, grep for the superseded rule's old wording, and for the HTML check tag nesting
  plus every table's `<th>`-vs-`<td>` column count (adding a table column is easy to do in the
  header and forget in the rows).

`Fermentum_ GDDv0.0.2.pdf` in the repo root is **legacy and NOT authoritative**. It is the
historical design doc the GDD v0.0.2 overhaul came from, it is a binary nobody can edit, and it
already disagrees with the code on many points. Never treat it as the source of truth, and never
"fix" the code to match it. `context/*.md` is the spec; `RULEBOOK.md`/`.html` is the reglamento.

## Commands

Core simulation has zero dependencies; dev (`pytest`, `httpx`) and `server` (`starlette`,
`uvicorn`) is a required dependency; only `dev` (`pytest`, `httpx`) is an optional group. Use the project venv at
`.venv/` (create with `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"` if it
doesn't exist yet — `starlette`/`uvicorn` come in as ordinary dependencies).

```bash
# Run the legacy integration suite (plain script, not pytest — asserts via print + sys.exit code)
python3 test_actions_suite.py

# Run the pytest suite (tests/ only — pytest is scoped there via testpaths so it never
# collects test_actions_suite.py, whose top-level sys.exit() would abort a pytest session)
.venv/bin/pytest

# Run the headless HTTP backend (single worker only — see server/app.py's concurrency note)
.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1

# Run the web client on http://localhost:3010 (separate terminal, needs the backend above already
# running) — see web/README.md. The port is pinned in vite.config.ts (port 3010 + strictPort, so a
# clash fails loudly instead of drifting to 3011) rather than using Vite's shared 5173 default.
# vite.config.ts proxies /games/* to :8000 so no CORS setup is needed in dev.
cd web && npm install && npm run dev

# Type-check + production build the web client
cd web && npm run build
```

`tests/test_golden_game.py` is a characterization test: it plays a fully deterministic game
(seeded global RNG, two scripted "bot" players from `tests/_bot.py`) through several full
Fase I/II/III cycles via `tests/_bot.py:jugar_dia`, and diffs the final state against
`tests/golden/day4_2p_seed1234.json`. Its purpose is to give behavior-preserving refactors of
`engine.py` a regression baseline to check against, since none existed before — and it has since
earned that twice over: it is what proved the removal of the blocking-callback path neutral, by
passing **unregenerated** after the migration. If a deliberate rules change
alters this golden game's outcome, regenerate the snapshot rather than hand-editing it.

`test_actions_suite.py` is a hand-rolled suite (`check()` / `xraises()` helpers) that exercises
every `ActionManager` action's happy path and failure path (96/96 passing). It's a standalone
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

`tests/test_investigacion_a_ciegas.py` covers the Acción G deck draw (`origen="mazo"`): the flat
price and that it does not vary with the grade drawn, that it takes `mazo_recetas[0]` and leaves
the four exposed cards alone, the fail-fast matrix with the deck **and** the discard asserted
untouched (including the ordering case where checking the deck before the Monedas would shuffle
everyone's discard for a doomed attempt), the on-demand reshuffle, both-empty raising
`RecipeDeckEmptyError`, card conservation across the whole system, the illegal parameter
combinations, the six availability rungs, the wire shapes through `resolver_comando`, and two
end-to-end HTTP cases (a successful blind draw with its registro sentence, and the 409).

`tests/test_reglamento_al_dia.py` is the guardrail for the rule below ("Every rules change MUST
update the rulebooks"): it parses `RULEBOOK.md` and `RULEBOOK.html` into normalized tables and
diffs them against the code — all 12 recipes cell by cell (grade, acquisition cost, water,
**all four zones**, points, coins), the 8 Patrocinio cards including the Datos column, the three
price tables, the climate/trend/recipe decks, technology costs, the rent table, the count and
order of scoring terms vs `Player.desglose_maestria`, and scalars like `VITALIDAD_INICIAL` and
`HARINA_RECULTIVO_MANUAL`. It also asserts the two files **agree with each other** (they are
hand-maintained in parallel, so drift between them is as likely as drift from the code) and that
the HTML is well-formed with every table's `<th>` count matching its `<td>` counts.
Two deliberate design points. It extracts whole *tables* rather than loose rows, because grade
names like "Básica" head rows in four different tables and matching on first-cell alone is
ambiguous by construction. And it compares every name **exactly**, with no tolerances: an earlier
version forgave connector words because the code said "Fallo Refrigeración" while the rulebooks
said "Fallo **de** Refrigeración", but a tolerance in the test is just a divergence nobody has to
fix — the names were unified instead (the rulebooks were right; the code's was the ungrammatical
one) and the tolerance went with them. **Prose is deliberately not checked.** There was briefly a
`FRASES_PROHIBIDAS` list of superseded wordings; it was removed *after measuring it* — injecting
the same contradiction two ways, it caught the exact sentence someone had enumerated and let the
equivalent rephrasing through. It was a portrait of four past migrations with no predictive value
for the next one, that nobody would prune and that could only grow. A rules test should not
accumulate history; if something like it is proposed again, bring the measurement. Keeping the
document free of self-contradiction is a human review, which is what the rule below is for.
When a deliberate rules change makes this suite fail, the fix is to update all four surfaces,
never to loosen the assertion. Verified by mutation: changing a payout in `models.py`, updating
only the `.md`, adding a scoring term, changing Acción H's cost, diverging a climate-card name,
and adding an HTML column header without the matching cells are each caught.

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
  anymore) and endgame/scoring (`resolver_horneado`, `calcular_ranking_final`).

  **One way to drive Phase II**, the turn state machine (used by `server/app.py`):
  `iniciar_dia()` then poll `jugador_activo` / call `terminar_turno_actual()` or
  `pasar_turno(player)` per visit, then `resolver_fase_III()`. See the `Fase` enum and
  `GameEngine.turno_nonce`. It runs exactly one day and stops — it does **not** auto-chain into
  the next day's Phase I, so a client can show the Phase III report before state moves under it
  (`FermentationReportModal.vue`).

  There used to be a second, blocking path — `ejecutar_dia_laboratorio(callback)` →
  `fase_I_ambiente` → `fase_II_accion(callback)` → `resolver_fase_III()` — which existed to give
  the CLI its per-day pause point. It was **removed with the CLI**; `server/` never used it, and
  two ways to drive one loop are two ways to drift. Worth knowing how that removal was made safe,
  because the same trick applies next time: the two were exactly equivalent (both went through
  `_preparar_fase_II` / `_avanzar_a_siguiente_elegible`), so the three tests that drove the
  callback path were migrated onto the state machine **first**, and
  `tests/test_golden_game.py` then passed against the **unmodified** snapshot. Passing without
  regenerating is the proof; regenerating and eyeballing the diff would not have been.

  The callback loop now lives once, in `tests/_bot.py:jugar_dia`, and **its nonce check is
  load-bearing, not defensive**: free actions (Alimentar, Descarte, Horas Extras, Pedido de
  Urgencia) don't end a visit and `heuristic_turn` returns as soon as one succeeds, so a driver
  that always closes would rob a visit and one that never closes would spin forever. Comparing
  `turno_nonce` across the callback is what tells the two apart — and getting it wrong fails
  *only* the golden game, since the other two consumers pass turn themselves.

  **Turn-economy rule (deliberate, diverges from `ACTIONS_REGISTRY.md`'s literal CLI-original
  behavior)**: Acción A (Alimentar), Acción E (Pliegues), Horas Extras and Pedido de Urgencia do
  **not** end a player's turn/visit by themselves — only a PA-costing action or an explicit
  `pasar_turno()` does. A player who has
  spent both PA elsewhere stays eligible for further visits solely to use an unused free action
  (`GameEngine._jugador_elegible`: `puntos_accion > 0 or not
  accion_alimentar_usada or not horas_extras_usadas or datos_investigacion >= 1 or ("E" not in
  acciones_pa_usadas_hoy and monedas >= min(PRECIO_PLIEGUES.values())) or ("descarte" not in
  acciones_pa_usadas_hoy and (monedas >= min(PRECIO_DESCARTE.values()) or reserva_agua >=
  min(COSTE_REFRESCO_AGUA.values())))` — note the Descarte clause checks **both** resources,
  since its two directions are priced in different ones). An explicit pass is a full forfeiture of
  the rest of the day, including unused free actions — anything that ends a player's turn **must**
  call `engine.pasar_turno(player)`, never assign `player.puntos_accion = 0` directly, or that
  player will be revisited forever (see `tests/_bot.py:heuristic_turn`'s final fallback for the
  required pattern).
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
  (`engine.PRECIO_AGUA`). The Bolsa trades in a whole bag (10 tokens, 100%) or **half a bag**
  (5 tokens, 50%) — the four wire operations `comprar`/`comprar_media`/`vender`/`vender_media`,
  mapped to (direction, quantity) by the single `actions.OPERACIONES_HARINA` table that all three
  of the method's loops (validate / simulate balances / apply) read, so a new size can't make them
  drift. A half bag costs ⌈compra/2⌉ and pays ⌊venta/2⌋ (derived inside
  `Market.precio_compra_harina`/`precio_venta_harina`, never a second price table): rounding in
  opposite directions is what stops the half bag being an arbitrage — at odd prices it is strictly
  worse per token, so it is liquidity, not a discount. A sale that rounds to 0 Monedas (Blanca at
  position 1) is legal, and the visor moves one space for a half bag exactly as for a whole one,
  since a transaction is a market signal regardless of size. Tests:
  `tests/test_mercado_media_bolsa.py` walks all 30 price cells.
  Meanwhile Acción F now pays out Monedas per zone on top of the existing
  points/Datos logic (`Recipe.monedas_*` per zone, flat `+2` Monedas Bono de Sabor); setup
  (`bootstrap.create_game`) now deals from an 8-card `PATROCINIO_CATALOG` instead of a hardcoded
  4-slot `player_index` table, driving both Día 1 turn order (`GameEngine`'s new `orden_inicial`
  param) and starting resources; the lab-upgrade cap (Acción D) is now per-technology, not a
  single "one upgrade per game" total, with a 4th tech (Criopreservación) added; and endgame
  scoring gained a "Conversión de riqueza" term. Recipe zone/point/Monedas values were rebalanced
  across the board — see `context/RECIPE_DATABASE.md`.

  **Three recipe grades, defined by the flour a card prints.** `Recipe.harina_base:
  TipoHarina` became `harinas: Tuple[Tuple[TipoHarina, int], ...]` — the flours the card prints,
  as (type, pct) pairs, always summing to 100%. `Grado` gained `INTERMEDIA`, and the grade is no
  longer authored: `models._grado_desde_harinas` derives it (Blanca 100 → Básica, one *special*
  flour 100 → Avanzada, two distinct types 50/50 → Intermedia), and `Recipe.__post_init__` raises
  when the `grado` field disagrees. Three pieces make that sound:
  - **Only two payment shapes are legal, and that is not arbitrary** — the Bolsa de Harinas
    vends a whole bag (10 tokens) and a half bag (5, `comprar_media`, `⌈p/2⌉`) and nothing else,
    so a 90/10 split would need a per-token buy primitive that doesn't exist. The cost ladder
    then falls out of `PRECIOS_HARINA` with no new table: Básica 2–6, Intermedia 3–7…5–9,
    Avanzada 4–8/6–10 Monedas.
  - **`grado` stays a *field*, not a `@property`.** This is the load-bearing implementation
    choice: `serialization.snapshot` is `dataclasses.asdict`, which serializes fields and never
    properties, so a computed `grado` would silently vanish from the golden snapshot and from
    every client payload — and `Recipe` is nested in four places (`carpeta_proyectos`,
    `estaciones_fermentacion[].recipe`, `market.recetas_visibles`,
    `archivo_horneado_exitoso[].recipe`), so injecting it in `views.py` is not one line.
    Validating in `__post_init__` buys the same "cannot lie" guarantee for free, and because
    `RECIPE_CATALOG` is a module-level constant a mislabelled card fails at `import models`.
  - **The tech gate left `grado`** — and then left the game entirely. Acción B used to read
    `grado == AVANZADA and not modulo_analitico`; with the grade derived, that would have
    auto-gated *any* future special-flour card, so it moved to the per-card `req_tecnologico`.
    One commit later that field was **deleted** and no recipe is technology-gated at all — see
    "Recipes cost Monedas" below. The history is worth knowing: `req_tecnologico` was dead weight,
    then briefly load-bearing, then gone.

  `requisito_harina` is a derived `Dict[str, int]` keyed exactly like `Player.reserva_harina`, so
  `ActionManager._require_harinas` (which replaced `_require_harina_tipo`) and Acción B's spend are
  each one loop over matching shapes rather than a branch per grade; the rejection names *every*
  missing flour, since with an Intermedia "you lack flour" doesn't say which half to go buy. The
  catalog grew to 12 (4/4/4): four Básicas because `bootstrap.create_game` cycles `i % len` and
  dealt player 4 a copy of player 1's card with only three, and the extra cards also thicken a deck
  feeding `NUM_RECIPE_SLOTS = 4`. `puntos_optimos` is banded per grade with no overlap (9–12 /
  13–16 / 17–20) while Monedas and zone widths deliberately are **not**, so "cheap points vs. cash
  cow" survives as a design axis inside a grade. Panettone prints Blanca, and Blanca-100 can only
  be a Básica, so it became an Intermedia (20 → 16 pts) rather than being re-floured into a rye
  bread; Pumpernickel is the new 20-point apex, pure rye by definition. `disponibilidad.py` needs
  no change (its `"B"` clause never checked flour); `VERSION_FORMATO` went to 9 because old pickles
  hold `Recipe`s with no `harinas`.

  One trap this change sprang, worth knowing about before adding a grade or a card:
  `Market.crear_inicial` built its deck as `get_recetas_avanzadas() + get_recetas_basicas()`, so
  the moment Pizza/Brioche/Panettone stopped being Avanzadas the **entire Intermedia tier fell out
  of the market** — unreachable, with every test still green. The deck is now built by
  `build_recipe_deck()` and shuffled as **one single deck**, all three grades mixed: a Básica can
  surface in the market exactly like an Avanzada. Scarcity is real but it comes from
  `COPIAS_POR_GRADO` (2 copies of an Avanzada against 4 of a Básica), **not from a stratum** — the
  deck is unevenly populated, not ordered. That matters beyond setup: the Investigación a ciegas
  buys the top card unseen, and a stratified deck would have made that a knowable early discount
  and a late rip-off instead of a bet. (An earlier revision did stack `avanzadas + intermedias`
  over the Básicas; that ordering is gone, and any prose still claiming it is stale.) A grade
  that isn't named in `crear_inicial` is invisible, so `tests/test_recetas_grado.py` asserts the
  deck contains every catalog card and all three grades.

  **The deck is 36 physical cards, not 12.** `RULEBOOK.md` always described a printed deck with
  copies while the sim dealt one card per protocol; that divergence is now closed.
  `models.COPIAS_POR_GRADO` (4 per Básica / 3 per Intermedia / 2 per Avanzada = 16+12+8) plus
  `expandir_copias` / `build_recipe_deck` mirror the `ClimateCard.cantidad` + `build_climate_deck`
  pair exactly — expand, don't shuffle, assert the total. Copies are **per grade, not per card**,
  unlike `ClimateCard.cantidad`: the grade is already derived from the flours, so a per-card table
  would be 12 derivable numbers free to contradict the rulebook. Copies are the same frozen
  instance repeated, so a market slot can legitimately show two Pan Grahams at once. Scarcity is
  the point: 8 Avanzada cards in 36 makes them rare as well as expensive.
  `bootstrap.create_game` then removes **one copy** per player of the Básica it dealt (`list.remove`,
  equality on a frozen dataclass) — one copy, not the protocol, or a 4-player game would empty the
  reserve stratum. Tests: `tests/test_recetas_grado.py`.

  **Recipes cost Monedas, and nothing gates them.** Acción G was the only free thing in the game
  (1 PA and no resource), so the recipe market was a queue rather than an economy; meanwhile 7 of
  the 12 cards declared `req_tecnologico`, putting the interesting half of the catalogue behind an
  unrelated purchase. Those two traded places. `engine.PRECIO_RECETA = {Básica: 1, Intermedia: 2,
  Avanzada: 3}` is charged by Acción G **additively** on top of its 1 PA — indexed by grade, like
  `PRECIO_PLIEGUES` and `COPIAS_POR_GRADO`, so no new `Recipe` field and no way for the price to
  disagree with the card. `req_tecnologico` is **deleted from `Recipe`**, not emptied: the rule is
  structural, with nowhere to write a tech gate on a recipe. Tech gates elsewhere (Estación 03 ←
  Cámara B, the Incubadora modifier, Cámara B's Pliegues variants, Criopreservación) are untouched.

  **The ordering in `accion_G_investigar_protocolo` is load-bearing**: `Market.tomar_receta`
  *removes* the card, so the price is read by peeking `recetas_visibles[i]` and validated
  **before** taking. Charging afterwards would mean every attempt by a broke player destroys a
  market card for everyone — a fail-fast violation that leaves no trace. `disponibilidad.py`'s
  `"G"` clause greys the space out against the cheapest **visible** recipe, not the global minimum:
  what a player can pay depends on the four cards actually on the table, and an all-Intermedia/
  Avanzada market is an ordinary draw from a deck that mixes the grades. (Since «Investigación a
  ciegas», that clause has a second, deck-side floor — see below.)

  **The Módulo Analítico had to be rebuilt**, because deleting the gate deleted its job. Its only
  other effect was `DATOS_BAKE_CENTRO_EXACTO_BONUS`, and the arithmetic made it a trap: with a
  handful of bakes in a game it needed ~3 perfectly-centred ones just to refund 3 Datos, while
  Criopreservación cost 2 for outright decay immunity. It now does three things and costs **4**
  (joint top with Cámara B): `AMPLIACION_OPTIMA_MODULO` widens the Zona Óptima by one square on
  each side, `DATOS_BAKE_MODULO_BONUS` pays 2 Datos on any óptima bake, and the centre bonus
  stacks to 3. Three things about the widening are easy to get wrong:
  - **It moves the collapse threshold.** The widening eats the sobrefermentada band from below, so
    `_avanzar_masas_jugador`'s auto-collapse check must pass the amplification. Forgetting it there
    is the one failure that makes the upgrade useless exactly where it matters, and every other
    zone call site would still look right. All four (`_calcular_puntos_zona`,
    `_calcular_monedas_zona`, `_calcular_datos_horneado`, the collapse trigger) read one helper,
    `GameEngine.ampliacion_zona_optima`.
  - **It is live, not sealed.** Unlike `modificador_incubadora`, it is recomputed from the owner's
    technologies at resolution time, so installing the Módulo rescues a mass already fermenting.
    Zones therefore became **per-player**, and `Recipe.zonas_efectivas(ampliacion)` is the only
    place the arithmetic lives. `es_centro_exacto` deliberately takes **no** amplification: a
    symmetric widening cannot move the centre, since `(a-n + b+n)//2 == (a+b)//2`.
  - **`HorneadoRecord` had to seal it anyway.** `zona_resultado` is a `@property` recomputed from
    the recipe's zones, so without the new `ampliacion_aplicada` field a Módulo bake that scored as
    óptima would be archived as "baja" forever. The record already seals every other outcome; this
    joins them.

  Client side, `server/views.py` injects `zonas_efectivas` onto the recipes a player **owns**
  (carpeta, stations, both archives) — market cards keep their printed zones, since nobody owns
  them — and `web/src/data/zonasReceta.ts` is a thin accessor with a printed-zone fallback. The
  collapse threshold is a rule the player reads to judge risk, so it is computed server-side for
  the same reason as `vitalidad_prevista`. `web/src/data/preciosReceta.ts` mirrors `PRECIO_RECETA`
  for `ModalG`'s labels and its disabled Confirmar, following the `preciosHarina.ts` precedent —
  a price change on the server needs that file edited too. `VERSION_FORMATO` went to 10 (two
  persisted shapes changed at once). Tests: `tests/test_precio_recetas.py`,
  `tests/test_ampliacion_optima.py`.

  **Four fermentation zones, and the position-0 hole they close.** The track went from three zones
  to four: `zona_crecimiento` is new at the bottom, and the other three were renamed to the
  rulebook's vocabulary — `zona_baja → zona_pre_fermento`, `zona_sobrefermentada → zona_colapso`,
  with their payouts (`puntos_pre_fermento`, `monedas_colapso`, …). The rename follows `22d7d1d`'s
  precedent and also settles the old `sobre`/`colapso` split, where one zone already had two names.

  **The bug this closed is worth knowing.** A mass is created at `posicion_track = 0`, but every
  card's low zone started at `1`, so position 0 belonged to no declared zone and fell through
  `_calcular_puntos_zona`'s final `return recipe.puntos_baja`. Acción B and Acción F are separate
  action spaces and a player has 2 PA, so you could **start a recipe and bake it the same day
  having fermented nothing** — Panettone paid 8 PM + 13 Monedas for it. Crecimiento is now the
  fallback, and it pays nothing; `tests/test_ampliacion_optima.py` pins the Panettone case by name.
  The general lesson the code now encodes: `esta_en_crecimiento` is deliberately **the default
  case, not a closed range**, so an unclassified position can only ever fall into the zone that
  pays zero.

  Three further things about the fourth zone:
  - **You cannot bake in crecimiento at all.** `accion_F_hornear` raises and `disponibilidad.py`
    greys the space out ("La masa aún está creciendo"). Blocking rather than paying zero matters
    because a 0-point bake would still land in `archivo_horneado_exitoso`, whose fifth entry ends
    the game for everyone — a leading player could otherwise slam the door with five raw bakes.
    Simposio Técnico remains the way to abandon a mass, and pays 1 Dato for it.
  - **Crecimiento has no payout fields.** You can never bake there, so `puntos_crecimiento` /
    `monedas_crecimiento` would be 24 numbers nothing reads — the `req_tecnologico` shape again.
    `TablaRendimiento.vue` renders that row as `—` with "no se hornea", which teaches the rule
    better than three zeros would.
  - **Crecimiento is never widened by the Módulo Analítico.** The widening still eats pre-fermento
    from above and colapso from below, so the "can I bake yet?" line stays put even if a player
    installs the Módulo mid-fermentation. `Recipe.__post_init__` gained a third validation for the
    consequence: pre-fermento must be at least `ANCHO_MINIMO_PRE_FERMENTO` wide
    (= `AMPLIACION_OPTIMA_MODULO + 1`, derived so it stays right if the Módulo ever widens by 2),
    or the widening would collapse it into an inverted range. `AMPLIACION_OPTIMA_MODULO` therefore
    **moved from `engine.py` to `models.py`** — `__post_init__` needs it and models cannot import
    engine.

  Zone boundaries are authored per card (half of the old low zone as the rule of thumb, with three
  deliberate deviations: Pan de Molde shorter as the forgiving entry card, Panettone and
  Pumpernickel longer as the most committing). Client side, `zonasReceta.ts` returns four ranges
  and exposes `estaEnCrecimiento` mirroring the server predicate; the fourth band reuses
  `PistaMedida`'s already-defined-but-unused `neutra` tone — its tone names stay generic because it
  also draws Vitalidad, Acidez and flour prices. `VERSION_FORMATO` went to 11.
  Tests: `tests/test_ampliacion_optima.py` (exhaustiveness over every position 0–20 on all 12
  cards, at both amplifications).

  **Acción E (Pliegues) — the second Monedas sink, and the only 0-PA action that occupies an
  action space.** E used to cost 1 PA for a flat +1 track space, i.e. a whole turn for one space;
  nobody took it. It is now **0 PA, priced in Monedas**, lives in the Gratuitas group, and does
  **not** end the visit (`ACCIONES_QUE_TERMINAN_TURNO["E"] = False`). Three pieces make that
  sound rather than merely generous:
  - **An escalating ladder, not a flat price** — `engine.PRECIO_PLIEGUES = {1: 1, 2: 3, 3: 6}`
    buys 1-3 total track spaces (marginal cost 1, 2, 3, so volume is never a discount). The wire
    param is a single `reparto: {slot_index: espacios}` map and the price is
    `PRECIO_PLIEGUES[sum(reparto.values())]`, so validate / price / apply all read one number —
    the same reason `OPERACIONES_HARINA` exists for the Bolsa.
  - **The once-per-day action space survives the loss of the PA cost.** This is the load-bearing
    part: Monedas are *renewable* (Acción C sells flour for cash every day), so "the price limits
    it" is false — without the space cap a rich player would be handed visits until their purse
    emptied. `Player.consumir_punto_accion` was split so `ocupar_espacio_accion(id)` can mark the
    space without spending PA, and `_jugador_elegible` gained a matching clause. No new persisted
    field, hence **no `VERSION_FORMATO` bump** — that was the deciding argument against a
    dedicated `tecnica_pliegues_usada` flag.
  - **Cámara B distributes, it does not multiply.** It no longer unlocks a separate `doble_masa`
    option; it lets the purchased spaces land on two masses instead of one. Its
    `recuperar_vitalidad` variant is a flat `PRECIO_PLIEGUES_VITALIDAD = 6`, priced at the top
    rung deliberately: metabolic decay is -1 Vitalidad/day, so a cheap daily +1 would buy
    permanent immunity to contamination (-3 PM, Acción B locked) for pocket change.

  Overshoot is **legal on purpose**: buying 3 spaces can push a mass past `zona_optima` into
  `zona_colapso`, which Fase III auto-bakes in collapse. That risk is the brake on the top
  rung, so `posicion_track` is never clamped here; `ModalE.vue` surfaces it with `PistaMedida`'s
  dashed projected bracket plus a warning instead of blocking the purchase. E emits no
  `GameEvent`, so being inside the undo window is safe (`engine.eventos` stays byte-identical
  across an undo — the invariant `AvisoAccion` exists to protect). `disponibilidad.py`'s E clause
  was rewritten for Monedas and, in the same edit, fixed a pre-existing bug that greyed E out with
  zero masses even though `recuperar_vitalidad` is legal with none. Prices are mirrored for the
  modal in `web/src/data/preciosPliegues.ts`, following the `preciosHarina.ts` precedent. Tests:
  `tests/test_pliegues_monedas.py`.

  **Pedido de Urgencia — both parcels are fixed, and the water one wasn't.** The action took
  `agua_tokens_urgencia: int` with no upper bound, forwarded verbatim by `server/commands.py` from
  a bare `<input type="number" min="1">`. Flour had been pinned at `HARINA_PEDIDO_URGENCIA = 50`
  for an explicit arbitrage reason; water was left open, and a recipe needs 10–17 tokens while a
  100% market lot costs 7–14 Monedas, so **1 Dato bought a whole game's water**. Water can't be
  resold, so there was no Monedas loop like flour's — the only brake was the −1 PM per 3 unused
  tokens at scoring, a ridiculous price for skipping the Suministro Hídrico all game. Now
  `actions.AGUA_PEDIDO_URGENCIA = 6` (30%), and the player picks *which* resource, never how much.
  Three things carry weight:
  - **The wire lost the quantity entirely.** Params are `{recurso: "harina", harina: "Centeno"}`
    or `{recurso: "agua"}`, and the signature is `(player, recurso, harina=None)` — the old
    `harina_urgencia` XOR `agua_tokens_urgencia > 0` pair is gone. Validating an int against the
    constant would have left a number on the wire that the rules say nobody chooses; a discriminator
    makes the illegal state unrepresentable instead.
  - **6 equals `AGUA_TOKENS_POR_LOTE[30]` and is deliberately not derived from it** — the
    `DATOS_SIMPOSIO`-vs-`PRECIO_RENTA` precedent again. It is chosen because the 30% lot costs 2–6
    Monedas, the same order as the flour half-bag's 1–3, so the Dato buys comparable value either
    way, and because two Pedidos then cover roughly one recipe's water, mirroring "two Pedidos make
    a bag". Resizing the market's lots must not silently rebalance a rescue action.
  - **Still no `GameEvent`, still no `VERSION_FORMATO` bump.** It is a 0-PA action inside the undo
    window, so emitting anything would shrink `engine.eventos` on a restore — the invariant
    `AvisoAccion` exists to protect, pinned here by `test_el_pedido_no_emite_eventos`. No persisted
    field changed shape, and the golden bot never calls the Pedido, so the snapshot passed
    unregenerated.

  `web/src/data/pedidoUrgencia.ts` mirrors both quantities for the modal and for
  `descripcionesAcciones.ts` (which now interpolates them instead of repeating "50" in prose),
  following the `preciosReceta.ts` precedent. Tests: `tests/test_pedido_urgencia.py`, plus
  `test_reglamento_al_dia.py::test_cantidad_del_pedido_de_urgencia` extended to demand the water
  figure in the canonical `N (P%)` notation in both rulebooks — verified by mutation.

  **Variedad de Recetas — the 7th scoring term, and the breakdown it forced.** Endgame scoring
  rewarded *how well* you bake and was indifferent to *what* you bake, so with duplicate copies of
  every card in the deck (`COPIAS_POR_GRADO`) the optimal line was to find one recipe whose flour
  you already stock and repeat it until the 5th bake ends the game. `Player.puntos_variedad` now
  pays `n*(n+1)//2` on `recetas_distintas_horneadas` = distinct `Recipe.id` in
  `archivo_horneado_exitoso` (0/1/3/6/10/15). Four things carry weight:
  - **Successes only, and that is an incentive argument, not a taxonomy one.** A collapse is free
    to provoke — start a mass, let Fase III auto-bake it on overshoot — so counting `archivo_colapsos`
    would let a player harvest the bonus without baking anything well.
  - **Triangular, not flat.** Marginal increments are 1,2,3,4,5, so a single repeat forfeits the
    largest increment on the board rather than an average one. The ceiling is genuinely 5 because
    the 5th *successful* bake ends the game.
  - **`Player.desglose_maestria` is now the single source of the formula.** `puntos_maestria_final`
    is `sum(desglose_maestria.values())`, and its **insertion order is the display order** for
    every consumer. This was forced, not cosmetic: the CLI had recomputed all six terms by hand,
    and that duplicate had already drifted — it never printed Conversión de Riqueza, so its
    breakdown did not sum to its own TOTAL. That duplication is a large part of why the CLI was
    eventually deleted rather than maintained. `tests/test_variedad_recetas.py` pins the key list.
  - **Variedad is the *first* tiebreaker**, ahead of Vitalidad (`calcular_ranking_final`'s sort
    tuple, `CORE_MECHANICS.md` §Desempate). `RankingView.vue` therefore orders
    its columns PM → Tipos → Vitalidad → Datos, so a tie reads left to right.

  Everything new is a `@property`, so `dataclasses.asdict` skips it: the golden snapshot is
  untouched, nothing persisted changed, and **no `VERSION_FORMATO` bump**. `server/views.py` ships
  `desglose_maestria` + `recetas_distintas_horneadas` from its existing per-player loop; the
  triangular formula is **not** mirrored in TypeScript (unlike `preciosHarina.ts` et al.) because
  the points arrive inside the breakdown and the only client-side arithmetic is "the next new kind
  is worth `n+1`". `MiTablero.vue`'s archive header shows the live count and PM;
  `RankingView.vue` renders the breakdown as one block per player under the table. The same commit
  added the two terms `CORE_MECHANICS.md` §3 had never documented — it listed 5 while the code
  applied 6, silently omitting the contamination penalty — so the doc list now matches
  `desglose_maestria` key for key. Tests: `tests/test_variedad_recetas.py`.

  **Desarrollo Tecnológico — the same curve, pointed at the engine instead of the repertoire.**
  Scoring rewarded *what you bake* and was indifferent to the *engine you build*: the four
  technologies paid only in-game, so `Player.puntos_desarrollo_tecnologico` now pays
  `n*(n+1)//2` on `Technologies.cantidad_instaladas` (0/1/3/6/10), slotted 5th in
  `desglose_maestria` right behind Variedad so the two breadth terms read as a pair. The intent
  is **symmetry, not a rebalance** — and it is accepted with open eyes that techs now pay a
  **third** time on top of their two in-game benefits (the Módulo widens the óptima, Cripo dodges
  the −3, Cámara B opens Estación 03). Four things carry weight:
  - **One derivation, two printed tables.** Both terms are the same curve, so the arithmetic moved
    out to a module-level `models.puntos_triangulares` that `puntos_variedad` also calls. That is
    not tidiness: `tests/test_reglamento_al_dia.py` now diffs **both** rulebook curves against
    that one function, so "same curve as Variedad" is structurally true rather than a claim two
    tables are free to contradict. Variedad's own table had never been checked — a gap in that
    file's stated contract, not a policy — and it came in with this one.
  - **The curve is a prefix of Variedad's, which nearly made the guardrail vacuous.**
    `0 / +1 / +3 / +6 / +10 / +15` literally contains `0 / +1 / +3 / +6 / +10`, so a substring
    check over §11.2 would pass with the tech row **deleted**. The `.html` check is therefore
    scoped to the row whose *name* cell matches the term. (The two documents are structurally
    different here: `.md` prints real tables, `.html` writes the curve as prose inside one
    `# / Componente / Cálculo` table whose literal index cells renumber on insert.) Verified by
    mutation: deleting the `.html` row fails exactly one test.
  - **Unweighted count, deliberately.** Criopreservación (2 Datos) scores like Cámara B (4),
    matching Variedad, where a Básica and an Avanzada are one class each. A Datos-weighted bracket
    table was rejected twice over: nothing on a card derives it, and it would drift silently the
    day `COSTOS_TECNOLOGIA` is rebalanced. Consequence, accepted and documented: cheap-first is
    strictly correct — a *sequencing* nudge, not a dominant line, since the top increment still
    needs all four.
  - **It is monotonic, and that is the asymmetry to not "fix".** The Simposio pops a record and
    Variedad drops a tier; nothing uninstalls a technology, because `Technologies.activar` has no
    inverse. Reversibility would need a whole new action with its own availability rules, modal,
    sound and rulebook section. The **tiebreaker chain is untouched** for a related reason: tech
    count correlates with the Datos rung already in it.

  No new server field — `tecnologias` already ships as four booleans, so `MiTablero.vue` derives
  the count itself (unlike `recetas_distintas_horneadas`, which had to be sent) and the points
  arrive inside `desglose_maestria`; `RankingView.vue` needed **zero** changes, since it iterates
  the breakdown. Everything added is a `@property`, so the golden snapshot passes
  **unregenerated** and there is no `VERSION_FORMATO` bump. The same commit fixed pre-existing
  drift in `web/src/data/tecnologias.ts`, which had the Módulo at 3 Datos (server says 4) and
  still advertised the deleted Avanzada gate — `ModalD.vue` renders that field, so it had been
  quoting the wrong price. Tests: `tests/test_desarrollo_tecnologico.py`.

  **Ingresos de Panadería — the archive became an income stream, and the Simposio became its
  only exit.** Baking paid once (`monedas_optima`, 16–28, the biggest cash event in the game) and
  the recipe never produced again: `archivo_horneado_exitoso` fed scoring and the endgame trigger
  but not the economy. Now every successful bake pays `engine.PRECIO_RENTA[grado]` (Básica 1 /
  Intermedia 2 / Avanzada 3) **every Fase III**, which turns the moment of baking into an
  investment decision instead of a pure scoring act. Five things carry the weight:
  - **It is not new money, and that is the whole design.** The 36 zone payouts were cut by
    `renta × 3` so the total is preserved and only the *timing* changes. The 3 is an
    **amortisation horizon common to every grade** — any bake recovers its old payout on the 3rd
    día regardless of card — so the temporal pressure is identical everywhere and choosing a
    recipe stays a question of points and flour, not payback speed. That horizon is **not a
    runtime constant**: it is the derivation the catalog numbers were authored with, documented in
    `PRECIO_RENTA`'s docstring. `tests/test_renta_panaderia.py::test_amortizacion_al_tercer_dia`
    pins it for all three grades, which is what stops a future rebalance breaking it silently.
  - **The cut had to hit all three zones, and the two alternatives are both broken.** Cutting only
    `monedas_optima` inverts Miche and Hogaza Centeno (a raw Pre-fermento sale would outpay a
    perfectly-timed bake); cutting Óptima+Pre-fermento but sparing `monedas_colapso` inverts all 12
    the other way (failing would outpay selling early). Only the uniform per-card shift keeps every
    card's internal order. Accepted side effect, documented rather than fixed: the **grade ladder
    inverts in the lump** (Panettone pays 7 in Pre-fermento vs Pan de Molde's 9) because the high
    grade cedes more to the stream — it is restored in *total* value by día 3, which is the point.
  - **Derive, never cache.** `GameEngine._cobrar_renta_panaderia` sums the live archive. There is
    no `Player.renta_diaria` field and no rate sealed into `HorneadoRecord`, and that is exactly
    what makes "if the record leaves the archive, its income leaves with it" true for free — the
    Simposio `pop()`s a record and the next night simply pays less, with no code coordinating it.
    A cached field would be precisely the bug this shape avoids; `test_se_deriva_del_archivo_vivo`
    is the guardrail. It also means a bake made in Fase II **collects that same night**, so no
    per-record bake date is needed. Colapsos pay nothing (`archivo_colapsos`): provoking one is
    free, so paying it would hand out the stream without baking anything well — the same incentive
    argument that already governs Variedad de Recetas.
  - **The Simposio Técnico is now the only way out of the archive.** It no longer discards from the
    carpeta or a station; it costs 1 PA **plus a successful bake**, and pays `DATOS_SIMPOSIO[grado]`
    (1/2/3). That is a **separate constant from `PRECIO_RENTA` despite identical values** —
    sharing one table would couple two unrelated rules so that rebalancing the rent silently moved
    what the Simposio pays. Sacrificing a record costs its base points, its rent, a Variedad tier
    and a step of the X/5 trigger all at once, and none of that needs coordinating code because
    `puntos_horneados` / `puntos_variedad` / `recetas_distintas_horneadas` are all `@property` over
    that one list. No Datos yield makes this *efficient*: it is an emergency lever, and in practice
    you always burn your cheapest bake. Emergent consequence documented, not fixed: a player at 4/5
    can sacrifice one to drop to 3/5 and delay the endgame — ruinously expensive, hence legitimate;
    a trigger already fired never reverts (`_partida_terminada` is latched).
  - **Two pre-existing bugs this change forced into the open.** Dropping the station origin removed
    the only way to abandon a mass, so starting a recipe is now an irreversible commitment (nothing
    ever gets stuck — Fase III advances every mass nightly — you just can no longer dodge
    `penalizacion_colapso`); `accion_F_hornear`'s Crecimiento message used to point at the Simposio
    and had to be rewritten. And with the cheap Datos source gone, **`vitalidad` had to start at 2**
    (`models.VITALIDAD_INICIAL`): Acción A repays +1/day against a -1 decay, so a player who feeds
    daily *orbits their starting value*, and from 1 the «Aletargamiento Invernal» card (-2, two
    copies in 30) forced contamination no matter how well you played — the shuffle, not a decision.
    From 2 it lands on 1. `PatrocinioCard` also gained a `datos` field (0–2, inverse to its
    Monedas) so the board is not Dato-less until the first Óptima bake, and Acción H dropped from
    50% to 30% flour so the buyable rescue stays reachable — note the units: `reserva_harina` is in
    **percent** (100 = one bag = 10 tokens), so the old 50 was half a bag, not five.

  `server/views.py` ships `renta_diaria` from its existing per-player loop (server-side for the
  same reason as `vitalidad_prevista`); `web/src/data/datosSimposio.ts` mirrors `DATOS_SIMPOSIO`
  for `ModalSimposio.vue`'s labels following the `preciosReceta.ts` precedent — the **rent is not
  mirrored**, it arrives precomputed. `ModalSimposio.vue` was rewritten to show what each sacrifice
  *costs* (points, rent, the X/5 step, and the Variedad tier — the last derived client-side since
  it is only lost when the record is the last copy of its recipe). `VERSION_FORMATO` went to 12
  (`PatrocinioCard` changed shape and old pickles hold the pre-cut economy). The golden snapshot
  was regenerated; its diff is exactly 36×3 payouts + 2 vitalidades + 1 starting Dato, nothing
  else. Tests: `tests/test_renta_panaderia.py`.

  **Simposio Técnico — la ponencia, a second rung priced in Monedas instead of a bake.** The
  Simposio had one payment and it was ruinous (the bake's 9–20 PM, its rent for the rest of the
  game, a Variedad tier and a step of the X/5 trigger), so nobody pulled the lever; meanwhile
  Ingresos de Panadería piles up Monedas late with nothing to buy but flour, and Datos — the only
  currency that buys technologies — arrive one at a time. `accion_simposio_tecnico` now takes a
  `modo`: `sacrificar` is unchanged, `ponencia` buys 1–3 Datos at
  `engine.PRECIO_DATO_SIMPOSIO` (5) Monedas each and leaves the archive alone. Six things carry
  weight:
  - **5 is the Conversión de Riqueza rate, and deliberately not derived from it.** A bought Dato
    costs exactly the PM those Monedas would have scored (`Player.desglose_maestria`'s
    `monedas // 5`), so it is a trade at par rather than free value. It is a separate constant for
    the `DATOS_SIMPOSIO`-vs-`PRECIO_RENTA` and `AGUA_PEDIDO_URGENCIA`-vs-`AGUA_TOKENS_POR_LOTE[30]`
    reason: rebalancing endgame scoring must not silently reprice an action.
  - **5 also has to beat 3**, the most a Pedido de Urgencia's half bag resells for (Centeno at
    position 5 sells 7, the half rounds down). At 4 or less, Monedas → Dato → media bolsa →
    Monedas would have been a money printer built from two actions that already existed.
  - **`MAX_DATOS_PONENCIA = 3` equals `DATOS_SIMPOSIO[AVANZADA]`.** No purse ever outpays a
    sacrificed Avanzada in one visit, so the sacrifice keeps a role its unchanged table alone
    would not give it; and since Jefatura pays 1 Dato for 1 PA and no Monedas, buying a single
    Dato is strictly worse than claiming it. The ponencia only pays at 2–3 at once.
  - **Both modes are gated on a non-empty archive, and that gate is load-bearing three times
    over.** It is what stops Patrocinio Monedas being a Día-1 Datos tap, what keeps
    `PLAYER_STATE.md`'s "no Datos on the table until the first bake" true, and what let
    `disponibilidad.py` go **completely untouched** — its clause (archive + PA + free space)
    already covers both. One mode per visit needs no rule either: the space is once per day.
  - **Comerciante does not discount it** (`DESCUENTO_COMERCIANTE` is Acción C only), stated in
    all four rule surfaces because the tech's own callout is where a reader would look.
  - **The wire is discriminated, and `modo` has no default.** `{modo, indice}` |
    `{modo, datos}`, the Pedido de Urgencia `recurso` precedent; `commands.py` type-checks only
    the selected mode's param and forwards the other raw, so `ActionManager` stays the only rules
    authority. A default would have let the old `(player, 0)` calls pass `0` as a mode and hide
    the migration, so every caller had to be updated.

  Neither mode emits a `GameEvent`, no persisted field changed shape (**no `VERSION_FORMATO`
  bump**), and `tests/_bot.py` never visits the Simposio, so the golden snapshot passes
  **unregenerated**. `datosSimposio.ts` mirrors both constants (the rent is still not mirrored —
  it arrives precomputed); `ModalSimposio.vue` gained a radio toggle and a 1–3 stepper with
  `ModalG.vue`'s "Cuesta X · tienes Y" disabled-Confirmar treatment. Tests:
  `tests/test_simposio_ponencia.py`, plus
  `test_reglamento_al_dia.py::test_la_ponencia_cuesta_monedas` (verified by mutation on both
  documents; the price appears in the section twice, so mutating only one occurrence passes —
  the check is honest, the first mutation attempt was not).

  **Turno de Mostrador — the floor of the board, and the only PA action that is not a space.**
  A player could hold PA and have no useful move — empty carpeta, mass still in Crecimiento,
  0 Monedas, 0 Datos, Jefatura already claimed by someone else — and the only exit was
  `pasar_turno`, which also forfeits the day's free actions. Leftover PA was lost silently:
  `resolver_fase_III` never reads `puntos_accion`, and the endgame «Desperdicio» penalty counts
  only flour and water. `accion_turno_mostrador` is 1 PA for `MONEDAS_MOSTRADOR` (= 1) Moneda.
  Four things carry weight:
  - **It occupies no action space, which is the whole point.** A player has 2 PA (3 with Horas
    Extras) and the hollow can occur once per PA, so a once-per-day space would fix half the
    problem. `Player.consumir_punto_accion` gained an `ocupa_espacio: bool = True` parameter —
    the exact inverse of the existing `ocupar_espacio_accion` (space without PA, for E and
    Descarte) — and `"mostrador"` never enters `acciones_pa_usadas_hoy`. It is therefore the
    mirror image of Reclamar Jefatura in the space rule: that one is exhausted for the **whole
    table** at once, this one is never exhausted at all. No new persisted field, so **no
    `VERSION_FORMATO` bump**.
  - **It is deliberately not gated on "nothing better to do".** That condition is not
    observable: `disponibilidad.py` reports Acción C enabled whenever the player has PA and
    hasn't used the space, even with nothing to trade. A guard would switch the floor off almost
    always, precisely when it is needed. It self-limits by being **weak, not by being closed** —
    hence the one-rung ladder (`agregar("mostrador", tiene_pa, "Sin PA")`), the only PA action
    whose availability check has no second clause.
  - **Monedas, and exactly 1.** In Datos it would loop with Horas Extras (1 Dato → +1 PA →
    1 Dato) and undercut Jefatura, which already pays 1 Dato for 1 PA *plus* turn order; in
    Vitalidad it would duplicate Acción A, which pays +1 for 10% flour at 0 PA. One Moneda is
    exactly what the retired 1-PA Acción E was worth — the action nobody ever took — which is
    the intended bar: every real action dominates it, so it is never a line of play.
  - **It emits no `GameEvent`**, like every other action but F, so `engine.eventos` is unchanged
    across it; being a PA action it closes the visit and the undo window (`es_gratuita` is
    derived from `ACCIONES_QUE_TERMINAN_TURNO`, so registering `"mostrador": True` was enough).

  This is the one change here that **regenerated the golden snapshot deliberately**:
  `tests/_bot.py:heuristic_turn` gained `_intentar_mostrador` as its last attempt before
  `pasar_turno`, so the bot stops forfeiting whole days. The diff is explainable — the recipe
  deck is the old one minus its top card (one extra Acción G), plus one extra market purchase
  and the Monedas — and `pasar_turno` is now reached only at 0 PA. Client side the three
  exhaustive `Record`s (`descripcionesAcciones.ts`, `sonidosAccion.ts`, `RegistroEventos.vue`'s
  icon map) each gained an entry, the sound is `principal(349.23)` — Fa4, the lowest note of the
  family, an octave under Jefatura's Fa5 and at the opposite end for the same reason — and
  `BarraAcciones.vue` reuses `ModalConfirmacion` (like Jefatura).

  **The pawn is shown anyway, and an `∞` badge is what makes it honest.** A space that records
  no visit reads as one nobody uses, so the Mostrador does get a marker — but the marker's usual
  meaning on this board is "closed for you today", which here would be a lie. `ESPACIOS_REPETIBLES`
  (next to the existing `ESPACIOS_GRATIS_UNA_VEZ_POR_DIA`) drives a small `∞` in the tile's free
  left corner, a matching tooltip line, and a different pawn `title` ("ya pasó por aquí hoy — el
  espacio sigue abierto"). Two things carry weight:
  - **The pawn is derived from `registro_acciones`, not from a new field.** `acciones_pa_usadas_hoy`
    must never contain `"mostrador"` — that is the invariant making the action repeatable — so the
    client filters the movement log it already receives whole in every snapshot, by `accion`,
    `environment.dia_actual` and `!deshecha`. No backend change, no new field, **no
    `VERSION_FORMATO` bump**. The `deshecha` clause is correct rather than load-bearing: a
    Mostrador is a PA action, so it closes the visit and the undo window and its entry can never be
    struck out. Day rollover clears the pawns with no code doing it, because the filter is on the
    day.
  - **One pawn per *visit*, deliberately not per player.** Going twice leaves two dots of your
    colour, so the corner reads as a count of what you spent there. This is the only pawn list in
    the game that can repeat a player — every other space's daily limit makes it impossible — and
    it forced two small things: the `v-for` key moved from `p.nombre` to the index (duplicate keys
    otherwise), and `.marcadores-jugador` gained `flex-wrap` with a `max-width` so the worst case
    (4 players × 3 PA = 12 dots) wraps to a second row inside the tile instead of overflowing it or
    reaching the `∞`. Measured in the browser: 12 dots occupy 67×16 px in a 111×49 px tile. The
    pawn `title` numbers the visit ("visita 2 de 2 hoy"), which is what answers the question a
    second dot of your own colour raises. `visitasMostrador` is a `computed` rather than a plain
    call because the movement log grows all game and the template would otherwise re-filter it once
    per pawn.
  - **Only the Mostrador gets the badge, and that is the rule to apply next time.** The `∞` marks a
    space that **contradicts its own group's header**: Principales says "un espacio distinto por
    visita". Pedido de Urgencia is equally unlimited but sits under Gratuitas, whose header already
    says "puedes encadenarlas", so there is nothing to correct and it keeps showing no marker.

  Tests: `tests/test_mostrador.py`, plus
  `test_reglamento_al_dia.py::test_el_mostrador_paga_monedas` (verified by mutation on both
  documents).

  **Investigación a ciegas — la Acción G aprende a robar del mazo, y es la primera acción que
  toca información oculta.** G only knew how to buy one of the 4 exposed cards, so a player with
  PA, coins and a market holding nothing they could use had no way to spend the space — and
  `disponibilidad.py` greyed it out precisely then. `origen="mazo"` takes the **top card of
  `mazo_recetas`** (index 0, the one tomorrow's refresh would reveal) for a flat
  `engine.PRECIO_RECETA_MAZO = 2` Monedas, unseen. Six things carry weight:
  - **Flat, and deliberately not derived.** It equals `PRECIO_RECETA[INTERMEDIA]` but is its own
    constant, the `DATOS_SIMPOSIO`-vs-`PRECIO_RENTA` and `AGUA_PEDIDO_URGENCIA`-vs-
    `AGUA_TOKENS_POR_LOTE[30]` precedent: repricing the visible table must not silently reprice
    the gamble. The card is paid for before it is known, so there is no grade to index. The 2 is
    chosen against the deck's own mix — (16·1 + 12·2 + 8·3)/36 ≈ 1.78 — so the blind card is a
    slightly **expensive** bet, not a discount, and it is the only route to an Avanzada for 2.
    This is also why the deck being **one uniformly shuffled deck** is load-bearing here and not
    just a setup detail: a stratified deck would make the same price a knowable early bargain and
    a late rip-off.
  - **Two irreversible steps, not one, and that reorders the fail-fast checks.** The existing
    comment only had to protect `tomar_receta` removing a card. The deck arm adds a second hazard:
    `robar_receta_del_mazo` may `random.shuffle` the discard into a new deck. So Monedas are
    checked **before** the deck is even consulted — otherwise a broke player's failed attempt
    would shuffle everyone's deck. `test_sin_monedas_no_se_rebaraja_el_descarte` is the guardrail,
    and it is the test that would catch the obvious "check the deck first" ordering.
  - **The reshuffle is one rule in one place.** `Market._rebarajar_descarte_si_agotado` was
    extracted verbatim from `protocolo_refresco`'s inline block when the second consumer appeared,
    keeping the RNG call sequence identical on the refresh path — which is what let the golden
    snapshot pass **unregenerated**. `actions.py` still imports no `random`; the shuffle lives in
    `engine`, pinned by `test_actions_no_importa_random`.
  - **`ACCIONES_QUE_REVELAN["G"]` stays False, and the audit comment it invalidated was
    rewritten.** That comment claimed no action touches `mazo_recetas`; now one does. The flag
    stays False for a structural reason, not an oversight: G is turn-ending, so `app.py` runs
    `limpiar_checkpoint()` for it and the draw is outside the undo window by construction. Marking
    it True would be actively broken — the revealing re-take runs *after* that clear, resurrecting
    a checkpoint for a closed visit. A module-level assert in `commands.py` now makes that
    combination impossible to introduce, so the contract only ever applies to **free** actions.
  - **The wire discriminator has a default, unlike Simposio's `modo`.** `origen: str = "mercado"`
    on both sides. The Simposio forced every caller to name its mode because a positional `0`
    would otherwise have silently become a mode; here nothing changes meaning, so an old call
    still says what it said — which is exactly what kept `tests/_bot.py` and the golden game
    untouched. Cross combinations are `InvalidActionError` rather than interpreted: the blind card
    is not chosen, so `indice_mercado` alongside `origen="mazo"` is an illegal state, not a hint.
  - **`RecipeDeckEmptyError` is new rather than a reused `MarketSlotEmptyError`.** The slot error's
    message promises the card comes back at the next Protocolo de Refresco. An exhausted
    mazo-plus-descarte does not come back with time — only a carpeta swap or a Simposio sacrifice
    refills the discard — so reusing it would have shipped a message that lies. `app.py` maps it
    to 409 `mazo_recetas_agotado`.

  `disponibilidad.py`'s `"G"` clause now has two floors (cheapest visible **or** 2 for the deck)
  and a six-rung motivo ladder, because "no visible recipes" and "can't afford the blind one" are
  different situations and the tooltip is the only place a player learns which. Client side,
  `MercadoPanel.vue` draws the deck as a face-down card beside the four slots (it must look
  buyable, not like a counter), `ModalG.vue` gains a "Del mercado / Del mazo" radio whose
  **initial** value flips to mazo when the table holds nothing affordable — a `ref`, not a
  `computed`, or it would fight the player's toggle — and `preciosReceta.ts` mirrors the new
  constant. The log line is its own sentence ("Investigó a ciegas … (robado del mazo)"): the card
  is public the moment it lands in the carpeta, but *where it came from* survives nowhere else.
  Everything added on the engine side is a method or a `@property`, so no persisted shape changed
  and there is **no `VERSION_FORMATO` bump**. Tests: `tests/test_investigacion_a_ciegas.py`, plus
  `test_reglamento_al_dia.py::test_la_investigacion_a_ciegas_cuesta_monedas` (verified by mutation
  on both documents, deleting the paragraph and changing the figure).
- **`events.py`** — `GameEvent`/`EventoTipo`/`EventSink`: a structured log of automatic,
  no-player-input state changes (chief-researcher assignment, climate reveal, market refresh,
  end-of-day discard of the market's oldest recipe, mass advance, structural collapse, every
  bake — manual or auto-collapse, both go through `resolver_horneado` — metabolic decay,
  contamination onset, game over with its reason).
  `GameEngine` always keeps the full log (`engine.eventos`) and optionally forwards each event,
  at emission time, to an injected `event_sink` — this is what `server/sessions.py`'s
  `GameSession.difundir_evento` plugs into (Milestone 5) to push events to connected SSE clients
  live, with no polling needed on the happy path. The Phase III report is built entirely from
  `engine.eventos[since_index:]` (`FermentationReportModal.vue`) — there's no before/after
  snapshot-diffing anywhere in the
  codebase anymore; an automatic event (like a structural collapse costing a player several
  points with no action on their part) is always something the engine explicitly said happened,
  not something a caller has to infer from a state diff. When adding new automatic engine
  behavior, emit an event for it at the point of mutation rather than expecting a caller to
  reconstruct it from before/after state.

- **`bootstrap.py`** — `create_game(nombres: List[str]) -> GameEngine`: the actual game-construction
  logic (shuffled basic-recipe assignment, Patrocinio deal, Day-1 turn order). The **only**
  constructor of a `GameEngine` outside tests that deliberately want a degenerate board; used by
  `server/sessions.py` and by every test that needs a real game. It was extracted here so the
  server would not have to import the CLI, and it outlived the CLI unchanged — which was the
  point: building a game never depended on who displayed it.
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

  **Acción D greys out against the cheapest *pending* technology.** D used to check only "space
  unused today" and PA, so the tile stayed lit with 0 Datos and the only feedback was the server's
  rejection after Confirmar — and the pass-advice modal, which lists every still-`habilitada`
  action, nagged that you could still install something when nothing was buyable. It now needs
  `datos_investigacion >= min(COSTOS_TECNOLOGIA[t] for t in player.tecnologias.pendientes)`,
  joining E, G and Descarte as a space that prices itself. Three things carry weight:
  - **Pending, not the catalog** — the same reason G reads the four *visible* recipes rather than
    the global minimum. Criopreservación is the catalog's cheapest at 2 Datos, so a player who
    already owns it faces a 3-Dato floor and 2 Datos must grey the space out. A `min` over
    `COSTOS_TECNOLOGIA.values()` looks identical and is wrong exactly there;
    `test_D_mide_contra_la_mejora_pendiente_mas_barata_no_contra_el_catalogo` is the guardrail,
    verified by mutation.
  - **Two motivos, because they are different situations.** "Sin Datos para ninguna mejora
    pendiente" is actionable, "Todas las mejoras ya están instaladas" is permanent, and the
    tooltip is the only place a player learns which. The ladder keeps `"Sin PA"` ahead of both,
    like G's.
  - **`Technologies.pendientes` iterates `TecnologiaID`**, unlike the older `cantidad_instaladas`
    which enumerates the five attributes by hand, so a sixth technology joins the check by
    declaring its enum member and its price. Being a `@property` it is invisible to
    `dataclasses.asdict`: golden snapshot untouched, no `VERSION_FORMATO` bump. `tests/_bot.py`
    never reads `acciones_disponibles`, so the golden game is unaffected either way.

  `ModalD.vue` mirrors it from `web/src/data/tecnologias.ts` by **disabling Confirmar only**
  (the `ModalG.vue` `puedePagar` precedent, with the same "Cuesta X · tienes Y" line): unaffordable
  pending upgrades stay selectable so their descriptions can still be read and saved for, and the
  initial selection is the first pending upgrade you can actually afford. This is **not a rules
  change** — `accion_D_implementar_mejora` is untouched and the action's legality is identical —
  so the rulebooks and `context/*.md` are deliberately not edited.

  **`insumos_receta` — the one thing this module counts per *card*, and why it is not a `motivo`.**
  A playtester held two recipes, forgot the one bought the day before, and spent a Dato on a
  Pedido de Urgencia for something already affordable. The carpeta is `MiTablero.vue`'s third
  sub-zone and at 1366×768 it wraps below `.region-tablero`'s internal scroll fold, so the fix is
  not layout: the reminder moved to where the eyes are when choosing, the «Iniciar Receta» tile,
  which shows one `IconoPan` per held recipe — full colour with a `--cobre` ring when its supplies
  are complete, greyscale when not. Four things carry weight:
  - **It is the deliberate exception to this module's own docstring.** Everything else here is a
    cheap per-*player* check feeding one `habilitada`/`motivo` pair; `insumos_receta` does the full
    flour-and-water arithmetic per carpeta card. That is a different question — "can I press the
    button?" versus "does it stretch to *this* card?" — and folding it into Acción B's `motivo`
    would give one string for N recipes, useless exactly when you hold two and only one is viable.
  - **Supplies only, never player-level blockers.** PA, free station, inóculo die and contamination
    stay in `acciones_disponibles`, so `completos: true` does **not** promise Confirmar will
    succeed; it promises that what's missing, if anything, is not the pantry. Verified live: a
    contaminated player sees the tile lit *and* the tooltip's `⚠ Cultivo contaminado`, each
    blocker stated once.
  - **It forced the water rule into one place, and that closed a real drift.**
    `GameEngine.agua_requerida` now owns the Alta Humedad −1, read by both `accion_B_iniciar_receta`
    (which charges it) and this function (which shows it). `ModalB.vue` had been computing the
    water check in TypeScript off the printed `tokens_agua`, so on a humid day it drew a ✗ against
    a cost the server would have accepted. The modal now renders the shipped rows and does no
    arithmetic; `test_lo_que_se_ensena_es_lo_que_la_accion_B_cobra` pins the two to one number.
  - **Every row ships, not just the shortfalls.** ModalB draws the full ✓/✗ list, so returning
    only failures would force it to rebuild the rest. Quantities stay in domain units (flour in
    percent, water in tokens); `web/src/data/insumosReceta.ts` formats them and holds no rules.

  `server/views.py` injects it **only** on `carpeta_proyectos`, beside `zonas_efectivas` — market
  cards belong to nobody and station/archive recipes are already paid for. Everything added is
  view-layer, so the golden snapshot is untouched and there is **no `VERSION_FORMATO` bump**. Not
  a rules change, so the rulebooks and `context/*.md` are deliberately not edited. One trap the
  tests sprang: `iniciar_dia()` draws a climate card, so any test asserting a water figure must
  pin `efecto_pasivo_activo` or it passes and fails by shuffle. Tests:
  `tests/test_insumos_receta.py`.
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
  - **`Tooltip.vue` — the second body-level overlay, for the same reason and a different one.**
    Three components each hand-rolled the same ~35 lines of `position: absolute` tooltip CSS
    (`BarraAcciones`'s action spaces, `RecetaCard`'s compact card, `MiTablero`'s `.mejora-slot`),
    and all three were **unreadable**: every `.region` is a scroll container (`overflow-y: auto`,
    and `.region-acciones` additionally `max-height: 40vh`), so a box opening *upward* from its
    anchor was clipped at the region's edge. Note the difference from the modal case — there the
    teleport fixes *flattening* by `:deep(.panel)`, here it fixes **clipping**, which no
    `z-index` can touch. One wrapper component now owns all three: the anchor goes in the default
    slot (so hover is read off the whole block — a `disabled` button fires no mouse events of its
    own) and the box in `#contenido`. It is `position: fixed`, teleported, and placed from
    `getBoundingClientRect()`: above the anchor when it fits, flipped below when it doesn't, and
    clamped horizontally against the viewport. Chosen over the Popover API + CSS anchor
    positioning, which needs no JS but has no Firefox support for the anchor half.
    Four details are load-bearing. The box renders at `opacity: 0` until measured, so there is no
    one-frame jump from the origin. It **hides on any scroll or resize**, because a `fixed` box
    goes stale the instant its anchor moves and the regions scroll independently. The `fijado`
    prop drives the `ⓘ` tap-toggle (touch has no hover) and pairs with a `cerrar` emit, since a
    body-level box must also close on outside-pointerdown and Escape — hunting for the same tiny
    `ⓘ` is not a dismissal path. And `pointer-events` is `none` unless pinned, so a hover box
    never swallows a click meant for the board underneath. **No component should write its own
    `.tooltip` rule again**; the native `title` attribute was also dropped from anything that
    opens one, since the browser's own box was rendering on top of it.
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
  has one component per player action, reading
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
  — an "inverse action" would be wrong exactly at the boundaries. It is safe because every action
  that can occur **inside the window** is deterministic over public information: the window holds
  only free actions, and none of them touches a hidden deck (`actions.py` imports no `random` —
  the one shuffle it can reach, the blind draw's, lives in `engine.Market`). Note the claim had to
  be narrowed once: Acción G in `origen="mazo"` does draw face-down, but it is a PA action, so it
  closes the visit and can never be inside the window. Inside that window only free actions occur,
  **none of which emit events** — so `engine.eventos` is byte-identical across
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

  **Endgame celebration — the only sound that differs per player, and the tie it exposed.**
  The ranking screen was a bare table: nothing marked the winner and nothing sounded. Now the
  winner's tab rains bread confetti and hears a fanfare while everyone else hears a short
  descending close. Four things carry weight:
  - **It cannot ride the `accion` SSE channel.** Every sound in the game until now was a
    server broadcast with one identical payload, so "a different sound per player" has no home
    there. Detection is client-side in `store.ts:aplicarEstado()`, where each tab already knows
    its own seat — gated on `fase_actual === 'terminada'`, **not** `partida_terminada` (that
    latches mid-last-day) and **not** a non-empty `ranking` (it ships in every snapshot,
    mid-game included, with partial results). `reproducirFanfarriaVictoria` /
    `reproducirCierreDerrota` live in `sonido.ts` next to the turn chime rather than in
    `sonidosAccion.ts`, whose exhaustive `Record<IdSonido, Sonido>` is keyed by wire action ids
    these two are not. The fanfare is deliberately longer, higher and chorded so it cannot be
    mistaken for Acción F's arpeggio, the game's other reward sound; the loser close is `sine`,
    since descending `sawtooth` is the Emergencia timbre and would read as "something failed".
  - **Confetti replays on reload, sound does not.** The confetti is mounted by `RankingView.vue`
    on `soyGanador`, so it is part of the screen; the sounds are one-shot on the live transition,
    guarded by a new non-reactive `finDePartidaSonado` seeded on reconnect. That seeding
    generalized `sembrarTurnoSinSonido(idx)` into `sembrarEstadoSinSonido(estado)`, which now
    seeds both guards from the first snapshot — the same "a reconnect is not a live transition"
    rule the turn chime already followed. The flag is reset in **both** `cerrarSesion()` and
    `volverAVistaDeLobby()`, like the other three.
  - **A perfect tie now shares the puesto, and that is a rules change.** `calcular_ranking_final`
    sorted with four criteria and let Python's stable `sorted` break what remained by seat order,
    then `enumerate`d distinct positions — so a genuine tie was decided by registration order,
    which no rulebook documented because it was not a rule, and which the client could not even
    detect (the view ships only `{posicion, player_idx}`). Tied players now share a position,
    competition-style (1, 1, 3). This is what lets the client keep asking `posicion === 1` and
    get co-winners right with no extra data on the wire. All four rule surfaces gained the new
    item; no test pinned position numbers, so nothing loosened. Tests:
    `tests/test_ranking_empate.py`.
  - **CSS keyframes, not canvas.** `ConfetiPanes.vue` is the first `@keyframes` in the repo: ~40
    teleported `IconoPan` pieces with randomized delay, drift, spin and size, one pass of ~7 s,
    then it unmounts itself. The global `prefers-reduced-motion` rule in `App.vue` clamps
    `animation-duration`, so it degrades for free — a rAF loop would sit outside that net and
    need its own `matchMedia` check. It cycles only the **8** recipe ids with distinct silhouettes;
    the other four hit `IconoPan`'s generic ellipse. `pointer-events: none` and `z-index: 30`
    keep it under the modal scale, so a last-night `FermentationReportModal` still sits on top.
    Nothing persisted changed: no `VERSION_FORMATO` bump, and `types.ts` was untouched.

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

  **Registro de acciones — the log the aviso channel could not be.** `AvisoAccion` fixed the
  *sound* and the board lag, but a sound is not a record: 13 of the 14 actions still left no trace
  (only F, via its `HORNEADO`), so `RegistroEventos.vue` showed the weather and the market and
  almost nothing any player actually did. The log is now `GameSession.registro_acciones`, a list of
  `EntradaRegistro` (`seq`, `accion`, `jugador_idx`, `dia`, `pos_eventos`, `mensaje`, `deshecha`).
  Five things carry weight:
  - **It lives on the session, not in `engine.eventos`, for the reason `AvisoAccion` already
    documents** — free actions sit inside the undo window and `restaurar_checkpoint` does
    `pickle.loads` of the whole engine, so an entry in the engine's log would make `len(eventos)`
    *shrink* on an undo. Being outside that pickle is also what makes the next point possible.
  - **It is append-only, and an undo marks rather than deletes.** `restaurar_checkpoint` flags
    every entry above `checkpoint_registro_len` (captured in `tomar_checkpoint`) as `deshecha`, and
    the route appends a "Deshizo su visita" line. The board reverting with no trace is worse than a
    struck-through line, especially for opponents who already heard the action's sound. Length, not
    a visit key, is enough: the checkpoint is taken before the visit's *first* free action and
    re-taken after an undo with the new length, so a second undo only reaches the newer entries.
    The flagging is in `sessions.py`, not the route, so it is testable without HTTP.
  - **The sentence is written server-side, in `commands.py:describir_accion`** — the one place
    where the wire params are already resolved *and* the `ActionManager` return value is in hand
    (F's `HorneadoRecord`, B's slot, the `int` the Simposio pays). Same reasoning as `engine.py`
    writing `GameEvent.mensaje` at the point of mutation. It is called after `resolver_comando`
    succeeded and before `_avanzar_fase_si_corresponde`; the actor's name is deliberately omitted,
    since the client prefixes it in the seat colour.
  - **`pos_eventos` is captured *before* the mutation**, which is what interleaves the two streams
    with no timestamps: an entry sorts after event `pos_eventos - 1` and before event
    `pos_eventos`, so "Horneó X" reads immediately above the `HORNEADO` it caused. It is written
    into `/actions` **before** the `ACCIONES_QUE_REVELAN` re-take, so a revealing action's entry
    falls inside the frozen length and a later undo can never strike it out.
  - **A force-pass has its own id here and not on the aviso channel.** The `AvisoAccion` stays
    `"pasar"` — it is the sound channel, and a forced pass sounds the same — while the entry is
    `pase_forzado` and names who forced it, which is the only place that information survives
    (`jugador_idx` holds who *was* passed). `forzar_pase` therefore keeps the requester's `Seat`,
    which it used to discard.

  Transport is the whole log inside `game_state_view`, no new route: an undo **mutates** old
  entries, which a `?since=N` delta cannot express without client-side delta logic the store
  deliberately avoids, and the `accion` frame already triggers `refrescarEstado()`, so live
  updates, reconnect and the undo flags all arrive for free. Cost is ~150–215 B/entry, roughly
  30–45 KB by the end of a 4-player game; `GZipMiddleware` is the lever if it ever matters.
  `VERSION_FORMATO` went to 17. This forced a real fix in `store.ts`: `onmessage` and
  `refrescarEventos` both pushed into `store.eventos` with no seq guard, and the merge indexes
  events by position, so a duplicate would no longer merely repeat a row — it would shift
  everything after it. Both paths now dedupe by seq (which also fixes duplicated rows in the Fase
  III report). Client side, `RegistroEventos.vue` drops its 12-entry cap and reversal for the full
  history newest-at-bottom with sticky auto-scroll (it follows only if you were already at the
  bottom), day separators, seat-coloured actor names, own lines washed in `--cobre`, and an
  exhaustive `Record<IdMovimiento, string>` icon map so a new action without an icon fails to
  compile. `IdMovimiento` lives next to `IdAccion`, following the `GRUPOS_ACCION` precedent. Two
  `test_undo.py` cases asserted whole-view equality across an undo and now compare the view minus
  `registro_acciones`, asserting the log's append-only shape separately — a pin, not a loosening.
  Not a rules change, so the rulebooks and `context/*.md` are deliberately untouched. Tests:
  `tests/test_registro_acciones.py`.

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

  **El reglamento dentro de la app (`ReglamentoView.vue` + `data/reglamento.ts`) — the rules are
  imported, never rewritten.** The client never mentioned that a rulebook exists: `RULEBOOK.html`
  sat in the repo root, the backend serves no static files, and nothing linked to it. Writing a
  "cómo se juega" page in Vue would have created a **fifth** rules surface free to contradict the
  other four (see "Every rules change MUST update the rulebooks") and the only one no test reads.
  Instead `data/reglamento.ts` does `import html from '../../../RULEBOOK.html?raw'`, `DOMParser`s
  it **once at module load**, keeps `main.innerHTML`, and throws away the file's own `<style>`,
  masthead, rail and footer; `ReglamentoView.vue` renders that with `v-html` and repaints ~20
  rulebook classes onto the board tokens. A rule now reaches players by editing the reglamento,
  which is mandatory anyway. `v-html` needs no sanitising and a comment says why: it is a repo
  file inlined at build time, the same trust level as the source tree. Six things carry weight:
  - **The `?raw` import needs `server.fs.allow: ['..']`, and its failure mode is the nasty kind.**
    Vite's workspace root resolves to `web/` (the repo root has no `pnpm-workspace.yaml`, no
    `lerna.json`, no `workspaces`, and `.git` does not count), and it re-checks `?raw` ids against
    that allow-list *even for a static import* — so **`vite build` works and `npm run dev` returns
    403**. The entry must be a **directory**: the second check runs with `?raw` still glued to the
    id, so a single-file entry never matches (`"…/RULEBOOK.html"` ≠ `"…/RULEBOOK.html?raw"`).
  - **The component is deliberately NOT `scoped`.** Its root is a `<Teleport>`, and Vue does not
    stamp `data-v-*` on teleported content, so in `modo="superpuesto"` **none** of the scoped CSS
    applied — the overlay rendered unpositioned and shoved the board down. Page mode looked
    perfect throughout, because there the teleport is disabled, which is exactly what made it easy
    to miss. Every selector in that file therefore hangs off `.reglamento`, and that is
    load-bearing rather than tidy: bare `.cuerpo` and `.cerrar` would collide with `GameView.vue`
    and `ModalShell.vue`.
  - **Two hosts, one component.** `modo="pagina"` is `App.vue`'s third branch, driven by
    `location.hash` (`#reglamento`, or `#reglamento/s7` to deep-link a section) with a **single**
    `hashchange` listener — adding `popstate` too would double-fire. No `vue-router`, matching the
    existing `?sala=` precedent, so `vue` stays the only runtime dependency.
    `modo="superpuesto"` is a full-screen `role="dialog"` opened from GameView's header that
    leaves the board mounted, so consulting a rule costs neither a panel's scroll position nor an
    open tooltip. **A live game beats the hash**: `enPartida` is checked first.
  - **In-content links are rewritten at parse time to `#reglamento/<id>`, but clicks are
    intercepted.** The rewrite is what makes copying or middle-clicking a link work; letting the
    click navigate would fire App's `hashchange` and, mid-game, rewrite the URL of a partida in
    progress. Overlay mode never touches the URL at all. Modified clicks (ctrl/cmd/shift) are
    left alone. The body holds 45 internal links and two of them point at an `h3` id, so the
    scheme accepts any id, not just `s\d+`.
  - **The TOC is rebuilt from `section.rule`, not copied from the file's `<nav class="rail">`.**
    A Vue `v-for` gets `@click`, `aria-current` and the `<details>` collapse as ordinary template
    code instead of DOM surgery on a `v-html` subtree, and it cannot drift from the sections that
    actually exist. The rail stays in the file for the standalone `file://` page.
  - **Both hosts use `defineAsyncComponent`**, so the ~84 KB of rulebook HTML rides its own chunk
    (≈30 KB gzipped) instead of the boot bundle, fetched on first open with no hand-rolled
    loading state. Lazily importing the raw string alone would add state for no gain.

  Accessibility of the overlay follows the existing modals: focus moves to the ✕ on open and is
  restored on close, Escape closes (the `Tooltip.vue` precedent), body scroll is locked, and
  `scroll-behavior: smooth` is turned off under `prefers-reduced-motion` — the global rule in
  `App.vue` only zeroes transitions and animations, so a JS/CSS smooth scroll falls outside that
  net and is the one place the preference must be handled by hand. Careful with the focus
  capture: it happens in the **setup body**, before the component moves focus itself, or it saves
  an element inside the overlay that is destroyed on close and the focus lands on `<body>`.

  This is not a rules change, so `context/*.md` and the reglamento's *content* are untouched —
  only the two maintenance comments, which claimed no test reads those files. Tests:
  `tests/test_reglamento_al_dia.py::test_el_html_tiene_la_estructura_que_la_app_renderiza` pins
  the structure the client parses (exactly one `<main>`, `s1..s12` in order with their printed
  ordinals, the rail agreeing, unique ids, no dangling internal link, and no
  `<script>`/`<style>`/`on*` inside `<main>`). It strips HTML comments first, the way a browser
  does — without that, a maintenance note that merely *mentions* `<main>` counts as a second tag,
  which is exactly how the test first failed. Verified by mutation: renaming a section id,
  removing `<main>`, and breaking an internal link each fail it. A break there leaves the in-game
  rulebook empty while the standalone file still opens perfectly, and nothing under `web/` would
  notice.

  **Portada y sala de espera — the pre-game screens.** `LobbyView.vue` was one 577-line component
  holding both the landing and the waiting room, clamped to 480px inside a shell that allows
  1100px, whose only art was a 🍞 in the `h1` and three emoji bullets, and whose single form gave
  "Crear sala" and "Unirse a sala" identical weight. It is now a three-line switch over
  `LandingView.vue` and `SalaEsperaView.vue`, with `FormularioSala.vue` and `TarjetasFases.vue`
  beside them. Four things carry weight:
  - **The invite-link ordering bug is the lesson to carry to the next component split.** Children
    mount **before** the parent's `onMounted`, so reading `?sala=` there left `FormularioSala`
    already set up with a null prop: the invite link opened the "Crear sala" tab with an empty
    code field. It is read in `LobbyView`'s **setup body** instead. The 577-line monolith could
    not have this bug; splitting it created it, and it is invisible to every test in the repo
    because nothing under `web/` is tested automatically.
  - **Copy lives in `web/src/data/copyLanding.ts`, and it holds no rule numbers.** No prices, no
    PA, no thresholds, no deck sizes — the only figure is "1–4 jugadores", a property of the
    product (`server/sessions.py:MAX_JUGADORES`) rather than a rule. A number on the portada would
    be a sixth copy nobody checks, and `test_reglamento_al_dia.py` cannot see this file. Voice is
    second person and gender-neutral (the old text said "investigadora jefa"), with the descriptor
    and the spec strip in third person as the box-back. `web/src/data/salas.ts` mirrors
    `UMBRAL_LIMPIEZA_LOBBY_SEGUNDOS` so the waiting room can say a room expires — until now it
    simply stopped existing with no warning, which is the kind of thing you only discover by
    leaving a lobby open over lunch.
  - **One primary action on screen at a time.** `FormularioSala.vue` replaces the "Crear … o …
    Unirse" stack with a segmented control; name and colour are shared, and only the selected
    mode's fields render. Typing a full code live-previews the room over the public
    `GET /games/{id}` (seats, count, and greying the colours already taken), and says which of
    "no existe" / "ya empezó" it is — three situations the old single error line conflated. Colour
    selection carries a **check glyph**, not just a ring: a selector *of colours* cannot signal
    its state with colour alone. Errors sit under the field they belong to rather than in one
    shared line at the bottom.
  - **`SalaEsperaView.vue` draws `max_jugadores` cells, filled or dashed-empty**, so "faltan dos"
    is visible without reading a counter, and the room code is `--fuente-dato` at display size
    because it is the one string that gets dictated aloud. `TarjetasFases.vue` is one component
    used by **both** screens deliberately: what you read while waiting is the same thing that
    explained the game before you joined, not a second wording free to drift.

  Not a rules change, so `context/*.md` and the rulebooks are untouched. `web/` has no automated
  tests (`vue-tsc -b` + a clean build is the whole check), so all of this was verified in a real
  browser: the two-column landing collapsing to form-first under 720px, create → waiting room →
  join from a second session → seat appearing within the 1.5 s poll → start, plus the three
  code-field states and the per-field validation.

  **Salas abiertas (`GET /games`) — the listing, and the privacy trade it makes.** The only way
  into a room was being told its six-letter code out of band, so someone opening the site without
  an invite met an empty code field and no way forward. `RoomManager.salas_abiertas()` returns
  the rooms a stranger can actually enter and `GET /games` publishes them; `SalasAbiertas.vue`
  renders them above the code field. Five things carry weight:
  - **Listed by default, with a "Sala privada" opt-out — and that means a code is no longer a
    secret unless the host asks.** Stated rather than buried, because it is a real change in what
    the code protects. The alternative (opt-in "Sala pública") was rejected for being empty in
    practice: a list you have to remember to switch on is a list nobody sees. `GameSession.privada`
    survives `reiniciar_a_lobby` like `max_jugadores`, and `views.py` ships it so
    `store.ts:crearSalaNueva` makes a **rematch inherit the privacy** — otherwise a private
    group's next game would quietly appear on the front page.
  - **The three filters are what stop the list from lying.** LOBBY, not private, and a free seat:
    `unirse` rejects a started room and a full one, so listing either would be offering a button
    that can only fail. `test_el_listado_solo_ofrece_salas_a_las_que_se_puede_entrar` covers all
    three, verified by mutation (dropping any one filter fails it).
  - **The route ships no tokens, and a test asserts the exact key set.** It is public, so a
    leaked `host_token` would let a stranger start someone's game and a leaked `Seat.token` would
    let them play another person's turn. `test_el_listado_no_filtra_ningun_token` greps the raw
    body for both and pins `{room_id, max_jugadores, segundos_abierta, seats}` — a whitelist, so
    a future field has to be added deliberately.
  - **`segundos_abierta` is computed server-side rather than shipping `creado_en`.** The client
    only wants to say "hace 3 min", and subtracting two different clocks gives nonsense as soon
    as one of them drifts. Same reasoning as `vitalidad_prevista` and `renta_diaria`.
  - **The poll lives in `FormularioSala`, not in `SalasAbiertas`.** The panel unmounts with the
    Crear/Unirse tab, but the count rides in the *tab label* ("Unirse · 2") precisely so someone
    on Crear learns rooms are waiting without switching — putting the interval in the panel would
    switch off exactly the counter that makes the feature discoverable. 3 s interval, cleared in
    `onUnmounted`, the `SalaEsperaView` precedent. A failed poll leaves the previous list alone:
    it is supporting information, not worth an error banner over the form.

  `_requerir_privada` demands a real `bool` rather than a truthy value, because the string
  `"no"` is truthy in Python and would mark private exactly the room the host wanted public.
  `VERSION_FORMATO` went to 19: a restored pickle without the attribute would break the whole
  listing route, not just its own row (`tests/test_robustness.py::test_privada_sobrevive_al_viaje_por_disco`).
  Tests: the five cases in `tests/test_server_api.py` plus that round-trip.

  **Aviso de sala nueva — four channels, because no single one reaches everybody.** A row quietly
  appearing in that list is easy to miss, and the player most likely to be waiting for a room is
  the one who tabbed away. Detection is a set difference over room ids in `refrescarSalas()`, and
  it fires: a short sound, a copper wash + "nueva" chip on the row for 6 s, a pulse on the tab
  badge, and the open-room count in `document.title`. Four things carry weight:
  - **Seed the first poll, never announce it.** Rooms that already existed when the page loaded
    are not an event; announcing them on load would confuse "this just happened" with "this was
    already here". It is the same rule `store.ts` applies to the turn chime and the endgame
    fanfare through `sembrarEstadoSinSonido` — a reconnect is not a live transition.
  - **The title is the only channel that reaches a background tab, and the sound is the one that
    may never work.** `sonido.ts` has no `AudioContext` until the first `pointerdown` in the tab
    (`habilitarAudio`, wired in `App.vue`), so a player who opened the landing and never clicked
    gets silence and a `console.debug` line — by design, not a bug. The title badge and the row
    highlight exist precisely to cover that player, which is why this is four channels and not
    just a ding.
  - **The sound came with a mute button, and that was not optional.** The only sound toggle lived
    in `GameView`'s header, i.e. nowhere near the landing. Making a screen emit sound with no
    visible way to silence it is the worse of the two failure modes, so `SalasAbiertas.vue`'s
    header carries one, writing the same durable `store.preferencias.sonido` through
    `establecerSonido`. Muting silences only the audio: the row, the badge and the title still
    announce, since they were never the intrusive part.
  - **One sound per poll, not per room**, or three rooms appearing together would chain three
    dings and read as an error. The timbre is E5→A5 at 0.16 gain, deliberately lower and quieter
    than the turn chime (A5→C#6 at 0.22): "it's your move" is a stronger claim than "something
    appeared", and if they sounded alike the more urgent one would lose its meaning. `sine`, not
    the `sawtooth` of the Emergencia protocols, which reads as "something failed".

  Both animations are `@keyframes`, so the global `prefers-reduced-motion` rule in `App.vue`
  clamps them for free (the `ConfetiPanes.vue` precedent) — and because the row's copper border
  and its chip are *not* animated, a reduced-motion player still gets the cue after the wash is
  clamped away. `reproducirAvisoSalaNueva` lives in `sonido.ts` beside the endgame sounds rather
  than in `data/sonidosAccion.ts`, whose exhaustive `Record<IdSonido, Sonido>` is keyed by wire
  action ids this is not. Nothing persisted changed shape: no `VERSION_FORMATO` bump.

  **Revelación del Patrocinio — the card survives the deal, so the app can show it.** The
  reglamento deals a Patrocinio card face down, reveals all of them at once and orders Día 1 by
  their Iniciativa; in the app none of that was visible, because `bootstrap.create_game` splatted
  the card into `Player.crear_dia_1` and kept only the permutation. A player started with
  resources they could not explain, in a position `OrdenTurnoPanel` attributed to a "Jefatura
  libre" nobody could have claimed. Now `Player.patrocinio: Optional[PatrocinioCard]` keeps the
  card, and `PatrocinioModal.vue` reveals it first thing. Four things carry weight:
  - **It is a `Player` field, not a view injection, because there is nothing to inject from.**
    `views.py` injects derived values (`renta_diaria`, `vitalidad_prevista`); the card is not
    derivable, it is *destroyed* at deal time. Being a frozen dataclass nested in a field it
    rides `serialization.snapshot` and the pickle for free, hence **`VERSION_FORMATO` 20** and a
    regenerated golden snapshot whose diff is exactly one `patrocinio` key per player (verified
    by stripping the key and comparing against the old file). No rule reads it after Día 1; the
    physical rule "the cards go back to the box" still holds for the *game*, and
    `PLAYER_STATE.md` says so.
  - **It goes ahead of `InicioDiaModal` in `GameView.vue`'s chain.** Both flags light up in the
    same first snapshot (Fase I has already run when `/start` returns, see
    `RoomManager.iniciar`), and the reveal is the only ordering where "what you have" precedes
    "what the weather does to it". The Día-1 position is read off `turno_orden`, not recomputed
    by sorting initiatives client-side — the engine already applied that rule.
  - **Once per tab per game, and deliberately not seeded on reconnect.** `store.ts`'s
    `patrocinioMostrado` follows `ultimaCartaClimaId`, not `jugadorEnTurnoAnterior`: a reload on
    Día 1 re-shows the reveal, since it is "your starting situation" rather than a transition you
    missed. Reset in both `cerrarSesion()` and `volverAVistaDeLobby()`, so a rematch shows it
    again, and gated on `dia_actual === 1` so it never fires later.
  - **`OrdenTurnoPanel` gets a Día-1 mode.** Each row carries its card's initiative and the note
    says the order came from the cards; the claim-the-Jefatura note still wins when someone has
    actually claimed it, which can happen on Día 1.

  The same commit fixed two stale doc lines in this exact area: `models.py`'s `crear_dia_1`
  docstring still claimed Datos were always 0, and `RULEBOOK.html`'s setup callout said
  "Vitalidad 1, 0 Datos" while the `.md` twin was right — prose `test_reglamento_al_dia.py` cannot
  see. Tests: `tests/test_patrocinio.py` (the deal-to-player mapping had never been asserted),
  plus a disk round-trip in `tests/test_robustness.py`.

### Error handling

All game-rule failures raise semantic exceptions from `exceptions.py` (never bare `Exception`,
`ValueError`, or a boolean return):

- `FermentumError` — base class for `except FermentumError` catch-all
- `ResourceDeficitError` → `NotEnoughActionPointsError`, `MissingResourceError`
- `RuleViolationError` → `StationBlockedError`, `CarpetaFullError`
- `InvalidActionError` — malformed/invalid call parameters
- Engine-flow errors: `PhaseViolationError`, `GameAlreadyOverError`,
  `InsufficientPlayersError`, `MarketSlotEmptyError`, `RecipeDeckEmptyError`,
  `NotYourTurnError` (server-layer turn
  ownership — every route funnels through `GameSession.asiento_por_token`)

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
`zona_colapso` auto-bakes at 0 PA cost with a penalty; then all players lose 1 vitality,
2 if "Aletargamiento Invernal" is active; then the market's oldest visible recipe is discarded —
`Market.descartar_receta_mas_antigua`, emits `RECETA_DESCARTADA`; then this morning's announced
trend is finally applied to the three flour price tracks —
`Market.aplicar_tendencia_pendiente`, emits `TENDENCIA_MERCADO` — so it governs *tomorrow's*
prices). The game ends when the climate deck is exhausted or
any player successfully bakes their 5th recipe (collapsed bakes don't count), then scores per
`CORE_MECHANICS.md` §3.
