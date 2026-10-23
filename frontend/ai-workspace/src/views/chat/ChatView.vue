<template>
  <ChatWorkspace mode="chat">
    <!-- 输入框上方：知识库问答入口（§4.2 第二入口：Chat 内选库） -->
    <template #input-before>
      <div class="kb-entry">
        <div class="kb-entry-row">
          <button
            type="button"
            class="kb-entry-chip"
            :class="{ active: pickerOpen }"
            @click="togglePicker"
          >
            <BookOpen class="w-3.5 h-3.5" />
            <span>知识库问答</span>
            <ChevronDown
              class="w-3 h-3 kb-entry-arrow"
              :class="{ open: pickerOpen }"
            />
          </button>
          <span class="kb-entry-note">选择知识库后，回答将基于库内文档检索生成并标注来源</span>
        </div>

        <!-- 知识库选择下拉 -->
        <transition name="dropdown">
          <div
            v-if="pickerOpen"
            class="kb-picker"
          >
            <div class="kb-picker-head">
              <span>选择知识库</span>
              <span class="kb-picker-count">{{ kbs.length }} 个可用</span>
            </div>

            <div
              v-if="kbStore.loading"
              class="kb-picker-tip"
            >
              加载中...
            </div>
            <div
              v-else-if="!kbs.length"
              class="kb-picker-tip"
            >
              暂无知识库，请先到知识库页创建
            </div>
            <button
              v-for="kb in kbs"
              :key="kb.id"
              type="button"
              class="kb-picker-item"
              @click="enterKb(kb.id)"
            >
              <BookOpen class="w-4 h-4 shrink-0" />
              <span class="kb-picker-name">{{ kb.name }}</span>
              <span class="kb-picker-meta">{{ kb.doc_count }} 份文档</span>
            </button>
          </div>
        </transition>
      </div>
    </template>
  </ChatWorkspace>

  <!-- 点击外部关闭知识库下拉 -->
  <div
    v-if="pickerOpen"
    class="popover-backdrop"
    @click="pickerOpen = false"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen, ChevronDown } from 'lucide-vue-next'
import ChatWorkspace from '@/components/chat/ChatWorkspace.vue'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'ChatView' })

const router = useRouter()
const kbStore = useKnowledgeBaseStore()

const pickerOpen = ref(false)
const kbs = computed(() => kbStore.bases?.items ?? [])

/** 打开下拉时按需加载知识库列表（已有数据不重复请求） */
async function togglePicker() {
  pickerOpen.value = !pickerOpen.value
  if (pickerOpen.value && !kbs.value.length) {
    await kbStore.fetchAll()
  }
}

/** 选定知识库：进入该知识库的问答页（检索范围通过 ?kb= 传递） */
function enterKb(id: number) {
  pickerOpen.value = false
  router.push({ path: '/knowledge/chat', query: { kb: String(id) } })
}
</script>

<style scoped>
/* 入口容器：为下拉提供定位基准 */
.kb-entry {
  position: relative;
}
.kb-entry-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.kb-entry-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px dashed var(--aws-border-strong, var(--aws-border));
  background: var(--aws-card);
  color: var(--aws-muted);
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
  transition: color 0.15s, border-color 0.15s, background-color 0.15s;
}
.kb-entry-chip:hover,
.kb-entry-chip.active {
  color: var(--aws-primary);
  border-color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 6%, var(--aws-card));
}
.kb-entry-arrow {
  transition: transform 0.15s;
}
.kb-entry-arrow.open {
  transform: rotate(180deg);
}
.kb-entry-note {
  font-size: 11px;
  color: var(--aws-placeholder);
}

/* 知识库选择下拉：向上展开 */
.kb-picker {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 320px;
  z-index: 50;
  padding: 8px;
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  background: var(--aws-card);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
}
.kb-picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px 8px;
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-muted);
}
.kb-picker-count {
  font-weight: 400;
  color: var(--aws-placeholder);
}
.kb-picker-tip {
  padding: 10px 8px;
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}
.kb-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px;
  border-radius: var(--aws-radius-sm);
  color: var(--aws-foreground);
  font-size: var(--aws-text-sm);
  text-align: left;
  transition: background-color 0.15s;
}
.kb-picker-item:hover {
  background: var(--aws-sidebar-active);
}
.kb-picker-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-picker-meta {
  flex: none;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}

/* 下拉背景遮罩（点击关闭） */
.popover-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}

/* 下拉动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
