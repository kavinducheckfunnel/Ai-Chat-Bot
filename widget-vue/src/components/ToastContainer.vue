<template>
  <teleport to="body">
    <div class="toast-stack" aria-live="polite">
      <transition-group name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast-${t.type}`"
          @click="remove(t.id)"
          role="alert"
        >
          <span class="toast-icon">{{ icons[t.type] }}</span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click.stop="remove(t.id)" aria-label="Close">✕</button>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { useToast } from '../composables/useToast'

const { toasts, remove } = useToast()
const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' }
</script>

<style>
.toast-stack {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
  max-width: 380px;
  width: calc(100vw - 48px);
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 14px;
  font-family: 'Inter', -apple-system, sans-serif;
  line-height: 1.4;
  cursor: pointer;
  pointer-events: all;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  backdrop-filter: blur(10px);
}

.toast-success { background: #052e16; border: 1px solid rgba(34,197,94,0.4); color: #86efac; }
.toast-error   { background: #1c0612; border: 1px solid rgba(239,68,68,0.4); color: #fca5a5; }
.toast-info    { background: #0c1a2e; border: 1px solid rgba(99,102,241,0.4); color: #a5b4fc; }
.toast-warning { background: #1c1400; border: 1px solid rgba(234,179,8,0.4); color: #fde047; }

.toast-icon { flex-shrink: 0; font-weight: 700; font-size: 13px; margin-top: 1px; }
.toast-msg  { flex: 1; }
.toast-close {
  background: none; border: none; color: inherit; opacity: 0.6;
  cursor: pointer; font-size: 12px; padding: 0 2px; margin-left: 4px;
  flex-shrink: 0; line-height: 1;
}
.toast-close:hover { opacity: 1; }

.toast-enter-active { transition: all 0.25s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from   { opacity: 0; transform: translateX(32px); }
.toast-leave-to     { opacity: 0; transform: translateX(32px); }
</style>
