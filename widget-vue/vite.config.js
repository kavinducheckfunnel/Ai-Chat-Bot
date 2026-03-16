import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js'

export default defineConfig({
  plugins: [
    vue(),
    // Inlines CSS into the widget JS bundle — single <script> tag embed, no separate .css needed
    cssInjectedByJsPlugin({
      jsAssetsFilterFunction: ({ fileName }) => fileName === 'assets/widget.js',
    }),
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
  build: {
    rollupOptions: {
      input: {
        widget: resolve(__dirname, 'index.html'),
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
