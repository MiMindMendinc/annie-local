import { defineConfig } from "vite";

// The preview serves the real FastAPI page, assets, APIs, and security headers.
// Vite is a development proxy only; it is not required by `annie launch`.
export default defineConfig({
  server: {
    host: "127.0.0.1",
    allowedHosts: ["terminal.local"],
    proxy: { "/": "http://127.0.0.1:18787" },
  },
});
