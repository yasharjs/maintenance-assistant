/*vite.config.ts*/

import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";
import path from "path";
import { componentTagger } from "lovable-tagger";

export default defineConfig(({ mode }) => ({
  server: {
    port: 50505,
    proxy: {
      "/conversation": "http://127.0.0.1:50505",
      "/history":      "http://127.0.0.1:50505",
      "/frontend_settings": "http://127.0.0.1:50505",
      "/.auth":        "http://127.0.0.1:50505"
    }
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));