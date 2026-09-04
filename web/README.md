# Fermentum web client

Vue 3 (`<script setup>`, TypeScript) + Vite, no component library, plain CSS.
Talks to the headless HTTP backend in `../server/` (Milestone 3) over REST for commands, and
gets live updates via SSE (`EventSource` against `/games/{id}/events/stream`, Milestone 5) with
slow polling (state every 4s, events every 15s) kept running underneath as a fallback in case the
SSE connection silently fails — `EventSource` reconnects on its own with backoff and resumes via
`Last-Event-ID`, so this is a safety net, not the primary path. Requires Node ≥20.19 or ≥22.12
(pinned via `.nvmrc`) — Vite 8 doesn't run on older Node.

## Running it

You need both the backend and this frontend running at once, in two terminals.

```bash
# Terminal 1, from the repo root: the backend
.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1

# Terminal 2, from web/: the frontend
npm install   # first time only
npm run dev
```

Open <http://localhost:3010>. El puerto está **fijado** en `vite.config.ts` (`port: 3010` +
`strictPort: true`) en vez de usar el 5173 por defecto de Vite: ese es el puerto que pide
cualquier proyecto Vite, así que dos repos abiertos a la vez se pisan. Con `strictPort`, si el
3010 está ocupado el arranque **falla** en lugar de saltar en silencio al 3011 — que es
justamente lo que haría que la URL volviera a depender de quién arrancó primero.

`vite.config.ts` proxies `/games/*` to the backend on `:8000`, so the client can use relative URLs
with no CORS setup needed in dev. El backend sigue en el 8000: si también choca con algo tuyo,
cámbialo en los tres sitios que lo nombran (`server/app.py`, el proxy de `vite.config.ts` y este
README).

`npm run build` type-checks (`vue-tsc -b`) and produces a static `dist/` bundle; `npm run preview`
serves that bundle locally.

## Structure

- `src/types.ts` — TypeScript mirror of the JSON `server/views.py` sends (`GameStateView`,
  `Player`, `Recipe`, etc.) — keep in sync with the Python side by hand; there's no shared schema.
- `src/api.ts` — thin `fetch` wrappers, one per backend route.
- `src/store.ts` — the entire client state: one `reactive()` object, updated by `aplicarEstado()`
  from whatever the server last returned. No Pinia/Vuex (the server always sends a full snapshot,
  never a delta) and no optimistic updates (the server is the only rules authority — submit, wait
  for the response, render it). `iniciarPolling()` opens the SSE connection and starts the slow
  fallback polling together; each SSE message immediately triggers a state refetch rather than
  waiting for the next fallback tick.
- `src/components/` — `LobbyView` (a three-line switch: `LandingView` — hero + narrative +
  `FormularioSala`'s segmented Crear/Unirse card — until you're seated, then `SalaEsperaView`)
  and `GameView` (`ClimaBanner`,
  `MercadoPanel`, `MiTablero`/`EstacionCard`, `TablerosOponentes`, `BarraAcciones`,
  `RegistroEventos`, `FermentationReportModal`, `RankingView`).
  `MiTablero` takes a `jugadorIdx` prop and can draw **any** player, since the server ships
  every player's full state to every client (`server/views.py`). `SelectorTablero`'s chips
  (which replace the region's label) and `TablerosOponentes`' rows both switch the Tablero
  region to another player's board; the selection lives in `store.jugadorObservado`
  (per-game, not a preference) and snaps back to your own board when your turn arrives.
- `src/components/SalasAbiertas.vue` — the public list of rooms waiting for players
  (`GET /games`), shown above the code field in the Unirse tab, with the count mirrored in the
  tab label so it is visible from the Crear tab too (hence the 3 s poll lives in
  `FormularioSala`, which stays mounted, not in the panel). The server already filters private,
  full and started rooms, so every row is one where joining will work; the component re-filters
  nothing. Hosts can tick "Sala privada" at creation to stay off the list — that flag is the
  only thing keeping a room code secret now.
- `src/data/copyLanding.ts` — every sentence on the landing and in the waiting room.
  Deliberately free of rule numbers (prices, PA, thresholds, deck sizes): those belong to the
  rulebook, which is tested against the code. The only figure allowed is "1–4 jugadores".
- `src/components/ReglamentoView.vue` + `src/data/reglamento.ts` — the full rulebook inside the
  app. It is **not** rewritten here: `RULEBOOK.html` (repo root) is imported with Vite's `?raw`,
  parsed once with `DOMParser`, stripped to its `<main>`, and repainted with the app's tokens, so
  a rules change reaches players by editing the reglamento and nothing else. Reachable two ways:
  `#reglamento` (or `#reglamento/s7` for a section) — the app's only hash route, handled in
  `App.vue`, no `vue-router` — and a header button during a game, which opens it as a full-screen
  overlay with the board still mounted behind. Both are lazy-loaded, so the ~84 KB of rulebook
  HTML is its own chunk. Two things will bite you if you edit that component: the `?raw` import
  needs `server.fs.allow: ['..']` in `vite.config.ts` (without it `npm run dev` 403s while
  `npm run build` works fine), and its `<style>` is deliberately **not** `scoped` — a `<Teleport>`
  root gets no `data-v-*` attribute, so scoped rules silently never applied in overlay mode. Every
  selector there must stay prefixed with `.reglamento`.
- `src/components/acciones/` — one component per player action, plus a shared
  `ModalConfirmacion.vue` for the three
  parameterless confirm actions (H, I, Horas Extras). Button enablement comes from the server's
  `acciones_disponibles` (see `disponibilidad.py`) — this client never reimplements
  `ActionManager`'s rules to decide whether a button should be clickable.
