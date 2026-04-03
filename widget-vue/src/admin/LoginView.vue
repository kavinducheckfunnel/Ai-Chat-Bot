<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
    </div>

    <div class="login-card">
      <div class="brand">
        <div class="brand-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#g)" stroke="none"/>
            <defs>
              <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366F1"/>
                <stop offset="100%" stop-color="#8B5CF6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span class="brand-name">Checkfunnel</span>
      </div>

      <h1 class="login-title">Welcome back</h1>
      <p class="login-sub">Sign in to your CheckFunnel account</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label>Username</label>
          <input
            v-model="form.username"
            type="text"
            placeholder="superadmin"
            autocomplete="username"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label>Password</label>
          <div class="password-wrap">
            <input
              v-model="form.password"
              :type="showPass ? 'text' : 'password'"
              placeholder="••••••••••"
              autocomplete="current-password"
              :disabled="loading"
            />
            <button type="button" class="eye-btn" @click="showPass = !showPass">
              <svg v-if="!showPass" width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#94A3B8" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="#94A3B8" stroke-width="2"/></svg>
              <svg v-else width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/><line x1="1" y1="1" x2="23" y2="23" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>

        <div v-if="error" class="error-msg">
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#EF4444" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/></svg>
          {{ error }}
        </div>

        <button type="submit" class="login-btn" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Sign in</span>
        </button>
      </form>

      <p class="signup-prompt">Don't have an account? <router-link to="/signup">Sign up free →</router-link></p>
      <p class="footer-note">CheckFunnel &copy; 2026</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const router = useRouter()
const api = useAdminApi()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const showPass = ref(false)

async function handleLogin() {
  error.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = 'Please enter username and password.'
    return
  }
  loading.value = true
  try {
    const data = await api.login(form.value.username, form.value.password)
    const isTenant = data.user?.role === 'tenant_admin' && !data.user?.is_superuser
    router.push(isTenant ? '/portal/inbox' : '/admin')
  } catch (e) {
    error.value = e.message || 'Invalid credentials.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0F172A;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
}

.blob-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #6366F1, #8B5CF6);
  top: -100px; left: -100px;
}

.blob-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #3B82F6, #06B6D4);
  bottom: -100px; right: -100px;
}

.login-card {
  position: relative;
  background: #1E293B;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 40px;
  width: 420px;
  box-shadow: 0 25px 50px rgba(0,0,0,0.4);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.brand-icon {
  width: 40px; height: 40px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #F1F5F9;
  letter-spacing: -0.3px;
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: #F1F5F9;
  margin-bottom: 6px;
  letter-spacing: -0.5px;
}

.login-sub {
  font-size: 14px;
  color: #64748B;
  margin-bottom: 28px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
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
  transition: border-color 0.2s;
}

.field input:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}

.field input::placeholder { color: #334155; }

.password-wrap {
  position: relative;
}

.password-wrap input {
  width: 100%;
  padding-right: 40px;
}

.eye-btn {
  position: absolute;
  right: 12px; top: 50%;
  transform: translateY(-50%);
  background: none; border: none;
  cursor: pointer; padding: 2px;
  display: flex; align-items: center;
}

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

.login-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px;
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 46px;
  margin-top: 4px;
}

.login-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.login-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.signup-prompt {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: #475569;
}

.signup-prompt a {
  color: #818cf8;
  text-decoration: none;
  font-weight: 500;
}
.signup-prompt a:hover { text-decoration: underline; }

.footer-note {
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  color: #334155;
}
</style>
