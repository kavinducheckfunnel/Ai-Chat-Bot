<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Zap class="h-5 w-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight">Create an account</h1>
          <p class="text-sm text-muted-foreground">Start your free trial today</p>
        </div>
      </div>

      <Card>
        <CardContent class="pt-6">
          <form @submit.prevent="handleSignup" class="space-y-4">
            <div class="space-y-2">
              <Label for="company">Company name</Label>
              <Input id="company" v-model="form.company_name" placeholder="Acme Inc." required />
            </div>
            <div class="space-y-2">
              <Label for="email">Email</Label>
              <Input id="email" v-model="form.email" type="email" placeholder="you@example.com" required />
            </div>
            <div class="space-y-2">
              <Label for="password">Password</Label>
              <Input id="password" v-model="form.password" type="password" placeholder="••••••••" required />
            </div>
            <div class="space-y-2">
              <Label for="confirm">Confirm password</Label>
              <Input id="confirm" v-model="form.confirm_password" type="password" placeholder="••••••••" required />
            </div>
            <div v-if="error" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ error }}</div>
            <Button type="submit" class="w-full" :disabled="loading">
              <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
              {{ loading ? 'Creating account…' : 'Create account' }}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p class="text-center text-sm text-muted-foreground">
        Already have an account?
        <RouterLink to="/admin/login" class="font-medium text-primary hover:underline">Sign in</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, Loader2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const router = useRouter()
const api = useAdminApi()
const form = ref({ company_name: '', email: '', password: '', confirm_password: '' })
const loading = ref(false)
const error = ref('')

async function handleSignup() {
  if (form.value.password !== form.value.confirm_password) { error.value = 'Passwords do not match'; return }
  loading.value = true; error.value = ''
  try {
    await api.register(form.value.company_name, form.value.email, form.value.password, form.value.confirm_password)
    router.push('/portal/setup')
  } catch (e) { error.value = e.message || 'Registration failed' }
  finally { loading.value = false }
}
</script>
