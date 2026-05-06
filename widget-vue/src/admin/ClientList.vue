<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Clients</h1>
        <p class="text-sm text-muted-foreground">Manage your chatbot clients and knowledge bases</p>
      </div>
      <Button @click="showModal = true">
        <Plus class="h-4 w-4" /> Add Client
      </Button>
    </div>

    <!-- Search -->
    <div class="relative max-w-sm">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input v-model="search" placeholder="Search clients…" class="pl-9" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16 gap-3 text-muted-foreground">
      <Loader2 class="h-5 w-5 animate-spin" /> Loading clients…
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <Building2 class="h-10 w-10 mb-3 opacity-30" />
      <p class="font-medium">No clients yet</p>
      <p class="text-sm mt-1">Add your first client to get started</p>
      <Button class="mt-4" @click="showModal = true"><Plus class="h-4 w-4" /> Add Client</Button>
    </div>

    <!-- Table -->
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Client</TableHead>
            <TableHead>Platform</TableHead>
            <TableHead v-if="isSuperAdmin">Tenant</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Sessions</TableHead>
            <TableHead>Knowledge Base</TableHead>
            <TableHead class="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="client in filtered" :key="client.id">
            <TableCell>
              <div class="flex items-center gap-3">
                <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white text-xs font-bold" :style="{ background: client.chatbot_color || '#6366f1' }">
                  {{ client.name.slice(0, 2).toUpperCase() }}
                </div>
                <div>
                  <p class="font-medium text-sm">{{ client.name }}</p>
                  <a v-if="client.domain_url" :href="client.domain_url" target="_blank" class="text-xs text-muted-foreground hover:text-primary truncate max-w-[160px] block">
                    {{ client.domain_url.replace(/https?:\/\//, '') }}
                  </a>
                  <span v-else class="text-xs text-muted-foreground">No URL set</span>
                </div>
              </div>
            </TableCell>
            <TableCell>
              <Badge variant="secondary" class="text-xs">{{ client.platform }}</Badge>
            </TableCell>
            <TableCell v-if="isSuperAdmin">
              <DropdownMenu v-if="isSuperAdmin" align="start">
                <template #trigger>
                  <button class="flex items-center gap-1 text-sm hover:text-primary transition-colors">
                    <Badge v-if="client.tenant_name" variant="outline" class="text-xs cursor-pointer">{{ client.tenant_name }}</Badge>
                    <Badge v-else variant="secondary" class="text-xs cursor-pointer text-muted-foreground">Unassigned</Badge>
                    <ChevronDown class="h-3 w-3 text-muted-foreground" />
                  </button>
                </template>
                <div class="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Assign to tenant</div>
                <DropdownMenuItem v-for="t in tenants" :key="t.id" @click="assignToTenant(client, t.id)">
                  {{ t.company_name || t.username }}
                </DropdownMenuItem>
                <DropdownMenuSeparator v-if="client.tenant_id" />
                <DropdownMenuItem v-if="client.tenant_id" :destructive="true" @click="assignToTenant(client, null)">Remove assignment</DropdownMenuItem>
              </DropdownMenu>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1.5">
                <div :class="['h-2 w-2 rounded-full', client.is_active ? 'bg-emerald-500' : 'bg-muted-foreground']" />
                <span class="text-sm">{{ client.is_active ? 'Active' : 'Inactive' }}</span>
              </div>
            </TableCell>
            <TableCell class="font-medium text-sm">{{ client.session_count || 0 }}</TableCell>
            <TableCell>
              <div class="space-y-0.5">
                <Badge :variant="ingestionVariant(client.ingestion_status)" class="text-xs">{{ client.ingestion_status || 'PENDING' }}</Badge>
                <p class="text-xs text-muted-foreground">{{ client.total_pages_ingested }} pages</p>
              </div>
            </TableCell>
            <TableCell>
              <div class="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" @click="$router.push('/admin/clients/' + client.id)" title="View">
                  <Eye class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" @click="triggerScrape(client)" :disabled="scrapingId === client.id || !client.domain_url" title="Re-scrape">
                  <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': scrapingId === client.id }" />
                </Button>
                <Button variant="ghost" size="icon" class="text-destructive hover:text-destructive" @click="confirmDelete(client)" title="Delete">
                  <Trash2 class="h-4 w-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <!-- Add Client Dialog -->
    <Dialog :open="showModal" @update:open="closeModal">
      <DialogHeader>
        <DialogTitle>Add New Client</DialogTitle>
      </DialogHeader>
      <div class="space-y-4 py-2">
        <div class="space-y-2">
          <Label>Business Name *</Label>
          <Input v-model="form.name" placeholder="e.g. The AI Tips" />
        </div>
        <div class="space-y-2">
          <Label>Website URL</Label>
          <Input v-model="form.domain_url" type="url" placeholder="https://example.com" />
          <p class="text-xs text-muted-foreground">Used to auto-scrape content for the knowledge base.</p>
        </div>
        <div class="space-y-2">
          <Label>Platform</Label>
          <Select v-model="form.platform">
            <option value="WORDPRESS">WordPress</option>
            <option value="SHOPIFY">Shopify</option>
            <option value="CUSTOM">Custom</option>
          </Select>
        </div>
        <div v-if="formError" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ formError }}</div>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="closeModal">Cancel</Button>
        <Button @click="createClient" :disabled="creating">
          <Loader2 v-if="creating" class="h-4 w-4 animate-spin" />
          {{ creating ? 'Creating…' : 'Create Client' }}
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Delete Confirm Dialog -->
    <Dialog :open="!!deleteTarget" @update:open="deleteTarget = null">
      <DialogHeader>
        <DialogTitle>Delete Client</DialogTitle>
      </DialogHeader>
      <p class="text-sm text-muted-foreground py-2">
        Are you sure you want to delete <strong class="text-foreground">{{ deleteTarget?.name }}</strong>? This cannot be undone.
      </p>
      <DialogFooter>
        <Button variant="outline" @click="deleteTarget = null">Cancel</Button>
        <Button variant="destructive" @click="doDelete" :disabled="deleting">
          <Loader2 v-if="deleting" class="h-4 w-4 animate-spin" />
          {{ deleting ? 'Deleting…' : 'Delete' }}
        </Button>
      </DialogFooter>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Search, Eye, RefreshCw, Trash2, Building2, Loader2, ChevronDown } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Select from '@/components/ui/Select.vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DialogHeader from '@/components/ui/DialogHeader.vue'
import DialogTitle from '@/components/ui/DialogTitle.vue'
import DialogFooter from '@/components/ui/DialogFooter.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import DropdownMenuItem from '@/components/ui/DropdownMenuItem.vue'
import DropdownMenuSeparator from '@/components/ui/DropdownMenuSeparator.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const api = useAdminApi()
const clients = ref([])
const tenants = ref([])
const loading = ref(false)
const search = ref('')
const showModal = ref(false)
const creating = ref(false)
const scrapingId = ref(null)
const deleteTarget = ref(null)
const deleting = ref(false)
const formError = ref('')
const isSuperAdmin = api.isSuperAdmin()
const form = ref({ name: '', domain_url: '', platform: 'WORDPRESS' })

const filtered = computed(() =>
  search.value ? clients.value.filter(c => c.name.toLowerCase().includes(search.value.toLowerCase())) : clients.value
)

function ingestionVariant(status) {
  if (status === 'DONE') return 'success'
  if (status === 'RUNNING') return 'warning'
  if (status === 'FAILED') return 'destructive'
  return 'secondary'
}

async function loadClients() {
  loading.value = true
  try {
    const [c, t] = await Promise.all([api.getClients(), isSuperAdmin ? api.getTenants() : Promise.resolve([])])
    clients.value = c || []
    tenants.value = t || []
  } finally { loading.value = false }
}

async function assignToTenant(client, tenantId) {
  try {
    const result = await api.assignClientToTenant(client.id, tenantId)
    client.tenant_id = result.tenant_id
    client.tenant_name = result.tenant_name
  } catch (e) { alert(e.message || 'Assignment failed.') }
}

function closeModal() { showModal.value = false; form.value = { name: '', domain_url: '', platform: 'WORDPRESS' }; formError.value = '' }

async function createClient() {
  formError.value = ''
  if (!form.value.name.trim()) { formError.value = 'Business name is required.'; return }
  creating.value = true
  try { clients.value.unshift(await api.createClient(form.value)); closeModal() }
  catch (e) { formError.value = e.message || 'Failed to create client.' }
  finally { creating.value = false }
}

async function triggerScrape(client) {
  scrapingId.value = client.id
  try { await api.triggerScrape(client.id); client.ingestion_status = 'RUNNING' }
  catch (e) { alert(e.message || 'Scrape failed.') }
  finally { scrapingId.value = null }
}

function confirmDelete(client) { deleteTarget.value = client }

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try { await api.deleteClient(deleteTarget.value.id); clients.value = clients.value.filter(c => c.id !== deleteTarget.value.id); deleteTarget.value = null }
  catch (e) { alert(e.message || 'Failed to delete.') }
  finally { deleting.value = false }
}

onMounted(loadClients)
</script>
