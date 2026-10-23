<template>
  <ChatWorkspace
    :key="kbId ?? 'none'"
    mode="knowledge"
    :knowledge-base-id="kbId ?? undefined"
    :knowledge-conversation-id="kb?.conversation_id ?? undefined"
    :welcome-title="welcomeTitle"
    :welcome-sub="welcomeSub"
    :placeholder="placeholder"
  >
    <!-- 顶部：知识库上下文头卡（问答范围 + 统计 + 返回详情） -->
    <template #header>
      <div class="kb-bar">
        <div class="kb-bar-icon">
          <BookOpen class="w-5 h-5" />
        </div>
        <div class="kb-bar-info">
          <div class="kb-bar-crumb">
            知识库 <ChevronRight class="w-3 h-3" /> 问答
          </div>
          <div class="kb-bar-title">
            {{ kb?.name ?? '未选择知识库' }}
          </div>
          <div class="kb-bar-stats">
            <span><b>{{ kb?.doc_count ?? 0 }}</b> 份文档</span>
            <span class="sep" />
            <span><b>{{ kb?.chunk_count ?? 0 }}</b> 个可检索片段</span>
            <span class="sep" />
            <span>仅检索"已完成"索引的文档</span>
          </div>
        </div>
        <div class="kb-bar-ops">
          <button
            v-if="kbId != null"
            type="button"
            class="link-btn"
            @click="backToDetail"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            返回详情
          </button>
          <button
            v-else
            type="button"
            class="link-btn"
            @click="router.push('/knowledge')"
          >
            <BookOpen class="w-3.5 h-3.5" />
            选择知识库
          </button>
        </div>
      </div>
    </template>

    <!-- 输入框上方：当前知识库 chip -->
    <template #input-before>
      <div class="kb-chip-row">
        <button
          type="button"
          class="kb-chip"
          :disabled="kbId == null"
          title="返回知识库详情更换知识库"
          @click="backToDetail"
        >
          <BookOpen class="w-3.5 h-3.5" />
          {{ kb?.name ?? '未选择知识库' }}
          <span class="switch">· 更换</span>
        </button>
        <span class="kb-chip-note">回答基于该知识库检索生成，并标注来源出处</span>
      </div>
    </template>
  </ChatWorkspace>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, ChevronRight, ArrowLeft } from 'lucide-vue-next'
import ChatWorkspace from '@/components/chat/ChatWorkspace.vue'
import { getKnowledgeBase, type KnowledgeBase } from '@/api/knowledgeBase'
import { useChatStore } from '@/stores/chat'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'KnowledgeView' })

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

// 进入知识库问答时清空当前选中的普通会话，避免加载到无关的聊天历史
chatStore.selectSession(null)

/** 当前知识库 id（由知识库详情页进入时通过 ?kb= 传入） */
const kbId = computed(() => {
  const id = Number(route.query.kb)
  return Number.isInteger(id) && id > 0 ? id : null
})

/** 当前知识库信息（问答检索范围与头卡统计） */
const kb = ref<KnowledgeBase | null>(null)

const welcomeTitle = computed(() =>
  (kb.value ? `基于「${kb.value.name}」提问` : '知识库问答'),
)
const welcomeSub = computed(() =>
  (kb.value
    ? `AI 将在 ${kb.value.doc_count} 份已索引文档中检索相关片段后作答，回答会标注来源文档与片段位置`
    : '从知识库详情页进入，即可基于该知识库检索问答'),
)
const placeholder = computed(() =>
  (kb.value
    ? `基于「${kb.value.name}」提问，例如：分块策略是什么？`
    : '基于知识库提问...'),
)

/** 加载当前知识库信息（?kb= 变化时重新加载，如从 Chat 选库跳转切换） */
async function loadKnowledgeBase() {
  if (kbId.value == null) {
    kb.value = null
    return
  }
  try {
    kb.value = await getKnowledgeBase(kbId.value)
  } catch {
    // 失败由拦截器统一提示，页面保持"未选择知识库"态
    kb.value = null
  }
}

// immediate 覆盖首次进入；watch 覆盖同路由更换 kb（组件被复用）的场景
watch(kbId, loadKnowledgeBase, { immediate: true })

/** 返回知识库详情（更换知识库也从这里进入） */
function backToDetail() {
  if (kbId.value == null) return
  router.push(`/knowledge/${kbId.value}`)
}
</script>

<style scoped>
/* 知识库上下文头卡：吸顶，与消息流保持同一内容宽度 */
.kb-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--aws-background) 88%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--aws-border);
}
.kb-bar-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  background: color-mix(in srgb, var(--aws-primary) 10%, var(--aws-card));
  color: var(--aws-primary);
}
.kb-bar-info {
  flex: 1;
  min-width: 0;
}
.kb-bar-crumb {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}
.kb-bar-title {
  margin-top: 2px;
  font-size: var(--aws-text-lg);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-bar-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.kb-bar-stats b {
  color: var(--aws-foreground);
  font-weight: var(--aws-weight-semibold);
}
.kb-bar-stats .sep {
  width: 1px;
  height: 10px;
  background: var(--aws-border);
}
.kb-bar-ops {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 12px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border);
  background: var(--aws-card);
  color: var(--aws-muted);
  font-size: var(--aws-text-xs);
  transition: border-color 0.15s, color 0.15s;
}
.link-btn:hover {
  border-color: var(--aws-primary);
  color: var(--aws-primary);
}

/* 输入框上方知识库 chip */
.kb-chip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.kb-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--aws-primary) 8%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-primary) 28%, var(--aws-border));
  color: var(--aws-primary);
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
  transition: background-color 0.15s;
}
.kb-chip:hover:not(:disabled) {
  background: color-mix(in srgb, var(--aws-primary) 14%, var(--aws-card));
}
.kb-chip:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.kb-chip .switch {
  color: var(--aws-muted);
  font-weight: var(--aws-weight-normal);
}
.kb-chip-note {
  font-size: 11px;
  color: var(--aws-placeholder);
}
</style>
