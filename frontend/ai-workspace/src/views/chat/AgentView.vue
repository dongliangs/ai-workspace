<template>
  <ChatWorkspace mode="agent" />
</template>

<script setup lang="ts">
import ChatWorkspace from '@/components/chat/ChatWorkspace.vue'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'AgentView' })
</script>
