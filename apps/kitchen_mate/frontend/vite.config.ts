import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Load env from parent directory (shared with backend)
  const env = loadEnv(mode, "..", "");

  return {
    plugins: [react()],
    // Inject SUPABASE_* env vars at build time (no VITE_ prefix needed)
    define: {
      __SUPABASE_URL__: JSON.stringify(env.SUPABASE_URL || ""),
      __SUPABASE_ANON_KEY__: JSON.stringify(env.SUPABASE_ANON_KEY || ""),
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
