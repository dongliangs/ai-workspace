<template>
  <div class="workspace">
    <!-- Welcome banner -->
    <section class="banner mb-6 p-5">
      <div class="flex flex-row items-center gap-6">
        <div class="flex-1 min-w-0 w-full">
          <h1 class="welcome-title mb-2" style="text-wrap: balance">欢迎回来，小明 👋</h1>
          <p class="welcome-tagline pt-2">让 AI 真正帮你完成工作</p>
          <p class="text-xs text-muted py-4">有什么新的想法任务交给智能助手，让它帮你高效完成。</p>
          <div class="relative w-full max-w-lg">
            <input
              v-model="prompt"
              type="text"
              placeholder="输入问题，让 AI 帮你开始创作..."
              class="prompt-input"
              @keyup.enter="onPrompt"
            />
            <button
              type="button"
              class="prompt-btn"
              :disabled="!prompt.trim()"
              @click="onPrompt"
            >
              <ArrowUp class="w-4 h-4" />
            </button>
          </div>
        </div>
        <div class="w-full lg:w-[280px] h-[160px] shrink-0">
          <svg viewBox="0 0 280 160" class="w-full h-full" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="ws-banner-grad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.08" />
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.20" />
              </linearGradient>
            </defs>
            <rect width="280" height="160" rx="12" fill="url(#ws-banner-grad)" />
            <rect x="70" y="36" width="140" height="92" rx="10" fill="#ffffff" stroke="#3b82f6" stroke-opacity="0.18" stroke-width="2" />
            <rect x="82" y="50" width="116" height="64" rx="4" fill="#3b82f6" fill-opacity="0.06" />
            <text x="140" y="90" text-anchor="middle" fill="#3b82f6" font-size="22" font-weight="700" style="font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">AI</text>
            <rect x="90" y="132" width="100" height="6" rx="3" fill="#3b82f6" fill-opacity="0.22" />
            <path d="M46 122 Q52 86 42 74 Q58 84 64 122 Z" fill="#10b981" fill-opacity="0.28" />
            <circle cx="52" cy="74" r="4" fill="#10b981" />
            <path d="M236 116 Q230 82 244 72 Q238 92 250 116 Z" fill="#3b82f6" fill-opacity="0.22" />
            <circle cx="242" cy="72" r="5" fill="#3b82f6" fill-opacity="0.55" />
            <path d="M210 44 L213 56 L225 60 L213 64 L210 76 L207 64 L195 60 L207 56 Z" fill="#3b82f6" fill-opacity="0.35" />
          </svg>
        </div>
      </div>
    </section>

    <!-- Quick start -->
    <section class="mb-6">
      <h2 class="section-title mb-4 py-4">快速开始</h2>
      <div class="quick-grid grid gap-4">
        <button
          v-for="item in quickStart"
          :key="item.title"
          type="button"
          class="quick-card"
          @click="onQuickClick(item)"
        >
          <div class="icon-box" :style="item.iconStyle">
            <component :is="item.icon" class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <div class="quick-title truncate">{{ item.title }}</div>
            <div class="quick-desc line-clamp-2 mt-1">{{ item.desc }}</div>
          </div>
          <span class="panel-link inline-flex items-center gap-1 mt-auto">
            <span>立即开始</span>
            <ArrowRight class="w-3 h-3" />
          </span>
        </button>
      </div>
    </section>

    <!-- Bottom grid -->
    <section class="bottom-grid grid gap-4">
      <!-- 最近使用 -->
      <div class="bg-card rounded-xl shadow-card p-5">
        <div class="panel-header">
          <h3 class="section-title">最近使用</h3>
          <a href="#" class="panel-link inline-flex items-center gap-1" @click.prevent="onViewAll('最近使用')">
            <span>查看全部</span>
            <ArrowRight class="w-3 h-3" />
          </a>
        </div>
        <div class="flex flex-col gap-3">
          <a
            v-for="(r, i) in recent"
            :key="i"
            href="#"
            class="flex items-center gap-3 group"
            @click.prevent="onItemClick(r)"
          >
            <div class="file-icon-box" :style="r.iconStyle">
              <component :is="r.icon" class="w-4 h-4" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="list-title truncate group-hover:text-primary transition-colors">{{ r.title }}</div>
              <div class="list-meta truncate">{{ r.meta }}</div>
            </div>
          </a>
        </div>
      </div>

      <!-- 热门模板 -->
      <div class="bg-card rounded-xl shadow-card p-5">
        <div class="panel-header">
          <h3 class="section-title">热门模板</h3>
          <a href="#" class="panel-link inline-flex items-center gap-1" @click.prevent="onViewAll('热门模板')">
            <span>查看更多</span>
            <ArrowRight class="w-3 h-3" />
          </a>
        </div>
        <div class="flex flex-col gap-3">
          <a
            v-for="(t, i) in templates"
            :key="i"
            href="#"
            class="flex items-center gap-3 group"
            @click.prevent="onItemClick(t)"
          >
            <div class="file-icon-box" :style="t.iconStyle">
              <component :is="t.icon" class="w-4 h-4" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="list-title truncate group-hover:text-primary transition-colors">{{ t.title }}</div>
              <div class="list-meta truncate">{{ t.meta }}</div>
            </div>
          </a>
        </div>
      </div>

      <!-- 系统公告 -->
      <div class="bg-card rounded-xl shadow-card p-5">
        <div class="panel-header">
          <h3 class="section-title">系统公告</h3>
          <a href="#" class="panel-link inline-flex items-center gap-1" @click.prevent="onViewAll('系统公告')">
            <span>查看全部</span>
            <ArrowRight class="w-3 h-3" />
          </a>
        </div>
        <div class="flex flex-col gap-3">
          <a
            v-for="(a, i) in announcements"
            :key="i"
            href="#"
            class="flex items-start gap-3 group"
            @click.prevent="onItemClick(a)"
          >
            <div class="file-icon-box mt-0.5" :style="a.iconStyle">
              <component :is="a.icon" class="w-4 h-4" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="list-title truncate group-hover:text-primary transition-colors">{{ a.title }}</div>
              <div class="list-meta truncate">{{ a.meta }}</div>
            </div>
          </a>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, type CSSProperties, type Component } from 'vue'
import {
  ArrowUp,
  ArrowRight,
  MessageSquare,
  FileBarChart,
  Lightbulb,
  Bot,
  FileText,
  BarChart2,
  LayoutTemplate,
  ClipboardList,
  Megaphone,
  FileType,
  Database,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'

const prompt = ref('')

interface QuickItem {
  title: string
  desc: string
  icon: Component
  iconStyle: CSSProperties
}

const quickStart: QuickItem[] = [
  {
    title: 'AI Chat',
    desc: '与 AI 进行智能对话，获取问题答案和建议',
    icon: MessageSquare,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 12%, #ffffff)',
      color: '#3b82f6',
    },
  },
  {
    title: '文件分析',
    desc: '上传文档，让 AI 帮你分析总结',
    icon: FileBarChart,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #10b981 12%, #ffffff)',
      color: '#10b981',
    },
  },
  {
    title: '知识问答',
    desc: '基于知识库快速获取准确信息',
    icon: Lightbulb,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 18%, #ffffff)',
      color: '#3b82f6',
    },
  },
  {
    title: 'Agent 任务',
    desc: '自动执行复杂任务，提升工作效率',
    icon: Bot,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #10b981 18%, #ffffff)',
      color: '#10b981',
    },
  },
]

interface ListItem {
  title: string
  meta: string
  icon: Component
  iconStyle: CSSProperties
}

const recent: ListItem[] = [
  {
    title: '数据分析报告',
    meta: '文档分析 · 2小时前',
    icon: FileText,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 10%, #ffffff)',
      color: '#3b82f6',
    },
  },
  {
    title: '产品需求文档',
    meta: '文档分析 · 昨天',
    icon: FileText,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #10b981 10%, #ffffff)',
      color: '#10b981',
    },
  },
  {
    title: '市场调研分析',
    meta: 'Agent 任务 · 3天前',
    icon: BarChart2,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 14%, #ffffff)',
      color: '#3b82f6',
    },
  },
]

const templates: ListItem[] = [
  {
    title: '数据分析报告',
    meta: '工作提效',
    icon: LayoutTemplate,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 10%, #ffffff)',
      color: '#3b82f6',
    },
  },
  {
    title: '产品方案策划',
    meta: '产品运营',
    icon: FileText,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #10b981 10%, #ffffff)',
      color: '#10b981',
    },
  },
  {
    title: '会议纪要整理',
    meta: '团队协作',
    icon: ClipboardList,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 14%, #ffffff)',
      color: '#3b82f6',
    },
  },
]

const announcements: ListItem[] = [
  {
    title: 'AI WorkSpace V0.8 正式发布',
    meta: '2026-09-21',
    icon: Megaphone,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 12%, #ffffff)',
      color: '#3b82f6',
    },
  },
  {
    title: '支持多种文档格式上传与解析',
    meta: '2026-09-18',
    icon: FileType,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #10b981 10%, #ffffff)',
      color: '#10b981',
    },
  },
  {
    title: '知识库功能上线，支持本地文件导入',
    meta: '2026-09-15',
    icon: Database,
    iconStyle: {
      backgroundColor: 'color-mix(in srgb, #3b82f6 12%, #ffffff)',
      color: '#3b82f6',
    },
  },
]

function onPrompt() {
  const text = prompt.value.trim();
  
  if (!text) return
  // ElMessage.success(`已提交：${text}`)
  prompt.value = ''
}

function onQuickClick(item: QuickItem) {
  ElMessage.info(`即将进入：${item.title}`)
}

function onItemClick(item: ListItem) {
  ElMessage.info(`打开：${item.title}`)
}

function onViewAll(name: string) {
  ElMessage.info(`查看全部：${name}`)
}
</script>

<style scoped>
.prompt-input {
  width: 100%;
  height: 44px;
  padding-left: 16px;
  padding-right: 48px;
  border-radius: var(--aws-radius-xl);
  border: 1px solid var(--aws-border);
  background: var(--aws-input);
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  box-shadow: var(--aws-shadow-card);
  transition: box-shadow 0.15s, border-color 0.15s;
}
.prompt-input::placeholder {
  color: var(--aws-placeholder);
}
.prompt-input:focus {
  outline: none;
  border-color: var(--aws-primary);
  box-shadow: var(--aws-shadow-card), 0 0 0 3px rgba(59, 130, 246, 0.2);
}
.prompt-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  border-radius: var(--aws-radius-md);
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s, opacity 0.15s;
}
.prompt-btn:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.prompt-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.bottom-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 20px;
}

.quick-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--aws-card);
  border-radius: var(--aws-radius-lg);
  box-shadow: var(--aws-shadow-card);
  padding: 20px;
  text-align: left;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}
.quick-card:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  transform: translateY(-2px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

@media (max-width: 1024px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}
</style>
