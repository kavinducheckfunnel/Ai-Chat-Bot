<template>
  <div class="admin-container">
    <Sidebar />
    <main class="admin-main">
      <header class="admin-header">
        <div class="header-with-action">
          <h1>Managed Clients</h1>
          <button @click="showModal = true" class="btn-primary">+ Add New Client</button>
        </div>
        <p>Manage tenants and their AI chatbot configurations</p>
      </header>

      <div v-if="loading" class="loading">Loading clients...</div>
      
      <div v-else class="client-table-container">
        <table class="client-table">
          <thead>
            <tr>
              <th>Client Name</th>
              <th>Domain</th>
              <th>Platform</th>
              <th>Status</th>
              <th>Sessions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="client in clients" :key="client.id">
              <td>
                <div class="client-name-cell">
                  <div class="client-icon">{{ client.name.charAt(0) }}</div>
                  <span>{{ client.name }}</span>
                </div>
              </td>
              <td><code>{{ client.domain_url }}</code></td>
              <td><span class="badge">{{ client.platform }}</span></td>
              <td>
                <span :class="['status-dot', client.is_active ? 'active' : 'inactive']"></span>
                {{ client.is_active ? 'Active' : 'Inactive' }}
              </td>
              <td>{{ client.session_count }}</td>
              <td>
                <div class="actions">
                  <router-link :to="'/admin/clients/' + client.id" class="btn-icon" title="View Details">👁️</router-link>
                  <button @click="triggerScrape(client.id)" class="btn-icon" title="Trigger Re-scrape">🔄</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- Simple Create Modal -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal">
        <h2>New AI Chatbot Client</h2>
        <form @submit.prevent="createClient">
          <div class="form-group">
            <label>Business Name</label>
            <input v-model="newClient.name" placeholder="e.g. Acme Corp" required />
          </div>
          <div class="form-group">
            <label>Website URL</label>
            <input v-model="newClient.domain_url" placeholder="https://acme.com" required />
          </div>
          <div class="form-group">
            <label>Platform</label>
            <select v-model="newClient.platform">
              <option value="WORDPRESS">WordPress</option>
              <option value="SHOPIFY">Shopify</option>
              <option value="CUSTOM">Custom</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" @click="showModal = false" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary">Create Client</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './Sidebar.vue'

const clients = ref([])
const loading = ref(true)
const showModal = ref(false)
const newClient = ref({
  name: '',
  domain_url: '',
  platform: 'WORDPRESS'
})

const fetchClients = async () => {
    loading.value = true
    try {
        const res = await fetch('http://localhost:8000/api/admin/clients/')
        clients.value = await res.json()
    } catch (e) {
        console.error("Failed to fetch clients", e)
    } finally {
        loading.value = false
    }
}

const createClient = async () => {
    try {
        const res = await fetch('http://localhost:8000/api/admin/clients/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newClient.value)
        })
        if (res.ok) {
            showModal.value = false
            newClient.value = { name: '', domain_url: '', platform: 'WORDPRESS' }
            await fetchClients()
        }
    } catch (e) {
        console.error("Failed to create client", e)
    }
}

const triggerScrape = async (id) => {
    alert("Triggering AI re-scrape for this domain...")
    try {
        await fetch(`http://localhost:8000/api/admin/clients/${id}/scrape/`, { method: 'POST' })
    } catch (e) {
        console.error("Scrape failed", e)
    }
}

onMounted(fetchClients)
</script>

<style scoped>
.admin-container {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
  font-family: 'Inter', sans-serif;
}
.admin-main {
  flex: 1;
  padding: 40px;
}
.header-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.btn-primary {
  background: #2563eb;
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
}
.client-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  overflow: hidden;
  margin-top: 32px;
}
.client-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.client-table th {
  padding: 16px 24px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.client-table td {
  padding: 16px 24px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}
.client-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.client-icon {
  width: 32px;
  height: 32px;
  background: #e2e8f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #64748b;
}
.badge {
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.active { background: #10b981; }
.status-dot.inactive { background: #94a3b8; }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  padding: 32px;
  border-radius: 16px;
  width: 100%;
  max-width: 480px;
}
.form-group {
  margin-bottom: 20px;
}
.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 0.875rem;
}
.form-group input, .form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
