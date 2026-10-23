<template>
  <div class="conv-header">
    <component
      :is="icon"
      class="conv-header-icon"
    />
    <span class="conv-header-title">{{ title }}</span>
    <span
      class="conv-header-badge"
      :class="`badge-${type}`"
    >{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { MessageSquare, Bot, BookOpen } from 'lucide-vue-next'
import type { ConversationType } from '@/api/conversation'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'ChatHeader' })

const props = defineProps<{
  /** 会话标题 */
  title: string
  /** 会话类型（chat / agent / knowledge），决定图标与模式徽标 */
  type: ConversationType
}>()

/** 会话类型 → 信息头图标（与侧边栏对话记录一致） */
const icon = computed<Component>(() => {
  if (props.type === 'agent') return Bot
  if (props.type === 'knowledge') return BookOpen
  return MessageSquare
})

/** 会话类型 → 模式文案 */
const label = computed(() => {
  if (props.type === 'agent') return 'Agent 模式'
  if (props.type === 'knowledge') return '知识库对话'
  return '普通对话'
})
</script>

<style scoped>
.conv-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  padding: 12px 16px 10px;
  background: color-mix(in srgb, var(--aws-background) 88%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--aws-border);
}
.conv-header-icon {
  width: 16px;
  height: 16px;
  flex: none;
  color: var(--aws-primary);
}
.conv-header-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
}
.conv-header-badge {
  flex: none;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--aws-text-xs);
  white-space: nowrap;
}
.conv-header-badge.badge-chat {
  color: var(--aws-muted);
  background: color-mix(in srgb, var(--aws-foreground) 6%, var(--aws-card));
  border: 1px solid var(--aws-border);
}
.conv-header-badge.badge-agent {
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 10%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-primary) 25%, var(--aws-border));
}
.conv-header-badge.badge-knowledge {
  color: var(--aws-success);
  background: color-mix(in srgb, var(--aws-success) 10%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-success) 25%, var(--aws-border));
}
</style>