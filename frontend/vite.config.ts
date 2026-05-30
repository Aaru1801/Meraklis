import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API calls to the FastAPI backend. In prod, the API serves the
// built assets from frontend/dist, so same-origin requests just work.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // The app's FastAPI backend runs on :8088; the local model server (NIM /
      // vLLM / TRT-LLM) owns :8000 per MODEL_BASE_URL, so the two never collide.
      "/api": { target: "http://127.0.0.1:8088", changeOrigin: true },
    },
  },
  build: { outDir: "dist" },
});
