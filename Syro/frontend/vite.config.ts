import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  // Optimisation esbuild
  esbuild: {
    target: 'es2020',
    logOverride: { 'this-is-undefined-in-esm': 'silent' }
  },
  // Optimisation du build
  build: {
    target: 'es2020',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['lucide-react', 'clsx', 'tailwind-merge']
        }
      }
    }
  },
  // Optimisation des dépendances
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'axios']
  }
})

