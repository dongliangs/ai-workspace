<template>
  <div class="agent-bubble">
    <!-- 执行步骤列表 -->
    <AgentSteps :steps="steps" />

    <!-- 工具调用卡片 -->
    <ToolCard
      v-for="t in tools"
      :key="t.id"
      :tool="t"
    />

    <!-- 打字机思考态（无内容且 pending） -->
    <span
      v-if="pending && !content"
      class="typing-dots"
    >
      <i /><i /><i />
    </span>

    <!-- 文本内容（Markdown 渲染） -->
    <MarkdownContent
      v-else-if="content"
      :content="content"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownContent from './MarkdownContent.vue'
import AgentSteps from './AgentSteps.vue'
import ToolCard from './ToolCard.vue'

/** Agent 执行步骤 */
export interface AgentStep {
  id: number
  label: string
  status: 'pending' | 'running' | 'done'
}

/** 工具调用 */
export interface ToolInvocation {
  id: number
  tool: string
  status: 'running' | 'success' | 'error' | 'stopped'
  arguments?: Record<string, unknown>
  result?: unknown
}

defineProps<{
  content: string
  steps: AgentStep[]
  tools: ToolInvocation[]
  pending?: boolean
}>()
</script>

<style scoped>
.agent-bubble {
  border-radius: var(--aws-radius-lg);
  border-top-left-radius: 4px;
  color: var(--aws-foreground);
}

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
</style>
