<template>
  <div v-if="ready" class="flex h-screen overflow-hidden bg-background">
    <PortalSidebar :client="client" />
    <main class="flex-1 overflow-y-auto">
      <router-view :client="client" @client-updated="onClientUpdated" />
    </main>
  </div>
  <div v-else class="flex h-screen items-center justify-center bg-background">
    <Loader2 class="h-8 w-8 animate-spin text-primary" />
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import PortalSidebar from './PortalSidebar.vue'

const router = useRouter()
const route = useRoute()
const api = useAdminApi()

const client = ref(null)
const ready = ref(false)

provide('portalClient', client)

async function loadClient() {
  try {
    const c = await api.getPortalClient()
    client.value = c
    if (c && !c.onboarding_complete && route.path !== '/portal/setup') {
      router.push('/portal/setup')
    } else if (!c && route.path !== '/portal/setup') {
      router.push('/portal/setup')
    }
  } catch {
    // token issue — let router guard handle it
  } finally {
    ready.value = true
  }
}

function onClientUpdated(updated) {
  client.value = { ...client.value, ...updated }
}

onMounted(loadClient)
</script>
