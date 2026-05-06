<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <!-- Logo -->
      <div class="flex flex-col items-center gap-3 text-center">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Zap class="h-5 w-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight">Checkfunnel</h1>
          <p class="text-sm text-muted-foreground">Sign in to your account</p>
        </div>
      </div>

      <!-- Card -->
      <Card>
        <CardContent class="pt-6">
          <form @submit.prevent="handleLogin" class="space-y-4">
            <div class="space-y-2">
              <Label for="email">Email</Label>
              <Input id="email" v-model="form.username" type="email" placeholder="you@example.com" autocomplete="email" required />
            </div>
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <Label for="password">Password</Label>
                <RouterLink to="/forgot-password" class="text-xs text-muted-foreground hover:text-primary underline underline-offset-4">
                  Forgot password?
                </RouterLink>
              </div>
              <div class="relative">
                <Input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="••••••••" autocomplete="current-password" required />
                <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" @click="showPassword = !showPassword">
                  <Eye v-if="!showPassword" class="h-4 w-4" />
                  <EyeOff v-else class="h-4 w-4" />
                </button>
              </div>
            </div>
            <div v-if="error" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ error }}</div>
            <Button type="submit" class="w-full" :disabled="loading">
              <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
              {{ loading ? 'Signing in…' : 'Sign in' }}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p class="text-center text-sm text-muted-foreground">
        Don't have an account?
        <RouterLink to="/signup" class="font-medium text-primary hover:underline">Sign up</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const router = useRouter()
const api = useAdminApi()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await api.login(form.value.username, form.value.password)
    const user = api.getUser()
    router.push(user?.role === 'tenant_admin' ? '/portal/inbox' : '/admin')
  } catch (e) {
    error.value = e.message || 'Invalid credentials'
  } finally {
    loading.value = false
  }
}
</script>
