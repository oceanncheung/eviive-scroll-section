import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// Single self-contained bundle: inlines every asset so the built page can be
// published as one file and, later, imported into Framer as one module.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    target: "es2022",
    assetsInlineLimit: 100000000,
    cssCodeSplit: false,
    rollupOptions: { output: { inlineDynamicImports: true, manualChunks: undefined } },
  },
})
