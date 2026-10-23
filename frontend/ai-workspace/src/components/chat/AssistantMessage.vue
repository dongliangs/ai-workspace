<template>
  <div class="msg-row assistant">
    <div class="avatar avatar-ai">
      <RobotMark :size="18" />
    </div>
    <div class="msg-main">
      <!-- 知识库问答：检索阶段状态（retrieval_start 后、检索结果/首个文本前） -->
      <div
        v-if="message.retrieving"
        class="retrieving-bar"
      >
        <Loader2 class="w-3.5 h-3.5 retrieving-spin" />
        <span>正在检索知识库...</span>
      </div>

      <!-- Agent 答复（含工具/步骤） -->
      <AgentMessageBubble
        v-if="!message.retrieving && (isAgentMode || message.steps || message.tools)"
        :content="message.content"
        :steps="message.steps ?? []"
        :tools="message.tools ?? []"
        :pending="message.pending"
      />

      <!-- 普通 Chat 答复（Markdown / 打字机） -->
      <div
        v-else-if="!message.retrieving"
        class="bubble assistant"
      >
        <span
          v-if="message.pending && !message.content"
          class="typing-dots"
        ><i /><i /><i /></span>
        <MarkdownContent
          v-else-if="message.content"
          :content="message.content"
        />
      </div>

      <!-- 知识库问答：参考来源列表（回答正文 [1][2] 角标对应 index） -->
      <SourceReferenceList
        v-if="message.sources?.length"
        :sources="message.sources ?? []"
      />

      <!-- 流式异常提示条（断网/超时/HTTP错误） -->
      <div
        v-if="message.error"
        class="stream-error-bar"
      >
        <AlertCircle class="w-4 h-4 shrink-0" />
        <span class="stream-error-text">{{ message.error }}</span>
        <button
          type="button"
          class="stream-retry-btn"
          :disabled="loading"
          @click="$emit('retry')"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          <span>重试</span>
        </button>
      </div>
      <!-- 用户停止生成且无内容时的兜底提示 -->
      <span
        v-else-if="!message.pending && !message.content"
        class="stopped-hint"
      >已停止生成</span>

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
          <button
            type="button"
            class="action-btn"
            title="重新生成"
            @click="$emit('retry')"
          >
            <RefreshCw class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertCircle, RefreshCw, Copy, Loader2 } from 'lucide-vue-next'
import MarkdownContent from './MarkdownContent.vue'
import AgentMessageBubble from './AgentMessageBubble.vue'
import SourceReferenceList from './SourceReferenceList.vue'
import RobotMark from './RobotMark.vue'
import type { ChatMessage } from './types'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'AssistantMessage' })

defineProps<{
  /** AI 消息实体 */
  message: ChatMessage
  /** 是否 Agent 模式（决定普通答复是否走 Agent 气泡渲染） */
  isAgentMode: boolean
  /** 是否有流式请求正在生成中（重试按钮禁用用） */
  loading: boolean
}>()

defineEmits<{
  copy: []
  retry: []
}>()
</script>

<style scoped>
.msg-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
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
.avatar-ai {
  background: linear-gradient(135deg, var(--aws-primary), var(--aws-primary-hover));
}
.msg-main {
  min-width: 0;
  max-width: calc(100% - 44px);
  display: flex;
  flex-direction: column;
}
.bubble {
  padding: 10px 14px;
  border-radius: var(--aws-radius-lg);
  font-size: var(--aws-text-base);
  line-height: var(--aws-leading-relaxed);
  word-break: break-word;
}
.bubble.assistant {
  background: transparent;
  border: none;
  color: var(--aws-foreground);
  border-top-left-radius: 4px;
  padding: 0;
}

/* 打字机思考态 */
.typing-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 16px;
}
.typing-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--aws-muted);
  display: inline-block;
  animation: typing-bounce 1.2s infinite ease-in-out;
}
.typing-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing-dots i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* 知识库问答：检索阶段状态条 */
.retrieving-bar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.retrieving-spin {
  animation: retrieving-spin 0.9s linear infinite;
}
@keyframes retrieving-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 流式异常提示条：浅红底 + 错误图标 + 文案 + 重试按钮 */
.stream-error-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: var(--aws-radius-md);
  background: color-mix(in srgb, #ef4444 8%, var(--aws-card));
  border: 1px solid color-mix(in srgb, #ef4444 25%, var(--aws-border));
  color: #ef4444;
  font-size: var(--aws-text-xs);
}
.stream-error-text {
  min-width: 0;
  flex: 1;
}
.stream-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: var(--aws-radius-sm);
  border: 1px solid color-mix(in srgb, #ef4444 35%, var(--aws-border));
  background: var(--aws-card);
  color: #ef4444;
  font-size: var(--aws-text-xs);
  transition: background-color 0.15s;
}
.stream-retry-btn:hover:not(:disabled) {
  background: color-mix(in srgb, #ef4444 10%, var(--aws-card));
}
.stream-retry-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* 用户停止生成且无内容时的兜底提示 */
.stopped-hint {
  display: inline-block;
  margin-top: 4px;
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
  font-style: italic;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  min-height: 18px;
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