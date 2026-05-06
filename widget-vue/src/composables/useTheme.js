import { ref } from 'vue'

// Module-level singleton — shared across all components
const _theme = ref(localStorage.getItem('cf_theme') || 'dark')

function _apply(t) {
  document.documentElement.setAttribute('data-theme', t)
  document.documentElement.classList.toggle('dark', t === 'dark')
  localStorage.setItem('cf_theme', t)
}

// Apply immediately on first import (before any component renders)
_apply(_theme.value)

export function useTheme() {
  function toggle() {
    const next = _theme.value === 'dark' ? 'light' : 'dark'
    _theme.value = next
    _apply(next)
  }

  function setTheme(t) {
    _theme.value = t
    _apply(t)
  }

  return { theme: _theme, toggle, setTheme }
}
