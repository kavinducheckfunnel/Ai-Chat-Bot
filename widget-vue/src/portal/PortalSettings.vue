<template>
  <div class="flex flex-col gap-0 p-6 max-w-3xl">

    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-semibold tracking-tight">Settings</h1>
    </div>

    <!-- Tab navigation -->
    <div class="border-b border-border mb-6">
      <div class="flex gap-1">
        <button
          v-for="t in settingsTabs" :key="t"
          class="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
          :class="activeTab === t.key ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="activeTab = t.key"
        >{{ t.label }}</button>
      </div>
    </div>

    <!-- ═══ CHANNELS & EMBED TAB ═══ -->
    <div v-if="activeTab === 'channels'" class="flex flex-col gap-4">

      <!-- Website embed -->
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col gap-5">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Globe class="h-4 w-4" />
            </div>
            <div class="flex-1">
              <h2 class="text-sm font-semibold text-foreground">Website</h2>
              <p class="text-xs text-muted-foreground mt-0.5">Add the chatbot to any website with a single code snippet.</p>
            </div>
            <span class="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">Active</span>
          </div>

          <div class="rounded-lg border border-border bg-muted/30 p-4 flex flex-col gap-4">
            <p class="text-sm font-semibold text-foreground">Choose how to add the widget code</p>

            <!-- Format tabs -->
            <div class="flex gap-2">
              <button
                v-for="f in formats" :key="f.id"
                class="flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
                :class="embedFormat === f.id ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border bg-background text-muted-foreground hover:bg-muted'"
                @click="embedFormat = f.id"
              >
                <span v-html="f.icon"></span>{{ f.label }}
              </button>
            </div>

            <p class="text-xs text-muted-foreground" v-if="embedFormat === 'wordpress'">
              Paste into your theme's <code class="rounded bg-muted px-1 font-mono text-foreground">functions.php</code>, or use the "Insert Headers and Footers" plugin → Footer section.
            </p>
            <p class="text-xs text-muted-foreground" v-else-if="embedFormat === 'react'">Drop this component anywhere in your React app tree.</p>
            <p class="text-xs text-muted-foreground" v-else>Paste before the <code class="rounded bg-muted px-1 font-mono text-foreground">&lt;/body&gt;</code> tag on every page.</p>

            <!-- Code block -->
            <div v-if="props.client" class="relative rounded-lg border border-border bg-background">
              <pre class="overflow-x-auto p-4 text-xs font-mono text-muted-foreground leading-relaxed whitespace-pre"><code>{{ embedCode }}</code></pre>
              <button
                class="mt-0 flex items-center gap-2 rounded-b-lg border-t border-border px-4 py-2.5 text-xs font-semibold transition-colors w-full"
                :class="copied ? 'text-emerald-600 bg-emerald-50' : 'text-muted-foreground hover:bg-muted'"
                @click="copyCode"
              >
                <Check v-if="copied" class="h-3.5 w-3.5 text-emerald-600" />
                <Copy v-else class="h-3.5 w-3.5" />
                {{ copied ? 'Copied!' : 'Copy code' }}
              </button>
            </div>
            <div v-else class="rounded-lg border border-border bg-background p-4 animate-pulse space-y-2">
              <div class="h-3 w-full rounded bg-muted"></div>
              <div class="h-3 w-3/5 rounded bg-muted"></div>
              <div class="h-3 w-full rounded bg-muted"></div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Other channels (off) -->
      <div class="flex flex-col gap-2">
        <div v-for="ch in offChannels" :key="ch.name" class="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3">
          <div class="h-8 w-8 rounded-lg flex items-center justify-center shrink-0" :class="ch.iconBg">
            <span v-html="ch.icon"></span>
          </div>
          <div class="flex-1">
            <span class="text-sm font-medium text-foreground">{{ ch.name }}</span>
          </div>
          <span class="inline-flex rounded px-2 py-0.5 text-[10px] font-bold uppercase bg-muted text-muted-foreground">OFF</span>
          <Button variant="outline" size="sm" disabled>Configure</Button>
        </div>
      </div>
    </div>

    <!-- ═══ CHATBOT TAB ═══ -->
    <div v-if="activeTab === 'chatbot'" class="flex flex-col gap-4">

      <!-- Appearance -->
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col gap-5">
          <h2 class="text-sm font-semibold">Chatbot appearance</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Chatbot name</label>
              <input v-model="form.chatbot_name" type="text" class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="AI Assistant" maxlength="60" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Notification email</label>
              <input v-model="form.notification_email" type="email" class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="you@company.com" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Theme</label>
            <div class="flex gap-2">
              <button
                v-for="t in ['dark', 'light']" :key="t"
                class="flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors"
                :class="form.chatbot_theme === t ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'"
                @click="form.chatbot_theme = t"
              >
                <span class="h-3 w-3 rounded-full" :class="t === 'dark' ? 'bg-slate-900 border border-slate-600' : 'bg-slate-100 border border-slate-300'"></span>
                {{ t.charAt(0).toUpperCase() + t.slice(1) }}
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Accent color</label>
            <div class="flex items-center gap-2 flex-wrap">
              <button
                v-for="c in presetColors" :key="c"
                class="h-6 w-6 rounded-full border-2 transition-all"
                :class="form.chatbot_color === c ? 'border-foreground ring-2 ring-primary ring-offset-1' : 'border-transparent'"
                :style="{ background: c }"
                @click="form.chatbot_color = c"
              ></button>
              <div class="flex items-center gap-2">
                <input type="color" v-model="form.chatbot_color" class="h-6 w-6 rounded-full border-none cursor-pointer p-0 bg-transparent" />
                <span class="text-xs font-mono text-muted-foreground">{{ form.chatbot_color }}</span>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">CTA message</label>
            <input v-model="form.cta_message" type="text" class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="You're clearly ready — grab your exclusive discount:" />
          </div>

          <div class="flex items-center gap-3">
            <Button @click="saveConfig" :disabled="saving" class="gap-2">
              <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
              Save changes
            </Button>
            <span v-if="saved" class="text-sm text-emerald-600 font-medium">Changes saved.</span>
          </div>
        </CardContent>
      </Card>

      <!-- Widget feature toggles -->
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col gap-0">
          <h2 class="text-sm font-semibold mb-1">Widget features</h2>
          <p class="text-xs text-muted-foreground mb-4">Enable or disable interactive features in the chat widget.</p>
          <div class="flex flex-col divide-y divide-border">
            <div class="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div>
                <p class="text-sm font-medium text-foreground">Voice input</p>
                <p class="text-xs text-muted-foreground mt-0.5">Visitors can dictate messages using their microphone (Web Speech API)</p>
              </div>
              <button
                class="relative h-6 w-11 rounded-full border transition-colors shrink-0"
                :class="form.voice_input_enabled ? 'bg-primary border-primary' : 'bg-muted border-border'"
                @click="form.voice_input_enabled = !form.voice_input_enabled; saveConfig()"
              >
                <span class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform" :class="form.voice_input_enabled ? 'translate-x-5' : 'translate-x-0.5'"></span>
              </button>
            </div>
            <div class="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div>
                <p class="text-sm font-medium text-foreground">Image input</p>
                <p class="text-xs text-muted-foreground mt-0.5">Visitors can attach and send images in the chat</p>
              </div>
              <button
                class="relative h-6 w-11 rounded-full border transition-colors shrink-0"
                :class="form.image_input_enabled ? 'bg-primary border-primary' : 'bg-muted border-border'"
                @click="form.image_input_enabled = !form.image_input_enabled; saveConfig()"
              >
                <span class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform" :class="form.image_input_enabled ? 'translate-x-5' : 'translate-x-0.5'"></span>
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Canned responses (gated) -->
      <div class="relative">
        <div v-if="features.allow_canned_responses === false" class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-xl bg-background/90 backdrop-blur-sm border border-border text-center px-6">
          <Lock class="h-6 w-6 text-muted-foreground" />
          <div>
            <p class="text-sm font-semibold text-foreground">Canned Responses require Starter plan</p>
            <RouterLink to="/portal/billing" class="mt-1 inline-block text-xs font-medium text-primary underline">Upgrade to Starter →</RouterLink>
          </div>
        </div>
        <Card>
          <CardContent class="pt-5 pb-5 flex flex-col gap-4">
            <div>
              <h2 class="text-sm font-semibold">Canned responses</h2>
              <p class="text-xs text-muted-foreground mt-0.5">Quick-reply shortcuts available during live takeover.</p>
            </div>
            <div class="flex flex-col gap-2.5">
              <div v-for="(cr, idx) in cannedResponses" :key="cr.id" class="flex gap-2 items-start">
                <div class="flex-1 flex flex-col gap-2">
                  <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="cr.title" placeholder="Title (e.g. Greeting)" maxlength="60" />
                  <textarea class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y min-h-14" v-model="cr.body" placeholder="Response text…" rows="2" maxlength="500" />
                </div>
                <button class="mt-1 h-8 w-8 shrink-0 rounded-md border border-red-200 bg-red-50 text-red-500 hover:bg-red-100 transition-colors flex items-center justify-center" @click="removeCanned(idx)">
                  <X class="h-3.5 w-3.5" />
                </button>
              </div>
              <button class="rounded-md border border-dashed border-primary/40 px-4 py-2 text-sm text-primary hover:bg-primary/5 transition-colors" @click="addCanned">
                + Add response
              </button>
            </div>
            <div class="flex justify-end">
              <Button @click="saveCanned" :disabled="cannedSaving" variant="outline" class="gap-2">
                <Loader2 v-if="cannedSaving" class="h-4 w-4 animate-spin" />
                {{ cannedSaved ? '✓ Saved' : 'Save canned responses' }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- ═══ KNOWLEDGE BASE TAB ═══ -->
    <div v-if="activeTab === 'knowledge'" class="flex flex-col gap-4">
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <div>
            <h2 class="text-sm font-semibold">Knowledge base</h2>
            <p class="text-xs text-muted-foreground mt-0.5">Your chatbot learns from your website content. Add your URL below to train it.</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Website URL</label>
            <div class="flex gap-2">
              <input v-model="form.domain_url" type="url" class="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="https://yoursite.com/" />
              <Button @click="triggerScrape" :disabled="scraping" class="gap-2 whitespace-nowrap">
                <Loader2 v-if="scraping" class="h-4 w-4 animate-spin" />
                Re-train
              </Button>
            </div>
          </div>
          <div v-if="props.client" class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <div class="h-2 w-2 rounded-full" :class="scrapeStatusDot"></div>
              <span class="text-sm font-medium" :class="scrapeStatusColor">{{ scrapeStatusLabel }}</span>
            </div>
            <span v-if="props.client.total_pages_ingested > 0" class="text-xs text-muted-foreground">
              {{ props.client.total_pages_ingested }} pages indexed
            </span>
          </div>
          <div v-if="scraping" class="space-y-1.5">
            <div class="h-1.5 rounded-full bg-muted overflow-hidden">
              <div class="h-full rounded-full bg-primary transition-all" :style="{ width: progressPct + '%' }"></div>
            </div>
            <p class="text-xs text-muted-foreground">Scanning pages…</p>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- ═══ INTEGRATIONS TAB ═══ -->
    <div v-if="activeTab === 'integrations'" class="flex flex-col gap-4">

      <!-- AI Model (BYOK) -->
      <GatedCard :locked="features.allow_byok === false" plan="Growth">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-violet-100 text-violet-600 flex items-center justify-center shrink-0">
              <Bot class="h-4 w-4" />
            </div>
            <div class="flex-1">
              <h2 class="text-sm font-semibold">AI Model (BYOK)</h2>
              <p class="text-xs text-muted-foreground mt-0.5">Use your own OpenAI, Anthropic or OpenRouter API key.</p>
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Provider</label>
            <div class="flex gap-2">
              <button v-for="p in aiProviders" :key="p.val" class="flex items-center rounded-md border px-3 py-1.5 text-sm font-medium transition-colors" :class="intForm.ai_provider === p.val ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'" @click="intForm.ai_provider = p.val">{{ p.label }}</button>
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">API Key</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.ai_api_key" placeholder="sk-… or your OpenRouter key" autocomplete="off" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Model ID</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.ai_model" placeholder="e.g. gpt-4o / claude-opus-4-6 / google/gemini-3.1-pro-preview" />
            <span class="text-xs text-muted-foreground">Leave blank to use the platform default (Gemini 3.1 Pro).</span>
          </div>
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save AI settings" />
        </CardContent>
      </GatedCard>

      <!-- WhatsApp -->
      <GatedCard :locked="features.allow_whatsapp === false" plan="Starter">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="WhatsApp Business" desc="Connect your Meta WhatsApp Business number." :active="intForm.whatsapp_enabled" bg="bg-emerald-100" color="text-emerald-600">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          </IntegrationHeader>
          <WebhookField label="Webhook URL (paste in Meta → Webhooks)" :url="whatsappWebhookUrl" />
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Phone Number ID</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.whatsapp_phone_number_id" placeholder="123456789012345" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Verify Token</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.whatsapp_verify_token" placeholder="my_secure_verify_token" />
            </div>
            <div class="flex flex-col gap-1.5 col-span-2">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Access Token</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.whatsapp_access_token" placeholder="EAAxxxxxxxxxxxxxxxx" autocomplete="off" />
            </div>
          </div>
          <ToggleRow label="Enable WhatsApp" :desc="intForm.whatsapp_enabled ? 'AI will reply to WhatsApp messages' : 'Disabled'" v-model="intForm.whatsapp_enabled" />
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save WhatsApp settings" />
        </CardContent>
      </GatedCard>

      <!-- Facebook Messenger -->
      <GatedCard :locked="features.allow_messenger === false" plan="Growth">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="Facebook Messenger" desc="Connect your Facebook Page to receive Messenger conversations." :active="intForm.messenger_enabled" bg="bg-blue-100" color="text-blue-600">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z"/></svg>
          </IntegrationHeader>
          <WebhookField label="Webhook URL (paste in Meta → Webhooks)" :url="messengerWebhookUrl" />
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Page ID</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.messenger_page_id" placeholder="123456789" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Verify Token</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.messenger_verify_token" placeholder="my_secure_verify_token" />
            </div>
            <div class="flex flex-col gap-1.5 col-span-2">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Page Access Token</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.messenger_page_access_token" placeholder="EAAxxxxxxxxxxxxxxxx" autocomplete="off" />
            </div>
          </div>
          <ToggleRow label="Enable Messenger" :desc="intForm.messenger_enabled ? 'AI will reply to Messenger messages' : 'Disabled'" v-model="intForm.messenger_enabled" />
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save Messenger settings" />
        </CardContent>
      </GatedCard>

      <!-- HubSpot CRM -->
      <GatedCard :locked="features.allow_hubspot === false" plan="Growth">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="HubSpot CRM" desc="Automatically sync captured leads to HubSpot as Contacts and Deals." :active="!!intForm.hubspot_api_key" bg="bg-orange-100" color="text-orange-600">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="2"/></svg>
          </IntegrationHeader>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">HubSpot Private App Token</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.hubspot_api_key" placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" autocomplete="off" />
            <span class="text-xs text-muted-foreground">Create a Private App in HubSpot → Settings → Integrations → Private Apps. Requires CRM (contacts + deals) scopes.</span>
          </div>
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save HubSpot settings" />
        </CardContent>
      </GatedCard>

      <!-- Telegram Bot -->
      <GatedCard :locked="features.allow_telegram === false" plan="Growth">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="Telegram Bot" desc="Connect a Telegram bot so visitors can chat via Telegram." :active="intForm.telegram_enabled" bg="bg-sky-100" color="text-sky-600">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>
          </IntegrationHeader>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Bot Token</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.telegram_bot_token" placeholder="123456:ABCdef..." autocomplete="off" />
            <span class="text-xs text-muted-foreground">Obtain from @BotFather on Telegram. Webhook URL: <code class="font-mono text-xs bg-muted px-1 rounded">{{ telegramWebhookUrl }}</code></span>
          </div>
          <ToggleRow label="Enable Telegram" :desc="intForm.telegram_enabled ? 'Enabled' : 'Disabled'" v-model="intForm.telegram_enabled" />
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save Telegram settings" />
        </CardContent>
      </GatedCard>

      <!-- Slack -->
      <GatedCard :locked="features.allow_slack === false" plan="Starter">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="Slack Notifications" desc="Get notified in Slack when a hot lead or new lead is captured." :active="!!intForm.slack_webhook_url" bg="bg-purple-100" color="text-purple-600">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>
          </IntegrationHeader>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Incoming Webhook URL</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="intForm.slack_webhook_url" placeholder="https://hooks.slack.com/services/..." autocomplete="off" />
            <span class="text-xs text-muted-foreground">Create an Incoming Webhook in your Slack workspace → Apps → Incoming Webhooks.</span>
          </div>
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save Slack settings" />
        </CardContent>
      </GatedCard>

      <!-- Outbound Webhook -->
      <GatedCard :locked="features.allow_webhooks === false" plan="Growth">
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <IntegrationHeader name="Outbound Webhook (Zapier / n8n)" desc="POST event data to an external URL when key events occur." :active="!!intForm.outbound_webhook_url" bg="bg-orange-100" color="text-orange-600">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          </IntegrationHeader>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Webhook URL</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.outbound_webhook_url" placeholder="https://hooks.zapier.com/hooks/catch/..." />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Events (comma-separated)</label>
            <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="text" v-model="intForm.outbound_webhook_events" placeholder="hot_lead,lead_captured,new_session" />
            <span class="text-xs text-muted-foreground">Available: <code class="font-mono text-xs bg-muted px-1 rounded">hot_lead</code>, <code class="font-mono text-xs bg-muted px-1 rounded">lead_captured</code>, <code class="font-mono text-xs bg-muted px-1 rounded">new_session</code></span>
          </div>
          <IntSaveButton :saving="intSaving" :saved="intSaved" @save="saveIntegrations" label="Save webhook settings" />
        </CardContent>
      </GatedCard>

      <!-- Change password -->
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col gap-4">
          <div>
            <h2 class="text-sm font-semibold">Change password</h2>
            <p class="text-xs text-muted-foreground mt-0.5">Update the password for your Checkfunnel account.</p>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current password</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="pwForm.current" placeholder="••••••••" autocomplete="current-password" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">New password</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="pwForm.next" placeholder="Min. 8 characters" autocomplete="new-password" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Confirm password</label>
              <input class="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" type="password" v-model="pwForm.confirm" placeholder="••••••••" autocomplete="new-password" />
            </div>
          </div>
          <div v-if="pwError" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{{ pwError }}</div>
          <div class="flex justify-end">
            <Button @click="changePassword" :disabled="pwSaving" variant="outline" class="gap-2">
              <Loader2 v-if="pwSaving" class="h-4 w-4 animate-spin" />
              {{ pwSaved ? '✓ Password updated' : 'Change password' }}
            </Button>
          </div>
        </CardContent>
      </Card>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, defineComponent, h } from 'vue'
import { Globe, Check, Copy, Loader2, Lock, Bot, X } from 'lucide-vue-next'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'
import { generateEmbedCode } from './embedCodeGenerator'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps({ client: Object })
const emit = defineEmits(['client-updated'])
const api = useAdminApi()

const activeTab = ref('channels')
const embedFormat = ref('html')
const copied = ref(false)
const saving = ref(false)
const saved = ref(false)
const scraping = ref(false)
const scrapePages = ref(0)
let scrapeTimer = null

const features = ref({})
onMounted(async () => {
  try {
    const data = await api.getFeatureFlags()
    features.value = data || {}
  } catch {}
})

const backendUrl = WIDGET_URL.replace('/widget/widget.js', '')

const settingsTabs = [
  { key: 'channels', label: 'Channels & embed' },
  { key: 'chatbot', label: 'Chatbot' },
  { key: 'knowledge', label: 'Knowledge base' },
  { key: 'integrations', label: 'Integrations' },
]

const offChannels = [
  { name: 'Messenger', iconBg: 'bg-blue-50', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="#0084FF"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z"/></svg>' },
  { name: 'Twilio SMS',  iconBg: 'bg-red-50',  icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#F22F46"/><circle cx="8.5" cy="8.5" r="1.5" fill="white"/><circle cx="15.5" cy="8.5" r="1.5" fill="white"/><circle cx="8.5" cy="15.5" r="1.5" fill="white"/><circle cx="15.5" cy="15.5" r="1.5" fill="white"/></svg>' },
]

// ── Inline sub-components ──────────────────────────────────────────────────────
const GatedCard = defineComponent({
  props: { locked: Boolean, plan: String },
  setup(props, { slots }) {
    return () => h('div', { class: 'relative' }, [
      props.locked && h('div', {
        class: 'absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-xl bg-background/90 backdrop-blur-sm border border-border text-center px-6'
      }, [
        h(Lock, { class: 'h-6 w-6 text-muted-foreground' }),
        h('div', {}, [
          h('p', { class: 'text-sm font-semibold text-foreground' }, `Requires ${props.plan} plan`),
          h('a', { href: '/portal/billing', class: 'mt-1 inline-block text-xs font-medium text-primary underline' }, `Upgrade to ${props.plan} →`),
        ]),
      ]),
      h(Card, {}, slots),
    ])
  },
})

const IntegrationHeader = defineComponent({
  props: { name: String, desc: String, active: Boolean, bg: String, color: String },
  setup(props, { slots }) {
    return () => h('div', { class: 'flex items-center gap-3' }, [
      h('div', { class: `h-9 w-9 rounded-lg ${props.bg} ${props.color} flex items-center justify-center shrink-0` }, slots.default?.()),
      h('div', { class: 'flex-1' }, [
        h('h2', { class: 'text-sm font-semibold' }, props.name),
        h('p', { class: 'text-xs text-muted-foreground mt-0.5' }, props.desc),
      ]),
      props.active
        ? h('span', { class: 'inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-600' }, 'Active')
        : h('span', { class: 'inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-semibold text-muted-foreground' }, 'Inactive'),
    ])
  },
})

const WebhookField = defineComponent({
  props: { label: String, url: String },
  setup(props) {
    return () => h('div', { class: 'flex flex-col gap-1.5' }, [
      h('label', { class: 'text-xs font-semibold uppercase tracking-wide text-muted-foreground' }, props.label),
      h('div', { class: 'rounded-md border border-border bg-muted/30 px-3 py-2' }, [
        h('code', { class: 'text-xs font-mono text-primary break-all' }, props.url),
      ]),
    ])
  },
})

const ToggleRow = defineComponent({
  props: { label: String, desc: String, modelValue: Boolean },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('div', { class: 'flex items-center justify-between gap-4' }, [
      h('div', {}, [
        h('p', { class: 'text-sm font-medium text-foreground' }, props.label),
        h('p', { class: 'text-xs text-muted-foreground mt-0.5' }, props.desc),
      ]),
      h('button', {
        class: `relative h-6 w-11 rounded-full border transition-colors shrink-0 ${props.modelValue ? 'bg-primary border-primary' : 'bg-muted border-border'}`,
        onClick: () => emit('update:modelValue', !props.modelValue),
      }, [
        h('span', { class: `absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${props.modelValue ? 'translate-x-5' : 'translate-x-0.5'}` }),
      ]),
    ])
  },
})

const IntSaveButton = defineComponent({
  props: { saving: Boolean, saved: Boolean, label: String },
  emits: ['save'],
  setup(props, { emit }) {
    return () => h('div', { class: 'flex justify-end' }, [
      h(Button, {
        variant: 'outline',
        disabled: props.saving,
        class: 'gap-2',
        onClick: () => emit('save'),
      }, () => [
        props.saving && h(Loader2, { class: 'h-4 w-4 animate-spin' }),
        props.saved ? '✓ Saved' : props.label,
      ]),
    ])
  },
})

// ── Integrations form ──────────────────────────────────────────────────────────
const intSaving = ref(false)
const intSaved = ref(false)
const intForm = ref({
  ai_api_key: '', ai_model: '', ai_provider: 'openrouter',
  whatsapp_phone_number_id: '', whatsapp_access_token: '', whatsapp_verify_token: '', whatsapp_enabled: false,
  messenger_page_id: '', messenger_page_access_token: '', messenger_verify_token: '', messenger_enabled: false,
  hubspot_api_key: '',
  telegram_bot_token: '', telegram_enabled: false,
  slack_webhook_url: '',
  outbound_webhook_url: '', outbound_webhook_events: 'hot_lead,lead_captured,new_session',
})

const aiProviders = [
  { val: 'openrouter', label: 'OpenRouter' },
  { val: 'openai', label: 'OpenAI' },
  { val: 'anthropic', label: 'Anthropic' },
]

const whatsappWebhookUrl = computed(() => props.client ? `${backendUrl}/api/chat/webhooks/whatsapp/${props.client.id}/` : '')
const messengerWebhookUrl = computed(() => props.client ? `${backendUrl}/api/chat/webhooks/messenger/${props.client.id}/` : '')
const telegramWebhookUrl = computed(() => props.client ? `${backendUrl}/api/chat/webhooks/telegram/${props.client.id}/` : '')

// ── Main form ──────────────────────────────────────────────────────────────────
const form = ref({
  chatbot_name: '', chatbot_color: '#6366F1', chatbot_theme: 'dark',
  notification_email: '', cta_message: '', domain_url: '',
  voice_input_enabled: false, image_input_enabled: false,
})

const presetColors = ['#ffffff', '#3B82F6', '#22c55e', '#ef4444', '#6366f1', '#f59e0b']

const formats = [
  { id: 'html',      label: 'HTML',      icon: '<span style="color:#e34c26;font-weight:700;font-size:11px">HTML</span>' },
  { id: 'wordpress', label: 'WordPress', icon: '<span style="color:#21759b;font-weight:700;font-size:11px">WP</span>' },
  { id: 'react',     label: 'React',     icon: '<span style="font-size:11px">⚛</span>' },
]

const embedCode = computed(() => {
  if (!props.client) return ''
  return generateEmbedCode(props.client.id, backendUrl, form.value.chatbot_color || '#6366f1', form.value.chatbot_name || 'AI Assistant', embedFormat.value)
})

watch(() => props.client, (c) => {
  if (!c) return
  form.value.chatbot_name = c.chatbot_name || ''
  form.value.chatbot_color = c.chatbot_color || '#6366F1'
  form.value.chatbot_theme = c.chatbot_theme || 'dark'
  form.value.notification_email = c.notification_email || ''
  form.value.cta_message = c.cta_message || ''
  form.value.domain_url = c.domain_url || ''
  form.value.voice_input_enabled = c.voice_input_enabled || false
  form.value.image_input_enabled = c.image_input_enabled || false
  scrapePages.value = c.total_pages_ingested || 0
  intForm.value.ai_api_key = c.ai_api_key || ''
  intForm.value.ai_model = c.ai_model || ''
  intForm.value.ai_provider = c.ai_provider || 'openrouter'
  intForm.value.whatsapp_phone_number_id = c.whatsapp_phone_number_id || ''
  intForm.value.whatsapp_access_token = c.whatsapp_access_token || ''
  intForm.value.whatsapp_verify_token = c.whatsapp_verify_token || ''
  intForm.value.whatsapp_enabled = c.whatsapp_enabled || false
  intForm.value.messenger_page_id = c.messenger_page_id || ''
  intForm.value.messenger_page_access_token = c.messenger_page_access_token || ''
  intForm.value.messenger_verify_token = c.messenger_verify_token || ''
  intForm.value.messenger_enabled = c.messenger_enabled || false
  intForm.value.hubspot_api_key = c.hubspot_api_key || ''
  intForm.value.telegram_bot_token = c.telegram_bot_token || ''
  intForm.value.telegram_enabled = c.telegram_enabled || false
  intForm.value.slack_webhook_url = c.slack_webhook_url || ''
  intForm.value.outbound_webhook_url = c.outbound_webhook_url || ''
  intForm.value.outbound_webhook_events = c.outbound_webhook_events || 'hot_lead,lead_captured,new_session'
  cannedResponses.value = (c.canned_responses || []).map(cr => ({ ...cr }))
}, { immediate: true })

// ── Canned responses ───────────────────────────────────────────────────────────
const cannedResponses = ref([])
const cannedSaving = ref(false)
const cannedSaved = ref(false)

function addCanned() { cannedResponses.value.push({ id: crypto.randomUUID(), title: '', body: '' }) }
function removeCanned(idx) { cannedResponses.value.splice(idx, 1) }
async function saveCanned() {
  if (!props.client) return
  cannedSaving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, { canned_responses: cannedResponses.value })
    emit('client-updated', updated)
    cannedSaved.value = true
    setTimeout(() => { cannedSaved.value = false }, 3000)
  } catch {} finally { cannedSaving.value = false }
}

// ── Password change ────────────────────────────────────────────────────────────
const pwForm = ref({ current: '', next: '', confirm: '' })
const pwSaving = ref(false)
const pwSaved = ref(false)
const pwError = ref('')

async function changePassword() {
  pwError.value = ''
  if (!pwForm.value.current) { pwError.value = 'Enter your current password.'; return }
  if (pwForm.value.next.length < 8) { pwError.value = 'New password must be at least 8 characters.'; return }
  if (pwForm.value.next !== pwForm.value.confirm) { pwError.value = 'Passwords do not match.'; return }
  pwSaving.value = true
  try {
    await api.changePassword(pwForm.value.current, pwForm.value.next)
    pwSaved.value = true
    pwForm.value = { current: '', next: '', confirm: '' }
    setTimeout(() => { pwSaved.value = false }, 4000)
  } catch (e) {
    pwError.value = e.message || 'Failed to update password.'
  } finally { pwSaving.value = false }
}

async function saveIntegrations() {
  if (!props.client) return
  intSaving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, intForm.value)
    emit('client-updated', updated)
    intSaved.value = true
    setTimeout(() => { intSaved.value = false }, 3000)
  } catch {} finally { intSaving.value = false }
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(embedCode.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}

async function saveConfig() {
  if (!props.client) return
  saving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, form.value)
    emit('client-updated', updated)
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch {} finally { saving.value = false }
}

async function triggerScrape() {
  if (!props.client) return
  scraping.value = true
  try {
    await api.updatePortalClient(props.client.id, { domain_url: form.value.domain_url })
    await api.triggerScrape(props.client.id)
    scrapeTimer = setInterval(async () => {
      try {
        const p = await api.getScrapeProgress(props.client.id)
        scrapePages.value = p.pages_scraped || 0
        if (p.status === 'DONE' || p.status === 'FAILED') {
          scraping.value = false
          emit('client-updated', { ingestion_status: p.status, total_pages_ingested: scrapePages.value })
          clearInterval(scrapeTimer)
        }
      } catch {}
    }, 1500)
  } catch { scraping.value = false }
}

const progressPct = computed(() => Math.min(90, scrapePages.value * 5 + 15))

const scrapeStatusDot = computed(() => {
  const s = props.client?.ingestion_status
  if (s === 'DONE') return 'bg-emerald-500'
  if (s === 'RUNNING') return 'bg-primary animate-pulse'
  if (s === 'FAILED') return 'bg-red-500'
  return 'bg-muted-foreground'
})

const scrapeStatusColor = computed(() => {
  const s = props.client?.ingestion_status
  if (s === 'DONE') return 'text-emerald-600'
  if (s === 'RUNNING') return 'text-primary'
  if (s === 'FAILED') return 'text-red-500'
  return 'text-muted-foreground'
})

const scrapeStatusLabel = computed(() => {
  const s = props.client?.ingestion_status
  if (s === 'DONE') return 'Training complete'
  if (s === 'RUNNING') return 'Training in progress…'
  if (s === 'FAILED') return 'Training failed'
  return 'Not trained yet'
})
</script>
