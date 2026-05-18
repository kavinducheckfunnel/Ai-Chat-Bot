<template>
  <div class="theme-pill">
    <button
      v-for="opt in options"
      :key="opt.value"
      class="theme-opt"
      :class="{ active: theme === opt.value }"
      @click="setTheme(opt.value)"
      :title="opt.label"
    >
      <span class="theme-icon" v-html="opt.icon" />
      <span class="theme-label">{{ opt.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'

const { theme, setTheme } = useTheme()

const options = [
  {
    value: 'light',
    label: 'Light',
    icon: `<svg width="13" height="13" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2"/>
      <path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
  },
  {
    value: 'system',
    label: 'System',
    icon: `<svg width="13" height="13" fill="none" viewBox="0 0 24 24">
      <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
  },
  {
    value: 'dark',
    label: 'Dark',
    icon: `<svg width="13" height="13" fill="none" viewBox="0 0 24 24">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
  },
]
</script>

<style scoped>
.theme-pill {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--cf-toggle-bg);
  border-radius: 10px;
  padding: 3px;
}

.theme-opt {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 5px 6px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--cf-toggle-text);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.theme-opt:hover {
  color: var(--cf-sidebar-item-hover-text);
}

.theme-opt.active {
  background: var(--cf-toggle-active-bg);
  color: var(--cf-toggle-active-text);
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}

.theme-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.theme-label {
  font-size: 11px;
}
</style>
