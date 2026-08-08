import { createRouter, createWebHistory } from 'vue-router'
import ADMIN from '../pages/admin.vue'
import MASTER from '../pages/master.vue'
import BOSS from '../pages/boss.vue'
import USER from '../pages/user.vue'
import LOGIN from '../pages/login.vue'
import SETUP from '../pages/setup.vue'
import ADMIN_MAP from '../pages/admin-map.vue'
import HOME from '../pages/HomePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    return to.hash
      ? { el: to.hash, behavior: reducedMotion ? 'auto' : 'smooth' }
      : { top: 0, behavior: reducedMotion ? 'auto' : 'smooth' }
  },
  routes: [{
    path: '/',
    name: 'home',
    component: HOME,
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
  }, {
    path: '/admin/markets',
    name: 'admin-markets',
    component: SETUP,
  }, {
    path: '/admin/teams',
    name: 'admin-teams',
    component: SETUP,
  }, {
    path: '/admin/map',
    name: 'admin-map',
    component: ADMIN_MAP,
  },{
    path: '/boss',
    name: 'boss',
    component: BOSS,
  },{
    path: '/master',
    name: 'master',
    component: MASTER,
    alias: ['/master/rates', '/master/challenges'],
  },{
  path: '/user',
    name: 'user',
    component: USER,
    alias: ['/user/map'],
  }],
})

export default router
