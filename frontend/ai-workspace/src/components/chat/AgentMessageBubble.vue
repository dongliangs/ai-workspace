<template>
  <div class="agent-bubble">
    <!-- 执行过程区：步骤 + 工具调用卡片（位于正文上方） -->
    <AgentSteps :steps="steps" />
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

    <!-- 图表输出：generate_chart 成功后渲染在正文下方 -->
    <ChartRenderer
      v-for="c in charts"
      :key="c.id"
      :option="c.option"
      :title="c.title"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownContent from './MarkdownContent.vue'
import AgentSteps from './AgentSteps.vue'
import ToolCard from './ToolCard.vue'
import ChartRenderer from './ChartRenderer.vue'

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

const props = defineProps<{
  content: string
  steps: AgentStep[]
  tools: ToolInvocation[]
  pending?: boolean
}>()

/** generate_chart 成功的图表输出（从工具结果提取，渲染在正文下方） */
const charts = computed(() => {
  const list: Array<{ id: number; option: Record<string, any>; title: string }> = []
  for (const t of props.tools) {
    if (t.tool !== 'generate_chart' || t.status !== 'success') continue
    const result = t.result as Record<string, any> | undefined
    const option = result?.echarts_option
    if (option) {
      list.push({ id: t.id, option, title: (result?.title as string) ?? '' })
    }
  }
  return list
})
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
