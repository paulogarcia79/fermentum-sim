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
    // RULEBOOK.html vive en la raiz del repo, no dentro de web/, y
    // ReglamentoView.vue lo importa con `?raw` para renderarlo dentro de la
    // app. Vite solo sirve su "workspace root" -- que aqui es web/, porque la
    // raiz no tiene ni pnpm-workspace.yaml ni lerna.json ni un package.json
    // con `workspaces`, y .git no cuenta -- y ademas trata un id `?raw` como
    // lectura de fichero, no como modulo: lo vuelve a comprobar contra esta
    // lista aunque la importacion sea estatica. Sin esto, `npm run dev`
    // responde 403 (la build de produccion no pasa por aqui y funcionaria,
    // que es la forma mas incomoda de descubrirlo).
    //
    // Tiene que ser un DIRECTORIO: una entrada de fichero suelto no vale,
    // porque la segunda comprobacion se hace con el `?raw` todavia pegado al
    // id y "…/RULEBOOK.html" nunca es igual a "…/RULEBOOK.html?raw".
    //
    // El `fs.deny` por defecto (.env*, certificados, **/.git/**) sigue en pie.
    fs: {
      allow: ['..'],
    },
  },
})
