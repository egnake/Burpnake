import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// BurpNake Frontend — Vite Configuration
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Dev modda /api isteklerini backend'e yonlendir
      '/api': {
        target: 'http://127.0.0.1:8899',
        changeOrigin: true,
      }
    }
  },
  build: {
    // Production build outputu
    outDir: 'dist',
    sourcemap: false,
  },
  // Docker / production'da backend URL'si env variable'dan
  define: {
    __BACKEND_URL__: JSON.stringify(process.env.VITE_API_BASE_URL || '')
  }
})
