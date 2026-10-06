<template>
  <header class="app-header px-6">
    <div class="flex-1 flex items-center min-w-0">
      <div class="relative w-full max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索功能、文件、知识库..."
          class="search-input"
          @keyup.enter="onSearch"
        >
      </div>
    </div>

    <div class="flex items-center gap-4 shrink-0 ml-4">
      <div class="relative">
        <button
          type="button"
          class="relative w-9 h-9 rounded-lg flex items-center justify-center text-muted hover:bg-sidebar-active hover:text-primary transition-colors"
          @click="toggleNotify"
        >
          <Bell class="w-5 h-5" />
          <span class="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary" />
        </button>

        <transition name="dropdown">
          <div
            v-if="notifyOpen"
            class="notify-dropdown"
          >
            <div class="notify-header">
              <span class="notify-title">通知</span>
              <span class="notify-count">{{ notifications.length }} 条未读</span>
            </div>
            <div class="notify-list">
              <a
                v-for="(n, i) in notifications"
                :key="i"
                href="#"
                class="notify-item"
                @click.prevent="notifyOpen = false"
              >
                <div
                  class="notify-dot"
                  :style="{ background: n.color }"
                />
                <div class="min-w-0">
                  <div class="notify-text truncate">{{ n.text }}</div>
                  <div class="notify-time">{{ n.time }}</div>
                </div>
              </a>
            </div>
            <div class="notify-footer">
              <a
                href="#"
                class="notify-all"
                @click.prevent="notifyOpen = false"
              >查看全部通知</a>
            </div>
          </div>
        </transition>
      </div>

      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium shrink-0">
          {{ userInfo?.nickname.substring(0,1) || '小' }}
        </div>
        <!-- <span class="text-sm text-foreground truncate">小明</span> -->
        <el-dropdown>
          <span class="user-menu text-sm truncate">
            {{ userInfo?.nickname || '小明' }}
            <el-icon>
              <ArroeDown />
            </el-icon>
          </span>
          <template #dropdown>
            <el-dropdoen-menu>
              <el-dropdown-item>
                个人设置
              </el-dropdown-item>
              <el-dropdown-item
                divided
                @click="handleLogout"
              >
                退出登录
              </el-dropdown-item>
            </el-dropdoen-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell, Search } from 'lucide-vue-next'
import { ElDropdown } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
// import type { AuthUser } from '@/stores/auth'

const keyword = ref('')
const notifyOpen = ref(false)
const authStore = useAuthStore()
interface Notice {
  text: string
  time: string
  color: string
}
// 从本地存储获取登录后返回的用户信息
const userInfo = authStore.user
const notifications = ref<Notice[]>([
  { text: 'AI WorkSpace V0.8 正式发布', time: '2小时前', color: '#3b82f6' },
  { text: '支持多种文档格式上传与解析', time: '昨天', color: '#10b981' },
  { text: '知识库功能上线，支持本地文件导入', time: '3天前', color: '#3b82f6' },
])

function toggleNotify() {
  notifyOpen.value = !notifyOpen.value
}

function onSearch() {
  if (!keyword.value.trim()) return
  // Placeholder search action
  console.log('search:', keyword.value)
}

function onDocClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.relative')) {
    notifyOpen.value = false
  }
}

const handleLogout = async () => {
	await authStore.logout()
	// 退出后重新加载页面，确保所有状态（pinia、缓存、组件）完全重置
	window.location.reload()
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.app-header {
  height: 64px;
  flex: none;
  display: flex;
  align-items: center;
  background: var(--aws-header);
  border-bottom: 1px solid var(--aws-border);
}
.search-input {
  width: 100%;
  height: 40px;
  padding-left: 36px;
  padding-right: 16px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border);
  background: var(--aws-input);
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  transition: box-shadow 0.15s, border-color 0.15s;
}
.search-input::placeholder {
  color: var(--aws-placeholder);
}
.search-input:focus {
  outline: none;
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.notify-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  max-width: calc(100vw - 32px);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
  z-index: 60;
  overflow: hidden;
}
.notify-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--aws-border);
}
.notify-title {
  font-size: var(--aws-text-base);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
}
.notify-count {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.notify-list {
  max-height: 320px;
  overflow-y: auto;
}
.notify-item {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  transition: background-color 0.15s;
}
.notify-item:hover {
  background: var(--aws-sidebar-active);
}
.notify-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex: none;
}
.notify-text {
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  line-height: var(--aws-leading-normal);
}
.notify-time {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 2px;
}
.notify-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--aws-border);
  text-align: center;
}
.notify-all {
  font-size: var(--aws-text-sm);
  color: var(--aws-primary);
}
.notify-all:hover {
  color: var(--aws-primary-hover);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
