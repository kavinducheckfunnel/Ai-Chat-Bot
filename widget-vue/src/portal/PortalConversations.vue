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

    <!-- Filter bar: channel chips (QA #1) + global date range (QA #10). Shared
         across both the List and Live grid views below. -->
    <div class="conv-filters">
      <div class="channel-chips" role="tablist" aria-label="Channel">
        <button v-for="c in channels" :key="c.value"
                :class="['chip', 'chip-' + c.value, { active: channel === c.value }]"
                @click="channel = c.value" role="tab" :aria-selected="channel === c.value">
          <span class="chip-ico" v-html="c.icon"></span>{{ c.label }}
        </button>
      </div>
      <PortalDateFilter v-model="datePeriod" @change="onDateChange" />
    </div>

    <!-- Body fills remaining height; the Inbox (list) manages its own internal
         3-panel scroll, the Live grid scrolls within the body. -->
    <div class="conv-body">
      <PortalInbox v-if="view === 'list'" :client="client" :channel="channel" :date-range="dateRange" embedded />
      <PortalLiveView v-else :client="client" :channel="channel" :date-range="dateRange" embedded />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PortalInbox from './PortalInbox.vue'
import PortalLiveView from './PortalLiveView.vue'
import PortalDateFilter from './PortalDateFilter.vue'

defineProps({ client: Object })
const route = useRoute()
const view = ref('list')
const channel = ref('all')
const datePeriod = ref('all')
const dateRange = ref({ period: 'all', dateFrom: null, dateTo: null })

const channels = [
  { value: 'all', label: 'All Channels', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" stroke="currentColor" stroke-width="1.4"/></svg>' },
  { value: 'website', label: 'Web Chat', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="14" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M8 21h8M12 18v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>' },
  { value: 'whatsapp', label: 'WhatsApp', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 00-8.6 15l-1.4 5 5.2-1.4A10 10 0 1012 2zm0 18a8 8 0 01-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8 8 0 1112 20zm4.5-6c-.2-.1-1.4-.7-1.6-.8s-.4-.1-.5.1-.6.8-.8.9-.3.2-.5 0a6.5 6.5 0 01-3.2-2.8c-.2-.4.2-.4.6-1.2a.4.4 0 000-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5a1 1 0 00-.7.3 3 3 0 00-.9 2.2 5.2 5.2 0 001.1 2.8 11.8 11.8 0 004.5 4c2 .9 2 .6 2.4.6a2.6 2.6 0 001.7-1.2 2.1 2.1 0 00.1-1.2c0-.1-.2-.1-.4-.2z"/></svg>' },
  { value: 'instagram', label: 'Instagram', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="3.5" stroke="currentColor" stroke-width="1.7"/><circle cx="17" cy="7" r="1.2" fill="currentColor"/></svg>' },
  { value: 'messenger', label: 'Messenger', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.3 2 2 6.2 2 11.7c0 3 1.4 5.7 3.7 7.4V22l3.4-1.9c.9.3 1.9.4 2.9.4 5.7 0 10-4.2 10-9.7S17.7 2 12 2zm1 13l-2.6-2.7L5.5 15l5.3-5.6 2.6 2.7L18.4 9 13 15z"/></svg>' },
]

function onDateChange(payload) {
  dateRange.value = payload
}

function setView(v) {
  view.value = v
  try { localStorage.setItem('cf_conv_view', v) } catch {}
}

onMounted(() => {
  // Deep-link support: /portal/inbox?view=live (also where /portal/live redirects).
  const q = route.query.view
  if (q === 'live' || q === 'list') { view.value = q }
  else { try { const s = localStorage.getItem('cf_conv_view'); if (s === 'live' || s === 'list') view.value = s } catch {} }
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

/* ── Filter bar ─────────────────────────────────────────────────────────── */
.conv-filters {
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; flex-wrap: wrap;
  padding: 0 32px 14px;
}
.channel-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 7px 14px; border-radius: 22px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); font-size: 12.5px; font-weight: 600;
  cursor: pointer; transition: all .15s; font-family: inherit; white-space: nowrap;
}
.chip:hover { border-color: #6366f1; }
.chip .chip-ico { display: inline-flex; opacity: .85; }
.chip.active { background: #6366f1; border-color: #6366f1; color: #fff; }
.chip.active .chip-ico { opacity: 1; }
.chip-whatsapp.active { background: #25d366; border-color: #25d366; }
.chip-instagram.active { background: #e1306c; border-color: #e1306c; }
.chip-messenger.active { background: #0084ff; border-color: #0084ff; }

@media (max-width: 600px) {
  .conv-header { padding: 18px 16px 12px; }
  .conv-filters { padding: 0 16px 12px; }
  .view-toggle button { padding: 7px 12px; }
}
</style>
