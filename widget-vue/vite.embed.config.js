/**
 * Loader build — produces dist/assets/embed.js as a self-contained IIFE.
 *
 * Served by Django at /widget/embed.js?client_id=X. The merchant pastes a
 * single stable <script> line; this bundle injects the full inline widget
 * (reusing generateEmbedCode) so future fixes deploy without re-pasting.
 *
 * IIFE (no import/export) so a plain <script src> tag executes it. No CSS
 * asset is emitted — the widget's styles live inside the generated snippet
 * string, not in a Vue SFC <style>.
 */
import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  build: {
    outDir: 'dist/assets',
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/embed-entry.js'),
      name: 'CheckfunnelEmbed',
      formats: ['iife'],
      fileName: () => 'embed.js',
    },
    rollupOptions: { external: [] },
  },
})
