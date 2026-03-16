<template>
  <div class="clients-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Clients</h1>
        <p class="page-sub">Manage your chatbot clients and their knowledge bases</p>
      </div>
      <button class="add-btn" @click="showModal = true">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
        Add Client
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading clients...</p>
    </div>

    <div v-else-if="!clients.length" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="#CBD5E1" stroke-width="1.5"/><circle cx="9" cy="7" r="4" stroke="#CBD5E1" stroke-width="1.5"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="#CBD5E1" stroke-width="1.5"/></svg>
      </div>
      <p class="empty-title">No clients yet</p>
      <p class="empty-sub">Add your first client to get started</p>
      <button class="add-btn" @click="showModal = true">Add Client</button>
    </div>

    <div v-else class="clients-table-wrap">
      <table class="clients-table">
        <thead>
          <tr>
            <th>Client</th>
            <th>Platform</th>
            <th>Tenant</th>
            <th>Status</th>
            <th>Sessions</th>
            <th>Knowledge Base</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="client in clients" :key="client.id">
            <td>
              <div class="client-name-cell">
                <div class="client-avatar" :style="{ background: client.chatbot_color || '#6366F1' }">
                  {{ client.name.slice(0, 2).toUpperCase() }}
                </div>
                <div>
                  <p class="client-name">{{ client.name }}</p>
                  <a v-if="client.domain_url" :href="client.domain_url" target="_blank" class="client-url">
                    {{ client.domain_url.replace('https://', '').replace('http://', '') }}
                  </a>
                  <span v-else class="client-url">No URL set</span>
                </div>
              </div>
            </td>
            <td>
              <span class="platform-badge" :class="'platform-' + client.platform.toLowerCase()">
                {{ client.platform }}
              </span>
            </td>
            <td>
              <div class="tenant-cell" v-if="isSuperAdmin">
                <span v-if="client.tenant_name" class="tenant-badge">{{ client.tenant_name }}</span>
                <span v-else class="unassigned-badge">Unassigned</span>
                <div class="assign-wrap">
                  <button class="assign-btn" @click="toggleAssignMenu(client.id)" title="Assign to tenant">
                    <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  </button>
                  <div v-if="assignMenuOpen === client.id" class="assign-dropdown">
                    <p class="assign-dropdown-label">Assign to tenant</p>
                    <button
                      v-for="t in tenants" :key="t.id"
                      class="assign-option"
                      :class="{ active: client.tenant_id === t.id }"
                      @click="assignToTenant(client, t.id)"
                    >{{ t.company_name || t.username }}</button>
                    <button v-if="client.tenant_id" class="assign-option unassign" @click="assignToTenant(client, null)">
                      Remove assignment
                    </button>
                  </div>
                </div>
              </div>
              <span v-else class="tenant-badge-ro">{{ client.tenant_name || '—' }}</span>
            </td>
            <td>
              <div class="status-dot-wrap">
                <span class="status-dot" :class="client.is_active ? 'active' : 'inactive'"></span>
                <span class="status-text">{{ client.is_active ? 'Active' : 'Inactive' }}</span>
              </div>
            </td>
            <td>
              <span class="sessions-count">{{ client.session_count || 0 }}</span>
            </td>
            <td>
              <div class="ingestion-cell">
                <span class="ingestion-badge" :class="'ing-' + (client.ingestion_status || 'pending').toLowerCase()">
                  {{ client.ingestion_status || 'PENDING' }}
                </span>
                <span class="pages-count">{{ client.total_pages_ingested }} pages</span>
              </div>
            </td>
            <td>
              <div class="actions">
                <button class="action-btn view-btn" @click="$router.push('/admin/clients/' + client.id)" title="View Details">
                  <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
                </button>
                <button
                  class="action-btn scrape-btn"
                  :class="{ loading: scrapingId === client.id }"
                  @click="triggerScrape(client)"
                  title="Trigger Re-scrape"
                  :disabled="scrapingId === client.id || !client.domain_url"
                >
                  <svg v-if="scrapingId !== client.id" width="15" height="15" fill="none" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  <div v-else class="mini-spinner"></div>
                </button>
                <button class="action-btn delete-btn" @click="confirmDelete(client)" title="Delete">
                  <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add Client Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>Add New Client</h3>
          <button class="modal-close" @click="closeModal">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>

        <div class="modal-body">
          <div class="field">
            <label>Business Name *</label>
            <input v-model="form.name" type="text" placeholder="e.g. The AI Tips" />
          </div>
          <div class="field">
            <label>Website URL</label>
            <input v-model="form.domain_url" type="url" placeholder="https://example.com" />
            <p class="field-hint">Used to auto-scrape content for the knowledge base.</p>
          </div>
          <div class="field">
            <label>Platform</label>
            <select v-model="form.platform">
              <option value="WORDPRESS">WordPress</option>
              <option value="SHOPIFY">Shopify</option>
              <option value="CUSTOM">Custom</option>
            </select>
          </div>

          <div v-if="form.domain_url" class="webhook-info">
            <p class="info-title">WordPress Webhook Setup</p>
            <p class="info-text">After creating the client, add this webhook URL to your WordPress site to keep the knowledge base in sync:</p>
            <p class="info-code">POST /api/scraper/webhooks/wordpress/&lt;client-id&gt;/</p>
            <p class="info-sub">Or use the "Sync Now" button in the client details to manually trigger a scrape.</p>
          </div>

          <div v-if="formError" class="form-error">{{ formError }}</div>
        </div>

        <div class="modal-footer">
          <button class="cancel-btn" @click="closeModal">Cancel</button>
          <button class="submit-btn" @click="createClient" :disabled="creating">
            <div v-if="creating" class="mini-spinner white"></div>
            <span v-else>Create Client</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal small">
        <div class="modal-header">
          <h3>Delete Client</h3>
          <button class="modal-close" @click="deleteTarget = null">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <p class="delete-warning">Are you sure you want to delete <strong>{{ deleteTarget.name }}</strong>? This cannot be undone.</p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="deleteTarget = null">Cancel</button>
          <button class="delete-confirm-btn" @click="doDelete" :disabled="deleting">
            <div v-if="deleting" class="mini-spinner white"></div>
            <span v-else>Delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const clients = ref([])
const tenants = ref([])
const loading = ref(false)
const showModal = ref(false)
const creating = ref(false)
const scrapingId = ref(null)
const deleteTarget = ref(null)
const deleting = ref(false)
const formError = ref('')
const assignMenuOpen = ref(null)
const isSuperAdmin = api.isSuperAdmin()

const form = ref({ name: '', domain_url: '', platform: 'WORDPRESS' })

async function loadClients() {
  loading.value = true
  try {
    const [c, t] = await Promise.all([api.getClients(), isSuperAdmin ? api.getTenants() : Promise.resolve([])])
    clients.value = c || []
    tenants.value = t || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function toggleAssignMenu(clientId) {
  assignMenuOpen.value = assignMenuOpen.value === clientId ? null : clientId
}

async function assignToTenant(client, tenantId) {
  assignMenuOpen.value = null
  try {
    const result = await api.assignClientToTenant(client.id, tenantId)
    client.tenant_id = result.tenant_id
    client.tenant_name = result.tenant_name
    // Keep tenants list in sync
    tenants.value = await api.getTenants() || tenants.value
  } catch (e) {
    alert(e.message || 'Assignment failed.')
  }
}

function closeModal() {
  showModal.value = false
  form.value = { name: '', domain_url: '', platform: 'WORDPRESS' }
  formError.value = ''
}

async function createClient() {
  formError.value = ''
  if (!form.value.name.trim()) {
    formError.value = 'Business name is required.'
    return
  }
  creating.value = true
  try {
    const client = await api.createClient(form.value)
    clients.value.unshift(client)
    closeModal()
  } catch (e) {
    formError.value = e.message || 'Failed to create client.'
  } finally {
    creating.value = false
  }
}

async function triggerScrape(client) {
  scrapingId.value = client.id
  try {
    await api.triggerScrape(client.id)
    client.ingestion_status = 'RUNNING'
  } catch (e) {
    alert(e.message || 'Scrape failed.')
  } finally {
    scrapingId.value = null
  }
}

function confirmDelete(client) {
  deleteTarget.value = client
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.deleteClient(deleteTarget.value.id)
    clients.value = clients.value.filter(c => c.id !== deleteTarget.value.id)
    deleteTarget.value = null
  } catch (e) {
    alert(e.message || 'Failed to delete.')
  } finally {
    deleting.value = false
  }
}

function closeAssignMenu(e) {
  if (!e.target.closest('.assign-wrap')) assignMenuOpen.value = null
}

onMounted(() => {
  loadClients()
  document.addEventListener('click', closeAssignMenu)
})
</script>

<style scoped>
.clients-page { max-width: 1200px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -0.4px; }
.page-sub { font-size: 14px; color: #64748B; margin-top: 4px; }

.add-btn {
  display: flex; align-items: center; gap: 7px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: white; border: none; border-radius: 10px;
  padding: 10px 18px; font-size: 14px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.add-btn:hover { opacity: 0.9; }

/* Loading / Empty */
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 80px; color: #94A3B8; font-size: 14px;
}

.empty-icon {
  width: 72px; height: 72px; background: #F1F5F9; border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
}
.empty-title { font-size: 16px; font-weight: 600; color: #475569; }
.empty-sub { font-size: 13px; color: #94A3B8; }

.loader {
  width: 32px; height: 32px; border: 3px solid #E2E8F0;
  border-top-color: #6366F1; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Table */
.clients-table-wrap {
  background: white; border-radius: 14px; border: 1px solid #F1F5F9;
  overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.clients-table { width: 100%; border-collapse: collapse; }

.clients-table thead tr { background: #F8FAFC; }
.clients-table th {
  padding: 12px 16px; text-align: left;
  font-size: 12px; font-weight: 600; color: #64748B;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid #F1F5F9;
}
.clients-table td {
  padding: 14px 16px; border-bottom: 1px solid #F8FAFC;
  vertical-align: middle;
}
.clients-table tbody tr:last-child td { border-bottom: none; }
.clients-table tbody tr:hover { background: #FAFAFA; }

.client-name-cell { display: flex; align-items: center; gap: 12px; }
.client-avatar {
  width: 36px; height: 36px; border-radius: 9px;
  color: white; font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.client-name { font-size: 14px; font-weight: 600; color: #0F172A; }
.client-url { font-size: 12px; color: #94A3B8; }
.client-url[href] { color: #6366F1; text-decoration: none; }
.client-url[href]:hover { text-decoration: underline; }

.platform-badge {
  font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px;
}
.platform-wordpress { background: #EEF2FF; color: #4338CA; }
.platform-shopify { background: #F0FDF4; color: #15803D; }
.platform-custom { background: #F8FAFC; color: #475569; }

.status-dot-wrap { display: flex; align-items: center; gap: 7px; }
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
}
.status-dot.active { background: #22C55E; }
.status-dot.inactive { background: #CBD5E1; }
.status-text { font-size: 13px; color: #475569; }

/* Tenant column */
.tenant-cell { display: flex; align-items: center; gap: 6px; }
.tenant-badge {
  font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px;
  background: rgba(99,102,241,0.1); color: #4F46E5; white-space: nowrap;
}
.unassigned-badge {
  font-size: 11px; color: #CBD5E1; font-style: italic;
}
.tenant-badge-ro { font-size: 12px; color: #475569; }
.assign-wrap { position: relative; }
.assign-btn {
  width: 22px; height: 22px; border-radius: 5px; border: 1px solid #E2E8F0;
  background: white; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #94A3B8; transition: all 0.15s; flex-shrink: 0;
}
.assign-btn:hover { background: #EEF2FF; border-color: #C7D2FE; color: #6366F1; }
.assign-dropdown {
  position: absolute; top: 28px; left: 0; z-index: 50;
  background: white; border: 1px solid #E2E8F0; border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12); min-width: 180px; padding: 6px;
}
.assign-dropdown-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  color: #94A3B8; padding: 4px 8px 6px;
}
.assign-option {
  display: block; width: 100%; text-align: left; padding: 7px 10px; border-radius: 7px;
  border: none; background: none; font-size: 13px; color: #334155;
  cursor: pointer; font-family: inherit; transition: all 0.1s;
}
.assign-option:hover { background: #F1F5F9; }
.assign-option.active { background: rgba(99,102,241,0.08); color: #4F46E5; font-weight: 600; }
.assign-option.unassign { color: #EF4444; margin-top: 4px; border-top: 1px solid #F1F5F9; border-radius: 0 0 7px 7px; }
.assign-option.unassign:hover { background: #FEF2F2; }

.sessions-count { font-size: 14px; font-weight: 600; color: #0F172A; }

.ingestion-cell { display: flex; align-items: center; gap: 8px; }
.ingestion-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 5px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.ing-pending { background: #F1F5F9; color: #64748B; }
.ing-running { background: #EFF6FF; color: #2563EB; }
.ing-done { background: #F0FDF4; color: #15803D; }
.ing-failed { background: #FEF2F2; color: #B91C1C; }
.pages-count { font-size: 12px; color: #94A3B8; }

.actions { display: flex; gap: 6px; }
.action-btn {
  width: 30px; height: 30px; border-radius: 7px; border: 1px solid #E2E8F0;
  background: white; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #64748B; transition: all 0.15s;
}
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.view-btn:hover { background: #EEF2FF; border-color: #C7D2FE; color: #4338CA; }
.scrape-btn:hover:not(:disabled) { background: #F0FDF4; border-color: #BBF7D0; color: #15803D; }
.delete-btn:hover { background: #FEF2F2; border-color: #FECACA; color: #DC2626; }

.mini-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.1);
  border-top-color: currentColor; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.mini-spinner.white { border-color: rgba(255,255,255,0.3); border-top-color: white; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px;
}

.modal {
  background: white; border-radius: 16px;
  width: 100%; max-width: 480px;
  box-shadow: 0 25px 50px rgba(0,0,0,0.15);
}
.modal.small { max-width: 380px; }

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 20px 0;
}
.modal-header h3 { font-size: 17px; font-weight: 600; color: #0F172A; }
.modal-close {
  background: none; border: none; cursor: pointer; padding: 4px;
  color: #94A3B8; border-radius: 6px; transition: all 0.15s;
}
.modal-close:hover { background: #F1F5F9; color: #475569; }

.modal-body { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { padding: 0 20px 20px; display: flex; gap: 10px; justify-content: flex-end; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 500; color: #475569; }
.field input, .field select {
  border: 1px solid #E2E8F0; border-radius: 9px; padding: 10px 12px;
  font-size: 14px; color: #0F172A; outline: none; font-family: inherit;
  transition: border-color 0.15s;
}
.field input:focus, .field select:focus { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.08); }
.field-hint { font-size: 12px; color: #94A3B8; }

.webhook-info {
  background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 14px;
}
.info-title { font-size: 13px; font-weight: 600; color: #15803D; margin-bottom: 6px; }
.info-text { font-size: 12px; color: #166534; line-height: 1.5; margin-bottom: 8px; }
.info-code { font-family: monospace; font-size: 11px; background: rgba(0,0,0,0.05); padding: 6px 10px; border-radius: 6px; color: #065F46; }
.info-sub { font-size: 11px; color: #94A3B8; margin-top: 8px; }

.form-error {
  background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px;
  padding: 10px 12px; font-size: 13px; color: #B91C1C;
}

.cancel-btn {
  background: white; border: 1px solid #E2E8F0; border-radius: 9px;
  padding: 9px 16px; font-size: 14px; font-weight: 500; color: #475569;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.cancel-btn:hover { background: #F8FAFC; }

.submit-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white;
  border: none; border-radius: 9px; padding: 9px 20px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  display: flex; align-items: center; gap: 8px; min-width: 120px; justify-content: center;
  transition: opacity 0.15s;
}
.submit-btn:hover:not(:disabled) { opacity: 0.9; }
.submit-btn:disabled { opacity: 0.6; }

.delete-warning { font-size: 14px; color: #475569; line-height: 1.5; }

.delete-confirm-btn {
  background: #EF4444; color: white; border: none; border-radius: 9px;
  padding: 9px 20px; font-size: 14px; font-weight: 600; cursor: pointer;
  font-family: inherit; display: flex; align-items: center; gap: 8px;
  min-width: 80px; justify-content: center; transition: opacity 0.15s;
}
.delete-confirm-btn:hover:not(:disabled) { opacity: 0.9; }
.delete-confirm-btn:disabled { opacity: 0.6; }
</style>
