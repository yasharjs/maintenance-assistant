import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
    sourcemap: true
  },
  server: {
    proxy: {
      '/conversation': 'http://127.0.0.1:50505',
      '/history': 'http://127.0.0.1:50505',
      '/frontend_settings': 'http://127.0.0.1:50505',
      '/.auth': 'http://127.0.0.1:50505'
      // '/ask': 'http://localhost:5050',
      // '/chat': 'http://localhost:5050'
    }
  }
})
