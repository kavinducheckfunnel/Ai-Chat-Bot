<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
    </div>

    <div class="auth-card">
      <div class="brand">
        <div class="brand-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#rpg)"/>
            <defs>
              <linearGradient id="rpg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366F1"/>
                <stop offset="100%" stop-color="#8B5CF6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span class="brand-name">Checkfunnel</span>
      </div>

      <!-- Invalid link state -->
      <template v-if="!uid || !token">
        <div class="invalid-state">
          <svg width="36" height="36" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#EF4444" stroke-width="2"/><path d="M15 9l-6 6M9 9l6 6" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/></svg>
          <h1 class="auth-title">Invalid link</h1>
          <p class="auth-sub">This reset link is missing required parameters. Please request a new one.</p>
          <router-link to="/forgot-password" class="auth-btn" style="display:block;text-align:center;text-decoration:none;margin-top:20px;">
            Request new link
          </router-link>
        </div>
      </template>

      <!-- Success state -->
      <template v-else-if="done">
        <div class="success-state">
          <svg width="36" height="36" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#22C55E" stroke-width="2"/><path d="M9 12l2 2 4-4" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <h1 class="auth-title">Password reset!</h1>
          <p class="auth-sub">Your password has been updated. You can now sign in with your new password.</p>
          <router-link to="/admin/login" class="auth-btn" style="display:block;text-align:center;text-decoration:none;margin-top:20px;">
            Sign in
          </router-link>
        </div>
      </template>

      <!-- Form state -->
      <template v-else>
        <h1 class="auth-title">Set new password</h1>
        <p class="auth-sub">Choose a strong password — at least 8 characters.</p>

        <form @submit.prevent="handleSubmit" class="auth-form">
          <div class="field">
            <label>New password</label>
            <div class="pw-wrap">
              <input
                v-model="newPw"
                :type="showPw ? 'text' : 'password'"
                placeholder="••••••••••"
                autocomplete="new-password"
                :disabled="loading"
              />
              <button type="button" class="eye-btn" @click="showPw = !showPw">
                <svg v-if="!showPw" width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#94A3B8" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="#94A3B8" stroke-width="2"/></svg>
                <svg v-else width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/><line x1="1" y1="1" x2="23" y2="23" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/></svg>
              </button>
            </div>
          </div>

          <div class="field">
            <label>Confirm password</label>
            <input v-model="confirmPw" type="password" placeholder="••••••••••" autocomplete="new-password" :disabled="loading" />
          </div>

          <!-- Password strength bar -->
          <div class="strength-bar" v-if="newPw">
            <div class="strength-fill" :style="{ width: strength.pct + '%', background: strength.color }"></div>
          </div>
          <p class="strength-label" v-if="newPw" :style="{ color: strength.color }">{{ strength.label }}</p>

          <div v-if="error" class="error-msg">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#EF4444" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/></svg>
            {{ error }}
          </div>

          <button type="submit" class="auth-btn" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            <span v-else>Reset password</span>
          </button>
        </form>
      </template>

      <p class="footer-note">CheckFunnel &copy; 2026</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const route = useRoute()

const uid = route.query.uid || ''
const token = route.query.token || ''

const newPw = ref('')
const confirmPw = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')
const done = ref(false)

const strength = computed(() => {
  const pw = newPw.value
  if (!pw) return { pct: 0, color: '#334155', label: '' }
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  const levels = [
    { pct: 20, color: '#EF4444', label: 'Very weak' },
    { pct: 40, color: '#F97316', label: 'Weak' },
    { pct: 60, color: '#EAB308', label: 'Fair' },
    { pct: 80, color: '#22C55E', label: 'Strong' },
    { pct: 100, color: '#10B981', label: 'Very strong' },
  ]
  return levels[Math.min(score - 1, 4)] || levels[0]
})

async function handleSubmit() {
  error.value = ''
  if (newPw.value.length < 8) { error.value = 'Password must be at least 8 characters.'; return }
  if (newPw.value !== confirmPw.value) { error.value = 'Passwords do not match.'; return }

  loading.value = true
  try {
    const res = await api.resetPassword(uid, token, newPw.value)
    if (res.detail && res.detail.toLowerCase().includes('invalid')) {
      error.value = res.detail
    } else {
      done.value = true
    }
  } catch (e) {
    error.value = e.message || 'Something went wrong. Please request a new reset link.'
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
.blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.15; }
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

.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 28px; }
.brand-icon { width: 36px; height: 36px; background: linear-gradient(135deg, #1e1b4b, #312e81); border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.brand-name { font-weight: 700; font-size: 18px; color: #f1f5f9; }

.auth-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0 0 6px; }
.auth-sub { font-size: 14px; color: #64748b; margin: 0 0 28px; line-height: 1.5; }

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
  width: 100%;
  box-sizing: border-box;
}
.field input:focus { border-color: #6366f1; }
.field input:disabled { opacity: 0.5; }

.pw-wrap { position: relative; }
.pw-wrap input { padding-right: 42px; }
.eye-btn { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; padding: 0; }

.strength-bar { height: 4px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
.strength-fill { height: 100%; border-radius: 4px; transition: width 0.3s, background 0.3s; }
.strength-label { font-size: 12px; margin: 0; }

.error-msg { display: flex; align-items: center; gap: 8px; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 8px; padding: 10px 12px; color: #fca5a5; font-size: 13px; }

.auth-btn { width: 100%; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 10px; padding: 13px; font-size: 15px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; margin-top: 4px; }
.auth-btn:hover:not(:disabled) { opacity: 0.9; }
.auth-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.invalid-state, .success-state { text-align: center; }
.invalid-state svg, .success-state svg { display: block; margin: 0 auto 16px; }

.footer-note { text-align: center; color: #334155; font-size: 12px; margin-top: 28px; }
</style>
