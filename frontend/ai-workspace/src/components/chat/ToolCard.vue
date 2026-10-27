<template>
  <div class="tool-card">
    <div class="tool-header">
      <span class="tool-icon-box">
        <component
          :is="toolIcon"
          class="w-4 h-4"
        />
      </span>
      <span class="tool-name">{{ toolLabel }}</span>
      <span
        class="tool-status"
        :class="tool.status"
      >
        <Loader2
          v-if="tool.status === 'running'"
          class="w-3 h-3 spin"
        />
        <Check
          v-else-if="tool.status === 'success'"
          class="w-3 h-3"
        />
        <XCircle
          v-else
          class="w-3 h-3"
        />
        {{ statusText }}
      </span>
    </div>
    <!-- 参数预览（key-value，非裸 JSON） -->
    <div
      v-if="argEntries.length"
      class="tool-args"
    >
      <div
        v-for="[k, v] in argEntries"
        :key="k"
        class="arg-row"
      >
        <span class="arg-key">{{ k }}</span>
        <span class="arg-val">{{ formatVal(v) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import {
  Check,
  XCircle,
  Loader2,
  Calculator,
  FileSpreadsheet,
  BarChart3,
  Wrench,
} from 'lucide-vue-next'

/** 工具调用卡片数据 */
interface ToolInvocation {
  id: number
  tool: string
  status: 'running' | 'success' | 'error' | 'stopped'
  arguments?: Record<string, unknown>
  result?: unknown
}

const props = defineProps<{
  tool: ToolInvocation
}>()

/** 工具名 → 图标 + 中文标签映射 */
const TOOL_META: Record<string, { icon: Component; label: string }> = {
  calculator: { icon: Calculator, label: '计算器' },
  analyze_excel: { icon: FileSpreadsheet, label: 'Excel 分析' },
  generate_chart: { icon: BarChart3, label: '图表生成' },
}

const toolIcon = computed<Component>(
  () => TOOL_META[props.tool.tool]?.icon ?? Wrench,
)
const toolLabel = computed(
  () => TOOL_META[props.tool.tool]?.label ?? props.tool.tool,
)

const statusText = computed(() => {
  switch (props.tool.status) {
    case 'running':
      return '执行中'
    case 'success':
      return '完成'
    case 'error':
      return '失败'
    case 'stopped':
      return '已停止'
    default:
      return ''
  }
})

const argEntries = computed(() =>
  Object.entries(props.tool.arguments ?? {}),
)

function formatVal(v: unknown): string {
  if (v == null) return '-'
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}
</script>

<style scoped>
.tool-card {
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-md);
  background: var(--aws-card);
  overflow: hidden;
  margin-bottom: 8px;
}
.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--aws-sidebar);
}
.tool-icon-box {
  width: 28px;
  height: 28px;
  border-radius: var(--aws-radius-sm);
  background: color-mix(in srgb, var(--aws-primary) 10%, transparent);
  color: var(--aws-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.tool-name {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-foreground);
  flex: 1;
}
.tool-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.tool-status.success {
  color: var(--aws-success);
}
.tool-status.error {
  color: #ef4444;
}
.tool-status.running {
  color: var(--aws-primary);
}
.tool-status.stopped {
  color: var(--aws-muted);
}
.tool-args {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.arg-row {
  display: flex;
  gap: 8px;
  font-size: var(--aws-text-xs);
}
.arg-key {
  color: var(--aws-muted);
  min-width: 60px;
}
.arg-val {
  color: var(--aws-foreground);
  word-break: break-all;
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
