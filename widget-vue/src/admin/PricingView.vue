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
@media (max-width: 720px) {
  .pr-philosophy { grid-template-columns: 1fr; }
  .pr-byok-grid { grid-template-columns: 1fr; }
  .pr-hero h1 { font-size: 30px; }
}
</style>
