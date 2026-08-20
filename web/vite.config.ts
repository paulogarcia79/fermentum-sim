import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Durante desarrollo, el backend (server/app.py, Milestone 3) corre por
// separado en :8000. Proxeamos /games para que el cliente pueda usar rutas
// relativas sin lidiar con CORS -- ver server/app.py para levantarlo:
//   .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/games': 'http://127.0.0.1:8000',
    },
  },
})
