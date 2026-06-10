<template>
  <div class="pricing-page">
    <header class="pr-header">
      <div class="pr-header-inner">
        <a href="/" class="pr-brand">Checkfunnel</a>
        <a href="/signup" class="pr-cta-top">Start free trial</a>
      </div>
    </header>

    <main class="pr-main">
      <!-- Hero -->
      <section class="pr-hero">
        <h1>Plans &amp; Pricing</h1>
        <p>Pay for what you use — billing scales with messages, not seats. Upgrade or downgrade month-to-month, and bring your own AI key on any plan.</p>
      </section>

      <!-- Pricing philosophy -->
      <section class="pr-section">
        <div class="pr-philosophy">
          <div class="pr-phil-item">
            <div class="pr-phil-icon">💸</div>
            <div class="pr-phil-title">Pay for what you use</div>
            <div class="pr-phil-body">Billing scales with messages — never arbitrary seat counts. Add unlimited team members at no extra cost.</div>
          </div>
          <div class="pr-phil-item">
            <div class="pr-phil-icon">📈</div>
            <div class="pr-phil-title">Grow at your own pace</div>
            <div class="pr-phil-body">Upgrade or downgrade plans month-to-month. Switch to annual any time for 15% off.</div>
          </div>
          <div class="pr-phil-item">
            <div class="pr-phil-icon">🔑</div>
            <div class="pr-phil-title">Bring your own AI key</div>
            <div class="pr-phil-body">Connect your OpenAI or Anthropic key on any plan to control AI costs directly — no markup.</div>
          </div>
        </div>
      </section>

      <!-- Detailed comparison -->
      <section class="pr-section">
        <h2 class="pr-h2">Compare plans</h2>
        <div class="pr-table-wrap">
          <table class="pr-table">
            <thead>
              <tr><th>Feature</th><th>Starter</th><th>Growth</th><th>Pro</th><th>Enterprise</th></tr>
            </thead>
            <tbody>
              <tr><td>Monthly messages</td><td>2,000</td><td>5,000</td><td>15,000</td><td>Unlimited</td></tr>
              <tr><td>Web channels</td><td>Website only</td><td>Web + 1 social</td><td>Web + omnichannel</td><td>All channels</td></tr>
              <tr><td>CRM integrations</td><td>—</td><td>Webhook (HubSpot, Zapier…)</td><td>Webhook + Direct HubSpot Sync</td><td>Custom</td></tr>
              <tr><td>BYOK support</td><td>✓ Optional</td><td>✓ Optional</td><td>✓</td><td>✓</td></tr>
              <tr><td>Voice command widget</td><td>—</td><td>✓</td><td>✓</td><td>✓ (Custom)</td></tr>
              <tr><td>Image upload for questions</td><td>—</td><td>✓</td><td>✓</td><td>✓</td></tr>
              <tr><td>Live chat takeover</td><td>—</td><td>✓</td><td>✓</td><td>✓</td></tr>
              <tr><td>Real-time inventory sync</td><td>—</td><td>—</td><td>✓</td><td>✓</td></tr>
              <tr><td>Custom website integration</td><td>—</td><td>—</td><td>—</td><td>✓ (Any platform)</td></tr>
              <tr><td>Custom internal DB</td><td>—</td><td>—</td><td>—</td><td>✓</td></tr>
              <tr><td>White-label branding</td><td>—</td><td>—</td><td>—</td><td>✓</td></tr>
              <tr><td>Support</td><td>Email</td><td>Email + Chat</td><td>Priority</td><td>Dedicated CSM</td></tr>
              <tr><td>Reports / exports</td><td>Basic</td><td>Standard</td><td>Advanced</td><td>Custom</td></tr>
              <tr><td>Data retention</td><td>30 days</td><td>90 days</td><td>1 year</td><td>Custom</td></tr>
            </tbody>
          </table>
        </div>
        <p class="pr-note">Omnichannel (WhatsApp + Facebook Messenger) requires a Meta Developer App and webhook configuration. Setup assistance is included on Growth, Pro, and Enterprise.</p>
      </section>

      <!-- Message-based billing -->
      <section class="pr-section">
        <h2 class="pr-h2">How message-based billing works</h2>
        <div class="pr-byok">
          <p class="pr-byok-lead">A <strong>message</strong> is counted each time the AI sends a response to a user — so your cost tracks the volume of conversations your chatbot handles. Human agent replies during Live Chat Takeover never count.</p>
          <div class="pr-byok-grid">
            <div class="pr-byok-item">✓ Add unlimited team members — no per-seat fees</div>
            <div class="pr-byok-item">✓ Predictable costs that scale with your business</div>
            <div class="pr-byok-item">✓ Estimate spend straight from your traffic data</div>
            <div class="pr-byok-item">✓ Pay annually on any plan and save 15%</div>
          </div>
          <div class="pr-byok-default" style="border-left-color:#f59e0b">
            <strong>Overage policy:</strong> automated alerts at 80% and 100% of your limit. Additional messages are billed at your plan's overage rate (Enterprise rates negotiated at contract) — or simply pause the chatbot once the limit is hit, no overage charged.
          </div>
        </div>
      </section>

      <!-- BYOK -->
      <section class="pr-section">
        <h2 class="pr-h2">BYOK — Bring Your Own AI Key</h2>
        <div class="pr-byok">
          <p class="pr-byok-lead">Connect your own OpenAI or Anthropic API key. Pay your AI provider directly for inference — no markup from Checkfunnel.</p>
          <div class="pr-byok-grid">
            <div class="pr-byok-item">✓ Full control over model selection (GPT-4o, Claude, etc.)</div>
            <div class="pr-byok-item">✓ Inference billed straight to your provider</div>
            <div class="pr-byok-item">✓ Use fine-tuned or custom models</div>
            <div class="pr-byok-item">✓ Compliant with your AI procurement policies</div>
          </div>
          <div class="pr-byok-default"><strong>Managed AI (default):</strong> clients without BYOK use our managed AI pool — costs bundled into the plan price.</div>
        </div>
      </section>

      <!-- Available add-ons -->
      <section class="pr-section">
        <h2 class="pr-h2">Available add-ons</h2>
        <div class="pr-table-wrap">
          <table class="pr-table">
            <thead><tr><th>Add-on</th><th>Price</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Extra Message / Image / Voice Pack</td><td>Contact us</td><td>Top-up credits without changing your plan.</td></tr>
              <tr><td>White-Label Branding</td><td>Contact us</td><td>Remove all Checkfunnel branding from the widget &amp; emails. Enterprise only.</td></tr>
            </tbody>
          </table>
        </div>
        <p class="pr-note">Add-ons attach to any plan and are billed monthly alongside your base subscription. <a href="mailto:sales@checkfunnel.com" style="color:#a5b4fc">Contact our team</a> to enable one.</p>
      </section>

      <!-- Integrations & required setup -->
      <section class="pr-section">
        <h2 class="pr-h2">Integrations &amp; required setup</h2>
        <div class="pr-table-wrap">
          <table class="pr-table">
            <thead><tr><th>Integration</th><th>Starter</th><th>Growth</th><th>Pro / Enterprise</th><th>Notes</th></tr></thead>
            <tbody>
              <tr v-for="row in integrationRows" :key="row.name">
                <td>{{ row.name }}</td>
                <td>{{ row.starter }}</td>
                <td>{{ row.growth }}</td>
                <td>{{ row.pro }}</td>
                <td>{{ row.notes }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="pr-note">Omnichannel requires a Meta Developer App and webhook configuration. Setup assistance is included on Growth, Pro, and Enterprise.</p>
      </section>

      <!-- Industries -->
      <section class="pr-section">
        <h2 class="pr-h2">Built for your industry</h2>
        <div class="pr-industries">
          <div class="pr-ind" v-for="ind in industries" :key="ind.title">
            <div class="pr-ind-emoji">{{ ind.emoji }}</div>
            <div class="pr-ind-title">{{ ind.title }}</div>
            <div class="pr-ind-tagline">{{ ind.tagline }}</div>
          </div>
        </div>
      </section>

      <!-- Competitor comparison -->
      <section class="pr-section">
        <h2 class="pr-h2">How we compare</h2>
        <div class="pr-table-wrap">
          <table class="pr-table pr-comp">
            <thead>
              <tr><th>Feature</th><th class="us">Checkfunnel</th><th>Intercom</th><th>Drift</th><th>ManyChat</th><th>Tidio</th></tr>
            </thead>
            <tbody>
              <tr><td>AI lead scoring</td><td class="us">✓ (3-EMA)</td><td>Partial</td><td>✓</td><td>✗</td><td>Partial</td></tr>
              <tr><td>Omnichannel (WA + FB)</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✓</td><td>Partial</td></tr>
              <tr><td>In-chat checkout</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✓</td><td>✗</td></tr>
              <tr><td>BYOK (own API key)</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td></tr>
              <tr><td>Voice AI</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td></tr>
              <tr><td>Message-based billing</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✓</td><td>✗</td></tr>
              <tr><td>White-label option</td><td class="us">✓</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Build your own custom package -->
      <section class="pr-section">
        <h2 class="pr-h2">Build your own custom package</h2>
        <p class="pr-note" style="font-style:normal;font-size:14px;color:#94a3b8;margin:-8px 0 22px">
          Not every business fits a fixed tier. Tell us your needs → we scope &amp; price it → we build &amp; launch. You pay only for what's in your package.
        </p>
        <div class="pr-table-wrap" style="margin-bottom:24px">
          <table class="pr-table">
            <thead><tr><th>Feature / module</th><th>What it does</th><th>Available from</th></tr></thead>
            <tbody>
              <tr v-for="f in featureMenu" :key="f.name">
                <td>{{ f.name }}</td>
                <td>{{ f.does }}</td>
                <td><span class="pr-from">{{ f.from }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pr-packages">
          <div v-for="pkg in packages" :key="pkg.name" class="pr-pkg" :class="pkg.cls">
            <div class="pr-pkg-name">{{ pkg.name }}</div>
            <div class="pr-pkg-tagline">{{ pkg.tagline }}</div>
            <ul class="pr-pkg-features">
              <li v-for="ft in pkg.features" :key="ft">{{ ft }}</li>
            </ul>
            <div class="pr-pkg-price">{{ pkg.price }}</div>
          </div>
        </div>
      </section>

      <!-- Custom CTA -->
      <section class="pr-section">
        <div class="pr-custom-cta">
          <div class="pr-custom-title">Need add-ons or a custom package?</div>
          <div class="pr-custom-sub">Tell us your channels, integrations, and message volume — we scope a package around your requirements.</div>
          <a href="mailto:sales@checkfunnel.com" class="pr-custom-btn">sales@checkfunnel.com</a>
        </div>
      </section>
    </main>

    <footer class="pr-footer">© {{ year }} Checkfunnel · <a href="/admin/login">Sign in</a> · <a href="/signup">Start free trial</a></footer>
  </div>
</template>

<script setup>
const year = new Date().getFullYear()
const industries = [
  { emoji: '🏨', title: 'Hotel & Hospitality', tagline: 'AI concierge, room service automation, guest experience' },
  { emoji: '🛍️', title: 'Retail & E-Commerce', tagline: 'Product discovery, cart recovery, order tracking' },
  { emoji: '🏥', title: 'Healthcare & Clinics', tagline: 'Appointment booking, patient triage, reminders' },
  { emoji: '🏠', title: 'Real Estate & Property', tagline: 'Lead qualification, property discovery, viewings' },
  { emoji: '🎓', title: 'Education & Training', tagline: 'Enrolment, course guidance, fee queries' },
]

// Section 7 — Integrations & required setup
const integrationRows = [
  { name: 'Stripe (Billing)',     starter: 'Required',  growth: 'Required',           pro: 'Required',  notes: 'All plans' },
  { name: 'WhatsApp Business',    starter: '—',         growth: 'Optional',           pro: 'Required',  notes: 'Stage 4' },
  { name: 'Facebook Messenger',   starter: '—',         growth: 'Optional',           pro: 'Required',  notes: 'Stage 4' },
  { name: 'Telegram Bot',         starter: 'Optional',  growth: 'Optional',           pro: 'Optional',  notes: 'All plans' },
  { name: 'HubSpot CRM',          starter: '—',         growth: 'Optional (Webhook)', pro: 'Required',  notes: 'Growth+' },
  { name: 'Slack Alerts',         starter: 'Optional',  growth: 'Optional',           pro: 'Optional',  notes: 'All plans' },
  { name: 'OpenAI / Anthropic',   starter: 'Optional',  growth: 'Optional',           pro: 'Required',  notes: 'BYOK plans' },
  { name: 'Outbound Webhooks',    starter: 'Optional',  growth: 'Optional',           pro: 'Optional',  notes: 'All plans' },
]

// Section 12 — Feature menu + example minimal packages
const featureMenu = [
  { name: 'Web Chat Widget',       does: 'Embeddable chatbot on your website',       from: 'All plans' },
  { name: 'WhatsApp Integration',  does: 'Respond via WhatsApp Business API',         from: 'Pro+' },
  { name: 'Facebook Messenger',    does: 'Chat automation on your Facebook page',     from: 'Pro+' },
  { name: 'Telegram Bot',          does: 'Automated Telegram channel responses',      from: 'All plans' },
  { name: 'AI Lead Scoring',       does: 'Score leads by behavior to prioritise',     from: 'All plans' },
  { name: 'In-Chat Checkout',      does: 'Complete purchases without leaving chat',   from: 'All plans' },
  { name: 'Live Chat Takeover',    does: 'Human agent joins mid-conversation',        from: 'Growth+' },
  { name: 'Voice Command Widget',  does: 'Voice-enabled AI interactions on web',      from: 'Growth+' },
  { name: 'Image Upload',          does: 'Users send images as part of their query',  from: 'Growth+' },
  { name: 'CRM via Webhook',       does: 'Sync leads to HubSpot, Zapier & more',      from: 'Growth+' },
  { name: 'Custom DB Integration', does: 'Connect any internal database or system',   from: 'Enterprise' },
  { name: 'Real-Time Inventory',   does: 'Live product / room / slot availability',   from: 'Pro+' },
  { name: 'BYOK (Own AI Key)',     does: 'Use your own OpenAI / Anthropic key',       from: 'All plans' },
  { name: 'White-Label Branding',  does: 'Remove Checkfunnel branding — your logo',   from: 'Enterprise' },
  { name: 'Advanced Reports',      does: 'Exportable analytics & insights',           from: 'Pro+' },
]
const packages = [
  { cls: 'pkg-wa',   name: 'WhatsApp Starter',  tagline: 'Just WhatsApp + AI replies',  features: ['WhatsApp Business channel', 'AI chatbot responses', 'Basic lead capture', 'Email support'], price: 'Contact sales' },
  { cls: 'pkg-crm',  name: 'Web + CRM Bundle',  tagline: 'Web chat with lead sync',     features: ['Web chat widget', 'AI lead scoring', 'HubSpot CRM sync', 'Standard reports'], price: 'Contact sales' },
  { cls: 'pkg-omni', name: 'Omnichannel Lean',  tagline: 'Web + WhatsApp + Facebook',   features: ['Any channel combination', 'In-chat checkout', 'Live chat takeover', 'BYOK support'], price: 'Contact sales' },
  { cls: 'pkg-full', name: 'Full Custom Build', tagline: 'Everything you need',          features: ['Any DB / platform', 'Custom message volume', 'Custom AI model / flow', 'White label + CSM'], price: 'Quoted per scope' },
]
</script>

<style scoped>
.pricing-page { min-height: 100vh; background: #0b0d12; color: #e2e8f0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.pr-header { border-bottom: 1px solid rgba(255,255,255,0.08); position: sticky; top: 0; background: rgba(11,13,18,0.92); backdrop-filter: blur(8px); z-index: 10; }
.pr-header-inner { max-width: 1080px; margin: 0 auto; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
.pr-brand { font-size: 18px; font-weight: 700; color: #fff; text-decoration: none; }
.pr-cta-top { background: #6366f1; color: #fff; text-decoration: none; font-size: 13px; font-weight: 600; padding: 9px 16px; border-radius: 8px; }
.pr-main { max-width: 1080px; margin: 0 auto; padding: 0 24px 60px; }
.pr-hero { text-align: center; padding: 64px 0 40px; }
.pr-hero h1 { font-size: 40px; font-weight: 800; letter-spacing: -1px; margin: 0 0 14px; color: #fff; }
.pr-hero p { font-size: 16px; color: #94a3b8; max-width: 640px; margin: 0 auto; line-height: 1.6; }
.pr-section { margin: 48px 0; }
.pr-h2 { font-size: 24px; font-weight: 700; color: #fff; margin: 0 0 22px; letter-spacing: -0.4px; }
.pr-philosophy { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.pr-phil-item { background: #141821; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 22px; }
.pr-phil-icon { font-size: 24px; margin-bottom: 10px; }
.pr-phil-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 6px; }
.pr-phil-body { font-size: 13px; color: #94a3b8; line-height: 1.55; }
.pr-table-wrap { overflow-x: auto; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; }
.pr-table { width: 100%; min-width: 640px; border-collapse: collapse; }
.pr-table th { text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; padding: 14px 16px; background: rgba(255,255,255,0.025); border-bottom: 1px solid rgba(255,255,255,0.07); white-space: nowrap; }
.pr-table td { padding: 13px 16px; font-size: 13px; color: #cbd5e1; border-bottom: 1px solid rgba(255,255,255,0.05); }
.pr-table tr:last-child td { border-bottom: none; }
.pr-table td:first-child { color: #fff; font-weight: 500; }
.pr-table .us { color: #a5b4fc; background: rgba(99,102,241,0.08); font-weight: 600; }
.pr-note { font-size: 12px; color: #64748b; font-style: italic; margin-top: 12px; line-height: 1.6; }
.pr-byok { background: #141821; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 24px; }
.pr-byok-lead { font-size: 15px; color: #cbd5e1; line-height: 1.6; margin: 0 0 16px; }
.pr-byok-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; margin-bottom: 16px; }
.pr-byok-item { font-size: 13px; color: #cbd5e1; }
.pr-byok-default { background: rgba(99,102,241,0.08); border-left: 3px solid #6366f1; border-radius: 6px; padding: 12px 14px; font-size: 13px; color: #94a3b8; }
.pr-byok-default strong { color: #fff; }
.pr-industries { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.pr-ind { background: #141821; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; }
.pr-ind-emoji { font-size: 28px; margin-bottom: 10px; }
.pr-ind-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 5px; }
.pr-ind-tagline { font-size: 12.5px; color: #94a3b8; line-height: 1.5; }
.pr-custom-cta { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 16px; padding: 36px 28px; text-align: center; }
.pr-custom-title { font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 8px; }
.pr-custom-sub { font-size: 14px; color: rgba(255,255,255,0.85); margin-bottom: 18px; line-height: 1.5; max-width: 560px; margin-left: auto; margin-right: auto; }
.pr-custom-btn { display: inline-block; background: #fff; color: #4f46e5; font-size: 15px; font-weight: 700; text-decoration: none; padding: 12px 26px; border-radius: 10px; }
.pr-footer { text-align: center; padding: 28px; font-size: 12px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.07); }
.pr-footer a { color: #a5b4fc; text-decoration: none; }

/* "Available from" pill in the custom-package feature menu */
.pr-from { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 20px; background: rgba(99,102,241,0.12); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.25); white-space: nowrap; }

/* Example minimal packages */
.pr-packages { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.pr-pkg { background: #141821; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px 18px 16px; display: flex; flex-direction: column; gap: 6px; }
.pr-pkg.pkg-wa   { border-top: 3px solid #22c55e; }
.pr-pkg.pkg-crm  { border-top: 3px solid #60a5fa; }
.pr-pkg.pkg-omni { border-top: 3px solid #c4b5fd; }
.pr-pkg.pkg-full { border-top: 3px solid #fbbf24; }
.pr-pkg-name { font-size: 15px; font-weight: 700; color: #fff; }
.pr-pkg-tagline { font-size: 12px; color: #94a3b8; margin-bottom: 6px; }
.pr-pkg-features { margin: 0; padding-left: 18px; list-style: none; display: flex; flex-direction: column; gap: 5px; }
.pr-pkg-features li { position: relative; font-size: 12.5px; color: #cbd5e1; line-height: 1.5; }
.pr-pkg-features li::before { content: '✓'; position: absolute; left: -16px; color: #22c55e; font-weight: 700; }
.pr-pkg-price { margin-top: auto; padding-top: 10px; font-size: 13px; font-weight: 600; color: #a5b4fc; border-top: 1px dashed rgba(255,255,255,0.1); }

@media (max-width: 720px) {
  .pr-philosophy { grid-template-columns: 1fr; }
  .pr-byok-grid { grid-template-columns: 1fr; }
  .pr-hero h1 { font-size: 30px; }
}
</style>
