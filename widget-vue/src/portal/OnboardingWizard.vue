<template>
  <div class="flex h-screen overflow-hidden">

    <!-- Left: steps panel -->
    <div class="w-[52%] min-w-[480px] flex flex-col bg-background border-r border-border px-12 py-8 overflow-y-auto">

      <!-- Top bar -->
      <div class="flex items-center justify-between mb-12 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
            <Zap class="h-4 w-4 text-primary" />
          </div>
          <span class="text-sm font-bold tracking-tight text-foreground">Checkfunnel</span>
        </div>
        <!-- Step dots -->
        <div class="flex items-center gap-1.5">
          <span
            v-for="n in 4" :key="n"
            class="h-2 rounded-full transition-all"
            :class="[
              step >= n ? 'bg-primary' : 'bg-muted',
              step === n ? 'w-6' : 'w-2',
            ]"
          ></span>
        </div>
      </div>

      <!-- Step content -->
      <div class="flex-1 flex flex-col justify-center">

        <!-- Step 1: Goal -->
        <div v-if="step === 1" class="flex flex-col gap-7 max-w-md">
          <h1 class="text-3xl font-bold tracking-tight text-foreground leading-tight">
            What should <span class="text-primary">{{ clientName }}</span> do first?
          </h1>
          <div class="flex flex-col gap-2.5">
            <button
              v-for="goal in goals" :key="goal.value"
              class="flex items-center gap-4 rounded-xl border px-5 py-4 text-left text-sm font-medium transition-all"
              :class="form.primary_goal === goal.value ? 'border-primary bg-primary/5 text-foreground' : 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground'"
              @click="form.primary_goal = goal.value"
            >
              <span class="text-xl">{{ goal.icon }}</span>
              {{ goal.label }}
            </button>
          </div>
          <div class="flex">
            <button class="rounded-xl bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40" :disabled="!form.primary_goal" @click="goNext">Next →</button>
          </div>
        </div>

        <!-- Step 2: Website URL -->
        <div v-if="step === 2" class="flex flex-col gap-6 max-w-md">
          <div>
            <h1 class="text-3xl font-bold tracking-tight text-foreground">Train your chatbot on your website</h1>
            <p class="text-sm text-muted-foreground mt-2">Paste your website URL and we'll automatically learn your content.</p>
          </div>
          <div class="flex gap-2">
            <input
              v-model="form.domain_url"
              type="url"
              class="flex-1 rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="https://yoursite.com/"
              @keyup.enter="triggerScrape"
            />
            <button
              class="rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40 flex items-center gap-2"
              @click="triggerScrape"
              :disabled="scraping || !form.domain_url"
            >
              <Loader2 v-if="scraping" class="h-4 w-4 animate-spin" />
              <span v-else>Train</span>
            </button>
          </div>

          <!-- Progress -->
          <div v-if="scraping || scrapeStatus === 'DONE' || scrapeStatus === 'FAILED'" class="space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-muted-foreground">
                <span v-if="scraping">Scanning pages…</span>
                <span v-else-if="scrapeStatus === 'DONE'" class="text-emerald-600">Training complete</span>
                <span v-else-if="scrapeStatus === 'FAILED'" class="text-red-500">Training failed — try again</span>
              </span>
              <span v-if="scrapePages > 0" class="font-medium text-primary">{{ scrapePages }} pages</span>
            </div>
            <div class="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="scrapeStatus === 'DONE' ? 'bg-emerald-500' : scrapeStatus === 'FAILED' ? 'bg-red-500' : 'bg-primary'"
                :style="{ width: progressPct + '%' }"
              ></div>
            </div>
          </div>

          <!-- Checklist -->
          <div class="space-y-2.5">
            <div class="flex items-center gap-2.5 text-sm" :class="form.domain_url ? 'text-emerald-600' : 'text-muted-foreground'">
              <div v-if="form.domain_url" class="h-4 w-4 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                <Check class="h-2.5 w-2.5 text-white" />
              </div>
              <div v-else class="h-4 w-4 rounded-full border-2 border-muted-foreground shrink-0"></div>
              Set website URL
            </div>
            <div class="flex items-center gap-2.5 text-sm" :class="scrapeStatus === 'DONE' ? 'text-emerald-600' : 'text-muted-foreground'">
              <div v-if="scrapeStatus === 'DONE'" class="h-4 w-4 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                <Check class="h-2.5 w-2.5 text-white" />
              </div>
              <div v-else class="h-4 w-4 rounded-full border-2 border-muted-foreground shrink-0"></div>
              Train on content
            </div>
          </div>

          <div class="flex items-center gap-3">
            <button class="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors" @click="step--">← Back</button>
            <button class="rounded-xl bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90" @click="goNext">
              {{ scrapeStatus === 'DONE' ? 'Next →' : 'Continue without training' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Chatbot setup -->
        <div v-if="step === 3" class="flex flex-col gap-6 max-w-md">
          <div>
            <h1 class="text-3xl font-bold tracking-tight text-foreground">Set up your chatbot</h1>
            <p class="text-sm text-muted-foreground mt-2">Give your chatbot a name and pick its accent color.</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Chatbot name</label>
            <input v-model="form.chatbot_name" type="text" class="rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="AI Assistant" maxlength="60" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Notification email</label>
            <input v-model="form.notification_email" type="email" class="rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="you@company.com" />
          </div>
          <div class="flex items-center gap-3">
            <button class="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors" @click="step--">← Back</button>
            <button class="rounded-xl bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90" @click="goNext">Next →</button>
          </div>
        </div>

        <!-- Step 4: Theme & color -->
        <div v-if="step === 4" class="flex flex-col gap-6 max-w-md">
          <div>
            <h1 class="text-3xl font-bold tracking-tight text-foreground">Make it feel like your brand</h1>
            <p class="text-sm text-muted-foreground mt-2">Adjust the theme and color to match your website.</p>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Theme</label>
            <div class="flex gap-3">
              <button
                v-for="t in ['light', 'dark']" :key="t"
                class="flex-1 flex flex-col items-center gap-2.5 rounded-xl border p-4 text-sm font-medium transition-all"
                :class="form.chatbot_theme === t ? 'border-primary bg-primary/5 text-foreground' : 'border-border text-muted-foreground hover:border-foreground/30'"
                @click="form.chatbot_theme = t"
              >
                <div class="w-20 h-12 rounded-lg flex items-end justify-end p-1.5" :class="t === 'light' ? 'bg-slate-100 border border-slate-200' : 'bg-slate-900 border border-slate-700'">
                  <div class="h-5 w-5 rounded-full" :class="t === 'light' ? 'bg-slate-800' : 'bg-primary'"></div>
                </div>
                <span>{{ t.charAt(0).toUpperCase() + t.slice(1) }}</span>
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Accent color</label>
            <div class="flex items-center gap-2.5 flex-wrap">
              <button
                v-for="c in presetColors" :key="c"
                class="h-7 w-7 rounded-full border-2 transition-all"
                :class="form.chatbot_color === c ? 'border-foreground ring-2 ring-primary ring-offset-1' : 'border-transparent'"
                :style="{ background: c }"
                @click="form.chatbot_color = c"
              ></button>
              <div class="flex items-center gap-2">
                <input type="color" v-model="form.chatbot_color" class="h-7 w-7 rounded-full border-none cursor-pointer p-0 bg-transparent" />
                <span class="text-xs font-mono text-muted-foreground">{{ form.chatbot_color }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <button class="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors" @click="step--">← Back</button>
            <button
              class="rounded-xl bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40 flex items-center gap-2"
              :disabled="saving"
              @click="finish"
            >
              <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
              <span v-else>Finish setup →</span>
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- Right: Widget preview -->
    <div class="flex-1 flex items-center justify-center relative transition-all" :style="previewBg">
      <span class="absolute top-6 left-1/2 -translate-x-1/2 text-[11px] font-semibold uppercase tracking-wider px-3 py-1 rounded-full bg-white/10 text-white/50">
        Widget preview
      </span>

      <!-- Floating chat bubble -->
      <div
        class="absolute bottom-10 right-10 h-14 w-14 rounded-full flex items-center justify-center shadow-xl cursor-pointer"
        :style="{ background: form.chatbot_color }"
      >
        <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" fill="white"/></svg>
      </div>

      <!-- Chat panel -->
      <div class="w-72 rounded-2xl overflow-hidden shadow-2xl" :class="form.chatbot_theme === 'dark' ? 'bg-slate-900' : 'bg-white'">
        <div class="flex items-center gap-2 px-4 py-3.5" :style="{ background: form.chatbot_color }">
          <div class="h-2 w-2 rounded-full bg-white/80"></div>
          <span class="text-sm font-semibold text-white">{{ form.chatbot_name || 'AI Assistant' }}</span>
        </div>
        <div class="px-5 py-6 text-center">
          <p class="text-2xl font-bold mb-2" :class="form.chatbot_theme === 'dark' ? 'text-white' : 'text-slate-900'">Hello! 👋</p>
          <p class="text-sm leading-relaxed" :class="form.chatbot_theme === 'dark' ? 'text-slate-400' : 'text-slate-500'">{{ greetingText }}</p>
        </div>
        <div class="px-4 pb-4 flex flex-col gap-2">
          <button class="w-full rounded-xl border py-2.5 text-sm font-semibold" :style="{ borderColor: form.chatbot_color, color: form.chatbot_color }">Let's chat</button>
          <button class="w-full rounded-xl border py-2.5 text-sm font-medium" :class="form.chatbot_theme === 'dark' ? 'border-slate-700 text-slate-400 bg-slate-800' : 'border-slate-200 text-slate-500 bg-slate-50'">Just browsing</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, Check, Loader2 } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'

const router = useRouter()
const api = useAdminApi()

const step = ref(1)
const saving = ref(false)
const scraping = ref(false)
const scrapeStatus = ref('')
const scrapePages = ref(0)
let scrapeTimer = null

const client = ref(null)
const clientName = computed(() => client.value?.name || 'your chatbot')

const form = ref({
  primary_goal: '',
  domain_url: '',
  chatbot_name: 'AI Assistant',
  notification_email: '',
  chatbot_theme: 'dark',
  chatbot_color: '#6366F1',
})

const goals = [
  { value: 'sales',   label: 'Grow sales',       icon: '📈' },
  { value: 'support', label: 'Automate support',  icon: '🤖' },
  { value: 'leads',   label: 'Generate leads',    icon: '🎯' },
]

const presetColors = ['#ffffff', '#3B82F6', '#22c55e', '#ef4444', '#6366f1', '#f59e0b']

const progressPct = computed(() => {
  if (scrapeStatus.value === 'DONE' || scrapeStatus.value === 'FAILED') return 100
  if (scraping.value) return Math.min(90, scrapePages.value * 5 + 10)
  return 0
})

const greetingText = computed(() => {
  if (form.value.primary_goal === 'sales') return 'Ready to find the perfect solution for you?'
  return "Need a hand? We'll point you in the right direction."
})

const previewBg = computed(() => ({
  background: form.value.chatbot_theme === 'dark'
    ? 'linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%)'
    : 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
}))

onMounted(async () => {
  try {
    const c = await api.getPortalClient()
    if (c) {
      client.value = c
      form.value.domain_url = c.domain_url || ''
      form.value.chatbot_name = c.chatbot_name || 'AI Assistant'
      form.value.notification_email = c.notification_email || ''
      form.value.chatbot_theme = c.chatbot_theme || 'dark'
      form.value.chatbot_color = c.chatbot_color || '#6366F1'
      form.value.primary_goal = c.primary_goal || ''
      scrapeStatus.value = c.ingestion_status === 'DONE' ? 'DONE' : ''
      scrapePages.value = c.total_pages_ingested || 0
    }
  } catch {}
})

async function saveStep() {
  if (!client.value) return
  try {
    await api.updatePortalClient(client.value.id, {
      primary_goal: form.value.primary_goal,
      domain_url: form.value.domain_url,
      chatbot_name: form.value.chatbot_name,
      notification_email: form.value.notification_email,
      chatbot_theme: form.value.chatbot_theme,
      chatbot_color: form.value.chatbot_color,
    })
  } catch {}
}

async function goNext() {
  await saveStep()
  step.value++
}

async function triggerScrape() {
  if (!client.value || !form.value.domain_url) return
  scraping.value = true
  scrapeStatus.value = 'RUNNING'
  scrapePages.value = 0
  try {
    await api.updatePortalClient(client.value.id, { domain_url: form.value.domain_url })
    await api.triggerScrape(client.value.id)
    scrapeTimer = setInterval(async () => {
      try {
        const progress = await api.getScrapeProgress(client.value.id)
        scrapePages.value = progress.pages_scraped || 0
        if (progress.status === 'DONE' || progress.status === 'FAILED') {
          scrapeStatus.value = progress.status
          scraping.value = false
          clearInterval(scrapeTimer)
        }
      } catch {}
    }, 1500)
  } catch {
    scraping.value = false
    scrapeStatus.value = 'FAILED'
  }
}

async function finish() {
  saving.value = true
  try {
    await api.updatePortalClient(client.value.id, { ...form.value, onboarding_complete: true })
    router.push('/portal/inbox')
  } catch {
    saving.value = false
  }
}
</script>
