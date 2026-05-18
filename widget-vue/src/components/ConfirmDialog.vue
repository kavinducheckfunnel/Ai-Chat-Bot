<template>
  <teleport to="body">
    <transition name="confirm-fade">
      <div v-if="state.visible" class="confirm-overlay" @click.self="respond(false)">
        <div class="confirm-box" role="dialog" aria-modal="true">
          <p class="confirm-message">{{ state.message }}</p>
          <div class="confirm-actions">
            <button class="confirm-btn confirm-cancel" @click="respond(false)">Cancel</button>
            <button class="confirm-btn confirm-ok" @click="respond(true)">Confirm</button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { useConfirm } from '../composables/useConfirm'
const { state, respond } = useConfirm()
</script>

<style>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.65);
  z-index: 99998;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(3px);
}

.confirm-box {
  background: #1a1a2e;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px;
  padding: 28px 28px 22px;
  max-width: 420px;
  width: calc(100vw - 48px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}

.confirm-message {
  color: #e2e8f0;
  font-size: 15px;
  line-height: 1.5;
  margin: 0 0 22px;
  font-family: 'Inter', -apple-system, sans-serif;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.confirm-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  font-family: 'Inter', -apple-system, sans-serif;
  transition: opacity 0.15s;
}
.confirm-btn:hover { opacity: 0.85; }

.confirm-cancel { background: rgba(255,255,255,0.08); color: #94a3b8; }
.confirm-ok     { background: #6366f1; color: #fff; }

.confirm-fade-enter-active, .confirm-fade-leave-active { transition: opacity 0.2s ease; }
.confirm-fade-enter-from, .confirm-fade-leave-to { opacity: 0; }
</style>
