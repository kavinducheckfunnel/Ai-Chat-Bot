/**
 * Widget-only build — produces dist/assets/widget.js as a self-contained IIFE.
 *
 * Why IIFE?  When WordPress (or any third-party site) loads the chatbot via:
 *   <script src="https://yourserver.com/widget/widget.js" data-client-id="..."></script>
 * the browser refuses to execute an ES-module bundle (contains `import` statements)
 * loaded without `type="module"`.  An IIFE has zero import/export statements and
 * works with any plain <script> tag.
 *
 * Why custom inlineCssPlugin?
 * Vue SFC <style> blocks are extracted to a separate .css file by default even in
 * lib mode.  We need a single .js file for a one-tag embed, so this plugin removes
 * the CSS asset from the bundle and prepends a tiny style-injection snippet into
 * the IIFE.
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import fs from 'fs'
import path from 'path'

/**
 * After the build writes all files to disk, find any CSS files in dist/assets
 * (excluding admin.css which belongs to the admin SPA), inject their content
 * into widget.js via a prepended style-injection snippet, then delete them.
 * We use closeBundle (post-write) because Vite emits CSS outside the Rollup
 * bundle object, so generateBundle can't see them.
 */
function inlineCssPlugin() {
  return {
    name: 'inline-css-into-iife',
    apply: 'build',
    closeBundle() {
      const assetsDir = resolve(__dirname, 'dist/assets')
      const widgetJs = path.join(assetsDir, 'widget.js')
      if (!fs.existsSync(widgetJs)) return

      const cssFiles = fs.readdirSync(assetsDir).filter(
        f => f.endsWith('.css') && !f.startsWith('admin.')
      )
      if (cssFiles.length === 0) return

      let css = ''
      for (const f of cssFiles) {
        css += fs.readFileSync(path.join(assetsDir, f), 'utf-8')
        fs.unlinkSync(path.join(assetsDir, f))
      }

      const inject =
        `(function(){var s=document.createElement('style');` +
        `s.textContent=${JSON.stringify(css)};` +
        `document.head.appendChild(s);})();\n`
      fs.writeFileSync(widgetJs, inject + fs.readFileSync(widgetJs, 'utf-8'))
      console.log('[inline-css-into-iife] CSS inlined and widget.js updated')
    },
  }
}

export default defineConfig({
  plugins: [
    vue(),
    inlineCssPlugin(),
  ],
  build: {
    outDir: 'dist/assets',
    emptyOutDir: false,       // admin files in dist/ must not be wiped
    lib: {
      entry: resolve(__dirname, 'src/main.js'),
      name: 'CheckfunnelWidget',
      formats: ['iife'],
      fileName: () => 'widget.js',   // explicit .js so the file is named widget.js
    },
    rollupOptions: {
      external: [],           // bundle Vue + all deps into the single IIFE
    },
  },
})
