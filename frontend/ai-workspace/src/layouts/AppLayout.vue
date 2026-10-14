<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppHeader />
      <div
        class="app-stage"
        :class="{ 'app-stage--flush': isFlushStage }"
      >
        <RouterView />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'

import { useAuthStore } from '@/stores/auth';
import { onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
const authStore = useAuthStore()
const route = useRoute()

// chat 等全屏页面去掉 stage 内边距，让页面内容自己控制留白
const isFlushStage = computed(() => route.meta.flush === true)

onMounted(async ()=> {
  await authStore.authCurrentUser()
})
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.app-main {
  flex: 1 1 0%;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.app-stage {
  flex: 1 1 0%;
  min-height: 0;
  overflow-y: auto;
  background: var(--aws-background);
  padding: 24px;
}
.app-stage--flush {
  padding: 0;
}
</style>
