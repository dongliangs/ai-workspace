<template>
  <div
    v-if="steps.length"
    class="agent-steps"
  >
    <div
      v-for="step in steps"
      :key="step.id"
      class="step-item"
    >
      <!-- 状态图标 -->
      <span class="step-icon">
        <Check
          v-if="step.status === 'done'"
          class="w-3.5 h-3.5"
        />
        <Loader2
          v-else-if="step.status === 'running'"
          class="w-3.5 h-3.5 spin"
        />
        <span
          v-else
          class="step-dot"
        />
      </span>
      <span class="step-label">{{ step.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Check, Loader2 } from 'lucide-vue-next'

/** Agent 执行步骤 */
interface AgentStep {
  id: number
  label: string
  status: 'pending' | 'running' | 'done'
}

defineProps<{
  steps: AgentStep[]
}>()
</script>

<style scoped>
.agent-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--aws-primary) 4%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-primary) 12%, var(--aws-border));
  border-radius: var(--aws-radius-md);
  margin-bottom: 8px;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
}
.step-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.step-icon:has(.check),
.step-item:has(.check) .step-icon {
  color: var(--aws-success);
}
.step-item:has(.spin) .step-icon {
  color: var(--aws-primary);
}
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--aws-border-strong);
  background: transparent;
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
/* lucide Check 颜色 */
.step-icon :deep(svg) {
  color: var(--aws-success);
}
.step-item:has(.spin) .step-icon :deep(svg) {
  color: var(--aws-primary);
}
</style>
