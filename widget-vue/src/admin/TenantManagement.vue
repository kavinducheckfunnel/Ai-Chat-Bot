<template>
  <div class="tenants-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Tenant Management</h1>
        <p class="page-sub">Create and manage tenant accounts and plan assignments</p>
      </div>
      <button class="add-btn" @click="showCreate = true">
        <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        New Tenant
      </button>
    </div>

    <!-- Tenants Table -->
    <div class="table-card">
      <div v-if="loading" class="loading-center">
        <div class="loader"></div>
      </div>
      <div v-else-if="!tenants.length" class="empty-state">
        <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="#CBD5E1" stroke-width="1.5"/><circle cx="9" cy="7" r="4" stroke="#CBD5E1" stroke-width="1.5"/></svg>
        <p>No tenants yet</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Company</th>
            <th>Plan</th>
            <th>Clients</th>
            <th>Sessions / mo</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tenants" :key="t.id">
            <td>
              <div class="user-cell">
                <div class="avatar">{{ t.username.slice(0,2).toUpperCase() }}</div>
                <div>
                  <p class="user-name">{{ t.username }}</p>
                  <p class="user-email">{{ t.email }}</p>
                </div>
              </div>
            </td>
            <td>{{ t.company_name || '—' }}</td>
            <td>
              <span class="plan-badge" :class="t.plan ? 'has-plan' : 'no-plan'">
                {{ t.plan || 'No Plan' }}
              </span>
            </td>
            <td class="center">{{ t.clients_count }}</td>
            <td class="center">{{ t.sessions_this_month }}</td>
            <td>
              <div class="action-row">
                <button class="action-btn edit-btn" @click="openEdit(t)">Edit</button>
                <button class="action-btn plan-btn" @click="openPlan(t)">Plan</button>
                <button class="action-btn impersonate-btn" @click="loginAsTenant(t)" :disabled="impersonating === t.id" title="Login as this tenant">
                  {{ impersonating === t.id ? '...' : 'Login As' }}
                </button>
                <button class="action-btn del-btn" @click="confirmDelete(t)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Tenant Modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <h3>New Tenant</h3>
          <button class="modal-close" @click="showCreate = false">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label>Username *</label>
              <input v-model="createForm.username" class="form-input" placeholder="tenant_username" />
            </div>
            <div class="form-group">
              <label>Password *</label>
              <input v-model="createForm.password" class="form-input" type="password" placeholder="••••••••" />
            </div>
            <div class="form-group">
              <label>Email</label>
              <input v-model="createForm.email" class="form-input" type="email" placeholder="tenant@company.com" />
            </div>
            <div class="form-group">
              <label>Company Name</label>
              <input v-model="createForm.company_name" class="form-input" placeholder="Acme Corp" />
            </div>
            <div class="form-group full">
              <label>Plan</label>
              <select v-model="createForm.plan_id" class="form-input">
                <option value="">No plan</option>
                <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }} (${{ p.price_monthly }}/mo)</option>
              </select>
            </div>
          </div>
          <p v-if="createError" class="form-error">{{ createError }}</p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showCreate = false">Cancel</button>
          <button class="submit-btn" @click="createTenant" :disabled="creating">
            {{ creating ? 'Creating...' : 'Create Tenant' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit Tenant Modal -->
    <div v-if="editTenant" class="modal-overlay" @click.self="editTenant = null">
      <div class="modal">
        <div class="modal-header">
          <h3>Edit: {{ editTenant.username }}</h3>
          <button class="modal-close" @click="editTenant = null">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label>Email</label>
              <input v-model="editForm.email" class="form-input" type="email" />
            </div>
            <div class="form-group">
              <label>Company Name</label>
              <input v-model="editForm.company_name" class="form-input" />
            </div>
            <div class="form-group full">
              <label>New Password (leave blank to keep current)</label>
              <input v-model="editForm.password" class="form-input" type="password" placeholder="••••••••" />
            </div>
          </div>
          <p v-if="editError" class="form-error">{{ editError }}</p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="editTenant = null">Cancel</button>
          <button class="submit-btn" @click="saveTenant" :disabled="saving">
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Assign Plan Modal -->
    <div v-if="planTenant" class="modal-overlay" @click.self="planTenant = null">
      <div class="modal modal-sm">
        <div class="modal-header">
          <h3>Assign Plan — {{ planTenant.username }}</h3>
          <button class="modal-close" @click="planTenant = null">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="plan-options">
            <div
              v-for="p in plans" :key="p.id"
              class="plan-option"
              :class="{ selected: selectedPlanId === p.id }"
              @click="selectedPlanId = p.id"
            >
              <div class="plan-name">{{ p.name }}</div>
              <div class="plan-price">${{ p.price_monthly }}/mo</div>
              <div class="plan-limits">{{ p.max_clients }} clients · {{ p.max_sessions_per_month }} sessions/mo</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="planTenant = null">Cancel</button>
          <button class="submit-btn" @click="savePlan" :disabled="!selectedPlanId || savingPlan">
            {{ savingPlan ? 'Assigning...' : 'Assign Plan' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Impersonate toast -->
    <div v-if="impersonateToast" class="toast" :class="impersonateToast.type">
      {{ impersonateToast.msg }}
    </div>

    <!-- Delete Confirm -->
    <div v-if="deleteTenant" class="modal-overlay" @click.self="deleteTenant = null">
      <div class="modal modal-sm">
        <div class="modal-body" style="padding:28px;text-align:center">
          <div class="del-icon">⚠️</div>
          <h3 class="del-title">Delete Tenant</h3>
          <p class="del-sub">This will permanently delete <strong>{{ deleteTenant.username }}</strong> and all their data.</p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="deleteTenant = null">Cancel</button>
          <button class="danger-btn" @click="doDelete" :disabled="deleting">{{ deleting ? 'Deleting...' : 'Delete' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const tenants = ref([])
const plans = ref([])
const loading = ref(false)

const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = ref({ username: '', password: '', email: '', company_name: '', plan_id: '' })

const editTenant = ref(null)
const editForm = ref({})
const saving = ref(false)
const editError = ref('')

const planTenant = ref(null)
const selectedPlanId = ref(null)
const savingPlan = ref(false)

const deleteTenant = ref(null)
const deleting = ref(false)

const impersonating = ref(null)
const impersonateToast = ref(null)

async function load() {
  loading.value = true
  try {
    const [t, p] = await Promise.all([api.getTenants(), api.getPlans()])
    tenants.value = t || []
    plans.value = p || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function createTenant() {
  createError.value = ''
  if (!createForm.value.username || !createForm.value.password) {
    createError.value = 'Username and password are required.'
    return
  }
  creating.value = true
  try {
    const t = await api.createTenant({ ...createForm.value })
    tenants.value.unshift({ ...t, clients_count: 0, sessions_this_month: 0 })
    showCreate.value = false
    createForm.value = { username: '', password: '', email: '', company_name: '', plan_id: '' }
  } catch (e) {
    createError.value = e.message
  } finally {
    creating.value = false
  }
}

function openEdit(t) {
  editTenant.value = t
  editForm.value = { email: t.email, company_name: t.company_name, password: '' }
  editError.value = ''
}

async function saveTenant() {
  editError.value = ''
  saving.value = true
  try {
    await api.updateTenant(editTenant.value.id, editForm.value)
    const idx = tenants.value.findIndex(x => x.id === editTenant.value.id)
    if (idx >= 0) tenants.value[idx] = { ...tenants.value[idx], ...editForm.value }
    editTenant.value = null
  } catch (e) {
    editError.value = e.message
  } finally {
    saving.value = false
  }
}

function openPlan(t) {
  planTenant.value = t
  selectedPlanId.value = t.plan_id || null
}

async function savePlan() {
  if (!selectedPlanId.value) return
  savingPlan.value = true
  try {
    await api.assignPlan(planTenant.value.id, selectedPlanId.value)
    const plan = plans.value.find(p => p.id === selectedPlanId.value)
    const idx = tenants.value.findIndex(x => x.id === planTenant.value.id)
    if (idx >= 0 && plan) { tenants.value[idx].plan = plan.name; tenants.value[idx].plan_id = plan.id }
    planTenant.value = null
  } catch (e) {
    alert(e.message)
  } finally {
    savingPlan.value = false
  }
}

async function loginAsTenant(t) {
  impersonating.value = t.id
  try {
    const data = await api.impersonateTenant(t.id)
    // Store the impersonation token — overwrites current superadmin token
    const prevToken = localStorage.getItem('cf_access_token')
    const prevUser = localStorage.getItem('cf_user')
    localStorage.setItem('cf_access_token', data.access)
    localStorage.setItem('cf_user', JSON.stringify({ ...data.tenant, role: data.tenant.role }))
    // Keep a breadcrumb so the admin can return to their own session
    localStorage.setItem('cf_impersonate_return_token', prevToken)
    localStorage.setItem('cf_impersonate_return_user', prevUser)
    localStorage.setItem('cf_impersonating', 'true')
    showToast(`Logged in as ${data.tenant.username} (${data.tenant.company_name})`, 'success')
    setTimeout(() => { window.location.href = '/admin/' }, 1200)
  } catch (e) {
    showToast(e.message || 'Impersonation failed', 'error')
  } finally {
    impersonating.value = null
  }
}

function showToast(msg, type = 'success') {
  impersonateToast.value = { msg, type }
  setTimeout(() => { impersonateToast.value = null }, 3000)
}

function confirmDelete(t) { deleteTenant.value = t }

async function doDelete() {
  deleting.value = true
  try {
    await api.deleteTenant(deleteTenant.value.id)
    tenants.value = tenants.value.filter(x => x.id !== deleteTenant.value.id)
    deleteTenant.value = null
  } catch (e) {
    alert(e.message)
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.tenants-page { max-width: 1100px; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -0.4px; }
.page-sub { font-size: 14px; color: #64748B; margin-top: 4px; }

.add-btn {
  display: flex; align-items: center; gap: 7px;
  background: #6366F1; color: white; border: none; border-radius: 9px;
  padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.add-btn:hover { background: #4F46E5; }

.table-card { background: white; border: 1px solid #F1F5F9; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }

.loading-center { display: flex; justify-content: center; padding: 48px; }
.loader { width: 28px; height: 28px; border: 3px solid #E2E8F0; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 60px; color: #94A3B8; font-size: 14px; }

.table { width: 100%; border-collapse: collapse; }
.table th { background: #F8FAFC; padding: 11px 16px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94A3B8; }
.table td { padding: 14px 16px; border-top: 1px solid #F8FAFC; font-size: 13px; color: #334155; }
.table tr:hover td { background: #FAFBFF; }
.center { text-align: center; }

.user-cell { display: flex; align-items: center; gap: 10px; }
.avatar { width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg,#6366F1,#8B5CF6); color: white; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.user-name { font-size: 13px; font-weight: 600; color: #1E293B; }
.user-email { font-size: 11px; color: #94A3B8; }

.plan-badge { padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
.has-plan { background: rgba(99,102,241,0.1); color: #4F46E5; }
.no-plan { background: #F1F5F9; color: #94A3B8; }

.action-row { display: flex; gap: 6px; }
.action-btn { padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; border: 1px solid; transition: all 0.15s; font-family: inherit; }
.edit-btn { background: #EFF6FF; border-color: #BFDBFE; color: #1D4ED8; }
.edit-btn:hover { background: #DBEAFE; }
.plan-btn { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.25); color: #6366F1; }
.plan-btn:hover { background: rgba(99,102,241,0.15); }
.del-btn { background: #FEF2F2; border-color: #FECACA; color: #DC2626; }
.del-btn:hover { background: #FEE2E2; }
.impersonate-btn { background: #F0FDF4; border-color: #86EFAC; color: #16A34A; }
.impersonate-btn:hover:not(:disabled) { background: #DCFCE7; }
.impersonate-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Toast */
.toast {
  position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 10px; font-size: 13px; font-weight: 600;
  z-index: 9999; box-shadow: 0 8px 24px rgba(0,0,0,0.12); animation: fadeIn 0.2s ease;
}
.toast.success { background: #16A34A; color: white; }
.toast.error { background: #DC2626; color: white; }
@keyframes fadeIn { from { opacity: 0; transform: translateX(-50%) translateY(8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal { background: white; border-radius: 16px; width: 100%; max-width: 540px; box-shadow: 0 25px 50px rgba(0,0,0,0.15); }
.modal-sm { max-width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 20px 16px; border-bottom: 1px solid #F1F5F9; }
.modal-header h3 { font-size: 16px; font-weight: 600; color: #0F172A; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: 1px solid #F1F5F9; }
.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: #94A3B8; border-radius: 6px; transition: all 0.15s; }
.modal-close:hover { background: #F1F5F9; color: #475569; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-group.full { grid-column: 1 / -1; }
.form-group label { font-size: 12px; font-weight: 600; color: #475569; }
.form-input { border: 1px solid #E2E8F0; border-radius: 8px; padding: 9px 12px; font-size: 13px; font-family: inherit; outline: none; transition: border-color 0.15s; }
.form-input:focus { border-color: #6366F1; }
.form-error { color: #DC2626; font-size: 12px; margin-top: 8px; }

.cancel-btn { background: #F1F5F9; border: 1px solid #E2E8F0; color: #475569; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; font-family: inherit; }
.cancel-btn:hover { background: #E2E8F0; }
.submit-btn { background: #6366F1; color: white; border: none; border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s; }
.submit-btn:hover:not(:disabled) { background: #4F46E5; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.danger-btn { background: #DC2626; color: white; border: none; border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; }
.danger-btn:hover:not(:disabled) { background: #B91C1C; }

/* Plan options */
.plan-options { display: flex; flex-direction: column; gap: 10px; }
.plan-option { padding: 14px; border: 2px solid #E2E8F0; border-radius: 10px; cursor: pointer; transition: all 0.15s; }
.plan-option:hover { border-color: #A5B4FC; background: #FAFBFF; }
.plan-option.selected { border-color: #6366F1; background: rgba(99,102,241,0.05); }
.plan-name { font-size: 14px; font-weight: 700; color: #0F172A; }
.plan-price { font-size: 13px; color: #6366F1; font-weight: 600; margin-top: 2px; }
.plan-limits { font-size: 11px; color: #94A3B8; margin-top: 4px; }

/* Delete */
.del-icon { font-size: 32px; margin-bottom: 12px; }
.del-title { font-size: 17px; font-weight: 700; color: #0F172A; margin-bottom: 8px; }
.del-sub { font-size: 13px; color: #64748B; line-height: 1.5; }
</style>
