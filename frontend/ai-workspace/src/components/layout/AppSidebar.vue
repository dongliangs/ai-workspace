<template>
  <aside class="app-sidebar">
    <div class="sidebar-inner">
      <!-- ============ 上半部分：Logo + 新建对话 + 导航（固定，不滚动） ============ -->
      <div class="sidebar-top">
        <!-- Logo -->
        <div class="flex items-center gap-2 mb-5">
          <div class="logo-mark w-8 h-8 rounded-lg flex items-center justify-center shrink-0">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 2L19.5 7V17L12 22L4.5 17V7L12 2Z"
                fill="white"
                fill-opacity="0.95"
              />
              <path
                d="M12 7V17M8 10V17M16 10V17"
                stroke="#3b82f6"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <span class="font-semibold text-[15px] text-foreground truncate">AI WorkSpace</span>
        </div>

        <!-- 导航菜单 -->
        <nav class="flex flex-col gap-1">
          <a
            v-for="item in navItems"
            :key="item.path"
            href="#"
            class="nav-item"
            :class="{ 'nav-active': isNavActive(item.path) }"
            @click.prevent="onNavClick(item)"
          >
            <component
              :is="item.icon"
              class="w-[18px] h-[18px]"
            />
            <span class="truncate">{{ item.label }}</span>
          </a>
        </nav>
      </div>

      <!-- ============ 下半部分：对话记录（/chat + /agent） + 用户信息 ============ -->
      <div class="sidebar-bottom">
        <!-- 对话记录区域：Chat / Agent 页面显示，按模式过滤，无限滚动加载 -->
        <template v-if="showSessionList">
          <div class="border-t border-border pt-3 flex-1 min-h-0 flex flex-col">
            <div class="flex items-center justify-between px-2 mb-2">
              <span class="text-xs font-medium text-muted">对话记录</span>
            </div>
            <div
              v-infinite-scroll="loadMore"
              v-loading="chatStore.loading"
              :infinite-scroll-disabled="!chatStore.hasMore || chatStore.loadingMore"
              :infinite-scroll-distance="20"
              :infinite-scroll-immediate="false"
              class="chat-history-scroll"
            >
              <a
                v-for="s in chatStore.sessions"
                :key="s.id"
                href="#"
                class="chat-history-item"
                :class="{ active: chatStore.currentId === s.id }"
                @click.prevent="onSelectSession(s.id)"
              >
                <MessageSquare class="w-4 h-4 shrink-0" />
                <span class="truncate">{{ s.title }}</span>
              </a>
              <div v-if="chatStore.loadingMore" class="loading-tip">
                加载中...
              </div>
              <div
                v-if="chatStore.sessions.length && !chatStore.hasMore"
                class="loading-tip"
              >
                没有更多了
              </div>
            </div>
          </div>
        </template>
      </div>
      <!-- 用户信息：固定在底部 -->
      <div class="pt-3 footer-side border-t border-border flex-none">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium shrink-0">
            {{ userInfo.user?.nickname.substring(0, 1) || '' }}
          </div>
          <div class="min-w-0">
            <div class="text-sm font-medium text-foreground truncate">
              {{ userInfo.user?.nickname || '' }}
            </div>
            <div class="text-xs text-muted truncate">
              {{ userInfo.user?.email || '--@--' }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  LayoutGrid,
  MessageSquare,
  FileText,
  BookOpen,
  Bot,
  Workflow,
} from 'lucide-vue-next'
import { computed, watch, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import type { ConversationType } from '@/api/conversation'

interface NavItem {
  label: string
  path: string
  icon: Component
}

const navItems: NavItem[] = [
  { label: '工作台', path: '/workspace', icon: LayoutGrid },
  { label: '新聊天', path: '/chat', icon: MessageSquare },
  // { label: '文件', path: '/files', icon: FileText },
  { label: '知识库', path: '/knowledge', icon: BookOpen },
  { label: 'Agent', path: '/agent', icon: Bot },
  { label: '工作流', path: '/workflow', icon: Workflow },
  // { label: '设置', path: '/settings', icon: Settings },
]

const router = useRouter()
const route = useRoute()
const userInfo = useAuthStore()
const chatStore = useChatStore()

/** 当前路由对应的会话类型（/chat → chat, /agent → agent） */
const routeMode = computed<ConversationType>(() =>
  route.path === '/agent' ? 'agent' : 'chat',
)

/** 是否在 Chat / Agent 页面：控制"对话记录"区域的显隐 */
const showSessionList = computed(() =>
  route.path === '/chat' || route.path === '/agent',
)

/**
 * 导航高亮：Chat / Agent 互斥高亮（不会两个同时 active）。
 * 其他路由按 path 精确匹配。
 */
function isNavActive(path: string): boolean {
  if (path === '/chat') return route.path === '/chat'
  if (path === '/agent') return route.path === '/agent'
  return route.path === path
}

/**
 * 进入 Chat / Agent 页面或切换模式时，按类型拉取最近会话。
 * - 切到 /chat → fetchRecent('chat')
 * - 切到 /agent → fetchRecent('agent')
 * 每次切换都重新拉取，确保列表与当前模式一致。
 */
watch(
  routeMode,
  (mode) => {
    if (showSessionList.value) {
      chatStore.fetchRecent(mode)
    }
  },
  { immediate: true },
)

function onNavClick(item: NavItem) {
  // Chat 和 Agent 入口都重置到欢迎态
  if (item.path === '/chat' || item.path === '/agent') {
    chatStore.selectSession(null)
  }
  router.push(item.path)
}

/**
 * 选中某个对话会话。
 * 根据会话 type 跳转对应路由（chat → /chat, agent → /agent），
 * 保持路由与会话类型一致。
 */
function onSelectSession(id: number) {
  const session = chatStore.sessions.find((s) => s.id === id)
  const targetType: ConversationType = session?.type ?? routeMode.value
  chatStore.selectSession(id)
  // 会话类型与当前路由不一致时跳转
  const targetPath = targetType === 'agent' ? '/agent' : '/chat'
  if (route.path !== targetPath) {
    router.push(targetPath)
  }
}

/** 触底加载更多（由 v-infinite-scroll 触发） */
function loadMore() {
  chatStore.loadMore()
}
</script>

<style scoped>
.app-sidebar {
  width: 220px;
  flex: none;
  background: var(--aws-sidebar);
}
.sidebar-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

/* 上半部分：固定高度，不参与滚动 */
.sidebar-top {
  flex: none;
}

/* 下半部分：占据剩余空间，内部对话记录可滚动，用户信息贴底 */
.sidebar-bottom {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: auto;
}

.logo-mark {
  background: linear-gradient(135deg, var(--aws-primary), var(--aws-primary-hover));
}

/* 对话记录滚动容器 */
.chat-history-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.chat-history-scroll::-webkit-scrollbar {
  display: none;
}
.chat-history-scroll {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.chat-history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--aws-muted);
  font-size: var(--aws-text-sm);
  transition: background-color 0.15s, color 0.15s;
}
.chat-history-item:hover {
  background-color: var(--aws-sidebar-active);
  color: var(--aws-primary);
}
.chat-history-item.active {
  background-color: var(--aws-sidebar-active);
  color: var(--aws-primary);
}

.loading-tip {
  text-align: center;
  padding: 8px;
  color: var(--aws-muted);
  font-size: var(--aws-text-xs);
}

@media (max-width: 1024px) {
  .app-sidebar {
    width: 200px;
  }
}
</style>
