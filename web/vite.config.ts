import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => ({
  ...(mode === "report"
    ? { define: { "process.env.NODE_ENV": JSON.stringify("production") } }
    : {}),
  plugins: [tailwindcss()],
  build:
    mode === "report"
      ? {
          outDir: "../src/qi/static-report",
          emptyOutDir: true,
          lib: {
            entry: "src/offline.tsx",
            name: "QiReport",
            formats: ["iife"],
            fileName: () => "viewer.js",
            cssFileName: "viewer",
          },
          minify: true,
        }
      : { outDir: "../src/qi/static", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
}));
