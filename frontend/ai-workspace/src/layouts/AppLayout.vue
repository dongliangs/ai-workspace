<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppHeader />
      <div class="app-stage">
        <RouterView />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'

import { useAuthStore } from '@/stores/auth';
import { onMounted } from 'vue';
const authStore = useAuthStore()

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
</style>
