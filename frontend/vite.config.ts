import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Local browser verification without changing backend CORS or exposing server internals.
  // API_PROXY_TARGET is server-only; production hosting must configure its own reverse proxy/CORS.
  const proxy = env.API_PROXY_TARGET ? {
    '/backend': { target: env.API_PROXY_TARGET, changeOrigin: true, rewrite: (path: string) => path.replace(/^\/backend/, '') },
  } : undefined
  return {
    plugins: [react(), tailwindcss()],
    server: { proxy },
    preview: { proxy },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
