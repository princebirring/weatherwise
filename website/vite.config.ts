import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the WeatherWise API runs separately:
//   uv run python -m weatherwise.api.server   (port 8080)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8080' } },
})
