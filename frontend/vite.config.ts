import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API calls to the FastAPI backend. In prod, the API serves the
// built assets from frontend/dist, so same-origin requests just work.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dev frontend proxies /api to the REAL GX10 backend (GB10 + Nemotron) over
      // Tailscale by default, so `npm run dev` exercises the live local models —
      // not a deterministic fallback. Override for a purely-local backend with:
      //   MERAKLIS_API=http://127.0.0.1:8088 npm run dev
      "/api": { target: process.env.MERAKLIS_API || "http://gx10-d8fb:8088", changeOrigin: true },
    },
  },
  build: { outDir: "dist" },
});
