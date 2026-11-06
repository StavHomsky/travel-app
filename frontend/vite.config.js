import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In development React runs on :5173 and Flask on :5000.
    // The proxy forwards /api calls to Flask, so the browser sees one origin
    // (the same thing nginx / the Kubernetes Ingress do in production).
    proxy: {
      // Port 5001 because macOS uses 5000 for AirPlay Receiver.
      '/api': process.env.API_URL || 'http://localhost:5001',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: false,
  },
})
