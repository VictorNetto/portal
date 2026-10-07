import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Accept requests proxied via nginx (Host: nginx) and from the browser
    // (localhost). 'allowedHosts: true' disables the dev-server host check —
    // safe here because the server is only reachable inside the Docker network.
    allowedHosts: true,
    // HMR websocket must work when the app is reached through nginx on :8080.
    hmr: { clientPort: 8080 },
    watch: { usePolling: true }, // reliable file-watching on the Windows bind mount
  },
})
