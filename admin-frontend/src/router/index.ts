import { createRouter, createWebHistory } from 'vue-router'
import ADMIN from '../pages/admin.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [{
    path: '/admin',
    name: 'admin',
    component: ADMIN
  }],
})

export default router