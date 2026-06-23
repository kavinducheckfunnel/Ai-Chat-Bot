<template>
  <div class="inbox-page">
    <div class="page-header">
      <div v-if="!embedded">
        <h1 class="page-title">Inbox</h1>
        <p class="page-sub">Real-time conversations from your website</p>
      </div>
      <div class="header-actions">
        <button class="mute-btn" @click="toggleMute" :title="muted ? 'Unmute notifications' : 'Mute notifications'">
          <svg v-if="!muted" width="16" height="16" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="16" height="16" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <line x1="23" y1="9" x2="17" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="17" y1="9" x2="23" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <div class="live-indicator">
          <span class="live-dot"></span>
          Live
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
        All chats
        <span class="tab-badge" v-if="totalCount">{{ totalCount }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">AI handled</button>
      <button class="tab" :class="{ active: activeTab === 'hot' }" @click="activeTab = 'hot'">
        Hot leads
        <span class="tab-badge hot" v-if="hotCount">{{ hotCount }}</span>
      </button>
    </div>

    <!-- Date-range filter banner — visible whenever the page was opened
         with ?from=&to= query params (e.g. via the invoice email's
         "View Monthly Conversations" CTA). -->
    <div v-if="dateFilterLabel" class="date-filter-banner">
      <span class="dfb-icon">📅</span>
      <span class="dfb-text">
        Showing conversations for <strong>{{ dateFilterLabel }}</strong>
      </span>
      <button class="dfb-clear" @click="clearDateFilter" type="button">Clear filter</button>
    </div>

    <div class="inbox-layout">
      <!-- ── Session list ─────────────────────────────────────────────── -->
      <div class="session-list" ref="listEl" @scroll="onListScroll" :class="{ 'mobile-hidden': mobileView !== 'list' }">
        <div v-if="loading" class="loading-state">
          <div class="skeleton-session" v-for="n in 4" :key="n">
            <div class="sk-avatar"></div>
            <div class="sk-lines"><div class="sk-line"></div><div class="sk-line short"></div></div>
          </div>
        </div>

        <div v-else-if="filteredSessions.length === 0" class="empty-state">
          <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#334155" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <p>No chats yet</p>
          <span>Sessions will appear here once visitors start chatting.</span>
        </div>

        <button
          v-else
          v-for="s in filteredSessions"
          :key="s.session_id"
          class="session-row"
          :class="{ active: selectedId === s.session_id }"
          @click="select(s)"
        >
          <div class="session-avatar-wrap">
            <div class="session-avatar" :style="{ background: heatColor(s.heat_score) }">
              {{ initials(s) }}
            </div>
            <span class="presence-dot" :class="presenceClass(s)" :title="presenceLabel(s)"></span>
          </div>
          <div class="session-meta">
            <div class="session-top-row">
              <span class="session-name">{{ s.lead_email || 'Visitor #' + s.session_id.slice(0,6) }}</span>
              <span class="session-time">{{ timeAgo(s.last_message_at || s.updated_at) }}</span>
            </div>
            <div class="session-preview">{{ lastMessage(s) }}</div>
            <div class="session-tags">
              <span class="tag" :class="kanbanClass(s.kanban_state)">{{ s.kanban_state }}</span>
              <span class="channel-badge" :class="'ch-' + (s.channel || 'website')">{{ channelLabel(s.channel) }}</span>
              <span v-if="s.takeover_active" class="takeover-dot" title="You are controlling this chat">⚡</span>
              <span class="heat-bar" :style="{ background: heatColor(s.heat_score), width: (s.heat_score / 100 * 60 + 20) + 'px' }"></span>
            </div>
          </div>
        </button>

        <div v-if="loadingMore" class="list-loading-more">Loading more…</div>
        <div v-else-if="!loading && nextOffset == null && sessions.length" class="list-end">
          {{ totalCount }} conversation{{ totalCount === 1 ? '' : 's' }}
        </div>
      </div>

      <!-- ── Chat panel ──────────────────────────────────────────────── -->
      <div class="chat-panel" :class="{ 'mobile-hidden': mobileView !== 'chat' }" v-if="selected">
        <div class="chat-panel-header">
          <!-- Mobile back button -->
          <button class="mobile-back-btn" @click="mobileView = 'list'" aria-label="Back to sessions">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <div class="chat-user-info">
            <div class="chat-avatar" :style="{ background: heatColor(selected.heat_score) }">{{ initials(selected) }}</div>
            <div>
              <p class="chat-name">{{ selected.lead_email || 'Visitor #' + selected.session_id.slice(0,6) }}</p>
              <p class="chat-sub">{{ selected.conversation_state }} · Heat {{ Math.round(selected.heat_score || 0) }}%</p>
            </div>
          </div>
          <div class="header-right-actions">
            <!-- Takeover controls -->
            <template v-if="selected.takeover_active">
              <span class="takeover-status-badge">⚡ In control</span>
              <button class="release-btn" @click="releaseTakeover" :disabled="releasingTakeover">
                {{ releasingTakeover ? '…' : 'Release to AI' }}
              </button>
            </template>
            <template v-else>
              <button class="takeover-btn" @click="takeover" :disabled="takingOver">
                {{ takingOver ? '…' : 'Take Over' }}
              </button>
            </template>
            <span class="kanban-badge" :class="kanbanClass(selected.kanban_state)">{{ selected.kanban_state }}</span>
            <!-- Mobile info button -->
            <button class="mobile-info-btn" @click="mobileView = 'details'" aria-label="Visitor details">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>

        <!-- Takeover banner -->
        <div v-if="selected.takeover_active" class="takeover-banner">
          ⚡ You are controlling this conversation — AI replies are paused
        </div>

        <div class="messages" ref="messagesEl">
          <div
            v-for="(msg, i) in chatHistory"
            :key="i"
            class="message"
            :class="[msg.role === 'user' ? 'user-msg' : 'ai-msg', msg.source === 'admin' ? 'admin-msg' : '']"
          >
            <span v-if="msg.source === 'admin'" class="msg-role-label">You (Admin)</span>
            <div class="bubble">
              <div v-if="msg.attachments && msg.attachments.length" class="bubble-attachments">
                <template v-for="(att, ai) in msg.attachments" :key="ai">
                  <img v-if="att.kind === 'image'" :src="att.url" class="att-image" @click="openAttachment(att.url)" alt="attachment" />
                  <audio v-else-if="att.kind === 'audio'" :src="att.url" controls class="att-audio"></audio>
                  <a v-else :href="att.url" target="_blank" rel="noopener" class="att-file">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                    {{ att.name || 'Download file' }}
                  </a>
                </template>
              </div>
              <span v-if="msg.message || msg.content">{{ msg.message || msg.content }}</span>
            </div>
          </div>
        </div>

        <!-- Admin message input (visible only during takeover) -->
        <div v-if="selected.takeover_active" class="admin-input-wrap">
          <!-- Pending attachments preview (QA #3) -->
          <div v-if="pendingAttachments.length" class="pending-atts">
            <div v-for="(att, i) in pendingAttachments" :key="i" class="pending-att">
              <img v-if="att.kind === 'image'" :src="att.url" class="pending-thumb" alt="" />
              <span v-else class="pending-file">{{ att.kind === 'audio' ? '🎙 voice note' : (att.name || 'file') }}</span>
              <button class="pending-remove" @click="removePending(i)">&times;</button>
            </div>
          </div>
          <div v-if="recording" class="recording-bar">
            <span class="rec-dot"></span> Recording… {{ recordSeconds }}s
            <button class="rec-stop" @click="stopRecording">Stop</button>
          </div>
          <div class="admin-input-area">
            <input ref="fileInput" type="file" class="hidden-file" @change="onFilePicked" accept="image/*,audio/*,application/pdf,.doc,.docx,.xls,.xlsx,.txt,.zip" />
            <button class="attach-btn" @click="fileInput?.click()" :disabled="uploadingAtt" title="Attach image or file">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="attach-btn" :class="{ recording: recording }" @click="recording ? stopRecording() : startRecording()" :disabled="uploadingAtt" title="Record voice note">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" stroke="currentColor" stroke-width="2"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
            <textarea
              class="admin-textarea"
              v-model="adminMsg"
              placeholder="Type your message… (Ctrl+Enter to send)"
              rows="2"
              @keydown.ctrl.enter.prevent="sendAdminMsg"
            ></textarea>
            <button class="admin-send-btn" @click="sendAdminMsg" :disabled="(!adminMsg.trim() && !pendingAttachments.length) || sendingMsg || uploadingAtt">
              <svg v-if="!sendingMsg" width="16" height="16" fill="none" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><polygon points="22 2 15 22 11 13 2 9 22 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <div v-else class="send-spinner"></div>
            </button>
          </div>
        </div>
      </div>

      <div class="chat-panel empty-panel" :class="{ 'mobile-hidden': mobileView !== 'chat' }" v-else>
        <svg width="32" height="32" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#1e293b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>Select a conversation</p>
      </div>

      <!-- ── Visitor details panel ───────────────────────────────────── -->
      <div class="visitor-panel" :class="{ 'mobile-hidden': mobileView !== 'details' }" v-if="selected">
        <!-- Mobile back button -->
        <div class="vp-mobile-back">
          <button class="mobile-back-btn" @click="mobileView = 'chat'">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Back to chat
          </button>
        </div>

        <!-- Customer -->
        <div class="vp-section customer-section">
          <div class="vp-customer-header">
            <div class="vp-avatar" :style="{ background: heatColor(selected.heat_score) }">
              {{ initials(selected) }}
            </div>
            <div class="vp-customer-info">
              <p class="vp-customer-name">{{ selected.lead_email ? selected.lead_email.split('@')[0] : 'Visitor' }}</p>
              <span class="status-chip">
                <span class="status-dot-green"></span>
                Chatting
              </span>
            </div>
          </div>

          <!-- Quick stats -->
          <div class="vp-stats-row">
            <div class="vp-stat">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ selected.message_count || 0 }}
            </div>
            <div class="vp-stat">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M9 12h6M9 16h6M17 21H7a2 2 0 01-2-2V5a2 2 0 012-2h5l5 5v11a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              0
            </div>
            <div class="first-visit-badge">First visit</div>
          </div>
        </div>

        <!-- Chat info -->
        <div class="vp-section">
          <div class="vp-section-title">Chat info</div>
          <div class="vp-rows">
            <div class="vp-row">
              <span class="vp-label">Assignee</span>
              <span class="vp-value">
                <span class="assignee-dot">A</span> You
              </span>
            </div>
            <div class="vp-row">
              <span class="vp-label">Chat ID</span>
              <span class="vp-value mono">{{ selected.session_id.slice(0,10).toUpperCase() }}</span>
            </div>
            <div class="vp-row">
              <span class="vp-label">Duration</span>
              <span class="vp-value">{{ chatDuration }}</span>
            </div>
          </div>
        </div>

        <!-- Visitor info -->
        <div class="vp-section">
          <div class="vp-section-title">Visitor info</div>
          <div class="vp-rows">
            <div class="vp-row" v-if="selected.lead_email">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </span>
              <span class="vp-value truncate">{{ selected.lead_email }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_city || selected.visitor_country">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2"/></svg>
              </span>
              <span class="vp-value">
                {{ [selected.visitor_city, selected.visitor_country].filter(Boolean).join(', ') }}
                {{ countryFlag(selected.visitor_country_code) }}
              </span>
            </div>
            <div class="vp-row" v-if="selected.visitor_timezone">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><polyline points="12 6 12 12 16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </span>
              <span class="vp-value">{{ visitorLocalTime }}</span>
            </div>
          </div>
        </div>

        <!-- Behavioral Scores (3-EMA) -->
        <div class="vp-section">
          <div class="vp-section-title">Behavioral Scores</div>
          <div class="ema-scores">
            <div class="ema-row">
              <div class="ema-header">
                <span class="ema-label">Intent</span>
                <span class="ema-value" :class="trendClass(selected.intent_trend)">
                  {{ emaPercent(selected.intent_ema) }}%
                  <span class="ema-trend-icon">{{ trendIcon(selected.intent_trend) }}</span>
                </span>
              </div>
              <div class="ema-track">
                <div class="ema-fill intent-fill" :style="{ width: emaPercent(selected.intent_ema) + '%' }"></div>
              </div>
            </div>
            <div class="ema-row">
              <div class="ema-header">
                <span class="ema-label">Budget</span>
                <span class="ema-value" :class="trendClass(selected.budget_trend)">
                  {{ emaPercent(selected.budget_ema) }}%
                  <span class="ema-trend-icon">{{ trendIcon(selected.budget_trend) }}</span>
                </span>
              </div>
              <div class="ema-track">
                <div class="ema-fill budget-fill" :style="{ width: emaPercent(selected.budget_ema) + '%' }"></div>
              </div>
            </div>
            <div class="ema-row">
              <div class="ema-header">
                <span class="ema-label">Urgency</span>
                <span class="ema-value" :class="trendClass(selected.urgency_trend)">
                  {{ emaPercent(selected.urgency_ema) }}%
                  <span class="ema-trend-icon">{{ trendIcon(selected.urgency_trend) }}</span>
                </span>
              </div>
              <div class="ema-track">
                <div class="ema-fill urgency-fill" :style="{ width: emaPercent(selected.urgency_ema) + '%' }"></div>
              </div>
            </div>
            <div class="heat-composite">
              <span class="ema-label">Overall heat</span>
              <span class="heat-chip" :style="{ background: heatColor(selected.heat_score) }">
                {{ Math.round(selected.heat_score || 0) }}%
              </span>
            </div>
          </div>
        </div>

        <!-- Activity timeline -->
        <div class="vp-section" v-if="timeline.length">
          <div class="vp-section-title">
            Activity timeline
            <span class="vp-count">{{ timeline.length }}</span>
          </div>
          <div class="timeline-list">
            <div
              v-for="(ev, i) in timeline.slice().reverse().slice(0, 30)"
              :key="i"
              class="timeline-row"
            >
              <span class="tl-icon" :class="'tl-' + ev.event_type">{{ eventIcon(ev.event_type) }}</span>
              <div class="tl-body">
                <div class="tl-label">{{ eventLabel(ev) }}</div>
                <div class="tl-meta">{{ formatTimelineTime(ev.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Hot Signals -->
        <div class="vp-section" v-if="hotSignals(selected).length">
          <div class="vp-section-title">Hot signals</div>
          <div class="hot-signals-list">
            <div class="hot-signal-row" v-for="sig in hotSignals(selected)" :key="sig.key">
              <span class="signal-icon">{{ sig.icon }}</span>
              <span class="signal-label">{{ sig.label }}</span>
              <span class="signal-value" :class="sig.level">{{ sig.value }}</span>
            </div>
          </div>
        </div>

        <!-- Chat tags -->
        <div class="vp-section">
          <div class="vp-section-title">Labels</div>
          <div class="vp-tags-row">
            <span class="vp-tag" :class="kanbanClass(selected.kanban_state)">{{ selected.kanban_state.replace('_', ' ').toLowerCase() }}</span>
            <span class="vp-tag vp-tag-state">{{ selected.conversation_state.replace('_', ' ').toLowerCase() }}</span>
            <span
              v-for="t in (selected.tags || [])"
              :key="t"
              class="vp-tag vp-tag-custom"
            >{{ t }}<button class="tag-del" @click.stop="removeTag(t)">✕</button></span>
          </div>
          <div class="tag-input-row">
            <input
              class="tag-input"
              v-model="tagInput"
              placeholder="Add label…"
              maxlength="50"
              @keydown.enter.prevent="addTag"
              @keydown.comma.prevent="addTag"
            />
            <button class="tag-add-btn" @click="addTag" :disabled="!tagInput.trim()">Add</button>
          </div>
          <p v-if="tagError" class="tag-error">{{ tagError }}</p>
        </div>

        <!-- Visited pages -->
        <div class="vp-section" v-if="selected.page_visits && selected.page_visits.length">
          <div class="vp-section-title">Visited pages <span class="vp-count">{{ selected.page_visits.length }}</span></div>
          <div class="vp-pages">
            <div class="vp-page-row" v-for="(pv, i) in selected.page_visits.slice().reverse()" :key="i">
              <span class="page-dot" :class="i === 0 ? 'page-dot-active' : ''"></span>
              <div class="page-info">
                <span class="page-title-text">{{ pv.title || pv.url }}</span>
                <span class="page-duration">{{ formatDuration(pv.duration_seconds) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Visit info -->
        <div class="vp-section">
          <div class="vp-section-title">Visit info</div>
          <div class="vp-rows">
            <div class="vp-row" v-if="selected.visitor_device">
              <span class="vp-label">Device</span>
              <span class="vp-value device-row">
                <span class="device-icon">
                  <!-- Desktop -->
                  <svg v-if="selected.visitor_device === 'desktop'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/><path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  <!-- Mobile -->
                  <svg v-else-if="selected.visitor_device === 'mobile'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                  <!-- Tablet -->
                  <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                </span>
                <span>{{ selected.visitor_device }}</span>
                <span v-if="selected.visitor_os" class="os-badge">{{ selected.visitor_os }}</span>
              </span>
            </div>
            <div class="vp-row" v-if="selected.visitor_browser">
              <span class="vp-label">Browser</span>
              <span class="vp-value">{{ selected.visitor_browser }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_referrer">
              <span class="vp-label">Referrer</span>
              <span class="vp-value truncate">{{ referrerHost(selected.visitor_referrer) }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_ip">
              <span class="vp-label">IP</span>
              <span class="vp-value mono">{{ selected.visitor_ip }}</span>
            </div>
          </div>
        </div>

        <!-- Empty state for new sessions with no data yet -->
        <div class="vp-no-data" v-if="!selected.visitor_country && !selected.visitor_ip && !selected.page_visits?.length">
          <svg width="24" height="24" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#334155" stroke-width="1.5"/><path d="M12 8v4M12 16h.01" stroke="#334155" stroke-width="2" stroke-linecap="round"/></svg>
          <p>Visitor data will appear<br>after the next chat message.</p>
        </div>

      </div>

      <!-- No session selected -->
      <div class="visitor-panel visitor-panel-empty" :class="{ 'mobile-hidden': mobileView !== 'details' }" v-else>
        <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" stroke="#1e293b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>Visitor details</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'
import { timeAgo, formatDuration } from '../composables/useFormat'

const props = defineProps({
  client: Object,
  embedded: Boolean,
  // Shared filters owned by the Conversations wrapper (QA #1, #10).
  channel: { type: String, default: 'all' },
  dateRange: { type: Object, default: () => ({ period: 'all', dateFrom: null, dateTo: null }) },
})
const api = useAdminApi()

const sessions = ref([])
const totalCount = ref(0)
const nextOffset = ref(null)
const loadingMore = ref(false)
const loading = ref(true)
const activeTab = ref('all')
const selectedId = ref(null)
const messagesEl = ref(null)
const listEl = ref(null)
let ws = null
const PAGE = 50

// ── Mobile panel navigation ───────────────────────────────────────────────────
const mobileView = ref('list') // 'list' | 'chat' | 'details'
const isMobile = () => window.innerWidth <= 768

// ── God View / Takeover ───────────────────────────────────────────────────────
const adminMsg = ref('')
const takingOver = ref(false)
const releasingTakeover = ref(false)
const sendingMsg = ref(false)

// ── Takeover media (QA #3) ─────────────────────────────────────────────────────
const fileInput = ref(null)
const pendingAttachments = ref([])
const uploadingAtt = ref(false)
const recording = ref(false)
const recordSeconds = ref(0)
let mediaRecorder = null
let recordChunks = []
let recordTimer = null

function openAttachment(url) { window.open(url, '_blank', 'noopener') }
function removePending(i) { pendingAttachments.value.splice(i, 1) }

async function uploadFile(file, kind) {
  if (!selected.value) return
  uploadingAtt.value = true
  try {
    const res = await api.uploadAttachment(selected.value.session_id, file, kind)
    pendingAttachments.value.push(res)
  } catch (e) {
    console.error('upload failed', e)
  } finally {
    uploadingAtt.value = false
  }
}

function onFilePicked(e) {
  const file = e.target.files?.[0]
  if (file) {
    const kind = file.type.startsWith('image/') ? 'image' : (file.type.startsWith('audio/') ? 'audio' : 'file')
    uploadFile(file, kind)
  }
  e.target.value = ''
}

async function startRecording() {
  if (recording.value) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    recordChunks = []
    mediaRecorder.ondataavailable = (ev) => { if (ev.data.size) recordChunks.push(ev.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(recordChunks, { type: 'audio/webm' })
      const file = new File([blob], `voice-${Date.now()}.webm`, { type: 'audio/webm' })
      await uploadFile(file, 'audio')
    }
    mediaRecorder.start()
    recording.value = true
    recordSeconds.value = 0
    recordTimer = setInterval(() => {
      recordSeconds.value++
      if (recordSeconds.value >= 120) stopRecording() // 2-min cap
    }, 1000)
  } catch (e) {
    console.error('mic access denied', e)
  }
}

function stopRecording() {
  if (!recording.value) return
  recording.value = false
  clearInterval(recordTimer)
  try { mediaRecorder?.stop() } catch {}
}

async function takeover() {
  if (!selected.value || takingOver.value) return
  takingOver.value = true
  try {
    await api.takeoverSession(selected.value.session_id)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], takeover_active: true }
  } catch {} finally { takingOver.value = false }
}

async function releaseTakeover() {
  if (!selected.value || releasingTakeover.value) return
  releasingTakeover.value = true
  try {
    await api.releaseSession(selected.value.session_id)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], takeover_active: false }
    adminMsg.value = ''
  } catch {} finally { releasingTakeover.value = false }
}

async function sendAdminMsg() {
  const msg = adminMsg.value.trim()
  const atts = [...pendingAttachments.value]
  if ((!msg && !atts.length) || !selected.value || sendingMsg.value) return
  sendingMsg.value = true
  const sid = selected.value.session_id
  const idx = sessions.value.findIndex(s => s.session_id === sid)
  // Optimistic bubble for instant feedback.
  if (idx !== -1) {
    const entry = { role: 'ai', message: msg, source: 'admin', _optimistic: true }
    if (atts.length) entry.attachments = atts
    const history = [...(sessions.value[idx].chat_history || []), entry]
    sessions.value[idx] = { ...sessions.value[idx], chat_history: history }
  }
  adminMsg.value = ''
  pendingAttachments.value = []
  nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
  try {
    await api.sendMessage(sid, msg, atts)
    // Authoritative refresh of THIS session's transcript replaces the
    // optimistic copy with the DB version, so a concurrent poll can't
    // leave a duplicate ("Hi Hi").
    const data = await api.getSessionHistory(sid)
    const i2 = sessions.value.findIndex(s => s.session_id === sid)
    if (i2 !== -1 && data && data.chat_history) {
      sessions.value[i2] = { ...sessions.value[i2], chat_history: data.chat_history }
      nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
    }
  } catch {} finally { sendingMsg.value = false }
}

// ── Duration timer ────────────────────────────────────────────────────────────
const chatDuration = ref('0m 0s')
const visitorLocalTime = ref('')
let durationTimer = null

function updateDuration() {
  const s = selected.value
  if (!s?.created_at) { chatDuration.value = '—'; return }

  const created = new Date(s.created_at).getTime()
  const lastActivity = new Date(s.updated_at || s.created_at).getTime()
  const idleMs = Date.now() - lastActivity
  const IDLE_LIMIT = 10 * 60 * 1000  // 10 minutes

  // If session has been idle for >10 min, freeze at updated_at - created_at
  const endTime = idleMs > IDLE_LIMIT ? lastActivity : Date.now()
  const elapsed = Math.floor((endTime - created) / 1000)

  const m = Math.floor(elapsed / 60)
  const sec = elapsed % 60
  chatDuration.value = `${m}m ${sec}s`
}

function updateVisitorClock() {
  const tz = selected.value?.visitor_timezone
  if (!tz) { visitorLocalTime.value = ''; return }
  try {
    const now = new Date()
    const fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour: 'numeric',
      minute: '2-digit',
      weekday: 'short',
    })
    visitorLocalTime.value = fmt.format(now)
  } catch { visitorLocalTime.value = '' }
}

function startTimers() {
  clearInterval(durationTimer)
  updateDuration()
  updateVisitorClock()
  durationTimer = setInterval(() => {
    updateDuration()
    updateVisitorClock()
  }, 1000)
}

// ── Notification sound ────────────────────────────────────────────────────────
const muted = ref(localStorage.getItem('cf_inbox_muted') === '1')

function toggleMute() {
  muted.value = !muted.value
  localStorage.setItem('cf_inbox_muted', muted.value ? '1' : '0')
}

function playNotificationSound() {
  if (muted.value) return
  try {
    const AudioCtx = window.AudioContext || window['webkitAudioContext']
    const ctx = new AudioCtx()
    const tones = [880, 1100]
    tones.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0, ctx.currentTime + i * 0.18)
      gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + i * 0.18 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.18 + 0.35)
      osc.start(ctx.currentTime + i * 0.18)
      osc.stop(ctx.currentTime + i * 0.18 + 0.35)
    })
    setTimeout(() => ctx.close(), 1200)
  } catch {}
}

const selected = computed(() => sessions.value.find(s => s.session_id === selectedId.value) || null)

const chatHistory = computed(() => {
  if (!selected.value?.chat_history) return []
  return selected.value.chat_history.slice(-40)
})

const hotCount = computed(() => sessions.value.filter(s => s.kanban_state === 'HOT_LEAD').length)

const filteredSessions = computed(() => {
  if (activeTab.value === 'ai') return sessions.value.filter(s => !s.takeover_active)
  if (activeTab.value === 'hot') return sessions.value.filter(s => s.kanban_state === 'HOT_LEAD' || s.heat_score > 65)
  return sessions.value
})

// ── Date-range filter (driven by ?from=YYYY-MM-DD&to=YYYY-MM-DD) ──────────
// Used by the invoice email's "View Monthly Conversations" CTA to land
// the tenant on this page filtered to the invoice's billing month.
const route = useRoute()
const router = useRouter()
const dateFrom = ref('')
const dateTo = ref('')

const dateFilterLabel = computed(() => {
  if (!dateFrom.value && !dateTo.value) return ''
  try {
    const fmt = (s) => new Date(s + 'T00:00:00').toLocaleDateString(undefined, {
      month: 'long', day: 'numeric', year: 'numeric',
    })
    if (dateFrom.value && dateTo.value) return `${fmt(dateFrom.value)} — ${fmt(dateTo.value)}`
    if (dateFrom.value) return `From ${fmt(dateFrom.value)}`
    return `Until ${fmt(dateTo.value)}`
  } catch {
    return `${dateFrom.value || ''} → ${dateTo.value || ''}`
  }
})

function clearDateFilter() {
  dateFrom.value = ''
  dateTo.value = ''
  // Strip the query params so a refresh doesn't restore the filter.
  router.replace({ path: route.path, query: { ...route.query, from: undefined, to: undefined } })
  loadSessions()
}

function _baseParams() {
  const params = { limit: PAGE }
  // Channel filter (QA #1) from the wrapper.
  if (props.channel && props.channel !== 'all') params.channel = props.channel
  // Date filter (QA #10) — explicit ?from/?to (invoice deep-link) wins, else the
  // shared wrapper date range.
  if (dateFrom.value) params.date_from = dateFrom.value
  else if (props.dateRange?.dateFrom) params.date_from = props.dateRange.dateFrom
  if (dateTo.value) params.date_to = dateTo.value
  else if (props.dateRange?.dateTo) params.date_to = props.dateRange.dateTo
  if (!params.date_from && !params.date_to && props.dateRange?.period && props.dateRange.period !== 'all' && props.dateRange.period !== 'custom') {
    params.period = props.dateRange.period
  }
  return params
}

async function loadSessions() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { ..._baseParams(), offset: 0 })
    const res = Array.isArray(data) ? data : (data?.results || [])
    sessions.value = res
    totalCount.value = Array.isArray(data) ? res.length : (data?.count ?? res.length)
    nextOffset.value = Array.isArray(data) ? null : (data?.next ?? null)
  } catch {} finally {
    loading.value = false
  }
}

// Infinite scroll: append the next page when the list nears its end (QA #4).
async function loadMore() {
  if (loadingMore.value || nextOffset.value == null || !props.client) return
  loadingMore.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { ..._baseParams(), offset: nextOffset.value })
    const res = Array.isArray(data) ? data : (data?.results || [])
    const seen = new Set(sessions.value.map(s => s.session_id))
    sessions.value.push(...res.filter(s => !seen.has(s.session_id)))
    nextOffset.value = Array.isArray(data) ? null : (data?.next ?? null)
  } catch {} finally {
    loadingMore.value = false
  }
}

function onListScroll(e) {
  const el = e.target
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 240) loadMore()
}

function select(s) {
  selectedId.value = s.session_id
  if (isMobile()) mobileView.value = 'chat'
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function lastMessage(s) {
  const h = s.chat_history
  if (!h || !h.length) return 'No messages yet'
  const last = h[h.length - 1]
  const text = last?.message || last?.content || ''
  return text.slice(0, 60) + (text.length > 60 ? '…' : '')
}

function initials(s) {
  if (s.lead_email) return s.lead_email[0].toUpperCase()
  return '#'
}

function heatColor(score) {
  if (!score) return '#64748b'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
}

function kanbanClass(state) {
  if (state === 'HOT_LEAD') return 'tag-hot'
  if (state === 'CONVERTED') return 'tag-converted'
  if (state === 'ENGAGED') return 'tag-engaged'
  return 'tag-new'
}

function channelLabel(channel) {
  if (channel === 'whatsapp') return 'WhatsApp'
  if (channel === 'messenger') return 'Messenger'
  if (channel === 'instagram') return 'Instagram'
  if (channel === 'telegram') return 'Telegram'
  return 'Web'
}

function presenceClass(s) {
  if (!s.updated_at) return 'presence-offline'
  const diffMin = (Date.now() - new Date(s.updated_at).getTime()) / 60000
  if (diffMin < 5) return 'presence-online'
  if (diffMin < 30) return 'presence-away'
  return 'presence-offline'
}

function presenceLabel(s) {
  if (!s.updated_at) return 'Offline'
  const diffMin = (Date.now() - new Date(s.updated_at).getTime()) / 60000
  if (diffMin < 5) return 'Online now'
  if (diffMin < 30) return 'Away'
  return 'Offline'
}

function emaPercent(val) {
  return Math.round((val || 0) * 100)
}

function trendIcon(trend) {
  if (trend === 'UP') return '↑'
  if (trend === 'DOWN') return '↓'
  return '→'
}

function trendClass(trend) {
  if (trend === 'UP') return 'trend-up'
  if (trend === 'DOWN') return 'trend-down'
  return 'trend-flat'
}

// ── Activity timeline ────────────────────────────────────────────────────────
const timeline = ref([])

async function loadTimeline(sessionId) {
  if (!sessionId) { timeline.value = []; return }
  try {
    const data = await api.getSessionTimeline(sessionId)
    timeline.value = data?.events || []
  } catch {
    timeline.value = []
  }
}

function eventIcon(t) {
  const map = {
    click: '👆', cta_click: '⭐', add_to_cart: '🛒', rage_click: '😤',
    form_focus: '✍️', form_abandoned: '⏸', copy: '📋',
    page_view: '📄', pricing_visit: '💰', exit_intent: '🚪',
    chat_user: '💬', chat_ai: '🤖',
  }
  return map[t] || '•'
}

function eventLabel(ev) {
  const p = ev.payload || {}
  switch (ev.event_type) {
    case 'click':       return `Clicked "${(p.text || 'element').slice(0, 50)}"`
    case 'cta_click':   return `Clicked CTA: "${(p.text || '').slice(0, 50)}"`
    case 'add_to_cart': return `🛒 Added to cart: "${(p.text || 'item').slice(0, 50)}"`
    case 'rage_click':  return 'Rage-clicked (frustration signal)'
    case 'form_focus':  return 'Started filling a form'
    case 'form_abandoned': return 'Abandoned a form'
    case 'copy':        return `Copied text: "${(p.value || p.text || '').slice(0, 40)}"`
    case 'page_view':   return `Viewed ${p.page_title || ev.page_url || '(page)'}` +
                               (p.duration_seconds ? ` (${formatDuration(p.duration_seconds)})` : '')
    case 'pricing_visit': return `Visited pricing page`
    case 'exit_intent': return 'Showed exit intent'
    case 'chat_user':   return `Said: "${(p.message || '').slice(0, 70)}"`
    case 'chat_ai':     return `AI replied: "${(p.message || '').slice(0, 70)}"`
    default:            return ev.event_type
  }
}

function formatTimelineTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const diff = Date.now() - d.getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function hotSignals(session) {
  const ctx = session?.behavioral_context || {}
  const signals = []

  const atc = ctx.add_to_cart_clicks || 0
  if (atc > 0) signals.push({ key: 'atc', icon: '🛒', label: 'Added to cart', value: `${atc}×`, level: 'sig-high' })

  const pricing = ctx.pricing_page_visits || 0
  if (pricing > 0) signals.push({ key: 'pricing', icon: '💰', label: 'Pricing page visits', value: `${pricing}×`, level: pricing >= 2 ? 'sig-high' : 'sig-med' })

  const checkout = ctx.checkout_visits || 0
  if (checkout > 0) signals.push({ key: 'checkout', icon: '📦', label: 'Checkout visits', value: `${checkout}×`, level: 'sig-high' })

  const cta = ctx.cta_clicks || 0
  if (cta > 0) signals.push({ key: 'cta', icon: '👆', label: 'CTA clicks', value: `${cta}×`, level: cta >= 2 ? 'sig-high' : 'sig-med' })

  const copies = ctx.copy_events || 0
  if (copies > 0) signals.push({ key: 'copy', icon: '📋', label: 'Copied content', value: `${copies}×`, level: 'sig-med' })

  const priceV = ctx.price_views || 0
  if (priceV > 0) signals.push({ key: 'price', icon: '👀', label: 'Viewed prices', value: `${priceV}×`, level: priceV >= 3 ? 'sig-high' : 'sig-med' })

  const time = ctx.time_on_site || 0
  if (time >= 60) signals.push({ key: 'time', icon: '⏱', label: 'Time on site', value: time >= 120 ? `${Math.floor(time / 60)}m ${time % 60}s` : `${time}s`, level: time >= 120 ? 'sig-med' : 'sig-low' })

  const scroll = ctx.scroll_depth || 0
  if (scroll >= 75) signals.push({ key: 'scroll', icon: '📜', label: 'Scroll depth', value: `${scroll}%`, level: scroll >= 90 ? 'sig-high' : 'sig-med' })

  const form = ctx.form_focused
  if (form) signals.push({ key: 'form', icon: '✍️', label: 'Filled a form', value: ctx.form_abandoned ? 'abandoned' : 'in progress', level: ctx.form_abandoned ? 'sig-low' : 'sig-med' })

  const rage = ctx.rage_clicks || 0
  if (rage > 0) signals.push({ key: 'rage', icon: '😤', label: 'Rage clicks', value: `${rage}×`, level: 'sig-low' })

  const video = ctx.video_plays || 0
  if (video > 0) signals.push({ key: 'video', icon: '▶️', label: 'Played video', value: `${video}×`, level: 'sig-med' })

  const files = ctx.file_downloads || 0
  if (files > 0) signals.push({ key: 'files', icon: '📥', label: 'Downloaded files', value: `${files}×`, level: 'sig-med' })

  // Sort: high first, then med, then low
  const order = { 'sig-high': 0, 'sig-med': 1, 'sig-low': 2 }
  signals.sort((a, b) => (order[a.level] || 2) - (order[b.level] || 2))

  return signals.slice(0, 7)
}

function countryFlag(code) {
  if (!code || code.length !== 2) return ''
  return [...code.toUpperCase()].map(c => String.fromCodePoint(c.codePointAt(0) + 127397)).join('')
}

function referrerHost(url) {
  if (!url) return ''
  try { return new URL(url).hostname.replace('www.', '') } catch { return url }
}

// ── Tags ─────────────────────────────────────────────────────────────────────
const tagInput = ref('')
const tagError = ref('')

async function addTag() {
  const tag = tagInput.value.trim()
  if (!tag || !selected.value) return
  const existing = selected.value.tags || []
  if (existing.includes(tag)) { tagError.value = 'Tag already exists.'; return }
  tagError.value = ''
  const newTags = [...existing, tag]
  try {
    await api.updateSessionTags(selected.value.session_id, newTags)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], tags: newTags }
    tagInput.value = ''
  } catch (e) {
    tagError.value = 'Failed to save tag.'
  }
}

async function removeTag(tag) {
  if (!selected.value) return
  const newTags = (selected.value.tags || []).filter(t => t !== tag)
  try {
    await api.updateSessionTags(selected.value.session_id, newTags)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], tags: newTags }
  } catch {}
}

// ── Desktop notifications ────────────────────────────────────────────────────
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

function showDesktopNotification(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted' || muted.value) return
  try {
    new Notification(title, { body, icon: '/favicon.ico', tag: 'cf-new-session' })
  } catch {}
}

// ── Channel polling (WhatsApp / Messenger / Telegram) ────────────────────────
let channelPollTimer = null

function startChannelPolling(sessionId) {
  stopChannelPolling()
  channelPollTimer = setInterval(async () => {
    try {
      const data = await api.getSessionHistory(sessionId)
      const idx = sessions.value.findIndex(s => s.session_id === sessionId)
      if (idx !== -1 && data.chat_history) {
        const current = sessions.value[idx].chat_history || []
        if (data.chat_history.length !== current.length) {
          sessions.value[idx] = { ...sessions.value[idx], chat_history: data.chat_history }
          nextTick(() => {
            if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
          })
        }
      }
    } catch {}
  }, 3000)
}

function stopChannelPolling() {
  if (channelPollTimer) { clearInterval(channelPollTimer); channelPollTimer = null }
}

// Read ?from= / ?to= when the page first renders so deep-links from the
// invoice email land on the right month's sessions.
function _syncFiltersFromRoute() {
  dateFrom.value = (route.query.from || '').toString()
  dateTo.value   = (route.query.to   || '').toString()
}

onMounted(async () => {
  requestNotificationPermission()
  _syncFiltersFromRoute()
  await loadSessions()
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'session_update') {
      const prevCount = sessions.value.length
      loadSessions().then(() => {
        if (sessions.value.length > prevCount) {
          playNotificationSound()
          showDesktopNotification('New visitor', 'A new visitor started a chat on your site.')
        }
      })
    }
  })
  startTimers()
})

onUnmounted(() => {
  if (ws) ws.close()
  clearInterval(durationTimer)
  stopChannelPolling()
})

watch(() => props.client, loadSessions)

// Re-fetch from the top whenever the wrapper changes channel or date range.
watch(() => [props.channel, props.dateRange], () => {
  selectedId.value = null
  loadSessions()
}, { deep: true })

// React to back/forward nav and to programmatic `router.push({ query })`.
watch(() => [route.query.from, route.query.to], () => {
  _syncFiltersFromRoute()
  loadSessions()
})

watch(selected, (s) => {
  if (s) {
    startTimers()
    loadTimeline(s.session_id)
    // For non-website channels, poll for new messages since there's no WebSocket
    if (s.channel && s.channel !== 'website') {
      startChannelPolling(s.session_id)
    } else {
      stopChannelPolling()
    }
  } else {
    stopChannelPolling()
    timeline.value = []
  }
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
})
</script>

<style scoped>
* { box-sizing: border-box; }

.inbox-page {
  display: flex;
  flex-direction: column;
  /* 100vh when standalone; 100% lets it fill the Conversations wrapper's body
     (which is itself height-constrained) without overflowing past it. */
  height: 100%;
  min-height: 0;
  padding: 28px 32px 0;
  font-family: 'Inter', -apple-system, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 3px; }

.header-actions { display: flex; align-items: center; gap: 10px; }

.mute-btn {
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  border-radius: 8px; color: var(--cf-text-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; transition: background 0.15s, color 0.15s;
}
.mute-btn:hover { background: var(--cf-bg-ghost-hover); color: var(--cf-text-secondary); }

.live-indicator {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: #22c55e;
  background: rgba(34,197,94,0.08); padding: 5px 12px;
  border-radius: 20px; border: 1px solid rgba(34,197,94,0.2);
}

.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #22c55e; animation: pulse 1.5s infinite;
}

.tabs {
  display: flex; gap: 2px;
  border-bottom: 1px solid var(--cf-border-subtle);
  margin-bottom: 0;
}

.tab {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 16px; background: none; border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px; font-weight: 500; color: var(--cf-text-muted);
  cursor: pointer; transition: all 0.12s; margin-bottom: -1px;
}
.tab:hover { color: var(--cf-text-secondary); }
.tab.active { color: #a5b4fc; border-bottom-color: #6366f1; }

.tab-badge {
  background: #334155; color: var(--cf-text-secondary);
  font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: 10px;
}
.tab-badge.hot { background: rgba(239,68,68,0.15); color: #ef4444; }

/* Date-range filter banner */
.date-filter-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  margin: 0 16px 8px;
  background: rgba(99,102,241,0.10);
  border: 1px solid rgba(99,102,241,0.30);
  border-radius: 9px;
  font-size: 13px; color: var(--cf-text-default, #0f172a);
}
.date-filter-banner .dfb-icon { font-size: 14px; flex-shrink: 0; }
.date-filter-banner .dfb-text { flex: 1; }
.date-filter-banner .dfb-text strong { font-weight: 600; }
.date-filter-banner .dfb-clear {
  background: transparent; border: 1px solid rgba(99,102,241,0.40);
  color: #6366f1; font-size: 12px; font-weight: 600;
  padding: 5px 10px; border-radius: 6px; cursor: pointer;
}
.date-filter-banner .dfb-clear:hover { background: rgba(99,102,241,0.15); }

/* ── 3-column layout ─────────────────────────────────────────────────── */
.inbox-layout {
  display: flex;
  flex: 1;
  gap: 0;
  overflow: hidden;
  border-top: 1px solid var(--cf-border-subtle);
}

/* ── Session list ────────────────────────────────────────────────────── */
.session-list {
  width: 280px; min-width: 280px;
  border-right: 1px solid var(--cf-border-subtle);
  overflow-y: auto; padding: 8px 0;
}

.loading-state { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.skeleton-session { display: flex; gap: 10px; align-items: center; }
.sk-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--cf-skeleton-color); flex-shrink: 0; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 7px; }
.sk-line { height: 10px; background: var(--cf-skeleton-color); border-radius: 4px; }
.sk-line.short { width: 55%; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; padding: 40px 20px; text-align: center; gap: 10px;
}
.empty-state p { font-size: 14px; font-weight: 500; color: var(--cf-text-muted); }
.empty-state span { font-size: 12px; color: var(--cf-text-muted); line-height: 1.5; }

.session-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 14px; background: none; border: none;
  width: 100%; text-align: left; cursor: pointer; transition: background 0.12s;
  border-bottom: 1px solid var(--cf-border-subtle);
}
.session-row:hover { background: var(--cf-bg-surface); }
.session-row.active { background: rgba(99,102,241,0.08); }

.session-avatar-wrap {
  position: relative; flex-shrink: 0; width: 34px; height: 34px;
}

.session-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: white;
}

.presence-dot {
  position: absolute; bottom: 0; right: 0;
  width: 9px; height: 9px; border-radius: 50%;
  border: 2px solid var(--cf-bg-page);
  transition: background 0.3s;
}
.presence-online  { background: #22c55e; }
.presence-away    { background: #f59e0b; }
.presence-offline { background: #475569; }

.session-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.session-top-row { display: flex; justify-content: space-between; align-items: baseline; }
.session-name { font-size: 13px; font-weight: 600; color: var(--cf-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
.session-time { font-size: 10px; color: var(--cf-text-muted); flex-shrink: 0; }
.session-preview { font-size: 12px; color: var(--cf-text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-tags { display: flex; align-items: center; gap: 6px; margin-top: 2px; }

.tag { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.tag-hot { background: rgba(239,68,68,0.12); color: #ef4444; }
.tag-converted { background: rgba(34,197,94,0.12); color: #22c55e; }
.tag-engaged { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.tag-new { background: rgba(71,85,105,0.3); color: var(--cf-text-muted); }
.heat-bar { height: 3px; border-radius: 2px; opacity: 0.6; }
.channel-badge { font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
.ch-website  { background: rgba(99,102,241,0.1); color: #a5b4fc; }
.ch-whatsapp { background: rgba(37,211,102,0.12); color: #25d366; }
.ch-messenger { background: rgba(0,132,255,0.12); color: #0084ff; }
.ch-instagram { background: rgba(225,48,108,0.12); color: #e1306c; }
.ch-telegram { background: rgba(42,171,238,0.12); color: #2aabee; }

.list-loading-more, .list-end {
  text-align: center; padding: 12px; font-size: 11px; color: var(--cf-text-muted);
}

/* ── Chat panel ──────────────────────────────────────────────────────── */
.chat-panel {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
  border-right: 1px solid var(--cf-border-subtle);
}

.empty-panel {
  align-items: center; justify-content: center;
  gap: 12px; color: var(--cf-text-muted); font-size: 14px;
}

.chat-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--cf-border-subtle);
}

.chat-user-info { display: flex; align-items: center; gap: 12px; }

.chat-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: white;
}

.chat-name { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); }
.chat-sub { font-size: 11px; color: var(--cf-text-muted); margin-top: 2px; }

.kanban-badge {
  font-size: 10px; font-weight: 700;
  padding: 3px 10px; border-radius: 20px;
  text-transform: uppercase; letter-spacing: 0.06em;
}

.messages {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 10px;
}

.message { display: flex; }
/* Agent/god-view inbox layout: the VISITOR (customer) sits on the LEFT, and
   the business side — the AI bot and you when you take over — sits on the
   RIGHT. This makes takeover read as "I'm replying to the customer", not
   "I'm chatting as the customer". */
.user-msg { justify-content: flex-start; }
.ai-msg { justify-content: flex-end; }

.bubble {
  max-width: 72%; padding: 10px 14px; border-radius: 14px;
  font-size: 13px; line-height: 1.55;
}
/* Visitor (customer) — neutral bubble on the left. */
.user-msg .bubble { background: var(--cf-chat-ai-bubble-bg); color: var(--cf-chat-ai-bubble-text); border-bottom-left-radius: 4px; }
/* AI bot — your automated side, soft indigo on the right. */
.ai-msg .bubble { background: rgba(99,102,241,0.16); color: var(--cf-text-primary); border-bottom-right-radius: 4px; }

/* ── Visitor panel ───────────────────────────────────────────────────── */
.visitor-panel {
  width: 272px; min-width: 272px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.visitor-panel-empty {
  align-items: center; justify-content: center; gap: 10px;
  color: var(--cf-text-muted); font-size: 13px;
}

.vp-section {
  padding: 16px;
  border-bottom: 1px solid var(--cf-border-subtle);
}

.customer-section { padding-bottom: 12px; }

.vp-customer-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px;
}

.vp-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: white; flex-shrink: 0;
}

.vp-customer-info { display: flex; flex-direction: column; gap: 5px; }
.vp-customer-name { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); }

.status-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 500; color: var(--cf-text-secondary);
}

.status-dot-green {
  width: 6px; height: 6px; border-radius: 50%;
  background: #22c55e; flex-shrink: 0;
}

.vp-stats-row {
  display: flex; align-items: center; gap: 8px;
}

.vp-stat {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; color: var(--cf-text-muted);
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 8px; padding: 4px 10px;
}

.first-visit-badge {
  font-size: 11px; font-weight: 600; color: #6366f1;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 20px; padding: 3px 10px;
  margin-left: auto;
}

.vp-section-title {
  font-size: 11px; font-weight: 700; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.08em;
  margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}

.vp-count {
  background: #334155; color: var(--cf-text-muted);
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
}

.vp-rows { display: flex; flex-direction: column; gap: 10px; }

.vp-row {
  display: flex; align-items: center; gap: 10px; min-height: 20px;
}

.vp-label {
  color: var(--cf-text-muted); font-size: 12px;
  flex-shrink: 0; width: 56px;
  display: flex; align-items: center;
}

.vp-value {
  font-size: 12px; color: var(--cf-text-primary);
  flex: 1; min-width: 0;
}

.vp-value.truncate {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.vp-value.mono {
  font-family: 'Fira Mono', 'JetBrains Mono', monospace;
  font-size: 11px; color: var(--cf-text-secondary);
}

.assignee-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: #f59e0b; color: white;
  font-size: 10px; font-weight: 700; margin-right: 5px;
}

.device-row {
  display: flex; align-items: center; gap: 6px;
}

.device-icon { color: var(--cf-text-muted); display: flex; align-items: center; }

.os-badge {
  font-size: 10px; font-weight: 600; color: var(--cf-text-muted);
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  border-radius: 4px; padding: 1px 6px;
}

/* Tags */
.vp-tags-row { display: flex; flex-wrap: wrap; gap: 6px; }

.vp-tag {
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 20px;
  text-transform: capitalize;
}

.vp-tag-state {
  background: rgba(71,85,105,0.3); color: var(--cf-text-muted);
}

/* Visited pages */
.vp-pages { display: flex; flex-direction: column; gap: 10px; }

.vp-page-row {
  display: flex; align-items: flex-start; gap: 8px;
}

.page-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #334155; flex-shrink: 0; margin-top: 4px;
}
.page-dot-active { background: #22c55e; }

.page-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.page-title-text { font-size: 12px; color: var(--cf-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.page-duration { font-size: 10px; color: var(--cf-text-muted); }

/* No data placeholder */
.vp-no-data {
  padding: 24px 16px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.vp-no-data p { font-size: 12px; color: var(--cf-text-muted); line-height: 1.6; }

@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ── Takeover styles ─────────────────────────────────────────────────────── */
.takeover-dot { font-size: 10px; }

.takeover-status-badge {
  font-size: 11px; font-weight: 600; color: #fbbf24;
  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.25);
  border-radius: 20px; padding: 3px 10px; white-space: nowrap;
}

.takeover-btn {
  padding: 5px 14px; font-size: 12px; font-weight: 600;
  background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc; border-radius: 8px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.takeover-btn:hover:not(:disabled) { background: rgba(99,102,241,0.25); }
.takeover-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.release-btn {
  padding: 5px 14px; font-size: 12px; font-weight: 600;
  background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25);
  color: #fca5a5; border-radius: 8px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.release-btn:hover:not(:disabled) { background: rgba(239,68,68,0.2); }
.release-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.takeover-banner {
  padding: 10px 20px;
  background: rgba(251,191,36,0.08);
  border-bottom: 1px solid rgba(251,191,36,0.2);
  font-size: 12px; font-weight: 600; color: #fbbf24;
  flex-shrink: 0;
}

.admin-input-wrap { flex-shrink: 0; border-top: 1px solid rgba(99,102,241,0.2); background: rgba(99,102,241,0.04); }
.admin-input-area {
  display: flex; gap: 8px; align-items: flex-end;
  padding: 12px 16px;
}

/* Attachment controls (QA #3) */
.hidden-file { display: none; }
.attach-btn {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  background: var(--cf-bg-input); border: 1px solid rgba(99,102,241,0.3);
  color: var(--cf-text-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all .15s;
}
.attach-btn:hover:not(:disabled) { color: #a5b4fc; border-color: rgba(99,102,241,0.6); }
.attach-btn:disabled { opacity: .5; cursor: not-allowed; }
.attach-btn.recording { color: #ef4444; border-color: #ef4444; }

.pending-atts { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 16px 0; }
.pending-att { position: relative; display: flex; align-items: center; gap: 6px; background: var(--cf-bg-input); border: 1px solid var(--cf-border-default); border-radius: 8px; padding: 4px 8px; font-size: 11px; color: var(--cf-text-secondary); }
.pending-thumb { width: 28px; height: 28px; object-fit: cover; border-radius: 5px; }
.pending-remove { background: none; border: none; color: var(--cf-text-muted); font-size: 16px; cursor: pointer; line-height: 1; }
.pending-remove:hover { color: #ef4444; }

.recording-bar { display: flex; align-items: center; gap: 8px; padding: 8px 16px 0; font-size: 12px; color: #ef4444; font-weight: 600; }
.rec-dot { width: 8px; height: 8px; border-radius: 50%; background: #ef4444; animation: pulse 1s infinite; }
.rec-stop { margin-left: auto; background: #ef4444; color: #fff; border: none; border-radius: 6px; padding: 3px 10px; font-size: 11px; font-weight: 600; cursor: pointer; }

/* Attachment bubbles */
.bubble-attachments { display: flex; flex-direction: column; gap: 6px; margin-bottom: 4px; }
.att-image { max-width: 220px; max-height: 220px; border-radius: 8px; cursor: pointer; display: block; }
.att-audio { max-width: 240px; height: 36px; }
.att-file { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #a5b4fc; text-decoration: none; padding: 6px 8px; background: rgba(99,102,241,0.1); border-radius: 6px; }
.att-file:hover { background: rgba(99,102,241,0.18); }

.admin-textarea {
  flex: 1; background: var(--cf-bg-input);
  border: 1px solid rgba(99,102,241,0.3); border-radius: 10px;
  padding: 9px 12px; font-size: 13px; color: var(--cf-text-primary);
  font-family: inherit; resize: none; outline: none;
  transition: border-color 0.15s;
}
.admin-textarea:focus { border-color: rgba(99,102,241,0.6); }

.admin-send-btn {
  width: 36px; height: 36px; border-radius: 10px;
  background: #6366f1; border: none; color: white;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: opacity 0.15s;
}
.admin-send-btn:hover:not(:disabled) { opacity: 0.85; }
.admin-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.send-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* You (admin) after takeover — solid accent on the right, clearly distinct
   from the AI's soft-indigo bubble so it's obvious a human is now replying. */
.admin-msg { flex-direction: column; align-items: flex-end; }
.admin-msg .bubble { background: #6366f1; color: #fff; border-bottom-right-radius: 4px; }
.msg-role-label { font-size: 10px; font-weight: 600; color: #6366f1; margin-bottom: 2px; align-self: flex-end; }

.header-right-actions {
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}

/* Mobile navigation buttons */
.mobile-back-btn { display: none; }
.mobile-info-btn { display: none; }
.vp-mobile-back { display: none; }

/* ── Mobile: single-panel navigation ─────────────────────────────────── */
@media (max-width: 768px) {
  .inbox-page {
    padding: 14px 12px 0;
    height: calc(100vh - 53px); /* subtract mobile topbar */
  }

  .inbox-layout {
    position: relative;
    flex: 1;
    overflow: hidden;
  }

  /* Hide non-active panels on mobile */
  .session-list.mobile-hidden,
  .chat-panel.mobile-hidden,
  .visitor-panel.mobile-hidden {
    display: none !important;
  }

  /* Full-width single panels on mobile */
  .session-list {
    width: 100%; min-width: 0;
    height: 100%;
    border-right: none;
    overflow-y: auto;
  }

  .chat-panel {
    width: 100%; min-width: 0;
    height: 100%;
    border-right: none;
  }

  .visitor-panel {
    width: 100%; min-width: 0;
    border-left: none;
  }

  /* Show mobile navigation buttons */
  .mobile-back-btn {
    display: flex; align-items: center; gap: 4px;
    background: none; border: none; color: #a5b4fc;
    font-size: 13px; font-weight: 500; cursor: pointer;
    padding: 4px 0; flex-shrink: 0;
  }

  .mobile-info-btn {
    display: flex; align-items: center; justify-content: center;
    background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
    border-radius: 8px; color: var(--cf-text-muted); cursor: pointer;
    width: 32px; height: 32px; flex-shrink: 0;
  }

  .vp-mobile-back {
    display: block;
    padding: 12px 16px;
    border-bottom: 1px solid var(--cf-border-subtle);
  }

  /* Compact header on mobile */
  .takeover-status-badge { display: none; }
  .kanban-badge { display: none; }
}

/* Tags */
.vp-tag-custom { background: rgba(99,102,241,0.1); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.2); display: inline-flex; align-items: center; gap: 4px; }
.tag-del { background: none; border: none; color: #818cf8; cursor: pointer; font-size: 10px; padding: 0 2px; line-height: 1; }
.tag-input-row { display: flex; gap: 6px; margin-top: 8px; }
.tag-input { flex: 1; background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default); border-radius: 7px; padding: 5px 10px; font-size: 12px; color: var(--cf-text-primary); outline: none; }
.tag-input:focus { border-color: rgba(99,102,241,0.4); }
.tag-add-btn { background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25); color: #a5b4fc; border-radius: 7px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
.tag-add-btn:hover:not(:disabled) { background: rgba(99,102,241,0.2); }
.tag-add-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.tag-error { font-size: 11px; color: #fca5a5; margin-top: 4px; }

/* ── EMA Behavioral Score Bars ──────────────────────────────────── */
.ema-scores { display: flex; flex-direction: column; gap: 10px; }

.ema-row { display: flex; flex-direction: column; gap: 4px; }

.ema-header {
  display: flex; align-items: center; justify-content: space-between;
}

.ema-label {
  font-size: 11px; color: var(--cf-text-muted); font-weight: 500;
}

.ema-value {
  font-size: 11px; font-weight: 600; display: flex; align-items: center; gap: 3px;
}

.trend-up    { color: #4ade80; }
.trend-down  { color: #f87171; }
.trend-flat  { color: var(--cf-text-muted); }

.ema-trend-icon { font-size: 10px; }

.ema-track {
  height: 5px; border-radius: 3px;
  background: var(--cf-border-subtle); overflow: hidden;
}

.ema-fill {
  height: 100%; border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 2px;
}

.intent-fill  { background: linear-gradient(90deg, #6366f1, #818cf8); }
.budget-fill  { background: linear-gradient(90deg, #22c55e, #4ade80); }
.urgency-fill { background: linear-gradient(90deg, #f59e0b, #fcd34d); }

.heat-composite {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 4px; padding-top: 8px;
  border-top: 1px solid var(--cf-border-subtle);
}

.heat-chip {
  font-size: 11px; font-weight: 700; color: white;
  padding: 2px 8px; border-radius: 8px;
}

/* ── Hot signals ─────────────────────────────────────────────────────────── */
.hot-signals-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.hot-signal-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: var(--cf-bg-input);
  border-radius: 7px;
  border: 1px solid var(--cf-border-subtle);
}
.signal-icon { font-size: 13px; flex-shrink: 0; }
.signal-label { font-size: 12px; color: var(--cf-text-secondary); flex: 1; }
.signal-value {
  font-size: 11px; font-weight: 600;
  padding: 2px 7px; border-radius: 6px;
}
.sig-high  { background: rgba(239,68,68,0.15);  color: #ef4444; }
.sig-med   { background: rgba(245,158,11,0.15); color: #f59e0b; }
.sig-low   { background: rgba(100,116,139,0.15); color: #64748b; }

/* ── Activity timeline ───────────────────────────────────────────────────── */
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 320px;
  overflow-y: auto;
  scrollbar-width: thin;
}
.timeline-list::-webkit-scrollbar { width: 4px; }
.timeline-list::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.25); border-radius: 4px; }
.timeline-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  background: var(--cf-bg-input);
  border-radius: 6px;
  border-left: 2px solid transparent;
  transition: background 0.15s;
}
.timeline-row:hover { background: var(--cf-bg-ghost-hover); }
.tl-icon {
  font-size: 13px;
  flex-shrink: 0;
  width: 18px;
  text-align: center;
  line-height: 1.4;
}
.tl-body { flex: 1; min-width: 0; }
.tl-label {
  font-size: 12px;
  color: var(--cf-text-secondary);
  line-height: 1.4;
  word-break: break-word;
}
.tl-meta {
  font-size: 10px;
  color: var(--cf-text-muted);
  margin-top: 1px;
}
.timeline-row:has(.tl-add_to_cart) { border-left-color: #f59e0b; }
.timeline-row:has(.tl-rage_click)  { border-left-color: #ef4444; }
.timeline-row:has(.tl-cta_click)   { border-left-color: #6366f1; }
</style>
