import { ref } from 'vue'

// Module-level singleton — shared across all components
const _theme = ref(localStorage.getItem('cf_theme') || 'dark')
let _mediaQuery = null

function _resolveEffective(t) {
  if (t !== 'system') return t
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function _onSystemChange() {
  _apply('system')
}

function _apply(t) {
  const effective = _resolveEffective(t)
  document.documentElement.setAttribute('data-theme', effective)
  document.documentElement.classList.toggle('dark', effective === 'dark')
  localStorage.setItem('cf_theme', t)

  if (_mediaQuery) {
    _mediaQuery.removeEventListener('change', _onSystemChange)
    _mediaQuery = null
  }
  if (t === 'system') {
    _mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    _mediaQuery.addEventListener('change', _onSystemChange)
  }
}

// Apply immediately on first import
_apply(_theme.value)

export function useTheme() {
  function setTheme(t) {
    _theme.value = t
    _apply(t)
  }

  return { theme: _theme, setTheme }
}
