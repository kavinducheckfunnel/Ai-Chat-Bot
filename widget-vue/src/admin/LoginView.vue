<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">
        <div class="logo-icon">CF</div>
        <h1>Checkfunnel</h1>
        <p>Admin Dashboard</p>
      </div>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>Username</label>
          <input v-model="username" type="text" placeholder="admin" autocomplete="username" required />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="••••••••" autocomplete="current-password" required />
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi.js'

const router = useRouter()
const { login } = useAdminApi()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
    router.push('/admin')
  } catch (e) {
    error.value = 'Invalid username or password.'
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
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%);
}
.login-card {
  background: white;
  border-radius: 16px;
  padding: 48px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.logo { text-align: center; margin-bottom: 36px; }
.logo-icon {
  width: 56px; height: 56px;
  background: #2563eb; color: white;
  border-radius: 14px; font-size: 1.25rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
}
.logo h1 { font-size: 1.5rem; font-weight: 700; color: #0f172a; }
.logo p { font-size: 0.875rem; color: #64748b; margin-top: 4px; }
.field { margin-bottom: 20px; }
.field label { display: block; font-size: 0.875rem; font-weight: 500; color: #374151; margin-bottom: 6px; }
.field input {
  width: 100%; padding: 10px 14px;
  border: 1.5px solid #e2e8f0; border-radius: 8px;
  font-size: 0.9375rem; outline: none; transition: border 0.2s;
}
.field input:focus { border-color: #2563eb; }
.error { color: #ef4444; font-size: 0.875rem; margin-bottom: 12px; }
button {
  width: 100%; padding: 12px;
  background: #2563eb; color: white;
  border: none; border-radius: 8px;
  font-size: 1rem; font-weight: 600; cursor: pointer;
  transition: background 0.2s;
}
button:hover:not(:disabled) { background: #1d4ed8; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
