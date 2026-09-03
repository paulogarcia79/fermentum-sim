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

Open the URL Vite prints (usually `http://localhost:5173`). `vite.config.ts` proxies `/games/*`
to the backend on `:8000`, so the client can use relative URLs with no CORS setup needed in dev.

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
- `src/components/` — `LobbyView` (create/join/start) and `GameView` (`ClimaBanner`,
  `MercadoPanel`, `MiTablero`/`EstacionCard`, `TablerosOponentes`, `BarraAcciones`,
  `RegistroEventos`, `FermentationReportModal`, `RankingView`).
  `MiTablero` takes a `jugadorIdx` prop and can draw **any** player, since the server ships
  every player's full state to every client (`server/views.py`). `SelectorTablero`'s chips
  (which replace the region's label) and `TablerosOponentes`' rows both switch the Tablero
  region to another player's board; the selection lives in `store.jugadorObservado`
  (per-game, not a preference) and snaps back to your own board when your turn arrives.
- `src/components/acciones/` — one component per player action, plus a shared
  `ModalConfirmacion.vue` for the three
  parameterless confirm actions (H, I, Horas Extras). Button enablement comes from the server's
  `acciones_disponibles` (see `disponibilidad.py`) — this client never reimplements
  `ActionManager`'s rules to decide whether a button should be clickable.
