<template>
  <div class="conversation">
    <template
      v-for="m in messages"
      :key="m.id"
    >
      <UserMessage
        v-if="m.role === 'user'"
        :message="m"
        :user-initial="userInitial"
        @copy="$emit('copy', m)"
      />
      <AssistantMessage
        v-else
        :message="m"
        :is-agent-mode="isAgentMode"
        :loading="loading"
        @copy="$emit('copy', m)"
        @retry="$emit('retry', m)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import UserMessage from './UserMessage.vue'
import AssistantMessage from './AssistantMessage.vue'
import type { ChatMessage } from './types'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'MessageList' })

defineProps<{
  /** 消息列表 */
  messages: ChatMessage[]
  /** 用户头像首字 */
  userInitial: string
  /** 是否 Agent 模式（决定普通答复是否走 Agent 气泡渲染） */
  isAgentMode: boolean
  /** 是否有流式请求正在生成中（重试按钮禁用用） */
  loading: boolean
}>()

defineEmits<{
  copy: [message: ChatMessage]
  retry: [message: ChatMessage]
}>()
</script>

<style scoped>
.conversation {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px 16px 24px;
  max-width: 820px;
  margin: 0 auto;
  width: 100%;
}
</style>