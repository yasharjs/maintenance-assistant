import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Minimal, stable React build. No externals.
export default defineConfig({
  plugins: [react()],
  server: {
    // run dev server on a different port than your backend
    port: 5173,
    proxy: {
      // point API calls to your backend on 50505
      '/conversation': 'http://127.0.0.1:50505',
      '/history': 'http://127.0.0.1:50505',
      '/frontend_settings': 'http://127.0.0.1:50505',
      '/.auth': 'http://127.0.0.1:50505',
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',     // keep your current copy step
    sourcemap: true,    // helps debug if something still breaks
  },
  optimizeDeps: {
    include: ['react', 'react-dom'],
    exclude: [],
  },
})
