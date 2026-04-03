<template>
  <div class="signup-page">
    <div class="signup-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>

    <div class="signup-wrap">
      <!-- Left panel: value props -->
      <div class="signup-left">
        <a href="/" class="brand">
          <div class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#sg)"/>
              <defs>
                <linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#A5B4FC"/>
                  <stop offset="100%" stop-color="#C4B5FD"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span class="brand-name">CheckFunnel</span>
        </a>

        <div class="left-content">
          <h2 class="left-headline">Start converting visitors into <em>customers</em> today.</h2>
          <p class="left-sub">Join hundreds of businesses using CheckFunnel to capture leads and close deals — automatically.</p>

          <div class="proof-list">
            <div class="proof-item" v-for="p in proofPoints" :key="p.text">
              <div class="proof-icon">{{ p.icon }}</div>
              <div>
                <div class="proof-title">{{ p.title }}</div>
                <div class="proof-text">{{ p.text }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="left-footer">Free 14-day trial · No credit card required</div>
      </div>

      <!-- Right panel: form -->
      <div class="signup-card">
        <h1 class="signup-title">Create your account</h1>
        <p class="signup-sub">Get started in 2 minutes — no code required.</p>

        <form @submit.prevent="handleSignup" class="signup-form">
          <div class="field">
            <label>Company name</label>
            <input
              v-model="form.company_name"
              type="text"
              placeholder="Acme Inc."
              autocomplete="organization"
              :disabled="loading"
            />
          </div>

          <div class="field">
            <label>Work email</label>
            <input
              v-model="form.email"
              type="email"
              placeholder="you@company.com"
              autocomplete="email"
              :disabled="loading"
            />
          </div>

          <div class="field">
            <label>Password</label>
            <div class="password-wrap">
              <input
                v-model="form.password"
                :type="showPass ? 'text' : 'password'"
                placeholder="Min. 8 characters"
                autocomplete="new-password"
                :disabled="loading"
              />
              <button type="button" class="eye-btn" @click="showPass = !showPass">
                <svg v-if="!showPass" width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#94A3B8" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="#94A3B8" stroke-width="2"/></svg>
                <svg v-else width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/><line x1="1" y1="1" x2="23" y2="23" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/></svg>
              </button>
            </div>
            <div class="password-strength" v-if="form.password">
              <div class="strength-bar">
                <div class="strength-fill" :style="{ width: strengthPct + '%', background: strengthColor }"></div>
              </div>
              <span class="strength-label" :style="{ color: strengthColor }">{{ strengthLabel }}</span>
            </div>
          </div>

          <div class="field">
            <label>Confirm password</label>
            <input
              v-model="form.confirm_password"
              :type="showPass ? 'text' : 'password'"
              placeholder="Re-enter password"
              autocomplete="new-password"
              :disabled="loading"
            />
          </div>

          <div class="terms-row">
            <input type="checkbox" id="terms" v-model="form.agreed" :disabled="loading" />
            <label for="terms" class="terms-label">
              I agree to the <a href="#" class="terms-link">Terms of Service</a> and <a href="#" class="terms-link">Privacy Policy</a>
            </label>
          </div>

          <div v-if="error" class="error-msg">
            <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#EF4444" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/></svg>
            {{ error }}
          </div>

          <button type="submit" class="signup-btn" :disabled="loading || !form.agreed">
            <span v-if="loading" class="spinner"></span>
            <span v-else>Create account →</span>
          </button>
        </form>

        <p class="login-link">
          Already have an account?
          <router-link to="/admin/login">Sign in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const router = useRouter()
const route = useRoute()
const api = useAdminApi()

const form = ref({
  company_name: '',
  email: '',
  password: '',
  confirm_password: '',
  agreed: false,
})

const loading = ref(false)
const error = ref('')
const showPass = ref(false)

const proofPoints = [
  { icon: '⚡', title: 'Deploy in 2 minutes', text: 'Paste one script tag — your AI is live instantly.' },
  { icon: '🎯', title: 'Real-time intent scoring', text: 'Know which visitors are ready to buy before they leave.' },
  { icon: '💰', title: '3× more leads', text: 'Automatically capture leads with heat-triggered forms.' },
]

// Pre-fill email from landing page hero form
onMounted(() => {
  if (route.query.email) {
    form.value.email = route.query.email
  }
})

// Password strength
const strengthPct = computed(() => {
  const p = form.value.password
  if (!p) return 0
  let score = 0
  if (p.length >= 8) score += 25
  if (p.length >= 12) score += 15
  if (/[A-Z]/.test(p)) score += 20
  if (/[0-9]/.test(p)) score += 20
  if (/[^A-Za-z0-9]/.test(p)) score += 20
  return Math.min(score, 100)
})

const strengthColor = computed(() => {
  if (strengthPct.value < 40) return '#ef4444'
  if (strengthPct.value < 70) return '#f59e0b'
  return '#22c55e'
})

const strengthLabel = computed(() => {
  if (strengthPct.value < 40) return 'Weak'
  if (strengthPct.value < 70) return 'Fair'
  return 'Strong'
})

async function handleSignup() {
  error.value = ''
  const { company_name, email, password, confirm_password } = form.value

  if (!company_name || !email || !password || !confirm_password) {
    error.value = 'Please fill in all fields.'
    return
  }
  if (password !== confirm_password) {
    error.value = 'Passwords do not match.'
    return
  }
  if (password.length < 8) {
    error.value = 'Password must be at least 8 characters.'
    return
  }

  loading.value = true
  try {
    await api.register(company_name, email, password, confirm_password)
    router.push('/portal/setup')
  } catch (e) {
    error.value = e.message || 'Registration failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.signup-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0F172A;
  position: relative;
  overflow: hidden;
}

.signup-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.12;
}

.blob-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, #6366F1, #8B5CF6);
  top: -200px; left: -200px;
}

.blob-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #3B82F6, #06B6D4);
  bottom: -150px; right: -150px;
}

.blob-3 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #8B5CF6, #EC4899);
  top: 50%; right: 30%;
  opacity: 0.07;
}

/* Layout */
.signup-wrap {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1fr 460px;
  max-width: 1000px;
  width: 100%;
  margin: 40px 24px;
  gap: 0;
  background: #1E293B;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 32px 64px rgba(0,0,0,0.5);
}

/* Left panel */
.signup-left {
  background: linear-gradient(145deg, #1e1b4b 0%, #1a1040 50%, #0f172a 100%);
  padding: 48px 44px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.signup-left::before {
  content: '';
  position: absolute;
  width: 400px; height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%);
  bottom: -100px; right: -100px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  margin-bottom: 60px;
}

.brand-icon {
  width: 36px; height: 36px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: #F1F5F9;
  letter-spacing: -0.3px;
}

.left-content { flex: 1; position: relative; z-index: 2; }

.left-headline {
  font-size: 28px;
  font-weight: 800;
  color: white;
  line-height: 1.2;
  letter-spacing: -0.7px;
  margin-bottom: 14px;
}

.left-headline em {
  font-family: 'Georgia', serif;
  font-style: italic;
  color: #a5b4fc;
}

.left-sub {
  font-size: 14px;
  color: rgba(255,255,255,0.45);
  line-height: 1.65;
  margin-bottom: 40px;
}

.proof-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.proof-item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.proof-icon {
  width: 36px; height: 36px;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.proof-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 3px;
}

.proof-text {
  font-size: 13px;
  color: rgba(255,255,255,0.38);
  line-height: 1.5;
}

.left-footer {
  font-size: 12px;
  color: rgba(255,255,255,0.2);
  margin-top: 40px;
  position: relative;
  z-index: 2;
}

/* Right panel: form */
.signup-card {
  padding: 48px 40px;
  background: #1E293B;
  border-left: 1px solid rgba(255,255,255,0.06);
}

.signup-title {
  font-size: 24px;
  font-weight: 700;
  color: #F1F5F9;
  margin-bottom: 6px;
  letter-spacing: -0.4px;
}

.signup-sub {
  font-size: 14px;
  color: #64748B;
  margin-bottom: 28px;
}

.signup-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  font-weight: 500;
  color: #94A3B8;
}

.field input {
  background: #0F172A;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 14px;
  color: #F1F5F9;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  width: 100%;
}

.field input:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}

.field input::placeholder { color: #334155; }

.password-wrap { position: relative; }
.password-wrap input { padding-right: 40px; }

.eye-btn {
  position: absolute;
  right: 12px; top: 50%;
  transform: translateY(-50%);
  background: none; border: none;
  cursor: pointer; padding: 2px;
  display: flex; align-items: center;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.strength-bar {
  flex: 1;
  height: 3px;
  background: rgba(255,255,255,0.08);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s, background 0.3s;
}

.strength-label {
  font-size: 11px;
  font-weight: 600;
  width: 36px;
  text-align: right;
}

.terms-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 2px;
}

.terms-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin-top: 1px;
  accent-color: #6366F1;
  flex-shrink: 0;
  cursor: pointer;
}

.terms-label {
  font-size: 12px;
  color: #64748B;
  line-height: 1.5;
  cursor: pointer;
}

.terms-link {
  color: #818cf8;
  text-decoration: none;
}
.terms-link:hover { text-decoration: underline; }

.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #FCA5A5;
}

.signup-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 13px;
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  margin-top: 4px;
}

.signup-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.signup-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.login-link {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: #475569;
}

.login-link a {
  color: #818cf8;
  text-decoration: none;
  font-weight: 500;
}
.login-link a:hover { text-decoration: underline; }

/* Responsive */
@media (max-width: 820px) {
  .signup-wrap {
    grid-template-columns: 1fr;
    margin: 0;
    border-radius: 0;
    min-height: 100vh;
  }
  .signup-left { display: none; }
  .signup-card { border-left: none; padding: 40px 24px; }
}
</style>
