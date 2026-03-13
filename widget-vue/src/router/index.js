import { createRouter, createWebHistory } from 'vue-router'
import ChatWidget from '../components/ChatWidget.vue'
import Dashboard from '../admin/Dashboard.vue'
import ClientList from '../admin/ClientList.vue'
import ClientDetail from '../admin/ClientDetail.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: ChatWidget
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Dashboard
  },
  {
    path: '/admin/clients',
    name: 'ClientList',
    component: ClientList
  },
  {
    path: '/admin/clients/:id',
    name: 'ClientDetail',
    component: ClientDetail
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
