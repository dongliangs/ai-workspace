<template>
  <div class="auth-shell">
    <!-- 左侧：品牌展示区 -->
    <aside class="auth-brand">
      <div class="brand-inner">
        <!-- Logo -->
        <div class="brand-logo">
          <span class="logo-badge">AI</span>
          <span class="logo-text">AI WorkSpace</span>
        </div>

        <!-- 标题与副标题 -->
        <div class="brand-copy">
          <h1 class="brand-title">
            让 AI 真正帮你完成工作
          </h1>
          <p class="brand-subtitle">
            文档分析 · 数据处理 · 知识问答 · 任务执行 · 智能创作
          </p>
        </div>

        <!-- 插画区（渐变背景 + 装饰元素） -->
        <div class="brand-illust">
          <div class="illust-card">
            <svg
              viewBox="0 0 320 220"
              class="illust-svg"
              xmlns="http://www.w3.org/2000/svg"
            >
              <!-- 笔记本电脑 -->
              <rect
                x="70"
                y="60"
                width="180"
                height="110"
                rx="8"
                fill="#fff"
                stroke="#3b82f6"
                stroke-width="2"
              />
              <rect
                x="80"
                y="70"
                width="160"
                height="80"
                rx="4"
                fill="#eff6ff"
              />
              <!-- 屏幕内容：AI 标识 -->
              <circle
                cx="160"
                cy="105"
                r="14"
                fill="#3b82f6"
              />
              <text
                x="160"
                y="111"
                text-anchor="middle"
                fill="#fff"
                font-size="14"
                font-weight="700"
                font-family="sans-serif"
              >AI</text>
              <line
                x1="120"
                y1="135"
                x2="200"
                y2="135"
                stroke="#dbeafe"
                stroke-width="3"
                stroke-linecap="round"
              />
              <line
                x1="135"
                y1="145"
                x2="185"
                y2="145"
                stroke="#dbeafe"
                stroke-width="3"
                stroke-linecap="round"
              />
              <!-- 底座 -->
              <path
                d="M55 175 H265 L250 195 H70 Z"
                fill="#3b82f6"
                opacity="0.15"
              />
              <!-- 装饰元素：漂浮的方块/圆环 -->
              <circle
                cx="270"
                cy="50"
                r="16"
                fill="none"
                stroke="#3b82f6"
                stroke-width="3"
                opacity="0.5"
              />
              <rect
                x="40"
                y="40"
                width="20"
                height="20"
                rx="4"
                fill="#3b82f6"
                opacity="0.4"
                transform="rotate(15 50 50)"
              />
              <circle
                cx="280"
                cy="170"
                r="10"
                fill="#10b981"
                opacity="0.4"
              />
              <rect
                x="260"
                y="130"
                width="16"
                height="16"
                rx="3"
                fill="#f59e0b"
                opacity="0.5"
                transform="rotate(20 268 138)"
              />
            </svg>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧：登录/注册表单区 -->
    <main class="auth-panel">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
// 认证页布局：左右分栏，左侧品牌展示，右侧承载登录/注册表单（RouterView）
</script>

<style scoped>
.auth-shell {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #ffffff;
}

/* ---------------- 左侧品牌区 ---------------- */
.auth-brand {
  flex: 1 1 50%;
  min-width: 0;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 50%, #ecfeff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  position: relative;
  overflow: hidden;
}

.auth-brand::before {
  /* 背景装饰：右上大圆形渐变 */
  content: '';
  position: absolute;
  top: -120px;
  right: -120px;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.12), transparent 70%);
  pointer-events: none;
}

.brand-inner {
  max-width: 480px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 40px;
  position: relative;
  z-index: 1;
}

/* Logo */
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.logo-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--aws-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--aws-foreground);
}

/* 标题 */
.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--aws-foreground);
  line-height: 1.3;
  margin: 0;
}
.brand-subtitle {
  font-size: 14px;
  color: var(--aws-muted);
  margin: 0;
}

/* 插画 */
.brand-illust {
  width: 100%;
  display: flex;
  justify-content: center;
}
.illust-card {
  width: 100%;
  max-width: 400px;
  aspect-ratio: 16 / 11;
  border-radius: 16px;
  background: linear-gradient(135deg, #dbeafe, #cffafe);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 20px 50px -20px rgba(59, 130, 246, 0.35);
}
.illust-svg {
  width: 100%;
  height: 100%;
  padding: 16px;
}

/* ---------------- 右侧表单区 ---------------- */
.auth-panel {
  flex: 1 1 50%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  padding: 48px;
}

/* ---------------- 响应式 ---------------- */
@media (max-width: 960px) {
  .auth-brand {
    display: none;
  }
  .auth-panel {
    flex: 1 1 100%;
  }
}

@media (max-width: 480px) {
  .auth-panel {
    padding: 24px;
  }
}
</style>
