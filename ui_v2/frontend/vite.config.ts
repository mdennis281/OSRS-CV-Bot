import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API_URL = process.env.VITE_API_URL ?? 'http://127.0.0.1:8010';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': API_URL,
      '/ws': {
        target: API_URL.replace('http', 'ws'),
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
