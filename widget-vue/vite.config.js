import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'admin-html-rewrite',
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          if (req.url.startsWith('/admin') && !req.url.includes('.')) {
            req.url = '/admin.html'
          }
          next()
        })
      },
    },
  ],
  server: {
    proxy: {
      // Proxy all API + widget requests to Django
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/widget': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections to Django/Daphne
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        admin: resolve(__dirname, 'admin.html'),
      },
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
      },
    },
  },
})
