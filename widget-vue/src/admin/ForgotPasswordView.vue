<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
    </div>

    <div class="auth-card">
      <router-link to="/admin/login" class="back-link">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Back to sign in
      </router-link>

      <div class="brand">
        <div class="brand-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#fg)"/>
            <defs>
              <linearGradient id="fg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366F1"/>
                <stop offset="100%" stop-color="#8B5CF6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span class="brand-name">Checkfunnel</span>
      </div>

      <template v-if="!sent">
        <h1 class="auth-title">Forgot your password?</h1>
        <p class="auth-sub">Enter your email and we'll send you a reset link.</p>

        <form @submit.prevent="handleSubmit" class="auth-form">
          <div class="field">
            <label>Email address</label>
            <input v-model="email" type="email" placeholder="you@company.com" autocomplete="email" :disabled="loading" />
          </div>

          <div v-if="error" class="error-msg">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#EF4444" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/></svg>
            {{ error }}
          </div>

          <button type="submit" class="auth-btn" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            <span v-else>Send reset link</span>
          </button>
        </form>
      </template>

      <template v-else>
        <div class="success-state">
          <div class="success-icon">
            <svg width="32" height="32" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#22C55E" stroke-width="2"/><path d="M9 12l2 2 4-4" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <h1 class="auth-title">Check your inbox</h1>
          <p class="auth-sub">If an account with <strong>{{ email }}</strong> exists, we've sent a reset link. Check your spam folder if you don't see it.</p>
          <router-link to="/admin/login" class="auth-btn" style="display:block;text-align:center;text-decoration:none;margin-top:24px;">
            Back to sign in
          </router-link>
        </div>
      </template>

      <p class="footer-note">CheckFunnel &copy; 2026</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)

async function handleSubmit() {
  error.value = ''
  if (!email.value) { error.value = 'Please enter your email.'; return }
  loading.value = true
  try {
    await api.forgotPassword(email.value.trim().toLowerCase())
    sent.value = true
  } catch (e) {
    error.value = e.message || 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0F172A;
  position: relative;
  overflow: hidden;
}

.auth-bg { position: absolute; inset: 0; pointer-events: none; }

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
}
.blob-1 { width: 500px; height: 500px; background: radial-gradient(circle, #6366F1, #8B5CF6); top: -100px; left: -100px; }
.blob-2 { width: 400px; height: 400px; background: radial-gradient(circle, #3B82F6, #06B6D4); bottom: -100px; right: -100px; }

.auth-card {
  position: relative;
  background: #1E293B;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 40px;
  width: 420px;
  box-shadow: 0 25px 50px rgba(0,0,0,0.4);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 13px;
  text-decoration: none;
  margin-bottom: 24px;
  transition: color 0.2s;
}
.back-link:hover { color: #94a3b8; }

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}
.brand-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #1e1b4b, #312e81);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-name { font-weight: 700; font-size: 18px; color: #f1f5f9; }

.auth-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0 0 6px; }
.auth-sub { font-size: 14px; color: #64748b; margin: 0 0 28px; line-height: 1.5; }
.auth-sub strong { color: #94a3b8; }

.auth-form { display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 500; color: #94a3b8; }
.field input {
  background: #0F172A;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 11px 14px;
  color: #f1f5f9;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.field input:focus { border-color: #6366f1; }
.field input:disabled { opacity: 0.5; cursor: not-allowed; }

.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  padding: 10px 12px;
  color: #fca5a5;
  font-size: 13px;
}

.auth-btn {
  width: 100%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 13px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-top: 4px;
}
.auth-btn:hover:not(:disabled) { opacity: 0.9; }
.auth-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  display: inline-block;
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.success-state { text-align: center; }
.success-icon { display: flex; justify-content: center; margin-bottom: 16px; }

.footer-note { text-align: center; color: #334155; font-size: 12px; margin-top: 28px; }
</style>
