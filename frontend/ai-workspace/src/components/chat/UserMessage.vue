<template>
  <div class="msg-row user">
    <div class="avatar avatar-user">
      {{ userInitial }}
    </div>
    <div class="msg-main">
      <div class="user-bubble-wrap">
        <!-- 附件预览 -->
        <div
          v-if="message.attachments?.length"
          class="msg-attachments"
        >
          <span
            v-for="a in message.attachments"
            :key="a.id"
            class="msg-attach-chip"
          >
            <FileSpreadsheet class="w-3.5 h-3.5 shrink-0" />
            <span class="truncate">{{ a.name }}</span>
            <span class="msg-attach-size">{{ a.size }}</span>
          </span>
        </div>
        <div class="bubble user">
          <span class="bubble-text">{{ message.content }}</span>
        </div>
      </div>

      <div class="msg-meta">
        <span class="msg-time">{{ message.time }}</span>
        <div
          v-if="!message.pending"
          class="msg-actions"
        >
          <button
            type="button"
            class="action-btn"
            title="复制"
            @click="$emit('copy')"
          >
            <Copy class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileSpreadsheet, Copy } from 'lucide-vue-next'
import type { ChatMessage } from './types'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'UserMessage' })

defineProps<{
  /** 用户消息实体 */
  message: ChatMessage
  /** 用户头像首字 */
  userInitial: string
}>()

defineEmits<{
  copy: []
}>()
</script>

<style scoped>
.msg-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.avatar-user {
  border-radius: 50%;
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
}
.msg-main {
  min-width: 0;
  max-width: calc(100% - 44px);
  display: flex;
  flex-direction: column;
}
.msg-row.user .msg-main {
  align-items: flex-end;
}
.user-bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
.msg-attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  padding: 4px 8px;
  border-radius: var(--aws-radius-md);
  background: color-mix(in srgb, var(--aws-primary) 10%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-primary) 20%, var(--aws-border));
  font-size: var(--aws-text-xs);
  color: var(--aws-foreground);
}
.msg-attach-size {
  color: var(--aws-muted);
}
.bubble {
  padding: 10px 14px;
  border-radius: var(--aws-radius-lg);
  font-size: var(--aws-text-base);
  line-height: var(--aws-leading-relaxed);
  word-break: break-word;
}
.bubble.user {
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  border-top-right-radius: 4px;
}
.bubble-text {
  white-space: pre-wrap;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  min-height: 18px;
}
.msg-row.user .msg-meta {
  flex-direction: row-reverse;
}
.msg-time {
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}
.msg-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.msg-row:hover .msg-actions {
  opacity: 1;
}
.action-btn {
  width: 22px;
  height: 22px;
  border-radius: var(--aws-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: background-color 0.15s, color 0.15s;
}
.action-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}
</style>