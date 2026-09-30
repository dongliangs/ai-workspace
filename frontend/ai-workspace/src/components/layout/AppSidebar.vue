<template>
  <aside class="app-sidebar">
    <div class="sidebar-inner">
      <!-- ============ 上半部分：Logo + 新建对话 + 导航（固定，不滚动） ============ -->
      <div class="sidebar-top">
        <!-- Logo -->
        <div class="flex items-center gap-2 mb-5">
          <div class="logo-mark w-8 h-8 rounded-lg flex items-center justify-center shrink-0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L19.5 7V17L12 22L4.5 17V7L12 2Z" fill="white" fill-opacity="0.95" />
              <path d="M12 7V17M8 10V17M16 10V17" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
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
            :class="{ 'nav-active': route.path === item.path }"
            @click.prevent="onNavClick(item)"
          >
            <component :is="item.icon" class="w-[18px] h-[18px]" />
            <span class="truncate">{{ item.label }}</span>
          </a>
        </nav>
      </div>

      <!-- ============ 下半部分：对话记录（仅 /chat） + 用户信息 ============ -->
      <div class="sidebar-bottom">
        <!-- 对话记录区域：仅 AI Chat 页面显示，超出可滚动 -->
        <template v-if="isChatPage">
          <div class="border-t border-border pt-3 flex-1 min-h-0 flex flex-col">
            <div class="flex items-center justify-between px-2 mb-2">
              <span class="text-xs font-medium text-muted">对话记录</span>
            </div>
            <div class="chat-history-scroll">
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
              <div class="text-sm font-medium text-foreground truncate">{{ userInfo.user?.nickname || '' }}</div>
              <div class="text-xs text-muted truncate">{{ userInfo.user?.email || '--@--' }}</div>
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
  Settings,
} from 'lucide-vue-next'
import { computed, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'

interface NavItem {
  label: string
  path: string
  icon: Component
}

const navItems: NavItem[] = [
  { label: '工作台', path: '/workspace', icon: LayoutGrid },
  { label: '新聊天', path: '/chat', icon: MessageSquare },
  { label: '文件', path: '/files', icon: FileText },
  { label: '知识库', path: '/knowledge', icon: BookOpen },
  { label: 'Agent', path: '/agents', icon: Bot },
  { label: '工作流', path: '/workflow', icon: Workflow },
  // { label: '设置', path: '/settings', icon: Settings },
]

const router = useRouter()
const route = useRoute()
const userInfo = useAuthStore()
const chatStore = useChatStore()

// 是否在 AI Chat 页面：控制"对话记录"区域的显隐
const isChatPage = computed(() => route.path === '/chat')

function onNavClick(item: NavItem) {
  // "新聊天"导航项：点击即创建新会话（即便是在 /chat 页也会重置）
  if (item.path === '/chat') {
    chatStore.createSession()
  }
  router.push(item.path)
}

/** 选中某个对话会话 */
function onSelectSession(id: number) {
  chatStore.selectSession(id)
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

@media (max-width: 1024px) {
  .app-sidebar {
    width: 200px;
  }
}
</style>
