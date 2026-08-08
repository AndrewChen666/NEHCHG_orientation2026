import { createRouter, createWebHistory } from 'vue-router'
import ADMIN from '../pages/admin.vue'
import MASTER from '../pages/master.vue'
import USER from '../pages/user.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [{
    path: '/admin',
    name: 'admin',
    component: ADMIN
  },{
    path: '/master',
    name: 'master',
    component: MASTER
  },{
    path: '/user',
    name: 'user',
    component: USER
  }],
})

export default router