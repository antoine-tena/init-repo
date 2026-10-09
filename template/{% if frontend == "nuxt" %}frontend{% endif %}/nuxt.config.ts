// https://nuxt.com/docs/api/configuration/nuxt-config
import tailwindcss from '@tailwindcss/vite'

// Origine du backend Django en développement, cible du proxy '/api/**' ci-dessous.
const DEFAULT_BACKEND_ORIGIN = 'http://localhost:8000'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {}
const backendOrigin = env.NUXT_BACKEND_URL ?? DEFAULT_BACKEND_ORIGIN

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // [IMPORTS-EXPLICITES] : les composants du projet s'importent à la main.
  components: { dirs: [] },
  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },
  typescript: { strict: true, typeCheck: false },
  runtimeConfig: {
    public: { apiBase: '/api' }
  },
  routeRules: {
    '/api/**': { proxy: `${backendOrigin}/api/**` }
  }
})
