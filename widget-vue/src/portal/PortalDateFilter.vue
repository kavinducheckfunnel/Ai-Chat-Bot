<template>
  <!-- Global date filter used across every portal tab (QA #10). Emits an
       update with { period, dateFrom, dateTo } whenever the selection changes.
       period is one of: all | today | 7d | 30d | 90d | custom -->
  <div class="date-filter">
    <div class="df-presets">
      <button v-for="p in presets" :key="p.value"
              :class="{ active: period === p.value && !customActive }"
              @click="selectPreset(p.value)">
        {{ p.label }}
      </button>
    </div>
    <div class="df-range" :class="{ active: customActive }">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="17" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M3 9h18M8 2v4M16 2v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      <input type="date" v-model="dateFrom" :max="dateTo || today" @change="applyCustom" aria-label="From date" />
      <span class="df-dash">–</span>
      <input type="date" v-model="dateTo" :min="dateFrom" :max="today" @change="applyCustom" aria-label="To date" />
      <button v-if="customActive" class="df-clear" @click="clearCustom" title="Clear range">&times;</button>
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

const customActive = computed(() => !!(dateFrom.value || dateTo.value))

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
  emitChange()
}

function applyCustom() {
  if (dateFrom.value && dateTo.value) emitChange()
}

function clearCustom() {
  dateFrom.value = ''
  dateTo.value = ''
  emitChange()
}
</script>

<style scoped>
.date-filter { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.df-presets {
  display: flex; gap: 3px; padding: 3px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  border-radius: 10px;
}
.df-presets button {
  background: none; border: none; border-radius: 7px;
  padding: 6px 12px; font-size: 12.5px; font-weight: 600;
  color: var(--cf-text-muted); cursor: pointer; transition: all .15s; font-family: inherit;
  white-space: nowrap;
}
.df-presets button:hover { color: var(--cf-text-secondary); }
.df-presets button.active { background: var(--cf-bg-item-active, rgba(99,102,241,.15)); color: #a5b4fc; }

.df-range {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: 10px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-muted); font-size: 12.5px;
}
.df-range.active { border-color: #6366f1; color: var(--cf-text-secondary); }
.df-range input[type="date"] {
  background: none; border: none; color: var(--cf-text-secondary);
  font-size: 12.5px; font-family: inherit; cursor: pointer; color-scheme: dark;
}
.df-dash { color: var(--cf-text-muted); }
.df-clear {
  background: none; border: none; color: var(--cf-text-muted);
  font-size: 18px; line-height: 1; cursor: pointer; padding: 0 2px;
}
.df-clear:hover { color: #ef4444; }

[data-theme="light"] .df-range input[type="date"] { color-scheme: light; }

@media (max-width: 640px) {
  .df-presets button { padding: 6px 9px; }
}
</style>
