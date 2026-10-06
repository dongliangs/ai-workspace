<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Sparkles,
  PenLine,
  Paperclip,
  Play,
  ArrowRight,
  MessageSquare,
  FileText,
  BookOpen,
  Bot,
  type LucideIcon,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 输入框内容
const prompt = ref('')

// 快速开始卡片配置
interface QuickCard {
  icon: LucideIcon
  title: string
  desc: string
  iconBg: string
  iconColor: string
}

const quickCards: QuickCard[] = [
  {
    icon: MessageSquare,
    title: 'AI Chat',
    desc: '与 AI 进行智能对话，获取问题答案和建议',
    iconBg: '#dbeafe',
    iconColor: '#2563eb',
  },
  {
    icon: FileText,
    title: '文件分析',
    desc: '上传文件，让 AI 帮你分析和总结',
    iconBg: '#dcfce7',
    iconColor: '#16a34a',
  },
  {
    icon: BookOpen,
    title: '知识问答',
    desc: '基于知识库，快速获取准确信息',
    iconBg: '#f3e8ff',
    iconColor: '#9333ea',
  },
  {
    icon: Bot,
    title: 'Agent 任务',
    desc: '自动执行复杂任务，提升工作效率',
    iconBg: '#ccfbf1',
    iconColor: '#0d9488',
  },
]

/**
 * 点击"开始执行"：
 * - 未登录 → 跳 /auth（带 redirect 回跳）
 * - 已登录 → 跳 /workspace 并携带 prompt
 */
function handleExecute() {
  if (!authStore.isAuthenticated) {
    router.push({ path: '/auth', query: { redirect: '/' } })
    return
  }
  router.push({ path: '/workspace', query: prompt.value ? { q: prompt.value } : undefined })
}

// 跳登录/注册
function goAuth() {
  router.push('/auth')
}
</script>

<template>
  <div class="home-page">
    <!-- ===== 顶部导航 ===== -->
    <header class="home-header">
      <div class="home-container header-inner">
        <div class="brand">
          <span class="brand-mark"><Sparkles :size="18" /></span>
          <span class="brand-name">AI WorkSpace</span>
        </div>
        <nav class="header-actions">
          <button
            class="btn-text"
            @click="goAuth"
          >
            登录
          </button>
          <button
            class="btn-primary-sm"
            @click="goAuth"
          >
            注册
          </button>
        </nav>
      </div>
    </header>

    <!-- ===== 主体 ===== -->
    <main class="home-main">
      <div class="home-container">
        <!-- Hero -->
        <section class="hero">
          <div class="hero-text">
            <span class="hero-badge">
              <Sparkles :size="14" />
              AI 驱动的智能工作台
            </span>
            <h1 class="hero-title">
              让 AI 真正帮你完成工作
            </h1>
            <p class="hero-features">
              文档分析 · 数据处理 · 知识问答 · 任务执行 · 智能创作
            </p>
          </div>
          <!-- 装饰插图：半透明文档卡片 + 星花 -->
          <div
            class="hero-illustration"
            aria-hidden="true"
          >
            <div class="doc-card">
              <div class="doc-line doc-line--1" />
              <div class="doc-line doc-line--2" />
              <div class="doc-line doc-line--3" />
              <div class="doc-line doc-line--4" />
            </div>
            <span class="spark"><Sparkles :size="22" /></span>
          </div>
        </section>

        <!-- 输入栏 -->
        <section class="prompt-bar">
          <div class="prompt-input">
            <PenLine
              class="prompt-icon-left"
              :size="20"
            />
            <input
              v-model="prompt"
              type="text"
              class="prompt-field"
              placeholder="告诉 AI 你想完成什么..."
              @keydown.enter="handleExecute"
            >
            <button
              class="prompt-attach"
              aria-label="添加附件"
            >
              <Paperclip :size="20" />
            </button>
            <button
              class="btn-execute"
              @click="handleExecute"
            >
              <Play :size="16" />
              开始执行
            </button>
          </div>
        </section>

        <!-- 快速开始 -->
        <section class="quick-section">
          <div class="section-head">
            <span class="section-accent" />
            <div>
              <h2 class="section-title">
                快速开始
              </h2>
              <p class="section-subtitle">
                选择你需要的功能，开启 AI 助手
              </p>
            </div>
          </div>

          <div class="quick-grid">
            <article
              v-for="card in quickCards"
              :key="card.title"
              class="quick-card"
              @click="handleExecute"
            >
              <div
                class="quick-icon"
                :style="{ background: card.iconBg, color: card.iconColor }"
              >
                <component
                  :is="card.icon"
                  :size="22"
                />
              </div>
              <h3 class="quick-card-title">
                {{ card.title }}
              </h3>
              <p class="quick-card-desc">
                {{ card.desc }}
              </p>
              <span class="quick-card-cta">
                <ArrowRight :size="16" />
              </span>
            </article>
          </div>
        </section>
      </div>
    </main>

    <!-- ===== 页脚 ===== -->
    <footer class="home-footer">
      <div class="home-container footer-inner">
        <span class="footer-note"> AI WorkSpace · 让工作更简单</span>
        <span class="footer-brand">2026年9月</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--aws-background);
}

.home-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
}

/* ===== 顶部导航 ===== */
.home-header {
  height: 64px;
  display: flex;
  align-items: center;
  background: var(--aws-card);
  border-bottom: 1px solid var(--aws-border);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--aws-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}
.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--aws-foreground);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-text {
  padding: 8px 16px;
  font-size: 14px;
  color: var(--aws-muted);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.15s;
}
.btn-text:hover {
  color: var(--aws-primary);
}
.btn-primary-sm {
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 500;
  color: var(--aws-primary-foreground);
  background: var(--aws-primary);
  border: none;
  border-radius: var(--aws-radius-md);
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary-sm:hover {
  background: var(--aws-primary-hover);
}

/* ===== 主体 ===== */
.home-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

/* ===== Hero ===== */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 40px;
  margin-bottom: 40px;
}
.hero-text {
  flex: 1;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--aws-primary);
  background: #eff6ff;
  border-radius: 999px;
  margin-bottom: 20px;
}
.hero-title {
  font-size: 40px;
  line-height: 1.25;
  font-weight: 700;
  color: var(--aws-foreground);
  margin: 0 0 14px;
}
.hero-features {
  font-size: 14px;
  color: var(--aws-muted);
  letter-spacing: 0.3px;
}

/* 装饰插图 */
.hero-illustration {
  position: relative;
  width: 280px;
  height: 200px;
  flex: none;
}
.doc-card {
  position: absolute;
  right: 0;
  top: 10px;
  width: 220px;
  height: 160px;
  background: #fff;
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  box-shadow: var(--aws-shadow-card);
  padding: 22px;
  opacity: 0.85;
  transform: rotate(-4deg);
}
.doc-line {
  height: 8px;
  border-radius: 4px;
  background: var(--aws-border);
  margin-bottom: 14px;
}
.doc-line--1 { width: 60%; background: var(--aws-primary); opacity: 0.7; }
.doc-line--2 { width: 90%; }
.doc-line--3 { width: 75%; }
.doc-line--4 { width: 50%; }
.spark {
  position: absolute;
  left: 30px;
  top: 0;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--aws-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.35);
  transform: rotate(8deg);
}

/* ===== 输入栏 ===== */
.prompt-bar {
  margin-bottom: 56px;
}
.prompt-input {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 56px;
  padding: 0 8px 0 20px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border-strong);
  border-radius: 999px;
  box-shadow: var(--aws-shadow-card);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.prompt-input:focus-within {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}
.prompt-icon-left {
  color: var(--aws-placeholder);
  flex: none;
}
.prompt-field {
  flex: 1;
  height: 100%;
  border: none;
  background: none;
  outline: none;
  font-size: 15px;
  color: var(--aws-foreground);
}
.prompt-field::placeholder {
  color: var(--aws-placeholder);
}
.prompt-attach {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: var(--aws-placeholder);
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.prompt-attach:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-muted);
}
.btn-execute {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 44px;
  padding: 0 22px;
  font-size: 15px;
  font-weight: 600;
  color: var(--aws-primary-foreground);
  background: var(--aws-primary);
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s;
  flex: none;
}
.btn-execute:hover {
  background: var(--aws-primary-hover);
}

/* ===== 快速开始 ===== */
.quick-section {
  margin-bottom: 40px;
}
.section-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
}
.section-accent {
  width: 4px;
  height: 28px;
  background: var(--aws-primary);
  border-radius: 2px;
  margin-top: 2px;
  flex: none;
}
.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--aws-foreground);
  margin: 0 0 4px;
}
.section-subtitle {
  font-size: 13px;
  color: var(--aws-muted);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
.quick-card {
  position: relative;
  padding: 24px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  box-shadow: var(--aws-shadow-card);
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}
.quick-card:hover {
  transform: translateY(-2px);
  border-color: var(--aws-primary);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.1);
}
.quick-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.quick-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--aws-foreground);
  margin: 0 0 8px;
}
.quick-card-desc {
  font-size: 13px;
  line-height: 1.5;
  color: var(--aws-muted);
}
.quick-card-cta {
  display: inline-flex;
  align-items: center;
  margin-top: 14px;
  color: var(--aws-primary);
  transition: transform 0.15s;
}
.quick-card:hover .quick-card-cta {
  transform: translateX(3px);
}

/* ===== 页脚 ===== */
.home-footer {
  padding: 24px 0;
  border-top: 1px solid var(--aws-border);
  background: var(--aws-card);
}
.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.footer-note {
  font-size: 12px;
  color: var(--aws-placeholder);
}
.footer-brand {
  font-size: 13px;
  color: var(--aws-muted);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .hero-illustration {
    display: none;
  }
  .hero-title {
    font-size: 30px;
  }
  .prompt-input {
    flex-wrap: wrap;
    height: auto;
    padding: 8px;
    border-radius: var(--aws-radius-xl);
  }
  .prompt-field {
    width: 100%;
    padding: 8px 12px;
  }
  .btn-execute {
    width: 100%;
    justify-content: center;
  }
}
@media (max-width: 640px) {
  .quick-grid {
    grid-template-columns: 1fr;
  }
  .home-container {
    padding: 0 20px;
  }
}
</style>
