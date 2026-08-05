import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    emptyOutDir: true,
    manifest: true,
    outDir: "../public/theme/dist",
    rollupOptions: {
      input: "src/main.tsx",
      output: {
        entryFileNames: "main.js"
      }
    }
  },
  server: {
    host: "0.0.0.0",
    port: 3000
  }
});
