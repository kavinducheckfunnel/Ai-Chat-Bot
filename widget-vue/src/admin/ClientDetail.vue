<template>
  <div class="flex flex-col gap-6 p-6 max-w-4xl">

    <div v-if="loading" class="flex flex-col items-center gap-3 py-16 text-muted-foreground">
      <Loader2 class="h-6 w-6 animate-spin" />
      <p class="text-sm">Loading client…</p>
    </div>

    <template v-else-if="client">

      <!-- Header -->
      <div class="flex items-start justify-between gap-4 shrink-0">
        <div class="flex items-center gap-4">
          <button class="flex items-center h-9 w-9 justify-center rounded-xl border border-border bg-background text-muted-foreground hover:bg-muted transition-colors" @click="$router.push('/admin/clients')">
            <ArrowLeft class="h-4 w-4" />
          </button>
          <div class="h-11 w-11 rounded-[11px] text-white text-sm font-bold flex items-center justify-center shrink-0" :style="{ background: client.chatbot_color || 'hsl(var(--primary))' }">
            {{ client.name.slice(0, 2).toUpperCase() }}
          </div>
          <div>
            <h1 class="text-xl font-semibold text-foreground">{{ client.name }}</h1>
            <a v-if="client.domain_url" :href="client.domain_url" target="_blank" class="text-xs text-primary hover:underline">{{ client.domain_url }}</a>
          </div>
        </div>
        <div class="flex items-center gap-2.5">
          <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold uppercase tracking-wider" :class="ingestionBadgeClass(client.ingestion_status)">
            {{ client.ingestion_status || 'PENDING' }}
          </span>
          <Button size="sm" @click="triggerScrape" :disabled="scraping || !client.domain_url" class="gap-2">
            <Loader2 v-if="scraping" class="h-3.5 w-3.5 animate-spin" />
            <RefreshCw v-else class="h-3.5 w-3.5" />
            {{ scraping ? 'Syncing…' : 'Sync Now' }}
          </Button>
        </div>
      </div>

      <!-- Scrape Progress -->
      <div v-if="scrapeProgress" class="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3.5">
        <div class="flex items-center justify-between mb-2.5">
          <span class="flex items-center gap-2 text-sm font-semibold text-blue-700">
            <span class="h-2 w-2 rounded-full bg-blue-500 animate-pulse shrink-0"></span>
            {{ scrapeProgress.phase === 'crawling' ? 'Crawling pages…' : 'Generating embeddings…' }}
          </span>
          <span v-if="scrapeProgress.total > 0" class="text-xs font-medium text-blue-600">{{ scrapeProgress.done }} / {{ scrapeProgress.total }} chunks</span>
          <span v-else-if="scrapeProgress.phase === 'crawling'" class="text-xs font-medium text-blue-600">Discovering pages…</span>
        </div>
        <div class="h-1.5 rounded-full bg-blue-200 overflow-hidden">
          <div
            class="h-full rounded-full transition-[width]"
            :class="{ 'scrape-indeterminate': scrapeProgress.total === 0 }"
            :style="{ width: scrapeProgress.total > 0 ? Math.round(scrapeProgress.done / scrapeProgress.total * 100) + '%' : '30%', background: 'linear-gradient(90deg,#3B82F6,#6366F1)' }"
          ></div>
        </div>
        <p class="text-[11px] text-blue-400 mt-2">This may take a few minutes depending on the size of your website.</p>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-border gap-1">
        <button
          v-for="tab in tabs" :key="tab.id"
          class="px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- ── OVERVIEW ── -->
      <div v-if="activeTab === 'overview'" class="flex flex-col gap-5">
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card v-for="stat in overviewStats" :key="stat.label">
            <CardContent class="pt-4 pb-4">
              <p class="text-xs text-muted-foreground mb-1">{{ stat.label }}</p>
              <p class="text-2xl font-bold tracking-tight" :class="stat.color || 'text-foreground'">{{ stat.value }}</p>
            </CardContent>
          </Card>
        </div>

        <Card v-if="analytics?.funnel">
          <CardContent class="pt-5">
            <h3 class="text-sm font-semibold text-foreground mb-4">Conversion Funnel</h3>
            <div class="flex flex-col gap-3">
              <div v-for="stage in funnelStages" :key="stage.key" class="flex items-center gap-3">
                <span class="text-xs text-muted-foreground w-24 shrink-0">{{ stage.label }}</span>
                <div class="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                  <div class="h-full rounded-full transition-[width]" :class="stage.barClass" :style="{ width: funnelWidth(stage.key) }"></div>
                </div>
                <span class="text-xs font-semibold text-foreground w-6 text-right">{{ analytics.funnel[stage.key] || 0 }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="pt-5">
            <div class="mb-4">
              <h3 class="text-sm font-semibold text-foreground mb-0.5">WordPress Installation</h3>
              <p class="text-xs text-muted-foreground">Choose the method that works best for your site.</p>
            </div>
            <div class="flex gap-2 mb-4">
              <button class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors" :class="embedMethod === 'plugin' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'" @click="embedMethod = 'plugin'">
                <Layers class="h-3.5 w-3.5" /> Plugin (Recommended)
              </button>
              <button class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors" :class="embedMethod === 'php' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'" @click="embedMethod = 'php'">
                <Code2 class="h-3.5 w-3.5" /> functions.php
              </button>
            </div>

            <div v-if="embedMethod === 'plugin'" class="flex flex-col gap-3">
              <ol class="flex flex-col gap-2 pl-5 list-decimal">
                <li class="text-xs text-muted-foreground leading-relaxed">In your WordPress dashboard, go to <strong class="text-foreground">Plugins → Add New</strong> and search for <strong class="text-foreground">"WPCode"</strong>. Install and activate it.</li>
                <li class="text-xs text-muted-foreground leading-relaxed">Go to <strong class="text-foreground">Code Snippets → Header &amp; Footer</strong> in your WordPress menu.</li>
                <li class="text-xs text-muted-foreground leading-relaxed">Paste the snippet below into the <strong class="text-foreground">Footer</strong> section and click <strong class="text-foreground">Save Changes</strong>.</li>
              </ol>
              <div class="flex items-start gap-3 rounded-lg bg-slate-900 px-4 py-3.5">
                <code class="flex-1 text-xs text-indigo-300 font-mono leading-relaxed break-all">{{ embedCode }}</code>
                <button class="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/10 text-slate-300 hover:bg-white/15 px-2.5 py-1.5 text-xs font-medium transition-colors shrink-0" @click="copyCode(embedCode, 'plugin')">
                  <Check v-if="copiedKey === 'plugin'" class="h-3.5 w-3.5 text-emerald-400" />
                  <Copy v-else class="h-3.5 w-3.5" />
                  {{ copiedKey === 'plugin' ? 'Copied!' : 'Copy' }}
                </button>
              </div>
            </div>

            <div v-if="embedMethod === 'php'" class="flex flex-col gap-3">
              <ol class="flex flex-col gap-2 pl-5 list-decimal">
                <li class="text-xs text-muted-foreground leading-relaxed">In your WordPress dashboard, go to <strong class="text-foreground">Appearance → Theme File Editor</strong>.</li>
                <li class="text-xs text-muted-foreground leading-relaxed">Select <strong class="text-foreground">functions.php</strong> from the file list on the right.</li>
                <li class="text-xs text-muted-foreground leading-relaxed">Paste the snippet below at the bottom of the file and click <strong class="text-foreground">Update File</strong>.</li>
              </ol>
              <div class="flex items-start gap-3 rounded-lg bg-slate-900 px-4 py-3.5">
                <code class="flex-1 text-xs text-indigo-300 font-mono leading-relaxed whitespace-pre break-all">{{ phpSnippet }}</code>
                <button class="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/10 text-slate-300 hover:bg-white/15 px-2.5 py-1.5 text-xs font-medium transition-colors shrink-0" @click="copyCode(phpSnippet, 'php')">
                  <Check v-if="copiedKey === 'php'" class="h-3.5 w-3.5 text-emerald-400" />
                  <Copy v-else class="h-3.5 w-3.5" />
                  {{ copiedKey === 'php' ? 'Copied!' : 'Copy' }}
                </button>
              </div>
            </div>

            <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3.5">
              <p class="text-xs font-semibold text-emerald-700 mb-1.5">WordPress Webhook URL (WooCommerce auto-sync):</p>
              <code class="block text-xs font-mono text-emerald-800 bg-black/5 rounded px-2.5 py-1.5 mb-2 break-all">{{ webhookUrl }}</code>
              <p class="text-[11px] text-muted-foreground">In WooCommerce → Settings → Advanced → Webhooks — add a "Product Updated" webhook pointing to this URL to auto-sync content changes.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- ── ANALYTICS ── -->
      <div v-if="activeTab === 'analytics'" class="flex flex-col gap-5">
        <div v-if="!analytics" class="flex justify-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
        <template v-else>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card v-for="stat in analyticsStats" :key="stat.label">
              <CardContent class="pt-4 pb-4">
                <p class="text-xs text-muted-foreground mb-1">{{ stat.label }}</p>
                <p class="text-2xl font-bold tracking-tight" :class="stat.color || 'text-foreground'">{{ stat.value }}</p>
              </CardContent>
            </Card>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Card>
              <CardContent class="pt-5">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Heat Distribution</h3>
                <div class="flex h-3 rounded-full overflow-hidden gap-0.5 mb-3.5">
                  <div class="rounded-full bg-blue-500 transition-all" :style="{ flex: analytics.heat_distribution?.cold || 0.01 }"></div>
                  <div class="rounded-full bg-orange-500 transition-all" :style="{ flex: analytics.heat_distribution?.warm || 0.01 }"></div>
                  <div class="rounded-full bg-red-500 transition-all" :style="{ flex: analytics.heat_distribution?.hot || 0.01 }"></div>
                </div>
                <div class="flex gap-4">
                  <div v-for="item in heatLegend" :key="item.label" class="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span class="h-2 w-2 rounded-full shrink-0" :class="item.dot"></span>
                    {{ item.label }} <strong class="text-foreground ml-1">{{ item.count ?? 0 }}</strong>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent class="pt-5">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Avg Engagement Scores</h3>
                <div class="flex flex-col gap-3.5">
                  <div v-for="g in emaGauges" :key="g.label" class="flex items-center gap-3">
                    <span class="text-xs text-muted-foreground w-12 shrink-0">{{ g.label }}</span>
                    <div class="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full transition-[width]" :style="{ width: (g.value || 0) + '%', background: g.gradient }"></div>
                    </div>
                    <span class="text-xs font-semibold text-foreground w-9 text-right">{{ g.value ?? 0 }}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent class="pt-5">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Sessions — Last 14 Days</h3>
              <svg v-if="analytics.daily_trend?.length" class="w-full h-16 block" viewBox="0 0 340 60" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="anGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="hsl(var(--primary))" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="hsl(var(--primary))" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <polyline :points="analyticsSparklineArea" fill="url(#anGrad)" stroke="none"/>
                <polyline :points="analyticsSparklinePoints" fill="none" stroke="hsl(var(--primary))" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
              </svg>
              <p v-else class="text-xs text-muted-foreground text-center py-5">No sessions in the last 14 days</p>
              <div v-if="analytics.daily_trend?.length" class="flex justify-between text-[11px] text-muted-foreground mt-1">
                <span>{{ analytics.daily_trend[0].date }}</span>
                <span>{{ analytics.daily_trend[analytics.daily_trend.length - 1].date }}</span>
              </div>
            </CardContent>
          </Card>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Card>
              <CardContent class="pt-5">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Kanban Breakdown</h3>
                <div class="flex flex-col gap-2.5">
                  <div v-for="(col, key) in kanbanCols" :key="key" class="flex items-center gap-2.5">
                    <span class="h-2.5 w-2.5 rounded-full shrink-0" :style="{ background: col.color }"></span>
                    <span class="flex-1 text-xs text-muted-foreground">{{ col.label }}</span>
                    <span class="text-xs font-bold text-foreground">{{ analytics.kanban_breakdown?.[key] ?? 0 }}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent class="pt-5">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Behavioral Events</h3>
                <div class="flex flex-col gap-3">
                  <div v-for="ev in behavioralEvents" :key="ev.label" class="flex items-center gap-3">
                    <div class="h-9 w-9 rounded-xl flex items-center justify-center shrink-0" :style="{ background: ev.bgColor, color: ev.iconColor }">
                      <component :is="ev.icon" class="h-4 w-4" />
                    </div>
                    <div>
                      <p class="text-xs text-muted-foreground">{{ ev.label }}</p>
                      <p class="text-lg font-bold text-foreground">{{ ev.value }}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </template>
      </div>

      <!-- ── SESSIONS ── -->
      <div v-if="activeTab === 'sessions'" class="flex flex-col gap-4">
        <div class="flex flex-wrap gap-2 items-center">
          <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input v-model="sessionFilters.q" class="pl-8 pr-3 h-8 rounded-lg border border-border bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary w-40" placeholder="Search email…" />
          </div>
          <select v-model="sessionFilters.state" class="h-8 rounded-lg border border-border bg-background text-xs px-2.5 focus:outline-none focus:ring-1 focus:ring-primary">
            <option value="">All states</option>
            <option value="RESEARCH">Research</option>
            <option value="EVALUATION">Evaluation</option>
            <option value="OBJECTION">Objection</option>
            <option value="RECOVERY">Recovery</option>
            <option value="READY_TO_BUY">Ready to Buy</option>
          </select>
          <input v-model="sessionFilters.date_from" type="date" class="h-8 rounded-lg border border-border bg-background text-xs px-2.5 w-32 focus:outline-none focus:ring-1 focus:ring-primary" />
          <input v-model="sessionFilters.date_to" type="date" class="h-8 rounded-lg border border-border bg-background text-xs px-2.5 w-32 focus:outline-none focus:ring-1 focus:ring-primary" />
          <input v-model="sessionFilters.min_heat" type="number" min="0" max="100" class="h-8 rounded-lg border border-border bg-background text-xs px-2.5 w-24 focus:outline-none focus:ring-1 focus:ring-primary" placeholder="Min heat" />
          <input v-model="sessionFilters.max_heat" type="number" min="0" max="100" class="h-8 rounded-lg border border-border bg-background text-xs px-2.5 w-24 focus:outline-none focus:ring-1 focus:ring-primary" placeholder="Max heat" />
          <label class="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground select-none">
            <input v-model="sessionFilters.has_lead" type="checkbox" class="accent-primary" /> Has lead
          </label>
        </div>

        <div v-if="loadingSessions" class="flex justify-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
        <div v-else-if="!sessions.length" class="flex flex-col items-center gap-2 py-12 text-muted-foreground">
          <MessageSquare class="h-8 w-8 opacity-30" />
          <p class="text-sm">No sessions match the current filters.</p>
        </div>
        <Card v-else>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-border">
                  <th class="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Visitor</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Heat</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">State</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Msgs</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Last Active</th>
                  <th class="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in sessions" :key="s.session_id" class="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                  <td class="px-4 py-3">
                    <p class="text-xs font-mono text-muted-foreground">{{ s.visitor_id?.slice(0, 16) }}…</p>
                    <p v-if="s.lead_email" class="text-[11px] text-primary">{{ s.lead_email }}</p>
                  </td>
                  <td class="px-4 py-3">
                    <p class="text-sm font-bold mb-1" :class="heatTextClass(s.heat_score)">{{ s.heat_score }}%</p>
                    <div class="h-1 w-14 rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full" :style="{ width: s.heat_score + '%', background: heatColor(s.heat_score) }"></div>
                    </div>
                  </td>
                  <td class="px-4 py-3">
                    <span class="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider" :class="stateClass(s.conversation_state)">
                      {{ s.conversation_state.replace('_', ' ') }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-sm font-semibold text-foreground">{{ s.message_count }}</td>
                  <td class="px-4 py-3 text-xs text-muted-foreground">{{ timeAgo(s.updated_at) }}</td>
                  <td class="px-4 py-3">
                    <button class="rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors" @click="viewSession(s)">View</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <!-- ── SETTINGS ── -->
      <div v-if="activeTab === 'settings'">
        <Card>
          <CardContent class="pt-5 flex flex-col gap-6">
            <div>
              <h3 class="text-sm font-semibold text-foreground pb-3 border-b border-border mb-4">Chatbot Branding</h3>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-medium text-muted-foreground">Display Name</label>
                  <input v-model="settingsForm.chatbot_name" type="text" placeholder="AI Assistant" class="h-9 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                </div>
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-medium text-muted-foreground">Theme Color</label>
                  <div class="flex gap-2 items-center">
                    <input type="color" v-model="settingsForm.chatbot_color" class="h-9 w-9 rounded-lg border border-border p-0.5 cursor-pointer" />
                    <input v-model="settingsForm.chatbot_color" type="text" class="flex-1 h-9 rounded-lg border border-border bg-background px-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                  </div>
                </div>
                <div class="flex flex-col gap-1.5 sm:col-span-2">
                  <label class="text-xs font-medium text-muted-foreground">Logo URL (optional)</label>
                  <input v-model="settingsForm.chatbot_logo_url" type="url" placeholder="https://…" class="h-9 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                </div>
              </div>
            </div>

            <div>
              <h3 class="text-sm font-semibold text-foreground pb-3 border-b border-border mb-4">FOMO Engine</h3>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-1.5 sm:col-span-2">
                  <label class="text-xs font-medium text-muted-foreground">Discount Code</label>
                  <input v-model="settingsForm.discount_code" type="text" placeholder="SAVE20" class="h-9 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                  <p class="text-[11px] text-muted-foreground">Sent to high-intent visitors (heat score ≥ 75)</p>
                </div>
                <div class="flex flex-col gap-1.5 sm:col-span-2">
                  <label class="text-xs font-medium text-muted-foreground">CTA Message</label>
                  <input v-model="settingsForm.cta_message" type="text" class="h-9 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                </div>
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-medium text-muted-foreground">Countdown (seconds)</label>
                  <input v-model="settingsForm.fomo_countdown_seconds" type="number" min="60" max="3600" class="h-9 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                </div>
              </div>
            </div>

            <div v-if="saveError" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ saveError }}</div>
            <div v-if="saveSuccess" class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">Settings saved!</div>

            <Button @click="saveSettings" :disabled="saving" class="w-fit gap-2">
              <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
              Save Changes
            </Button>
          </CardContent>
        </Card>
      </div>

    </template>

    <!-- Session Chat Modal -->
    <div v-if="selectedSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="selectedSession = null">
      <div class="bg-background border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-xl">
        <div class="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 class="text-base font-semibold text-foreground">Chat History</h3>
            <p class="text-xs text-muted-foreground font-mono mt-0.5">{{ selectedSession.visitor_id }}</p>
          </div>
          <button class="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors" @click="selectedSession = null">
            <X class="h-4 w-4" />
          </button>
        </div>
        <div v-if="loadingSession" class="flex justify-center items-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
        <div v-else class="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <div
            v-for="(msg, i) in sessionDetail?.chat_history || []"
            :key="i"
            class="flex flex-col max-w-[85%]"
            :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
          >
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
            <p class="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl m-0" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'">
              {{ msg.message || msg.content }}
            </p>
          </div>
          <p v-if="!sessionDetail?.chat_history?.length" class="text-sm text-muted-foreground text-center py-6">No chat history.</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'
import { ArrowLeft, RefreshCw, Loader2, Search, MessageSquare, X, Copy, Check, Layers, Code2, Eye, DoorOpen, Tag } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

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
  state: '', date_from: '', date_to: '', min_heat: '', max_heat: '', has_lead: false, q: '',
})

const tabs = [
  { id: 'overview',  label: 'Overview' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'sessions',  label: 'Sessions' },
  { id: 'settings',  label: 'Settings' },
]

const funnelStages = [
  { key: 'RESEARCH',    label: 'Research',    barClass: 'bg-blue-500' },
  { key: 'EVALUATION',  label: 'Evaluation',  barClass: 'bg-yellow-500' },
  { key: 'OBJECTION',   label: 'Objection',   barClass: 'bg-red-500' },
  { key: 'RECOVERY',    label: 'Recovery',    barClass: 'bg-orange-500' },
  { key: 'READY_TO_BUY', label: 'Ready to Buy', barClass: 'bg-emerald-500' },
]

const kanbanCols = {
  NEW:       { label: 'New',       color: '#94A3B8' },
  CONTACTED: { label: 'Contacted', color: '#3B82F6' },
  QUALIFIED: { label: 'Qualified', color: '#F97316' },
  CONVERTED: { label: 'Converted', color: '#22C55E' },
  LOST:      { label: 'Lost',      color: '#EF4444' },
}

const settingsForm = ref({
  chatbot_name: '', chatbot_color: '#3B82F6', chatbot_logo_url: '',
  discount_code: '', cta_message: '', fomo_countdown_seconds: 600,
})

const embedCode = computed(() =>
  client.value ? `<script src="${WIDGET_URL}?client_id=${client.value.id}"><\/script>` : ''
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

const overviewStats = computed(() => [
  { label: 'Total Sessions', value: analytics.value?.total_sessions ?? '—' },
  { label: 'Hot Leads',      value: analytics.value?.hot_sessions ?? '—', color: 'text-red-500' },
  { label: 'Avg. Intent',    value: analytics.value?.avg_intent != null ? analytics.value.avg_intent + '%' : '—' },
  { label: 'Pages Ingested', value: analytics.value?.pages_ingested ?? '—' },
])

const analyticsStats = computed(() => [
  { label: 'Total Sessions', value: analytics.value?.total_sessions ?? 0 },
  { label: 'Avg Heat Score', value: (analytics.value?.avg_heat_score ?? 0) + '%', color: (analytics.value?.avg_heat_score || 0) >= 70 ? 'text-red-500' : (analytics.value?.avg_heat_score || 0) >= 40 ? 'text-orange-500' : '' },
  { label: 'Leads Captured', value: analytics.value?.leads_captured ?? 0, color: 'text-primary' },
  { label: 'Hot Sessions',   value: analytics.value?.hot_sessions ?? 0, color: 'text-red-500' },
])

const heatLegend = computed(() => [
  { label: 'Cold', dot: 'bg-blue-500',   count: analytics.value?.heat_distribution?.cold },
  { label: 'Warm', dot: 'bg-orange-500', count: analytics.value?.heat_distribution?.warm },
  { label: 'Hot',  dot: 'bg-red-500',    count: analytics.value?.heat_distribution?.hot },
])

const emaGauges = computed(() => [
  { label: 'Intent', value: analytics.value?.avg_intent,  gradient: 'linear-gradient(90deg,#6366F1,#8B5CF6)' },
  { label: 'Budget', value: analytics.value?.avg_budget,  gradient: 'linear-gradient(90deg,#22C55E,#16A34A)' },
  { label: 'Urgency',value: analytics.value?.avg_urgency, gradient: 'linear-gradient(90deg,#F97316,#EF4444)' },
])

const behavioralEvents = computed(() => [
  { label: 'Page Views',           value: analytics.value?.analytics_events?.page_views ?? 0,          icon: Eye,     bgColor: 'rgba(99,102,241,0.1)', iconColor: '#6366F1' },
  { label: 'Exit Intent Triggers', value: analytics.value?.analytics_events?.exit_intent_count ?? 0,   icon: DoorOpen,bgColor: 'rgba(249,115,22,0.1)',  iconColor: '#F97316' },
  { label: 'Pricing Page Visits',  value: analytics.value?.analytics_events?.pricing_page_visits ?? 0, icon: Tag,     bgColor: 'rgba(34,197,94,0.1)',   iconColor: '#22C55E' },
])

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

function ingestionBadgeClass(status) {
  const s = (status || 'pending').toLowerCase()
  if (s === 'running') return 'bg-blue-50 text-blue-600'
  if (s === 'done')    return 'bg-emerald-50 text-emerald-600'
  if (s === 'failed')  return 'bg-red-50 text-red-600'
  return 'bg-muted text-muted-foreground'
}

function heatTextClass(score) {
  if ((score || 0) >= 70) return 'text-red-500'
  if ((score || 0) >= 40) return 'text-orange-500'
  return 'text-primary'
}

function heatColor(score) {
  if ((score || 0) >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if ((score || 0) >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
}

function stateClass(state) {
  const map = { RESEARCH: 'bg-blue-50 text-blue-700', EVALUATION: 'bg-yellow-50 text-yellow-700', OBJECTION: 'bg-red-50 text-red-700', RECOVERY: 'bg-orange-50 text-orange-700', READY_TO_BUY: 'bg-emerald-50 text-emerald-700' }
  return map[state] || 'bg-blue-50 text-blue-700'
}

function funnelWidth(key) {
  if (!analytics.value?.funnel) return '0%'
  const max = Math.max(...Object.values(analytics.value.funnel), 1)
  return ((analytics.value.funnel[key] || 0) / max * 100) + '%'
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

async function loadClient() {
  loading.value = true
  try {
    const [clientData, analyticsData] = await Promise.all([
      api.getClient(route.params.id),
      api.getClientAnalytics(route.params.id),
    ])
    client.value = clientData
    const flat = {}
    for (const [k, v] of Object.entries(analyticsData || {})) {
      flat[k] = (v && typeof v === 'object' && 'value' in v) ? v.value : v
    }
    analytics.value = flat
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
    if (sessionFilters.state)     params.state     = sessionFilters.state
    if (sessionFilters.date_from) params.date_from = sessionFilters.date_from
    if (sessionFilters.date_to)   params.date_to   = sessionFilters.date_to
    if (sessionFilters.min_heat)  params.min_heat  = sessionFilters.min_heat
    if (sessionFilters.max_heat)  params.max_heat  = sessionFilters.max_heat
    if (sessionFilters.has_lead)  params.has_lead  = 'true'
    if (sessionFilters.q)         params.q         = sessionFilters.q
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
      if (data.phase) scrapeProgress.value = { phase: data.phase, done: data.done, total: data.total }
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

onMounted(loadClient)
watch(activeTab, (tab) => { if (tab === 'sessions') loadSessions() })
watch(sessionFilters, onFilterChange)
</script>

<style scoped>
@keyframes indeterminate {
  0%   { transform: translateX(-120%); }
  100% { transform: translateX(400%); }
}
.scrape-indeterminate { animation: indeterminate 1.6s ease-in-out infinite; }
</style>
