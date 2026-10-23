<template>
  <div class="chat-page">
    <!-- 主体：顶部上下文 + 会话信息头 + 欢迎态 / 对话态，可滚动 -->
    <div
      ref="bodyRef"
      class="chat-body"
    >
      <!-- 顶部上下文插槽：知识库问答的知识库信息头卡 -->
      <slot name="header" />

      <!-- 会话信息头：本次聊天的标题与模式（知识库问答由上方头卡承载，不重复展示） -->
      <ChatHeader
        v-if="mode !== 'knowledge' && chatStore.currentSession"
        :title="chatStore.currentSession.title"
        :type="sessionType"
      />

      <!-- 欢迎态 -->
      <ChatWelcome
        v-if="!messages.length"
        :title="resolvedWelcome.title"
        :sub="resolvedWelcome.sub"
        :suggestions="suggestions"
        @select="onSuggestion"
      />

      <!-- 对话态：消息流（按 role 分发 UserMessage / AssistantMessage） -->
      <MessageList
        v-else
        :messages="messages"
        :user-initial="userInitial"
        :is-agent-mode="isAgentMode"
        :loading="loading"
        @copy="onCopy"
        @retry="onRegenerate"
      />
    </div>

    <!-- 输入栏（断网条 / 文件上传 / 胶囊输入框 / 上下行动区 slot） -->
    <ChatInputBar
      v-model:input="input"
      v-model:attachments="attachments"
      :offline="offline"
      :loading="loading"
      :placeholder="resolvedPlaceholder"
      :can-send="canSend"
      :allow-upload="mode !== 'knowledge'"
      @submit="onSend()"
      @stop="stop"
      @uploading-change="(v: boolean) => (hasUploading = v)"
    >
      <!-- 输入框上方：知识库上下文 chip 等 -->
      <template #before-input>
        <slot name="input-before" />
      </template>

      <!-- 输入框下方：选择工具（仅 Agent 模式） -->
      <template #actions>
        <div
          v-if="mode === 'agent'"
          class="input-actions-row"
        >
          <button
            type="button"
            class="ghost-btn"
            :class="{ 'ghost-active': toolPopoverOpen }"
            @click="toolPopoverOpen = !toolPopoverOpen"
          >
            <Wrench class="w-3.5 h-3.5" />
            <span>选择工具</span>
            <ChevronDown class="w-3 h-3" />
          </button>

          <!-- 工具选择下拉 -->
          <transition name="dropdown">
            <div
              v-if="toolPopoverOpen"
              class="tool-popover"
            >
              <div class="tool-popover-title">
                选择 Agent 可用工具
              </div>
              <label
                v-for="t in availableTools"
                :key="t.id"
                class="tool-option"
              >
                <input
                  v-model="selectedTools"
                  type="checkbox"
                  :value="t.id"
                >
                <component
                  :is="t.icon"
                  class="w-4 h-4"
                />
                <span class="tool-option-name">{{ t.name }}</span>
                <span class="tool-option-desc">{{ t.desc }}</span>
              </label>
            </div>
          </transition>
        </div>
      </template>
    </ChatInputBar>

    <!-- 点击外部关闭工具弹出层 -->
    <div
      v-if="toolPopoverOpen"
      class="popover-backdrop"
      @click="toolPopoverOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { Wrench, ChevronDown } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import ChatHeader from './ChatHeader.vue'
import ChatWelcome from './ChatWelcome.vue'
import MessageList from './MessageList.vue'
import ChatInputBar from './ChatInputBar.vue'
import { useChatMode, type ChatMode } from '@/composables/chat/useChatMode'
import { useChatMessages } from '@/composables/chat/useChatMessages'
import { useStreamReply } from '@/composables/chat/useStreamReply'
import type { ChatMessage, MessageAttachment, Suggestion } from './types'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'ChatWorkspace' })

const props = defineProps<{
  /** 视图模式：普通聊天 / Agent / 知识库问答 */
  mode: ChatMode
  /** 知识库 id（knowledge 模式传入，作为问答检索范围） */
  knowledgeBaseId?: number
  /** 知识库绑定的问答会话 id（knowledge 模式传入，恢复历史消息） */
  knowledgeConversationId?: number
  /** 欢迎标题覆盖（知识库模式按具体知识库名称动态展示） */
  welcomeTitle?: string
  /** 欢迎副标题覆盖 */
  welcomeSub?: string
  /** 输入框占位符覆盖 */
  placeholder?: string
}>()

/* ------------------------------------------------------------------ */
/*  状态                                                              */
/* ------------------------------------------------------------------ */
const authStore = useAuthStore()
const chatStore = useChatStore()
const userInitial = computed(() => authStore.user?.nickname?.substring(0, 1) || '我')

/**
 * 知识库问答会话 id：该模式下会话由后端在首次提问时创建，
 * 前端不预建（避免在普通会话列表里插入空会话），这里只记录后端回传的 id 供后续消息复用。
 */
const knowledgeConvId = ref<number | null>(null)

/* 模式配置（欢迎态 / 建议卡 / 占位符 / Agent 工具选择） */
const {
  isAgentMode,
  currentType,
  sessionType,
  suggestions,
  welcome,
  placeholder,
  availableTools,
  selectedTools,
  toolPopoverOpen,
} = useChatMode(props.mode)

const resolvedWelcome = computed(() => ({
  title: props.welcomeTitle ?? welcome.title,
  sub: props.welcomeSub ?? welcome.sub,
}))
const resolvedPlaceholder = computed(() => props.placeholder ?? placeholder)

/* 滚动容器 + 滚动到底部（先于 useChatMessages 定义，供其历史加载后滚动） */
const bodyRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    const el = bodyRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

/* 消息 / 输入 / 附件状态 + 历史会话加载 */
const {
  messages,
  input,
  attachments,
  hasUploading,
  historyLoading,
  uid,
  now,
  loadConversation,
} = useChatMessages(scrollToBottom)

/* 流式回复（普通 Chat / Agent / 知识库问答）+ loading / 停止 */
const { loading, stop, runReply } = useStreamReply({
  messages,
  uid,
  now,
  scrollToBottom,
  mode: props.mode,
  selectedTools,
  // 知识库问答：把检索范围带给问答接口
  knowledgeBaseId: () => props.knowledgeBaseId ?? null,
  // 知识库问答：记录后端创建的会话 id
  onKnowledgeConversation: (id) => {
    knowledgeConvId.value = id
  },
})

/** 网络状态：断网时输入栏上方显示警告条，并阻止发送新消息 */
const offline = ref(typeof navigator !== 'undefined' ? !navigator.onLine : false)
function handleOnline() {
  offline.value = false
  ElMessage.success('网络已恢复')
}
function handleOffline() {
  offline.value = true
  ElMessage.warning('网络连接已断开，请检查网络设置')
}

/** 是否可发送：无历史加载中、有内容且无上传中的附件 */
const canSend = computed(() => {
  if (historyLoading.value) return false
  if (hasUploading.value) return false
  return input.value.trim().length > 0
})

/* ------------------------------------------------------------------ */
/*  会话切换监听                                                      */
/* ------------------------------------------------------------------ */
watch(
  () => chatStore.currentId,
  (id) => {
    if (id == null) {
      messages.value = []
      attachments.value = []
      hasUploading.value = false
      input.value = ''
      return
    }
    // 新建会话：不加载历史（避免空数组覆盖 onSend 刚 push 的消息），消费掉标记
    if (chatStore.justCreated) {
      chatStore.justCreated = false
      return
    }
    // 切换到已有会话：清空当前消息并加载历史
    messages.value = []
    attachments.value = []
    hasUploading.value = false
    input.value = ''
    loadConversation(id)
  },
)

/* 知识库问答：知识库已绑定会话时恢复会话并加载历史
 * （kb 信息在 KnowledgeView 中异步加载，绑定 id 迟于挂载到达，故用 watch） */
watch(
  () => props.knowledgeConversationId,
  (id) => {
    if (props.mode !== 'knowledge' || id == null) return
    if (knowledgeConvId.value === id) return
    knowledgeConvId.value = id
    loadConversation(id)
  },
  { immediate: true },
)

/**
 * 页面挂载后：
 * 1. 如果 store 里有 pendingPrompt（从 workspace 跳转过来），消费它作为首条消息发送
 * 2. 否则如果已有 currentId（从 sidebar 直接点进会话），加载该会话的信息与历史消息
 */
onMounted(() => {
  // 全局网络状态监听：断网/恢复时更新警告条并 toast 提示
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  const pending = chatStore.pendingPrompt
  if (pending) {
    chatStore.pendingPrompt = null
    onSend(pending)
  } else if (chatStore.currentId != null) {
    loadConversation(chatStore.currentId)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})

/* ------------------------------------------------------------------ */
/*  发送消息                                                          */
/* ------------------------------------------------------------------ */
async function onSend(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return

  // 历史消息加载中：此时发送会与历史覆盖形成竞态，直接拦截
  if (historyLoading.value) {
    ElMessage.warning('正在加载会话历史，请稍候...')
    return
  }

  // 断网预检：提前拦截，不发注定失败的请求
  if (offline.value) {
    ElMessage.error('网络连接已断开，请检查网络后重试')
    return
  }

  // 有附件仍在上传中，阻止发送
  if (hasUploading.value) {
    ElMessage.warning('文件上传中，请稍候...')
    return
  }

  // 会话 id：
  // - knowledge：后端在首次提问时自动创建 knowledge 会话，前端不预建避免产生空会话
  // - chat / agent：无选中会话时用消息前 30 字符作 title 创建
  let conversationId: number | null
  if (props.mode === 'knowledge') {
    conversationId = knowledgeConvId.value
  } else {
    if (chatStore.currentId == null) {
      await chatStore.createSession(content.slice(0, 30), currentType.value)
    }
    conversationId = chatStore.currentId
    if (conversationId == null) return
  }

  // 收集已上传文件的 file_id
  const fileIds = attachments.value.flatMap((a) =>
    (a.status === 'done' && a.file_id ? [a.file_id] : []),
  )

  // 用户消息（含附件预览）
  const userAttachments: MessageAttachment[] = attachments.value
    .filter((a) => a.status === 'done')
    .map((a) => ({ id: a.uid, name: a.name, size: a.size }))

  messages.value.push({
    id: uid(),
    role: 'user',
    content,
    time: now(),
    attachments: userAttachments.length ? userAttachments : undefined,
  })
  input.value = ''
  attachments.value = []
  hasUploading.value = false
  scrollToBottom()

  await runReply(conversationId, content, fileIds)
}

function onSuggestion(item: Suggestion) {
  if (loading.value) return
  onSend(item.title)
}

/* ------------------------------------------------------------------ */
/*  重新生成 / 复制                                                   */
/* ------------------------------------------------------------------ */
async function onRegenerate(m: ChatMessage) {
  if (loading.value) return
  const idx = messages.value.findIndex((x) => x.id === m.id)
  let userText = ''
  const fileIds: number[] = []
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      userText = messages.value[i].content
      break
    }
  }
  if (!userText) return
  const conversationId = props.mode === 'knowledge' ? knowledgeConvId.value : chatStore.currentId
  // 知识库问答首次提问尚未拿到会话 id 时允许重发（后端会创建会话）
  if (conversationId == null && props.mode !== 'knowledge') return

  messages.value.splice(idx)
  await runReply(conversationId, userText, fileIds)
}

async function onCopy(m: ChatMessage) {
  if (!m.content) return
  try {
    await navigator.clipboard.writeText(m.content)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
/* 整体容器：chat 路由下 .app-stage 无 padding（router meta.flush），height:100% 正好填满视口 */
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
  background: var(--aws-background);
}

/* 主体滚动区 */
.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

/* 输入框下方幽灵文字按钮行 */
.input-actions-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding-left: 8px;
  position: relative;
}
.ghost-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: var(--aws-radius-md);
  color: var(--aws-muted);
  background: transparent;
  border: none;
  font-size: var(--aws-text-xs);
  transition: color 0.15s, background-color 0.15s;
}
.ghost-btn:hover:not(:disabled) {
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 6%, transparent);
}
.ghost-btn.ghost-active {
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 8%, transparent);
}
.ghost-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 工具弹出层 */
.tool-popover {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 0;
  width: 280px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
  z-index: 50;
  overflow: hidden;
  padding: 8px;
}
.tool-popover-title {
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-muted);
  padding: 4px 8px 8px;
}
.tool-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: var(--aws-radius-sm);
  cursor: pointer;
  transition: background-color 0.15s;
  font-size: var(--aws-text-sm);
}
.tool-option:hover {
  background: var(--aws-sidebar-active);
}
.tool-option input[type="checkbox"] {
  accent-color: var(--aws-primary);
}
.tool-option-name {
  font-weight: var(--aws-weight-medium);
  color: var(--aws-foreground);
}
.tool-option-desc {
  color: var(--aws-muted);
  font-size: var(--aws-text-xs);
  margin-left: auto;
}

/* 弹出层 backdrop */
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
