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
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/chat/index.vue'),
        },
        {
          path: 'agent',
          name: 'Agent',
          component: () => import('@/views/chat/index.vue'),
        },
      ],
    },
  ],
})

// 路由守卫：
// - AppLayout 下所有路由（/workspace、/chat、/agent）均需登录，未登录跳 /auth（带 redirect）
// - /auth 已登录则跳 /workspace（避免重复登录）
// - / 已登录则跳 /workspace（首页是未登录落地页）
const PROTECTED_PATHS = ['/workspace', '/chat', '/agent']

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (PROTECTED_PATHS.some((p) => to.path.startsWith(p)) && !auth.isAuthenticated) {
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
