<template>
  <div class="welcome-wrap">
    <div class="welcome-logo">
      <RobotMark :size="32" />
    </div>
    <h2 class="welcome-title">
      {{ title }}
    </h2>
    <p class="welcome-sub">
      {{ sub }}
    </p>

    <div class="suggestion-grid">
      <button
        v-for="item in suggestions"
        :key="item.title"
        type="button"
        class="suggestion-card"
        @click="$emit('select', item)"
      >
        <div
          class="suggestion-icon"
          :style="tintStyle(item.tint)"
        >
          <component
            :is="item.icon"
            class="w-4 h-4"
          />
        </div>
        <div class="min-w-0 text-left">
          <div class="suggestion-title truncate">
            {{ item.title }}
          </div>
          <div class="suggestion-desc line-clamp-2">
            {{ item.desc }}
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CSSProperties } from 'vue'
import RobotMark from './RobotMark.vue'
import type { Suggestion } from './types'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'ChatWelcome' })

defineProps<{
  /** 欢迎标题（按模式传入，如「你好！我是你的 AI 助手」） */
  title: string
  /** 欢迎副标题 / 能力说明 */
  sub: string
  /** 建议卡列表 */
  suggestions: Suggestion[]
}>()

defineEmits<{
  select: [suggestion: Suggestion]
}>()

/** 建议卡图标底色（按 tint 着色） */
function tintStyle(tint: 'primary' | 'success'): CSSProperties {
  const c = tint === 'primary' ? 'var(--aws-primary)' : 'var(--aws-success)'
  return {
    backgroundColor: `color-mix(in srgb, ${c} 12%, var(--aws-card))`,
    color: c,
  }
}
</script>

<style scoped>
.welcome-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px 8px;
}
.welcome-logo {
  width: 64px;
  height: 64px;
  border-radius: var(--aws-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  background: linear-gradient(135deg, var(--aws-primary), var(--aws-primary-hover));
}
.welcome-title {
  font-size: var(--aws-text-xl);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
  margin-bottom: 8px;
}
.welcome-sub {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  margin-bottom: 32px;
  max-width: 480px;
  text-align: center;
}
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
  max-width: 768px;
}
.suggestion-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: var(--aws-radius-lg);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  text-align: left;
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.15s;
}
.suggestion-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  border-color: var(--aws-border-strong);
  transform: translateY(-1px);
}
.suggestion-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.suggestion-title {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-foreground);
}
.suggestion-desc {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 4px;
}
</style>