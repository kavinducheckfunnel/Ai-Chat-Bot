<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Zap class="h-5 w-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight">Set new password</h1>
          <p class="text-sm text-muted-foreground">Choose a strong password for your account</p>
        </div>
      </div>

      <Card>
        <CardContent class="pt-6">
          <div v-if="done" class="space-y-4">
            <div class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              Password updated successfully!
            </div>
            <Button class="w-full" @click="$router.push('/admin/login')">Go to login</Button>
          </div>
          <form v-else @submit.prevent="handleSubmit" class="space-y-4">
            <div class="space-y-2">
              <Label for="password">New password</Label>
              <Input id="password" v-model="form.new_password" type="password" placeholder="••••••••" required />
            </div>
            <div v-if="error" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ error }}</div>
            <Button type="submit" class="w-full" :disabled="loading">
              <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
              {{ loading ? 'Updating…' : 'Update password' }}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Zap, Loader2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const route = useRoute()
const api = useAdminApi()
const form = ref({ new_password: '' })
const loading = ref(false)
const done = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true; error.value = ''
  try {
    await api.resetPassword(route.query.uid, route.query.token, form.value.new_password)
    done.value = true
  } catch (e) { error.value = e.message || 'Reset failed. Link may have expired.' }
  finally { loading.value = false }
}
</script>
