<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Zap class="h-5 w-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight">Reset password</h1>
          <p class="text-sm text-muted-foreground">Enter your email to receive a reset link</p>
        </div>
      </div>

      <Card>
        <CardContent class="pt-6">
          <div v-if="sent" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Check your email — a reset link has been sent.
          </div>
          <form v-else @submit.prevent="handleSubmit" class="space-y-4">
            <div class="space-y-2">
              <Label for="email">Email</Label>
              <Input id="email" v-model="email" type="email" placeholder="you@example.com" required />
            </div>
            <div v-if="error" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ error }}</div>
            <Button type="submit" class="w-full" :disabled="loading">
              <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
              {{ loading ? 'Sending…' : 'Send reset link' }}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p class="text-center text-sm text-muted-foreground">
        <RouterLink to="/admin/login" class="font-medium text-primary hover:underline">← Back to login</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Zap, Loader2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const api = useAdminApi()
const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true; error.value = ''
  try { await api.forgotPassword(email.value); sent.value = true }
  catch (e) { error.value = e.message || 'Something went wrong' }
  finally { loading.value = false }
}
</script>
