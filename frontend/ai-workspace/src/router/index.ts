import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 首页：未登录落地页（工作台未登录态），登录用户访问 / 跳到 /workspace
    {
      path: '/',
      name: 'Home',
      component: () => import('@/views/home/index.vue'),
    },
    {
      path: '/auth',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'Auth',
          component: () => import('@/views/auth/index.vue'),
        },
      ],
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        {
          path: 'workspace',
          name: 'Workspace',
          component: () => import('@/views/workspace/index.vue'),
        },
        {
          path:'chat',
          name: 'Chat',
          component: () => import('@/views/chat/index.vue')
        }
      ],
    },
  ],
})

// 路由守卫：
// - /workspace 需登录，未登录跳 /auth（带 redirect 参数，登录后回跳）
// - /auth 已登录则跳 /workspace（避免重复登录）
// - / 已登录则跳 /workspace（首页是未登录落地页）
router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.path.startsWith('/workspace') && !auth.isAuthenticated) {
    return { path: '/auth', query: { redirect: to.fullPath } }
  }
  if (to.path === '/auth' && auth.isAuthenticated) {
    return { path: '/workspace' }
  }
  if (to.path === '/' && auth.isAuthenticated) {
    return { path: '/workspace' }
  }
  return true
})

export default router
