import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录' } },
  { path: '/', name: 'SeatOverview', component: () => import('../views/SeatOverview.vue'), meta: { requiresAuth: true, title: '座位' } },
  { path: '/checkin', name: 'CheckIn', component: () => import('../views/CheckIn.vue'), meta: { requiresAuth: true, title: '签到' } },
  { path: '/attendance', name: 'MyAttendance', component: () => import('../views/MyAttendance.vue'), meta: { requiresAuth: true, title: '我的出勤' } },
  { path: '/leaderboard', name: 'Leaderboard', component: () => import('../views/Leaderboard.vue'), meta: { requiresAuth: true, title: '排行榜' } },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '管理后台' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 实验室座位系统` : '实验室座位系统'
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    localStorage.setItem('redirectAfterLogin', to.fullPath)
    next('/login')
  } else {
    next()
  }
})

export default router
