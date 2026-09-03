import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Durante desarrollo, el backend (server/app.py, Milestone 3) corre por
// separado en :8000. Proxeamos /games para que el cliente pueda usar rutas
// relativas sin lidiar con CORS -- ver server/app.py para levantarlo:
//   .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1
export default defineConfig({
  plugins: [vue()],
  server: {
    // 3010 y no el 5173 por defecto de Vite: esa es la puerta que TODO proyecto
    // Vite pide, asi que dos repos abiertos a la vez se pisan. Aqui esta fijada
    // a proposito para que la URL del laboratorio no cambie segun que mas haya
    // levantado.
    port: 3010,
    // Fallar en vez de saltar a 3011. Sin esto Vite busca la siguiente puerta
    // libre EN SILENCIO, que es exactamente el problema que fijar la puerta
    // venia a resolver: la URL volveria a depender de quien arranco primero.
    strictPort: true,
    proxy: {
      '/games': 'http://127.0.0.1:8000',
    },
  },
})
