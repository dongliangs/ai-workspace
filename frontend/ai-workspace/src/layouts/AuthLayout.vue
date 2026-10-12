<template>
  <div class="auth-shell">
    <!-- 左侧：品牌展示区（科幻风） -->
    <aside class="auth-brand">
      <!-- 背景装饰层：星空 / 网格 / 透视地面 / 轨道环 / HUD 角标 / 扫描线 -->
      <div class="bg-grid" aria-hidden="true"></div>
      <div class="bg-stars" aria-hidden="true"></div>
      <div class="bg-floor" aria-hidden="true"></div>
      <div class="orbit orbit-a" aria-hidden="true"><span class="orbit-dot"></span></div>
      <div class="orbit orbit-b" aria-hidden="true"><span class="orbit-dot"></span></div>
      <span class="hud-corner hud-tl" aria-hidden="true"></span>
      <span class="hud-corner hud-tr" aria-hidden="true"></span>
      <span class="hud-corner hud-bl" aria-hidden="true"></span>
      <span class="hud-corner hud-br" aria-hidden="true"></span>
      <span class="scanline" aria-hidden="true"></span>

      <div class="brand-inner">
        <!-- 顶栏：Logo + 系统状态 -->
        <div class="brand-top">
          <div class="brand-logo">
            <span class="logo-badge">AI</span>
            <span class="logo-text">AI WorkSpace</span>
          </div>
          <div class="sys-status">
            <span class="sys-dot"></span>
            <span class="sys-text">SYS.ONLINE</span>
          </div>
        </div>

        <!-- 主文案 -->
        <div class="brand-copy">
          <p class="brand-eyebrow">// AI_AGENT_PLATFORM · v2.0</p>
          <h1 class="brand-title">
            让 <em>AI</em> 真正<br>帮你完成工作<span class="caret"></span>
          </h1>
          <p class="brand-subtitle">
            一站式智能工作台，从文档到洞察，从数据到决策。
          </p>
        </div>

        <!-- 终端模拟卡片 -->
        <div class="terminal">
          <div class="terminal-head">
            <span class="t-led t-led-r"></span>
            <span class="t-led t-led-y"></span>
            <span class="t-led t-led-g"></span>
            <span class="t-title">AI.CORE // SYSTEM CONSOLE</span>
          </div>
          <div class="terminal-body">
            <p class="t-line">
              <span class="t-prompt">$</span> analyze --file 销售数据.xlsx
            </p>
            <p class="t-line t-ok">
              <span class="t-mark">✓</span> 解析完成 · 3,842 行 · 12 列
            </p>
            <p class="t-line t-ok">
              <span class="t-mark">✓</span> 已生成趋势图表 chart_q3.png
            </p>
            <p class="t-line t-info">
              <span class="t-mark">→</span> 智能洞察：Q3 环比增长 <b>23.6%</b>
            </p>
            <p class="t-line">
              <span class="t-prompt">$</span> <span class="t-cursor"></span>
            </p>
          </div>
        </div>

        <!-- 能力矩阵 -->
        <div class="feature-grid">
          <div class="feature-item">
            <span class="f-icon"><FileText :size="17" /></span>
            <div class="f-meta">
              <span class="f-name">文档分析</span>
              <span class="f-desc">PDF / Word / Excel</span>
            </div>
          </div>
          <div class="feature-item">
            <span class="f-icon"><BarChart3 :size="17" /></span>
            <div class="f-meta">
              <span class="f-name">数据处理</span>
              <span class="f-desc">清洗 · 统计 · 可视化</span>
            </div>
          </div>
          <div class="feature-item">
            <span class="f-icon"><MessageSquare :size="17" /></span>
            <div class="f-meta">
              <span class="f-name">知识问答</span>
              <span class="f-desc">基于文档精准回答</span>
            </div>
          </div>
          <div class="feature-item">
            <span class="f-icon"><Zap :size="17" /></span>
            <div class="f-meta">
              <span class="f-name">任务执行</span>
              <span class="f-desc">Agent 自动化完成</span>
            </div>
          </div>
        </div>

        <!-- 底部数据栏 -->
        <div class="brand-stats">
          <div class="stat">
            <span class="stat-num">10+</span>
            <span class="stat-label">支持文件格式</span>
          </div>
          <span class="stat-divider"></span>
          <div class="stat">
            <span class="stat-num">99.9%</span>
            <span class="stat-label">服务可用性</span>
          </div>
          <span class="stat-divider"></span>
          <div class="stat">
            <span class="stat-num">24/7</span>
            <span class="stat-label">智能待命</span>
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
import { FileText, BarChart3, MessageSquare, Zap } from 'lucide-vue-next'
// 认证页布局：左侧科幻风品牌展示，右侧承载登录/注册表单（RouterView）
</script>

<style scoped>
.auth-shell {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #ffffff;
}

/* ================= 左侧品牌区（科幻风） ================= */
.auth-brand {
  flex: 1 1 50%;
  min-width: 0;
  background: #04060d;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 44px;
  position: relative;
  overflow: hidden;
}

/* ---------- 背景层 ---------- */
/* 透视网格地面 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(34, 211, 238, 0.045) 0 1px, transparent 1px 56px),
    repeating-linear-gradient(90deg, rgba(34, 211, 238, 0.045) 0 1px, transparent 1px 56px);
  pointer-events: none;
}

/* 星空：双层星点 + 闪烁 */
.bg-stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 25px 35px, rgba(255, 255, 255, 0.65), transparent 100%),
    radial-gradient(1px 1px at 95px 110px, rgba(255, 255, 255, 0.35), transparent 100%),
    radial-gradient(1.5px 1.5px at 160px 50px, rgba(165, 243, 252, 0.55), transparent 100%),
    radial-gradient(1px 1px at 210px 150px, rgba(255, 255, 255, 0.4), transparent 100%),
    radial-gradient(1.5px 1.5px at 60px 180px, rgba(165, 243, 252, 0.35), transparent 100%);
  background-size: 260px 220px;
  animation: twinkle 5s ease-in-out infinite alternate;
  pointer-events: none;
}
@keyframes twinkle {
  from { opacity: 0.55; }
  to   { opacity: 1; }
}

/* 透视地面：底部科幻网格，向地平线消失 */
.bg-floor {
  position: absolute;
  left: -25%;
  right: -25%;
  bottom: -30px;
  height: 240px;
  background-image:
    repeating-linear-gradient(0deg, rgba(34, 211, 238, 0.1) 0 1px, transparent 1px 44px),
    repeating-linear-gradient(90deg, rgba(34, 211, 238, 0.1) 0 1px, transparent 1px 44px);
  transform: perspective(420px) rotateX(62deg);
  transform-origin: center top;
  -webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 0.9), transparent 85%);
  mask-image: linear-gradient(to top, rgba(0, 0, 0, 0.9), transparent 85%);
  pointer-events: none;
}

/* 旋转轨道环（贴边部署，不占布局空间） */
.orbit {
  position: absolute;
  border: 1px dashed rgba(34, 211, 238, 0.22);
  border-radius: 50%;
  pointer-events: none;
}
.orbit-a {
  width: 320px;
  height: 320px;
  top: -110px;
  right: -110px;
  animation: spin 32s linear infinite;
}
.orbit-b {
  width: 190px;
  height: 190px;
  bottom: 40px;
  left: -80px;
  animation: spin 22s linear infinite reverse;
}
.orbit-dot {
  position: absolute;
  top: -3px;
  left: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.9);
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* HUD 角标：四角 L 形括号 */
.hud-corner {
  position: absolute;
  width: 34px;
  height: 34px;
  pointer-events: none;
  opacity: 0.7;
}
.hud-tl { top: 20px; left: 20px; border-top: 2px solid #22d3ee; border-left: 2px solid #22d3ee; }
.hud-tr { top: 20px; right: 20px; border-top: 2px solid #22d3ee; border-right: 2px solid #22d3ee; }
.hud-bl { bottom: 20px; left: 20px; border-bottom: 2px solid #22d3ee; border-left: 2px solid #22d3ee; }
.hud-br { bottom: 20px; right: 20px; border-bottom: 2px solid #22d3ee; border-right: 2px solid #22d3ee; }

/* 全屏扫描线：周期性自上而下掠过 */
.scanline {
  position: absolute;
  left: 0;
  right: 0;
  top: -140px;
  height: 140px;
  background: linear-gradient(to bottom, transparent, rgba(34, 211, 238, 0.05) 55%, rgba(34, 211, 238, 0.12) 98%, transparent);
  animation: scan 8s linear infinite;
  pointer-events: none;
  z-index: 2;
}
@keyframes scan {
  from { top: -140px; }
  to   { top: 100%; }
}

/* ---------- 内容列 ---------- */
.brand-inner {
  max-width: 460px;
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

/* 入场动画：逐块上浮 */
.brand-top, .brand-copy, .terminal, .feature-grid, .brand-stats {
  animation: fade-up 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.brand-top    { animation-delay: 0s; }
.brand-copy   { animation-delay: 0.1s; }
.terminal     { animation-delay: 0.2s; }
.feature-grid { animation-delay: 0.32s; }
.brand-stats  { animation-delay: 0.44s; }

@keyframes fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ---------- 顶栏 ---------- */
.brand-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.logo-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: #22d3ee;
  color: #04060d;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.5px;
  /* 六边形舱体 */
  clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);
  filter: drop-shadow(0 0 10px rgba(34, 211, 238, 0.65));
}
.logo-text {
  font-size: 17px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.3px;
}
.sys-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-family: ui-monospace, 'Cascadia Code', Consolas, 'SF Mono', monospace;
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #34d399;
}
.sys-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  animation: pulse 2s ease-out infinite;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5); }
  70%  { box-shadow: 0 0 0 7px rgba(52, 211, 153, 0); }
  100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
}

/* ---------- 主文案 ---------- */
.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.brand-eyebrow {
  margin: 0;
  font-family: ui-monospace, 'Cascadia Code', Consolas, 'SF Mono', monospace;
  font-size: 12px;
  letter-spacing: 3px;
  color: #22d3ee;
  white-space: nowrap;
}
.brand-title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.28;
  color: #f8fafc;
  letter-spacing: 2px;
  text-shadow: 0 0 30px rgba(34, 211, 238, 0.25);
}
.brand-title em {
  font-style: normal;
  color: #22d3ee;
  text-shadow: 0 0 22px rgba(34, 211, 238, 0.65);
}
.caret {
  display: inline-block;
  width: 3px;
  height: 0.9em;
  margin-left: 8px;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.8);
  vertical-align: -0.08em;
  animation: blink 1.1s steps(2, start) infinite;
}
@keyframes blink {
  to { visibility: hidden; }
}
.brand-subtitle {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #7c8aa0;
}

/* ---------- 终端模拟卡片（切角舱体） ---------- */
.terminal {
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(8, 15, 30, 0.82);
  clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px));
  padding: 1px; /* 让边框跟随切角 */
  box-shadow: 0 24px 48px -24px rgba(0, 0, 0, 0.85);
  overflow: hidden;
}
.terminal-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  border-bottom: 1px solid rgba(34, 211, 238, 0.16);
  background: rgba(34, 211, 238, 0.04);
}
.t-led {
  width: 8px;
  height: 8px;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
}
.t-led-r { background: #f87171; box-shadow: 0 0 6px rgba(248, 113, 113, 0.7); }
.t-led-y { background: #fbbf24; box-shadow: 0 0 6px rgba(251, 191, 36, 0.7); }
.t-led-g { background: #34d399; box-shadow: 0 0 6px rgba(52, 211, 153, 0.7); }
.t-title {
  margin-left: 8px;
  font-family: ui-monospace, 'Cascadia Code', Consolas, 'SF Mono', monospace;
  font-size: 11px;
  letter-spacing: 1.2px;
  color: #4f6a8a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.terminal-body {
  padding: 10px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.t-line {
  margin: 0;
  font-family: ui-monospace, 'Cascadia Code', Consolas, 'SF Mono', monospace;
  font-size: 11.5px;
  line-height: 1.4;
  color: #c3d3e8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  animation: fade-up 0.5s ease both;
}
.t-line:nth-child(1) { animation-delay: 0.55s; }
.t-line:nth-child(2) { animation-delay: 0.95s; }
.t-line:nth-child(3) { animation-delay: 1.35s; }
.t-line:nth-child(4) { animation-delay: 1.75s; }
.t-line:nth-child(5) { animation-delay: 2.15s; }
.t-prompt { color: #22d3ee; margin-right: 7px; }
.t-ok .t-mark { color: #34d399; margin-right: 7px; }
.t-info .t-mark { color: #22d3ee; margin-right: 7px; }
.t-info b {
  color: #22d3ee;
  font-weight: 700;
  text-shadow: 0 0 14px rgba(34, 211, 238, 0.6);
}
.t-cursor {
  display: inline-block;
  width: 8px;
  height: 14px;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.8);
  vertical-align: -2px;
  animation: blink 1s steps(2, start) infinite;
}

/* ---------- 能力矩阵（切角模块） ---------- */
.feature-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid rgba(34, 211, 238, 0.16);
  background: rgba(34, 211, 238, 0.03);
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));
  transition: border-color 0.25s ease, background 0.25s ease;
}
.feature-item:hover {
  border-color: rgba(34, 211, 238, 0.55);
  background: rgba(34, 211, 238, 0.08);
}
.f-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  color: #22d3ee;
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(34, 211, 238, 0.08);
  clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);
}
.f-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.f-name {
  font-size: 13.5px;
  font-weight: 600;
  color: #e2e8f0;
}
.f-desc {
  font-size: 11.5px;
  color: #5d7290;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------- 底部数据栏 ---------- */
.brand-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid rgba(34, 211, 238, 0.14);
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
}
.stat-num {
  font-family: ui-monospace, 'Cascadia Code', Consolas, 'SF Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #22d3ee;
  text-shadow: 0 0 16px rgba(34, 211, 238, 0.45);
}
.stat-label {
  font-size: 11.5px;
  color: #5d7290;
  letter-spacing: 1px;
}
.stat-divider {
  width: 1px;
  height: 30px;
  background: rgba(34, 211, 238, 0.18);
}

/* ================= 右侧表单区 ================= */
.auth-panel {
  flex: 1 1 50%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  padding: 48px;
}

/* ================= 响应式 ================= */
/* 矮视口紧凑模式：保证内容完整显示不裁切 */
@media (max-height: 700px) {
  .auth-brand {
    padding: 20px 40px;
  }
  .brand-title {
    font-size: 26px;
  }
  .terminal-head {
    padding: 7px 14px;
  }
  .terminal-body {
    gap: 5px;
    padding: 8px 14px 10px;
  }
  .t-line {
    font-size: 11px;
  }
  .feature-grid {
    gap: 8px;
  }
  .feature-item {
    padding: 6px 12px;
  }
  .stat-num {
    font-size: 18px;
  }
}

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

/* 弱化动效偏好 */
@media (prefers-reduced-motion: reduce) {
  .brand-top, .brand-copy, .terminal, .feature-grid, .brand-stats, .t-line {
    animation: none;
  }
  .caret, .t-cursor, .sys-dot, .scanline, .orbit-a, .orbit-b, .bg-stars {
    animation: none;
  }
}
</style>
