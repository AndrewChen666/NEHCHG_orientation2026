import { createRouter, createWebHistory } from 'vue-router'
import ADMIN from '../pages/admin.vue'
import MASTER from '../pages/master.vue'
import USER from '../pages/user.vue'
import LOGIN from '../pages/login.vue'
import SETUP from '../pages/setup.vue'
import MARKET from '../pages/market.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [{
    path: '/',
    redirect: '/login',
  }, {
    path: '/login',
    name: 'login',
    component: LOGIN,
  }, {
    path: '/admin/setup',
    name: 'admin-setup',
    component: SETUP,
  }, {
    path: '/admin',
    name: 'admin',
    component: ADMIN,
    alias: ['/admin/markets', '/admin/teams', '/admin/map'],
  },{
    path: '/master',
    name: 'master',
    component: MASTER,
    alias: ['/master/rates', '/master/challenges'],
  },{
    path: '/user',
    name: 'user',
    component: USER,
    alias: ['/user/challenges', '/user/map'],
  }, {
    path: '/user/market',
    name: 'user-market',
    component: MARKET,
  }],
})

export default router
