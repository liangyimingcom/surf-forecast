import { createRouter, createWebHistory } from 'vue-router'

// 3 路由页（Fable5 §3.1）+ /status 数据健康页（R2 §3.2）。history 模式；后端 SPA 回退。
const routes = [
  { path: '/', name: 'home', component: () => import('../pages/HomePage.vue') },
  { path: '/spots', name: 'spots', component: () => import('../pages/SpotsPage.vue') },
  { path: '/spot/:slug', name: 'spot', component: () => import('../pages/SpotPage.vue') },
  { path: '/status', name: 'status', component: () => import('../pages/StatusPage.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({ history: createWebHistory(), routes })
