import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // HMR websocket must work when the app is reached through nginx on :8080.
    hmr: { clientPort: 8080 },
    watch: { usePolling: true }, // reliable file-watching on the Windows bind mount
  },
})
