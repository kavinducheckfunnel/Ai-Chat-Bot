/**
 * Generates the chat widget embed snippet.
 *
 * Returns a tiny <script> tag that loads the hosted Vue widget. The widget
 * fetches branding/config from the backend on load and re-polls every 60 s,
 * so when the tenant changes colours / chatbot name / CTA message in the
 * portal, the change appears on their site within ~60s — NO RE-PASTE EVER.
 *
 * Format wrappers (wordpress, react) just decorate the same one-liner.
 *
 * Note: kept as a plain .js file so the Vue SFC tokeniser never tries to
 * parse the embedded <script>/<style> tags as real HTML.
 */

export function generateEmbedCode(id, url, color, botName, format) {
  if (!id || !url) return ''

  const widgetSrc = url + '?client_id=' + id
  const scriptTag = '<script src="' + widgetSrc + '" async></' + 'script>'

  if (format === 'wordpress') {
    return [
      '<?php',
      '/**',
      ' * Checkfunnel AI chat widget loader.',
      ' * Paste into your active theme\'s functions.php, or use the',
      ' * "Insert Headers and Footers" plugin (Footer section).',
      ' * Branding & feature flags update live from the Checkfunnel portal.',
      ' */',
      'function checkfunnel_widget() {',
      "    echo '" + scriptTag.replace(/'/g, "\\'") + "';",
      '}',
      "add_action( 'wp_footer', 'checkfunnel_widget' );",
    ].join('\n')
  }

  if (format === 'react') {
    return [
      "import { useEffect } from 'react'",
      '',
      '/**',
      ' * <CheckfunnelWidget /> can be dropped anywhere in your component tree.',
      ' * Branding & feature flags update live from the Checkfunnel portal.',
      ' */',
      'export function CheckfunnelWidget() {',
      '  useEffect(() => {',
      "    if (document.getElementById('cf-widget-script')) return",
      "    const s = document.createElement('script')",
      "    s.id = 'cf-widget-script'",
      "    s.src = '" + widgetSrc + "'",
      '    s.async = true',
      '    document.body.appendChild(s)',
      '    return () => { s.remove() }',
      '  }, [])',
      '  return null',
      '}',
    ].join('\n')
  }

  // Default: plain HTML — paste before </body> on any page.
  return [
    '<!-- Checkfunnel AI chat widget — branding updates live from the portal -->',
    scriptTag,
  ].join('\n')
}
