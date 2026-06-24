<template>
  <!-- Global date filter used across every portal tab (QA #10). Emits an
       update with { period, dateFrom, dateTo } whenever the selection changes.
       period is one of: all | today | 7d | 30d | 90d | custom

       Rendered as a compact dropdown: a calendar trigger showing the active
       range, opening a popover with the presets + a custom range picker. -->
  <div class="date-filter">
    <button class="df-trigger" :class="{ open }" @click="open = !open" type="button">
      <svg class="df-cal" width="15" height="15" viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="17" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M3 9h18M8 2v4M16 2v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      <span class="df-label">{{ currentLabel }}</span>
      <svg class="df-caret" width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>

    <div v-if="open" class="df-backdrop" @click="open = false"></div>
    <div v-if="open" class="df-pop">
      <div class="df-presets">
        <button v-for="p in presets" :key="p.value"
                :class="{ active: period === p.value && !customActive }"
                @click="selectPreset(p.value)" type="button">
          {{ p.label }}
        </button>
      </div>
      <div class="df-pop-divider"></div>
      <div class="df-range" :class="{ active: customActive }">
        <span class="df-range-label">Custom range</span>
        <div class="df-range-inputs">
          <input type="date" v-model="dateFrom" :max="dateTo || today" @change="applyCustom" aria-label="From date" />
          <span class="df-dash">–</span>
          <input type="date" v-model="dateTo" :min="dateFrom" :max="today" @change="applyCustom" aria-label="To date" />
          <button v-if="customActive" class="df-clear" @click="clearCustom" title="Clear range" type="button">&times;</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '30d' }, // initial preset
})
const emit = defineEmits(['update:modelValue', 'change'])

const presets = [
  { label: 'All Time', value: 'all' },
  { label: 'Today', value: 'today' },
  { label: 'This Week', value: '7d' },
  { label: 'This Month', value: '30d' },
  { label: '90 Days', value: '90d' },
]

const period = ref(props.modelValue || '30d')
const dateFrom = ref('')
const dateTo = ref('')
const today = new Date().toISOString().slice(0, 10)
const open = ref(false)

const customActive = computed(() => !!(dateFrom.value || dateTo.value))

function fmtShort(s) {
  try {
    return new Date(s + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch { return s }
}

const currentLabel = computed(() => {
  if (customActive.value) {
    if (dateFrom.value && dateTo.value) return `${fmtShort(dateFrom.value)} – ${fmtShort(dateTo.value)}`
    if (dateFrom.value) return `From ${fmtShort(dateFrom.value)}`
    return `Until ${fmtShort(dateTo.value)}`
  }
  const p = presets.find(x => x.value === period.value)
  return p ? p.label : 'All Time'
})

function emitChange() {
  emit('update:modelValue', period.value)
  emit('change', {
    period: customActive.value ? 'custom' : period.value,
    dateFrom: dateFrom.value || null,
    dateTo: dateTo.value || null,
  })
}

function selectPreset(v) {
  period.value = v
  dateFrom.value = ''
  dateTo.value = ''
  open.value = false
  emitChange()
}

function applyCustom() {
  if (dateFrom.value && dateTo.value) { emitChange(); open.value = false }
}

function clearCustom() {
  dateFrom.value = ''
  dateTo.value = ''
  emitChange()
}
</script>

<style scoped>
.date-filter { position: relative; display: inline-flex; }

/* ── Trigger button ─────────────────────────────────────────────────────── */
.df-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 10px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all .15s; font-family: inherit; white-space: nowrap;
}
.df-trigger:hover { border-color: #6366f1; color: var(--cf-text-primary); }
.df-trigger.open { border-color: #6366f1; color: var(--cf-text-primary); }
.df-cal { color: var(--cf-text-muted); flex-shrink: 0; }
.df-label { min-width: 0; }
.df-caret { color: var(--cf-text-muted); flex-shrink: 0; transition: transform .2s; }
.df-trigger.open .df-caret { transform: rotate(90deg); }

/* ── Popover ────────────────────────────────────────────────────────────── */
.df-backdrop { position: fixed; inset: 0; z-index: 40; }
.df-pop {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: 41;
  width: 300px; padding: 12px;
  background: var(--cf-bg-surface, #0f172a);
  border: 1px solid var(--cf-border-default); border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0,0,0,0.35);
}
.df-presets { display: flex; flex-wrap: wrap; gap: 6px; }
.df-presets button {
  background: var(--cf-bg-input, rgba(148,163,184,0.08)); border: 1px solid var(--cf-border-default);
  border-radius: 8px; padding: 7px 12px; font-size: 12.5px; font-weight: 600;
  color: var(--cf-text-secondary); cursor: pointer; transition: all .15s; font-family: inherit;
  white-space: nowrap;
}
.df-presets button:hover { border-color: #6366f1; }
.df-presets button.active { background: #6366f1; border-color: #6366f1; color: #fff; }

.df-pop-divider { height: 1px; background: var(--cf-border-subtle, rgba(148,163,184,0.15)); margin: 12px 0; }

.df-range { display: flex; flex-direction: column; gap: 8px; }
.df-range-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--cf-text-muted);
}
.df-range-inputs {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px; border-radius: 9px;
  background: var(--cf-bg-input, rgba(148,163,184,0.06)); border: 1px solid var(--cf-border-default);
}
.df-range.active .df-range-inputs { border-color: #6366f1; }
.df-range input[type="date"] {
  background: none; border: none; color: var(--cf-text-secondary);
  font-size: 12.5px; font-family: inherit; cursor: pointer; color-scheme: dark;
  flex: 1; min-width: 0;
}
.df-dash { color: var(--cf-text-muted); }
.df-clear {
  background: none; border: none; color: var(--cf-text-muted);
  font-size: 18px; line-height: 1; cursor: pointer; padding: 0 2px;
}
.df-clear:hover { color: #ef4444; }

[data-theme="light"] .df-range input[type="date"] { color-scheme: light; }

@media (max-width: 640px) {
  .df-pop { width: 280px; }
}
</style>
