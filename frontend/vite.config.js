import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser only talks to Vite; Vite forwards API calls to the Python servers.
export default defineConfig({
  plugins: [react()],
  publicDir: "../samples", // serves the sample PDFs at /<file name>
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8001", rewrite: (path) => path.replace(/^\/api/, "") }, // app server
      "/chat": "http://127.0.0.1:8002", // copilot chat API
    },
  },
});
