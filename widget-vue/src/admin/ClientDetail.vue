<template>
  <div class="detail-page">
    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading client...</p>
    </div>

    <template v-else-if="client">
      <!-- Header -->
      <div class="page-header">
        <div class="header-left">
          <button class="back-btn" @click="$router.push('/admin/clients')">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M19 12H5M12 5l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
          <div class="client-avatar" :style="{ background: client.chatbot_color || '#6366F1' }">
            {{ client.name.slice(0, 2).toUpperCase() }}
          </div>
          <div>
            <h1 class="page-title">{{ client.name }}</h1>
            <a v-if="client.domain_url" :href="client.domain_url" target="_blank" class="client-url">
              {{ client.domain_url }}
            </a>
          </div>
        </div>
        <div class="header-actions">
          <span class="ingestion-badge" :class="'ing-' + (client.ingestion_status || 'pending').toLowerCase()">
            {{ client.ingestion_status || 'PENDING' }}
          </span>
          <button class="scrape-btn" @click="triggerScrape" :disabled="scraping || !client.domain_url">
            <div v-if="scraping" class="mini-spinner white"></div>
            <svg v-else width="15" height="15" fill="none" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            {{ scraping ? 'Syncing...' : 'Sync Now' }}
          </button>
        </div>
      </div>

      <!-- Scrape Progress Bar -->
      <div v-if="scrapeProgress" class="scrape-progress-wrap">
        <div class="scrape-progress-header">
          <span class="scrape-phase-label">
            <span class="scrape-pulse-dot"></span>
            {{ scrapeProgress.phase === 'crawling' ? 'Crawling pages...' : 'Generating embeddings...' }}
          </span>
          <span v-if="scrapeProgress.total > 0" class="scrape-count-label">
            {{ scrapeProgress.done }} / {{ scrapeProgress.total }} chunks
          </span>
          <span v-else-if="scrapeProgress.phase === 'crawling'" class="scrape-count-label">
            Discovering pages...
          </span>
        </div>
        <div class="scrape-track">
          <div
            class="scrape-fill"
            :class="{ 'scrape-fill--indeterminate': scrapeProgress.total === 0 }"
            :style="scrapeProgress.total > 0 ? { width: Math.round(scrapeProgress.done / scrapeProgress.total * 100) + '%' } : {}"
          ></div>
        </div>
        <p class="scrape-hint">This may take a few minutes depending on the size of your website.</p>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button v-for="tab in tabs" :key="tab.id" class="tab" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
          {{ tab.label }}
        </button>
      </div>

      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'" class="tab-content">
        <div class="overview-stats">
          <div class="ov-stat">
            <p class="ov-label">Total Sessions</p>
            <p class="ov-value">{{ analytics?.total_sessions ?? '—' }}</p>
          </div>
          <div class="ov-stat">
            <p class="ov-label">Hot Leads</p>
            <p class="ov-value hot">{{ analytics?.hot_sessions ?? '—' }}</p>
          </div>
          <div class="ov-stat">
            <p class="ov-label">Avg. Intent</p>
            <p class="ov-value">{{ analytics?.avg_intent ?? '—' }}%</p>
          </div>
          <div class="ov-stat">
            <p class="ov-label">Pages Ingested</p>
            <p class="ov-value">{{ analytics?.pages_ingested ?? '—' }}</p>
          </div>
        </div>

        <!-- Funnel -->
        <div v-if="analytics?.funnel" class="funnel-section">
          <h3 class="section-title">Conversion Funnel</h3>
          <div class="funnel">
            <div v-for="stage in funnelStages" :key="stage.key" class="funnel-row">
              <span class="funnel-label">{{ stage.label }}</span>
              <div class="funnel-bar-wrap">
                <div class="funnel-bar" :class="stage.color" :style="{ width: funnelWidth(stage.key) }"></div>
              </div>
              <span class="funnel-count">{{ analytics.funnel[stage.key] || 0 }}</span>
            </div>
          </div>
        </div>

        <!-- Embed Code -->
        <div class="embed-section">
          <div class="embed-header">
            <div>
              <h3 class="section-title" style="margin-bottom:4px;">WordPress Installation</h3>
              <p class="embed-sub" style="margin-bottom:0;">Choose the method that works best for your site.</p>
            </div>
          </div>

          <!-- Method tabs -->
          <div class="method-tabs">
            <button class="method-tab" :class="{ active: embedMethod === 'plugin' }" @click="embedMethod = 'plugin'">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Plugin (Recommended)
            </button>
            <button class="method-tab" :class="{ active: embedMethod === 'php' }" @click="embedMethod = 'php'">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><polyline points="8 6 2 12 8 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              functions.php
            </button>
          </div>

          <!-- Plugin method -->
          <div v-if="embedMethod === 'plugin'" class="method-content">
            <ol class="install-steps">
              <li>In your WordPress dashboard, go to <strong>Plugins → Add New</strong> and search for <strong>"WPCode"</strong> (or "Insert Headers and Footers"). Install and activate it.</li>
              <li>Go to <strong>Code Snippets → Header &amp; Footer</strong> in your WordPress menu.</li>
              <li>Paste the snippet below into the <strong>Footer</strong> section and click <strong>Save Changes</strong>.</li>
            </ol>
            <div class="embed-code-wrap">
              <code class="embed-code">{{ embedCode }}</code>
              <button class="copy-btn" @click="copyCode(embedCode, 'plugin')">
                <svg v-if="copiedKey !== 'plugin'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" stroke-width="2"/></svg>
                <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" stroke="#22C55E" stroke-width="2.5" stroke-linecap="round"/></svg>
                {{ copiedKey === 'plugin' ? 'Copied!' : 'Copy' }}
              </button>
            </div>
          </div>

          <!-- functions.php method -->
          <div v-if="embedMethod === 'php'" class="method-content">
            <ol class="install-steps">
              <li>In your WordPress dashboard, go to <strong>Appearance → Theme File Editor</strong>.</li>
              <li>Select <strong>functions.php</strong> from the file list on the right.</li>
              <li>Paste the snippet below at the bottom of the file and click <strong>Update File</strong>.</li>
            </ol>
            <div class="embed-code-wrap">
              <code class="embed-code embed-code--php">{{ phpSnippet }}</code>
              <button class="copy-btn" @click="copyCode(phpSnippet, 'php')">
                <svg v-if="copiedKey !== 'php'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" stroke-width="2"/></svg>
                <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" stroke="#22C55E" stroke-width="2.5" stroke-linecap="round"/></svg>
                {{ copiedKey === 'php' ? 'Copied!' : 'Copy' }}
              </button>
            </div>
          </div>

          <!-- Webhook -->
          <div class="webhook-note">
            <p class="note-title">WordPress Webhook URL (WooCommerce auto-sync):</p>
            <code class="note-code">{{ webhookUrl }}</code>
            <p class="note-sub">In WooCommerce → Settings → Advanced → Webhooks — add a "Product Updated" webhook pointing to this URL to auto-sync content changes.</p>
          </div>
        </div>
      </div>

      <!-- Analytics Tab -->
      <div v-if="activeTab === 'analytics'" class="tab-content">
        <div v-if="!analytics" class="loading-state"><div class="loader"></div></div>
        <template v-else>

          <!-- Top stat row -->
          <div class="an-stats-row">
            <div class="an-stat">
              <p class="an-label">Total Sessions</p>
              <p class="an-value">{{ analytics.total_sessions ?? 0 }}</p>
            </div>
            <div class="an-stat">
              <p class="an-label">Avg Heat Score</p>
              <p class="an-value" :class="analytics.avg_heat_score >= 70 ? 'hot' : analytics.avg_heat_score >= 40 ? 'warm' : ''">
                {{ analytics.avg_heat_score ?? 0 }}%
              </p>
            </div>
            <div class="an-stat">
              <p class="an-label">Leads Captured</p>
              <p class="an-value" style="color:#6366F1">{{ analytics.leads_captured ?? 0 }}</p>
            </div>
            <div class="an-stat">
              <p class="an-label">Hot Sessions</p>
              <p class="an-value hot">{{ analytics.hot_sessions ?? 0 }}</p>
            </div>
          </div>

          <!-- Heat Distribution + Avg EMA Gauges -->
          <div class="an-two-col">
            <div class="an-card">
              <h3 class="an-card-title">Heat Distribution</h3>
              <div class="an-heat-bar">
                <div class="an-hd-cold" :style="{ flex: analytics.heat_distribution?.cold || 0.01 }"></div>
                <div class="an-hd-warm" :style="{ flex: analytics.heat_distribution?.warm || 0.01 }"></div>
                <div class="an-hd-hot"  :style="{ flex: analytics.heat_distribution?.hot  || 0.01 }"></div>
              </div>
              <div class="an-heat-legend">
                <div class="an-hl-item"><span class="an-dot cold"></span><span>Cold</span><strong>{{ analytics.heat_distribution?.cold ?? 0 }}</strong></div>
                <div class="an-hl-item"><span class="an-dot warm"></span><span>Warm</span><strong>{{ analytics.heat_distribution?.warm ?? 0 }}</strong></div>
                <div class="an-hl-item"><span class="an-dot hot"></span><span>Hot</span><strong>{{ analytics.heat_distribution?.hot ?? 0 }}</strong></div>
              </div>
            </div>

            <div class="an-card">
              <h3 class="an-card-title">Avg Engagement Scores</h3>
              <div class="an-gauges">
                <div class="an-gauge-row">
                  <span class="an-gauge-label">Intent</span>
                  <div class="an-gauge-bar"><div class="an-gauge-fill intent" :style="{ width: (analytics.avg_intent || 0) + '%' }"></div></div>
                  <span class="an-gauge-val">{{ analytics.avg_intent ?? 0 }}%</span>
                </div>
                <div class="an-gauge-row">
                  <span class="an-gauge-label">Budget</span>
                  <div class="an-gauge-bar"><div class="an-gauge-fill budget" :style="{ width: (analytics.avg_budget || 0) + '%' }"></div></div>
                  <span class="an-gauge-val">{{ analytics.avg_budget ?? 0 }}%</span>
                </div>
                <div class="an-gauge-row">
                  <span class="an-gauge-label">Urgency</span>
                  <div class="an-gauge-bar"><div class="an-gauge-fill urgency" :style="{ width: (analytics.avg_urgency || 0) + '%' }"></div></div>
                  <span class="an-gauge-val">{{ analytics.avg_urgency ?? 0 }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Daily Trend Sparkline -->
          <div class="an-card an-full">
            <h3 class="an-card-title">Sessions — Last 14 Days</h3>
            <div class="an-spark-wrap">
              <svg v-if="analytics.daily_trend?.length" class="an-spark" viewBox="0 0 340 60" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="anGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#6366F1" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="#6366F1" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <polyline :points="analyticsSparklineArea" fill="url(#anGrad)" stroke="none"/>
                <polyline :points="analyticsSparklinePoints" fill="none" stroke="#6366F1" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
              </svg>
              <p v-else class="an-no-data">No sessions in the last 14 days</p>
            </div>
            <div class="an-spark-labels" v-if="analytics.daily_trend?.length">
              <span>{{ analytics.daily_trend[0].date }}</span>
              <span>{{ analytics.daily_trend[analytics.daily_trend.length - 1].date }}</span>
            </div>
          </div>

          <!-- Kanban Breakdown + Analytics Events -->
          <div class="an-two-col">
            <div class="an-card">
              <h3 class="an-card-title">Kanban Breakdown</h3>
              <div class="an-kanban-list">
                <div v-for="(col, key) in kanbanCols" :key="key" class="an-kanban-row">
                  <span class="an-kanban-dot" :style="{ background: col.color }"></span>
                  <span class="an-kanban-label">{{ col.label }}</span>
                  <span class="an-kanban-count">{{ analytics.kanban_breakdown?.[key] ?? 0 }}</span>
                </div>
              </div>
            </div>

            <div class="an-card">
              <h3 class="an-card-title">Behavioral Events</h3>
              <div class="an-events-list">
                <div class="an-event-row">
                  <div class="an-event-icon" style="background:rgba(99,102,241,0.1);color:#6366F1">
                    <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
                  </div>
                  <div><p class="an-event-label">Page Views</p><p class="an-event-val">{{ analytics.analytics_events?.page_views ?? 0 }}</p></div>
                </div>
                <div class="an-event-row">
                  <div class="an-event-icon" style="background:rgba(249,115,22,0.1);color:#F97316">
                    <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  </div>
                  <div><p class="an-event-label">Exit Intent Triggers</p><p class="an-event-val">{{ analytics.analytics_events?.exit_intent_count ?? 0 }}</p></div>
                </div>
                <div class="an-event-row">
                  <div class="an-event-icon" style="background:rgba(34,197,94,0.1);color:#22C55E">
                    <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/><path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  </div>
                  <div><p class="an-event-label">Pricing Page Visits</p><p class="an-event-val">{{ analytics.analytics_events?.pricing_page_visits ?? 0 }}</p></div>
                </div>
              </div>
            </div>
          </div>

        </template>
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="tab-content">
        <div class="settings-card">
          <h3 class="settings-section">Chatbot Branding</h3>
          <div class="settings-grid">
            <div class="field">
              <label>Display Name</label>
              <input v-model="settingsForm.chatbot_name" type="text" placeholder="AI Assistant" />
            </div>
            <div class="field">
              <label>Theme Color</label>
              <div class="color-field">
                <input type="color" v-model="settingsForm.chatbot_color" class="color-picker" />
                <input v-model="settingsForm.chatbot_color" type="text" class="color-text" />
              </div>
            </div>
            <div class="field full">
              <label>Logo URL (optional)</label>
              <input v-model="settingsForm.chatbot_logo_url" type="url" placeholder="https://..." />
            </div>
          </div>

          <h3 class="settings-section" style="margin-top: 24px;">FOMO Engine</h3>
          <div class="settings-grid">
            <div class="field full">
              <label>Discount Code</label>
              <input v-model="settingsForm.discount_code" type="text" placeholder="SAVE20" />
              <p class="field-hint">Sent to high-intent visitors (heat score ≥ 75)</p>
            </div>
            <div class="field full">
              <label>CTA Message</label>
              <input v-model="settingsForm.cta_message" type="text" />
            </div>
            <div class="field">
              <label>Countdown (seconds)</label>
              <input v-model="settingsForm.fomo_countdown_seconds" type="number" min="60" max="3600" />
            </div>
          </div>

          <div v-if="saveError" class="form-error">{{ saveError }}</div>
          <div v-if="saveSuccess" class="form-success">Settings saved!</div>

          <button class="save-btn" @click="saveSettings" :disabled="saving">
            <div v-if="saving" class="mini-spinner white"></div>
            <span v-else>Save Changes</span>
          </button>
        </div>
      </div>

      <!-- Sessions Tab -->
      <div v-if="activeTab === 'sessions'" class="tab-content">

        <!-- Filter bar -->
        <div class="session-filters">
          <input
            v-model="sessionFilters.q"
            class="sf-input sf-search"
            placeholder="Search email..."
          />
          <select v-model="sessionFilters.state" class="sf-select">
            <option value="">All states</option>
            <option value="RESEARCH">Research</option>
            <option value="EVALUATION">Evaluation</option>
            <option value="OBJECTION">Objection</option>
            <option value="RECOVERY">Recovery</option>
            <option value="READY_TO_BUY">Ready to Buy</option>
          </select>
          <input v-model="sessionFilters.date_from" type="date" class="sf-input sf-date" title="From date" />
          <input v-model="sessionFilters.date_to"   type="date" class="sf-input sf-date" title="To date" />
          <input v-model="sessionFilters.min_heat" type="number" min="0" max="100" class="sf-input sf-heat" placeholder="Min heat" />
          <input v-model="sessionFilters.max_heat" type="number" min="0" max="100" class="sf-input sf-heat" placeholder="Max heat" />
          <label class="sf-toggle">
            <input v-model="sessionFilters.has_lead" type="checkbox" />
            <span>Has lead</span>
          </label>
        </div>

        <div v-if="loadingSessions" class="loading-state">
          <div class="loader"></div>
        </div>
        <div v-else-if="!sessions.length" class="empty-state">
          <p>No sessions match the current filters.</p>
        </div>
        <div v-else class="sessions-table-wrap">
          <table class="sessions-table">
            <thead>
              <tr>
                <th>Visitor</th>
                <th>Heat</th>
                <th>State</th>
                <th>Messages</th>
                <th>Last Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in sessions" :key="s.session_id">
                <td class="visitor-cell">
                  <span class="visitor-id">{{ s.visitor_id?.slice(0, 16) }}...</span>
                  <span v-if="s.lead_email" class="lead-email">{{ s.lead_email }}</span>
                </td>
                <td>
                  <div class="heat-cell">
                    <span class="heat-val" :class="heatClass(s.heat_score)">{{ s.heat_score }}%</span>
                    <div class="mini-heat-bar">
                      <div :style="{ width: s.heat_score + '%', background: heatColor(s.heat_score) }"></div>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="state-badge" :class="stateClass(s.conversation_state)">
                    {{ s.conversation_state.replace('_', ' ') }}
                  </span>
                </td>
                <td class="msgs-cell">{{ s.message_count }}</td>
                <td class="time-cell">{{ timeAgo(s.updated_at) }}</td>
                <td>
                  <button class="view-session-btn" @click="viewSession(s)">View</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Session Chat Modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>Chat History</h3>
            <p class="modal-sub">{{ selectedSession.visitor_id }}</p>
          </div>
          <button class="modal-close" @click="selectedSession = null">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div v-if="loadingSession" class="modal-loading"><div class="loader"></div></div>
        <div v-else class="chat-history">
          <div v-for="(msg, i) in sessionDetail?.chat_history || []" :key="i" class="chat-msg" :class="msg.role === 'user' ? 'user-msg' : 'ai-msg'">
            <span class="msg-role">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
            <p class="msg-text">{{ msg.message || msg.content }}</p>
          </div>
          <p v-if="!sessionDetail?.chat_history?.length" class="no-history">No chat history.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'

const route = useRoute()
const api = useAdminApi()

const client = ref(null)
const analytics = ref(null)
const sessions = ref([])
const loading = ref(true)
const loadingSessions = ref(false)
const scraping = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const activeTab = ref('overview')
const embedMethod = ref('plugin')
const copiedKey = ref('')
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)
const scrapeProgress = ref(null)
let _scrapePoller = null

const sessionFilters = reactive({
  state: '',
  date_from: '',
  date_to: '',
  min_heat: '',
  max_heat: '',
  has_lead: false,
  q: '',
})

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'sessions', label: 'Sessions' },
  { id: 'settings', label: 'Settings' },
]

const funnelStages = [
  { key: 'RESEARCH', label: 'Research', color: 'bar-blue' },
  { key: 'EVALUATION', label: 'Evaluation', color: 'bar-yellow' },
  { key: 'OBJECTION', label: 'Objection', color: 'bar-red' },
  { key: 'RECOVERY', label: 'Recovery', color: 'bar-orange' },
  { key: 'READY_TO_BUY', label: 'Ready to Buy', color: 'bar-green' },
]

const kanbanCols = {
  NEW:          { label: 'New',          color: '#94A3B8' },
  CONTACTED:    { label: 'Contacted',    color: '#3B82F6' },
  QUALIFIED:    { label: 'Qualified',    color: '#F97316' },
  CONVERTED:    { label: 'Converted',    color: '#22C55E' },
  LOST:         { label: 'Lost',         color: '#EF4444' },
}

const settingsForm = ref({
  chatbot_name: '',
  chatbot_color: '#3B82F6',
  chatbot_logo_url: '',
  discount_code: '',
  cta_message: '',
  fomo_countdown_seconds: 600,
})

const embedCode = computed(() =>
  client.value
    ? `<script src="${WIDGET_URL}?client_id=${client.value.id}"><\/script>`
    : ''
)

const phpSnippet = computed(() =>
  client.value
    ? `<?php\nfunction checkfunnel_widget() {\n    echo '<script src="${WIDGET_URL}?client_id=${client.value.id}"><\\/script>';\n}\nadd_action( 'wp_footer', 'checkfunnel_widget' );`
    : ''
)

const webhookUrl = computed(() =>
  client.value
    ? `${WIDGET_URL.replace('/widget/widget.js', '')}/api/scraper/webhooks/wordpress/${client.value.id}/`
    : ''
)

function funnelWidth(key) {
  if (!analytics.value?.funnel) return '0%'
  const max = Math.max(...Object.values(analytics.value.funnel), 1)
  return ((analytics.value.funnel[key] || 0) / max * 100) + '%'
}

async function loadClient() {
  loading.value = true
  try {
    const [clientData, analyticsData] = await Promise.all([
      api.getClient(route.params.id),
      api.getClientAnalytics(route.params.id),
    ])
    client.value = clientData
    analytics.value = analyticsData
    settingsForm.value = {
      chatbot_name: clientData.chatbot_name || 'AI Assistant',
      chatbot_color: clientData.chatbot_color || '#3B82F6',
      chatbot_logo_url: clientData.chatbot_logo_url || '',
      discount_code: clientData.discount_code || '',
      cta_message: clientData.cta_message || '',
      fomo_countdown_seconds: clientData.fomo_countdown_seconds || 600,
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadSessions() {
  loadingSessions.value = true
  try {
    const params = {}
    if (sessionFilters.state)     params.state      = sessionFilters.state
    if (sessionFilters.date_from) params.date_from  = sessionFilters.date_from
    if (sessionFilters.date_to)   params.date_to    = sessionFilters.date_to
    if (sessionFilters.min_heat)  params.min_heat   = sessionFilters.min_heat
    if (sessionFilters.max_heat)  params.max_heat   = sessionFilters.max_heat
    if (sessionFilters.has_lead)  params.has_lead   = 'true'
    if (sessionFilters.q)         params.q          = sessionFilters.q
    sessions.value = await api.getClientSessions(route.params.id, params) || []
  } catch {}
  loadingSessions.value = false
}

let _filterDebounce = null
function onFilterChange() {
  clearTimeout(_filterDebounce)
  _filterDebounce = setTimeout(loadSessions, 300)
}

async function triggerScrape() {
  scraping.value = true
  try {
    await api.triggerScrape(route.params.id)
    client.value.ingestion_status = 'RUNNING'
    scrapeProgress.value = { phase: 'crawling', done: 0, total: 0 }
    _startProgressPolling()
  } catch (e) {
    alert(e.message || 'Scrape failed.')
  } finally {
    scraping.value = false
  }
}

function _startProgressPolling() {
  clearInterval(_scrapePoller)
  _scrapePoller = setInterval(async () => {
    try {
      const data = await api.getScrapeProgress(route.params.id)
      if (data.phase) {
        scrapeProgress.value = { phase: data.phase, done: data.done, total: data.total }
      }
      client.value.ingestion_status = data.status
      if (data.status === 'DONE' || data.status === 'FAILED') {
        clearInterval(_scrapePoller)
        _scrapePoller = null
        scrapeProgress.value = null
        client.value.total_pages_ingested = data.pages_ingested
        if (analytics.value) analytics.value.pages_ingested = data.pages_ingested
      }
    } catch {
      clearInterval(_scrapePoller)
      _scrapePoller = null
      scrapeProgress.value = null
    }
  }, 2000)
}

async function saveSettings() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    const updated = await api.updateClient(route.params.id, settingsForm.value)
    Object.assign(client.value, updated)
    saveSuccess.value = true
    setTimeout(() => saveSuccess.value = false, 3000)
  } catch (e) {
    saveError.value = e.message || 'Failed to save.'
  } finally {
    saving.value = false
  }
}

async function viewSession(session) {
  selectedSession.value = session
  sessionDetail.value = null
  loadingSession.value = true
  try {
    sessionDetail.value = await api.getSession(session.session_id)
  } catch {}
  loadingSession.value = false
}

async function copyCode(text, key) {
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key
    setTimeout(() => copiedKey.value = '', 2000)
  } catch {}
}

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg, #EF4444, #F97316)'
  if (score >= 40) return 'linear-gradient(90deg, #F97316, #EAB308)'
  return 'linear-gradient(90deg, #3B82F6, #06B6D4)'
}

function stateClass(state) {
  const map = { RESEARCH: 'state-blue', EVALUATION: 'state-yellow', OBJECTION: 'state-red', RECOVERY: 'state-orange', READY_TO_BUY: 'state-green' }
  return map[state] || 'state-blue'
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

// Sparkline computed properties for the analytics tab
const analyticsSparklinePoints = computed(() => {
  const trend = analytics.value?.daily_trend
  if (!trend || trend.length < 2) return ''
  const W = 340, H = 60, PAD = 4
  const maxVal = Math.max(...trend.map(d => d.count), 1)
  return trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / maxVal) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const analyticsSparklineArea = computed(() => {
  const trend = analytics.value?.daily_trend
  if (!trend || trend.length < 2) return ''
  const W = 340, H = 60, PAD = 4
  const maxVal = Math.max(...trend.map(d => d.count), 1)
  const pts = trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / maxVal) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `${pts[0].split(',')[0]},${H} ${pts.join(' ')} ${pts[pts.length - 1].split(',')[0]},${H}`
})

onMounted(loadClient)
watch(activeTab, (tab) => { if (tab === 'sessions') loadSessions() })
watch(sessionFilters, onFilterChange)
</script>

<style scoped>
/* ── Session filter bar ──────────────────────────────────────────────── */
.session-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}

.sf-input, .sf-select {
  height: 34px;
  padding: 0 10px;
  background: #1E293B;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #CBD5E1;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.sf-input:focus, .sf-select:focus { border-color: #6366F1; }
.sf-select { padding-right: 28px; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='none' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6' stroke='%2364748B' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 9px center; }
.sf-search { width: 160px; }
.sf-date   { width: 130px; color-scheme: dark; }
.sf-heat   { width: 90px; }

.sf-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #64748B;
  user-select: none;
}
.sf-toggle input { accent-color: #6366F1; cursor: pointer; }
.sf-toggle:hover span { color: #CBD5E1; }

.detail-page { max-width: 1000px; }

.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }

.back-btn {
  background: white; border: 1px solid #E2E8F0; border-radius: 9px;
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #64748B; transition: all 0.15s;
}
.back-btn:hover { background: #F8FAFC; color: #0F172A; }

.client-avatar {
  width: 44px; height: 44px; border-radius: 11px;
  color: white; font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

.page-title { font-size: 22px; font-weight: 700; color: #0F172A; }
.client-url { font-size: 13px; color: #6366F1; text-decoration: none; }
.client-url:hover { text-decoration: underline; }

.header-actions { display: flex; align-items: center; gap: 10px; }

.ingestion-badge {
  font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.ing-pending { background: #F1F5F9; color: #64748B; }
.ing-running { background: #EFF6FF; color: #2563EB; }
.ing-done { background: #F0FDF4; color: #15803D; }
.ing-failed { background: #FEF2F2; color: #B91C1C; }

.scrape-btn {
  display: flex; align-items: center; gap: 7px;
  background: #0F172A; color: white; border: none; border-radius: 9px;
  padding: 9px 16px; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.scrape-btn:hover:not(:disabled) { opacity: 0.85; }
.scrape-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Tabs */
.tabs { display: flex; gap: 0; border-bottom: 1px solid #F1F5F9; margin-bottom: 24px; }

.tab {
  background: none; border: none; cursor: pointer; font-family: inherit;
  padding: 10px 18px; font-size: 14px; font-weight: 500; color: #64748B;
  border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.15s;
}
.tab:hover { color: #0F172A; }
.tab.active { color: #6366F1; border-bottom-color: #6366F1; }

.tab-content { padding-top: 4px; }

/* Overview */
.overview-stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px;
}

.ov-stat {
  background: white; border: 1px solid #F1F5F9; border-radius: 12px; padding: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.ov-label { font-size: 12px; color: #94A3B8; font-weight: 500; margin-bottom: 4px; }
.ov-value { font-size: 28px; font-weight: 700; color: #0F172A; letter-spacing: -0.5px; }
.ov-value.hot { color: #EF4444; }

/* Funnel */
.funnel-section, .embed-section {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px; padding: 20px;
  margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.section-title { font-size: 15px; font-weight: 600; color: #0F172A; margin-bottom: 16px; }

.funnel { display: flex; flex-direction: column; gap: 12px; }
.funnel-row { display: flex; align-items: center; gap: 12px; }
.funnel-label { font-size: 13px; color: #475569; width: 110px; flex-shrink: 0; }
.funnel-bar-wrap { flex: 1; background: #F1F5F9; border-radius: 4px; height: 8px; overflow: hidden; }
.funnel-bar { height: 100%; border-radius: 4px; transition: width 0.6s; min-width: 4px; }
.bar-blue { background: #3B82F6; }
.bar-yellow { background: #EAB308; }
.bar-red { background: #EF4444; }
.bar-orange { background: #F97316; }
.bar-green { background: #22C55E; }
.funnel-count { font-size: 13px; font-weight: 600; color: #0F172A; width: 30px; text-align: right; }

/* Embed */
.embed-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.embed-sub { font-size: 13px; color: #64748B; margin-bottom: 12px; }
.embed-sub code { background: #F1F5F9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }

.method-tabs { display: flex; gap: 6px; margin-bottom: 16px; }
.method-tab {
  display: flex; align-items: center; gap: 6px;
  background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
  padding: 7px 14px; font-size: 13px; font-weight: 500; color: #64748B;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.method-tab:hover { background: #EEF2FF; border-color: #C7D2FE; color: #4338CA; }
.method-tab.active { background: #EEF2FF; border-color: #6366F1; color: #4338CA; font-weight: 600; }

.method-content { margin-bottom: 16px; }

.install-steps {
  margin: 0 0 14px 0; padding-left: 20px;
  display: flex; flex-direction: column; gap: 8px;
}
.install-steps li { font-size: 13px; color: #475569; line-height: 1.6; }
.install-steps li strong { color: #0F172A; }

.embed-code--php { white-space: pre; }

.embed-code-wrap {
  background: #0F172A; border-radius: 10px; padding: 14px 16px;
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  margin-bottom: 16px;
}
.embed-code { font-size: 12px; color: #A5B4FC; font-family: monospace; line-height: 1.5; flex: 1; word-break: break-all; }

.copy-btn {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.1);
  color: #CBD5E1; border-radius: 7px; padding: 5px 10px;
  font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
  transition: all 0.15s; flex-shrink: 0;
}
.copy-btn:hover { background: rgba(255,255,255,0.15); }

.webhook-note {
  background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 14px;
}
.note-title { font-size: 12px; font-weight: 600; color: #15803D; margin-bottom: 6px; }
.note-code { display: block; font-family: monospace; font-size: 12px; color: #065F46; background: rgba(0,0,0,0.05); padding: 6px 10px; border-radius: 6px; margin-bottom: 8px; word-break: break-all; }
.note-sub { font-size: 11px; color: #94A3B8; }

/* Settings */
.settings-card {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.settings-section { font-size: 15px; font-weight: 600; color: #0F172A; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9; }

.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.field.full { grid-column: 1 / -1; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 500; color: #475569; }
.field input {
  border: 1px solid #E2E8F0; border-radius: 9px; padding: 10px 12px;
  font-size: 14px; color: #0F172A; outline: none; font-family: inherit;
  transition: border-color 0.15s;
}
.field input:focus { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.08); }
.field-hint { font-size: 12px; color: #94A3B8; }

.color-field { display: flex; gap: 8px; align-items: center; }
.color-picker { width: 38px; height: 38px; border-radius: 8px; border: 1px solid #E2E8F0; padding: 2px; cursor: pointer; }
.color-text { flex: 1; border: 1px solid #E2E8F0; border-radius: 9px; padding: 10px 12px; font-size: 14px; font-family: monospace; outline: none; }

.form-error { background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 10px 12px; font-size: 13px; color: #B91C1C; }
.form-success { background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 10px 12px; font-size: 13px; color: #15803D; }

.save-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white;
  border: none; border-radius: 9px; padding: 10px 24px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  margin-top: 20px; min-width: 130px; transition: opacity 0.15s;
}
.save-btn:hover:not(:disabled) { opacity: 0.9; }
.save-btn:disabled { opacity: 0.6; }

/* Sessions Table */
.sessions-table-wrap {
  background: white; border-radius: 14px; border: 1px solid #F1F5F9;
  overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.sessions-table { width: 100%; border-collapse: collapse; }
.sessions-table th {
  padding: 11px 14px; text-align: left;
  font-size: 12px; font-weight: 600; color: #64748B;
  text-transform: uppercase; letter-spacing: 0.05em;
  background: #F8FAFC; border-bottom: 1px solid #F1F5F9;
}
.sessions-table td { padding: 13px 14px; border-bottom: 1px solid #F8FAFC; vertical-align: middle; }
.sessions-table tbody tr:last-child td { border-bottom: none; }
.sessions-table tbody tr:hover { background: #FAFAFA; }

.visitor-cell { display: flex; flex-direction: column; gap: 2px; }
.visitor-id { font-size: 12px; font-family: monospace; color: #475569; }
.lead-email { font-size: 11px; color: #6366F1; }

.heat-cell { display: flex; flex-direction: column; gap: 4px; }
.heat-val { font-size: 13px; font-weight: 700; }
.heat-val.hot { color: #DC2626; }
.heat-val.warm { color: #EA580C; }
.heat-val.cool { color: #2563EB; }
.mini-heat-bar { height: 4px; width: 60px; background: #F1F5F9; border-radius: 2px; overflow: hidden; }
.mini-heat-bar div { height: 100%; border-radius: 2px; }

.state-badge {
  font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.04em;
}
.state-blue { background: #EFF6FF; color: #1D4ED8; }
.state-yellow { background: #FFFBEB; color: #B45309; }
.state-red { background: #FEF2F2; color: #B91C1C; }
.state-orange { background: #FFF7ED; color: #C2410C; }
.state-green { background: #F0FDF4; color: #15803D; }

.msgs-cell { font-size: 13px; font-weight: 600; color: #0F172A; }
.time-cell { font-size: 12px; color: #94A3B8; }

.view-session-btn {
  background: white; border: 1px solid #E2E8F0; border-radius: 7px;
  padding: 5px 12px; font-size: 12px; font-weight: 500; color: #475569;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.view-session-btn:hover { background: #EEF2FF; border-color: #C7D2FE; color: #4338CA; }

/* Loading / Empty */
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 60px; color: #94A3B8; font-size: 14px;
}
.loader { width: 32px; height: 32px; border: 3px solid #E2E8F0; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal { background: white; border-radius: 16px; width: 100%; max-width: 600px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 25px 50px rgba(0,0,0,0.15); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 20px 16px; border-bottom: 1px solid #F1F5F9; }
.modal-header h3 { font-size: 16px; font-weight: 600; color: #0F172A; }
.modal-sub { font-size: 12px; color: #94A3B8; font-family: monospace; margin-top: 2px; }
.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: #94A3B8; border-radius: 6px; transition: all 0.15s; }
.modal-close:hover { background: #F1F5F9; color: #475569; }
.modal-loading { display: flex; justify-content: center; padding: 40px; }
.chat-history { overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg { max-width: 85%; }
.user-msg { align-self: flex-end; }
.ai-msg { align-self: flex-start; }
.msg-role { font-size: 11px; font-weight: 600; color: #94A3B8; margin-bottom: 4px; display: block; }
.user-msg .msg-role { text-align: right; }
.msg-text { font-size: 13px; line-height: 1.5; padding: 10px 14px; border-radius: 12px; }
.user-msg .msg-text { background: #EFF6FF; color: #1E3A8A; border-bottom-right-radius: 4px; }
.ai-msg .msg-text { background: #F8FAFC; color: #334155; border: 1px solid #E2E8F0; border-bottom-left-radius: 4px; }
.no-history { color: #94A3B8; font-size: 13px; text-align: center; padding: 20px; }
.mini-spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.1); border-top-color: currentColor; border-radius: 50%; animation: spin 0.7s linear infinite; }
.mini-spinner.white { border-color: rgba(255,255,255,0.3); border-top-color: white; }

/* ── Analytics Tab ─────────────────────────────────────────────── */
.an-stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px;
}
.an-stat {
  background: white; border: 1px solid #F1F5F9; border-radius: 12px;
  padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.an-label { font-size: 12px; color: #94A3B8; font-weight: 500; margin-bottom: 4px; }
.an-value { font-size: 26px; font-weight: 700; color: #0F172A; letter-spacing: -0.5px; }
.an-value.hot  { color: #EF4444; }
.an-value.warm { color: #F97316; }

.an-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

.an-card {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px;
  padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.an-card.an-full { margin-bottom: 16px; }

.an-card-title { font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px; }

/* Heat distribution */
.an-heat-bar { display: flex; height: 12px; border-radius: 6px; overflow: hidden; gap: 2px; margin-bottom: 14px; }
.an-hd-cold { background: #3B82F6; border-radius: 6px; transition: flex 0.4s; }
.an-hd-warm { background: #F97316; border-radius: 6px; transition: flex 0.4s; }
.an-hd-hot  { background: #EF4444; border-radius: 6px; transition: flex 0.4s; }
.an-heat-legend { display: flex; gap: 16px; }
.an-hl-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #64748B; }
.an-hl-item strong { color: #0F172A; margin-left: 2px; }
.an-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.an-dot.cold { background: #3B82F6; }
.an-dot.warm { background: #F97316; }
.an-dot.hot  { background: #EF4444; }

/* EMA Gauges */
.an-gauges { display: flex; flex-direction: column; gap: 14px; }
.an-gauge-row { display: flex; align-items: center; gap: 10px; }
.an-gauge-label { font-size: 12px; color: #94A3B8; width: 48px; flex-shrink: 0; }
.an-gauge-bar { flex: 1; background: #F1F5F9; border-radius: 4px; height: 8px; overflow: hidden; }
.an-gauge-fill { height: 100%; border-radius: 4px; transition: width 0.6s; }
.an-gauge-fill.intent  { background: linear-gradient(90deg, #6366F1, #8B5CF6); }
.an-gauge-fill.budget  { background: linear-gradient(90deg, #22C55E, #16A34A); }
.an-gauge-fill.urgency { background: linear-gradient(90deg, #F97316, #EF4444); }
.an-gauge-val { font-size: 12px; font-weight: 600; color: #475569; width: 34px; text-align: right; }

/* Sparkline */
.an-spark-wrap { min-height: 64px; }
.an-spark { width: 100%; height: 64px; display: block; }
.an-spark-labels { display: flex; justify-content: space-between; font-size: 11px; color: #94A3B8; margin-top: 4px; }
.an-no-data { font-size: 13px; color: #CBD5E1; text-align: center; padding: 20px; }

/* Kanban breakdown */
.an-kanban-list { display: flex; flex-direction: column; gap: 10px; }
.an-kanban-row { display: flex; align-items: center; gap: 10px; }
.an-kanban-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.an-kanban-label { flex: 1; font-size: 13px; color: #475569; }
.an-kanban-count { font-size: 13px; font-weight: 700; color: #0F172A; }

/* Behavioral events */
.an-events-list { display: flex; flex-direction: column; gap: 12px; }
.an-event-row { display: flex; align-items: center; gap: 12px; }
.an-event-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.an-event-label { font-size: 12px; color: #94A3B8; }
.an-event-val { font-size: 18px; font-weight: 700; color: #0F172A; }

/* ── Scrape progress bar ─────────────────────────────────────────────── */
.scrape-progress-wrap {
  margin-bottom: 20px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 12px;
  padding: 14px 16px;
}

.scrape-progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.scrape-phase-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1D4ED8;
}

.scrape-pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3B82F6;
  animation: pulseDot 1.2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes pulseDot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.7); }
}

.scrape-count-label {
  font-size: 12px;
  color: #2563EB;
  font-weight: 500;
}

.scrape-track {
  height: 6px;
  background: #DBEAFE;
  border-radius: 99px;
  overflow: hidden;
}

.scrape-fill {
  height: 100%;
  background: linear-gradient(90deg, #3B82F6, #6366F1);
  border-radius: 99px;
  transition: width 0.5s ease;
  min-width: 4%;
}

.scrape-fill--indeterminate {
  width: 30% !important;
  animation: indeterminate 1.6s ease-in-out infinite;
}

@keyframes indeterminate {
  0%   { transform: translateX(-120%); }
  100% { transform: translateX(400%); }
}

.scrape-hint {
  margin-top: 8px;
  font-size: 11px;
  color: #60A5FA;
}
</style>
