<template>
  <div class="conv-page">
    <!-- Unified header: one title + a view switch (replaces the old separate
         "All chats" and "Live View" nav items). -->
    <div class="conv-header">
      <div class="conv-titles">
        <h1 class="conv-title">Conversations</h1>
        <p class="conv-sub">Live chats from every channel — read, monitor, and take over.</p>
      </div>
      <div class="view-toggle" role="tablist" aria-label="Conversation view">
        <button :class="{ active: view === 'list' }" @click="setView('list')" role="tab" :aria-selected="view === 'list'">
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          List
        </button>
        <button :class="{ active: view === 'live' }" @click="setView('live')" role="tab" :aria-selected="view === 'live'">
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="2"/><rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="2"/><rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="2"/><rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="2"/></svg>
          Live grid
        </button>
      </div>
    </div>

    <!-- Body fills remaining height; the Inbox (list) manages its own internal
         3-panel scroll, the Live grid scrolls within the body. -->
    <div class="conv-body">
      <PortalInbox v-if="view === 'list'" :client="client" embedded />
      <PortalLiveView v-else :client="client" embedded />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PortalInbox from './PortalInbox.vue'
import PortalLiveView from './PortalLiveView.vue'

defineProps({ client: Object })
const route = useRoute()
const view = ref('list')

function setView(v) {
  view.value = v
  try { localStorage.setItem('cf_conv_view', v) } catch {}
}

onMounted(() => {
  // Deep-link support: /portal/inbox?view=live (also where /portal/live redirects).
  const q = route.query.view
  if (q === 'live' || q === 'list') { view.value = q; return }
  try { const s = localStorage.getItem('cf_conv_view'); if (s === 'live' || s === 'list') view.value = s } catch {}
})
</script>

<style scoped>
.conv-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.conv-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 32px 14px;
  flex-wrap: wrap;
}
.conv-titles { min-width: 0; }
.conv-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 3px; }
.conv-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; }

.view-toggle {
  display: flex;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-default);
  border-radius: 10px;
  padding: 3px;
  gap: 3px;
  flex-shrink: 0;
}
.view-toggle button {
  display: inline-flex; align-items: center; gap: 6px;
  background: none; border: none; border-radius: 8px;
  padding: 7px 14px; font-size: 13px; font-weight: 600;
  color: var(--cf-text-muted); cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.view-toggle button:hover { color: var(--cf-text-secondary); }
.view-toggle button.active { background: var(--cf-bg-item-active, rgba(99,102,241,0.15)); color: #a5b4fc; }

.conv-body { flex: 1; min-height: 0; overflow-y: auto; }

@media (max-width: 600px) {
  .conv-header { padding: 18px 16px 12px; }
  .view-toggle button { padding: 7px 12px; }
}
</style>
