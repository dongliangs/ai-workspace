<template>
  <div class="chat-page">
    <!-- 主体：欢迎态 / 对话态，可滚动 -->
    <div
      ref="bodyRef"
      class="chat-body"
    >
      <!-- 欢迎态 -->
      <div
        v-if="!messages.length"
        class="welcome-wrap"
      >
        <div class="welcome-logo">
          <RobotMark :size="32" />
        </div>
        <h2 class="welcome-title">
          你好！我是你的 AI 助手
        </h2>
        <p class="welcome-sub">
          你可以向我提问，或让我帮你完成各类任务
        </p>

        <div class="suggestion-grid">
          <button
            v-for="item in suggestions"
            :key="item.title"
            type="button"
            class="suggestion-card"
            @click="onSuggestion(item)"
          >
            <div
              class="suggestion-icon"
              :style="tintStyle(item.tint)"
            >
              <component
                :is="item.icon"
                class="w-4 h-4"
              />
            </div>
            <div class="min-w-0 text-left">
              <div class="suggestion-title truncate">
                {{ item.title }}
              </div>
              <div class="suggestion-desc line-clamp-2">
                {{ item.desc }}
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- 对话态 -->
      <div
        v-else
        class="conversation"
      >
        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-row"
          :class="m.role"
        >
          <!-- 头像 -->
          <div
            v-if="m.role === 'assistant'"
            class="avatar avatar-ai"
          >
            <RobotMark :size="18" />
          </div>
          <div
            v-else
            class="avatar avatar-user"
          >
            {{ userInitial }}
          </div>

          <!-- 气泡 + 时间 + 操作 -->
          <div class="msg-main">
            <div
              class="bubble"
              :class="m.role"
            >
              <!-- 思考中：内容为空且 pending -->
              <span
                v-if="m.pending && !m.content"
                class="typing-dots"
              >
                <i /><i /><i />
              </span>
              <span
                v-else
                class="bubble-text"
              >{{ m.content }}</span>
            </div>
            <div class="msg-meta">
              <span class="msg-time">{{ m.time }}</span>
              <div
                v-if="!m.pending"
                class="msg-actions"
              >
                <button
                  type="button"
                  class="action-btn"
                  title="复制"
                  @click="onCopy(m)"
                >
                  <Copy class="w-3.5 h-3.5" />
                </button>
                <button
                  v-if="m.role === 'assistant'"
                  type="button"
                  class="action-btn"
                  title="重新生成"
                  @click="onRegenerate(m)"
                >
                  <RefreshCw class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入栏 -->
    <div class="chat-input-bar">
      <!-- 附件 chip -->
      <div
        v-if="attachments.length"
        class="attach-chips"
      >
        <span
          v-for="a in attachments"
          :key="a.id"
          class="attach-chip"
        >
          <Paperclip class="w-3 h-3 shrink-0" />
          <span class="attach-name truncate">{{ a.name }}</span>
          <span class="attach-size">{{ a.size }}</span>
          <button
            type="button"
            class="attach-remove"
            @click="removeAttachment(a.id)"
          >
            <X class="w-3 h-3" />
          </button>
        </span>
      </div>

      <div class="input-wrap">
        <input
          v-model="input"
          type="text"
          class="chat-input"
          placeholder="输入你的问题，或上传文件..."
          :disabled="loading"
          @keyup.enter="onEnter"
        >
        <div class="input-actions">
          <button
            type="button"
            class="icon-btn"
            title="上传文件"
            @click="triggerFile"
          >
            <Paperclip class="w-4 h-4" />
          </button>
          <button
            type="button"
            class="send-btn"
            :class="{ 'is-stop': loading }"
            :disabled="!loading && !input.trim()"
            @click="onSendClick"
          >
            <Square
              v-if="loading"
              class="w-4 h-4"
            />
            <ArrowUp
              v-else
              class="w-4 h-4"
            />
          </button>
        </div>
      </div>
      <p class="disclaimer">
        AI 生成内容仅供参考
      </p>

      <input
        ref="fileInput"
        type="file"
        multiple
        hidden
        @change="onFileChange"
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, type Component, type CSSProperties } from 'vue'
import { h, defineComponent } from 'vue'
import {
  Paperclip,
  ArrowUp,
  Square,
  Copy,
  RefreshCw,
  X,
  BarChart2,
  FileText,
  PieChart,
  Code,
  ClipboardList,
  Languages,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { sendMessageStream, getMessages, getConversation } from '@/api/conversation'
import type { ChatMessageDTO } from '@/api/conversation'

/* ------------------------------------------------------------------ */
/*  RobotMark：欢迎态 logo 与 AI 头像复用的机器人 SVG                 */
/* ------------------------------------------------------------------ */
const RobotMark = defineComponent({
  name: 'RobotMark',
  props: { size: { type: Number, default: 32 } },
  setup(props) {
    return () =>
      h(
        'svg',
        {
          width: props.size,
          height: props.size,
          viewBox: '0 0 24 24',
          fill: 'none',
          xmlns: 'http://www.w3.org/2000/svg',
        },
        [
          h('rect', { x: 6, y: 4, width: 12, height: 14, rx: 4, fill: 'white', 'fill-opacity': 0.95 }),
          h('circle', { cx: 10, cy: 10, r: 1.5, fill: 'var(--aws-primary)' }),
          h('circle', { cx: 14, cy: 10, r: 1.5, fill: 'var(--aws-primary)' }),
          h('path', { d: 'M9.5 14.5C10.5 15.5 13.5 15.5 14.5 14.5', stroke: 'var(--aws-primary)', 'stroke-width': 1.5, 'stroke-linecap': 'round' }),
          h('path', { d: 'M12 18V21', stroke: 'white', 'stroke-width': 2, 'stroke-linecap': 'round' }),
          h('path', { d: 'M8 21H16', stroke: 'white', 'stroke-width': 2, 'stroke-linecap': 'round' }),
        ],
      )
  },
})

/* ------------------------------------------------------------------ */
/*  类型定义                                                          */
/* ------------------------------------------------------------------ */
interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  pending?: boolean
}

interface Attachment {
  id: number
  name: string
  size: string
}

interface Suggestion {
  title: string
  desc: string
  icon: Component
  tint: 'primary' | 'success'
}

/* ------------------------------------------------------------------ */
/*  状态                                                              */
/* ------------------------------------------------------------------ */
const authStore = useAuthStore()
const chatStore = useChatStore()
const userInitial = computed(() => authStore.user?.nickname?.substring(0, 1) || '我')

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const attachments = ref<Attachment[]>([])
const cancelled = ref(false)
/** 当前流式请求的 AbortController，停止按钮用它中断流 */
let abortCtrl: AbortController | null = null

/**
 * 监听当前会话切换：从 sidebar 点击不同对话记录时触发。
 * - currentId 为 null：清空消息，显示欢迎态
 * - currentId 有值且为新建会话（justCreated）：跳过历史加载，让 onSend 继续发送
 *   （新会话本就没有历史，若强行加载会拿到空数组覆盖掉刚 push 的消息）
 * - currentId 有值且为已有会话：调 GET /conversations/{id} + /messages 加载历史消息
 */
watch(
  () => chatStore.currentId,
  (id) => {
    if (id == null) {
      messages.value = []
      attachments.value = []
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
    input.value = ''
    loadConversation(id)
  },
)

/**
 * 页面挂载后：
 * 1. 如果 store 里有 pendingPrompt（从 workspace 跳转过来），消费它作为首条消息发送
 * 2. 否则如果已有 currentId（从 sidebar 直接点进会话），加载该会话的信息与历史消息
 */
onMounted(() => {
  const pending = chatStore.pendingPrompt
  if (pending) {
    chatStore.pendingPrompt = null // 消费后清空，避免重复触发
    onSend(pending)
  } else if (chatStore.currentId != null) {
    loadConversation(chatStore.currentId)
  }
})

/**
 * 进入会话时加载：调 GET /conversations/{id} 刷新会话元信息，
 * 再调 GET /conversations/{id}/messages 加载历史消息。
 */
async function loadConversation(conversationId: number) {
  try {
    // 刷新会话元信息（标题等），同步到 store 的 sessions 列表，保证 sidebar 显示一致
    const conv = await getConversation(conversationId)
    const idx = chatStore.sessions.findIndex((s) => s.id === conv.id)
    if (idx !== -1) {
      chatStore.sessions[idx] = conv
    } else {
      chatStore.sessions.unshift(conv)
    }
  } catch {
    // 会话信息加载失败不阻塞消息加载，拦截器已弹错
  }

  await loadMessages(conversationId)
}

/**
 * 加载会话历史消息（GET /conversations/{id}/messages）。
 * 后端按 created_at ASC 返回，直接映射为前端 ChatMessage 渲染。
 */
async function loadMessages(conversationId: number) {
  try {
    const list = await getMessages(conversationId)
    messages.value = (list ?? []).map((m: ChatMessageDTO) => ({
      id: m.id,
      role: m.role as 'user' | 'assistant',
      content: m.content,
      time: formatTime(m.created_at),
    }))
    scrollToBottom()
  } catch {
    // 请求失败时拦截器已弹错，消息列表保持空（欢迎态）
  }
}

/** 把后端 ISO 时间字符串格式化为 HH:mm 显示 */
function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

const bodyRef = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// 自增 id，避免用 index 作 key 在删除/重排时复用错乱。
let _id = 0
const uid = () => ++_id

const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

/* ------------------------------------------------------------------ */
/*  建议卡数据（与设计稿一致）                                        */
/* ------------------------------------------------------------------ */
const suggestions: Suggestion[] = [
  { title: '帮我分析这份Excel文件', desc: '数据分析 / 表格处理', icon: BarChart2, tint: 'primary' },
  { title: '写一份产品方案', desc: '文档写作 / 方案策划', icon: FileText, tint: 'success' },
  { title: '分析市场趋势', desc: '行业分析 / 竞品调研', icon: PieChart, tint: 'primary' },
  { title: '代码优化建议', desc: '编程辅助 / 代码审查', icon: Code, tint: 'success' },
  { title: '生成一份图表', desc: '数据可视化', icon: ClipboardList, tint: 'primary' },
  { title: '翻译中英文内容', desc: '语言翻译 / 润色优化', icon: Languages, tint: 'success' },
]

// 建议卡图标底色：用 color-mix 调淡主题色，与设计稿一致
function tintStyle(tint: 'primary' | 'success'): CSSProperties {
  const c = tint === 'primary' ? 'var(--aws-primary)' : 'var(--aws-success)'
  return {
    backgroundColor: `color-mix(in srgb, ${c} 12%, var(--aws-card))`,
    color: c,
  }
}

/* ------------------------------------------------------------------ */
/*  滚动到底部                                                        */
/* ------------------------------------------------------------------ */
function scrollToBottom() {
  nextTick(() => {
    const el = bodyRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

/* ------------------------------------------------------------------ */
/*  发送消息（流式输出）                                                */
/* ------------------------------------------------------------------ */
async function onSend(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return

  // 若当前无选中会话（直接访问 /chat），用消息前 30 字符作 title 创建会话
  if (chatStore.currentId == null) {
    await chatStore.createSession(content.slice(0, 30))
  }
  const conversationId = chatStore.currentId
  if (conversationId == null) return

  // 用户消息
  messages.value.push({
    id: uid(),
    role: 'user',
    content,
    time: now(),
  })
  input.value = ''
  scrollToBottom()

  await runReply(conversationId, content)
}

/**
 * 流式调用发送消息接口：后端保存 user message → 调 LLM → 逐块返回 assistant 内容。
 * 前端用 for await...of 逐块消费，增量追加到 assistant 消息实现打字机效果。
 * cancelled.value = true 可中断（用户点击停止按钮时触发）。
 */
async function runReply(conversationId: number, userText: string) {
  loading.value = true
  cancelled.value = false

  // 预占位一条 assistant 消息，内容逐步追加
  messages.value.push({
    id: uid(),
    role: 'assistant',
    content: '',
    time: now(),
    pending: true,
  })
  const idx = messages.value.length - 1
  scrollToBottom()

  // AbortController：用户点击停止按钮时 abort 中断流
  abortCtrl = new AbortController()

  try {
    for await (const chunk of sendMessageStream(conversationId, userText, {
      signal: abortCtrl.signal,
    })) {
      if (cancelled.value) break
      // chunk 是后端返回的增量内容（delta content），直接追加
      messages.value[idx].content += chunk.content
      scrollToBottom()
    }
    if (!cancelled.value) {
      messages.value[idx].pending = false
      messages.value[idx].time = now()
    }
  } catch (err) {
    // 用户主动中断：AbortError，不弹错，保留已生成内容
    if (err instanceof DOMException && err.name === 'AbortError') {
      messages.value[idx].pending = false
    } else {
      // 真实错误：移除占位消息，request stream 内部已弹错
      messages.value.splice(idx, 1)
    }
  } finally {
    loading.value = false
    abortCtrl = null
  }
}

function onEnter() {
  onSend()
}

function onSendClick() {
  // 加载中：点击 = 停止生成，中断流并标记取消
  if (loading.value) {
    cancelled.value = true
    abortCtrl?.abort()
    return
  }
  onSend()
}

function onSuggestion(item: Suggestion) {
  if (loading.value) return
  onSend(item.title)
}

/* ------------------------------------------------------------------ */
/*  重新生成 / 新对话 / 复制                                           */
/* ------------------------------------------------------------------ */
async function onRegenerate(m: ChatMessage) {
  if (loading.value) return
  const idx = messages.value.findIndex((x) => x.id === m.id)
  let userText = ''
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      userText = messages.value[i].content
      break
    }
  }
  if (!userText) return
  const conversationId = chatStore.currentId
  if (conversationId == null) return

  messages.value.splice(idx)
  await runReply(conversationId, userText)
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

/* ------------------------------------------------------------------ */
/*  附件                                                              */
/* ------------------------------------------------------------------ */
function triggerFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files) return
  for (const f of Array.from(target.files)) {
    attachments.value.push({
      id: uid(),
      name: f.name,
      size: formatSize(f.size),
    })
  }
  target.value = '' // 允许重复选同一文件
}

function removeAttachment(id: number) {
  attachments.value = attachments.value.filter((a) => a.id !== id)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}
</script>

<style scoped>
/* 整体容器：用负边距抵消 AppLayout .app-stage 的 24px padding，
   让输入栏贴底、内容区铺满整个 stage。 */
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  margin: -24px;
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

/* ---------------- 欢迎态 ---------------- */
.welcome-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px 8px;
}
.welcome-logo {
  width: 64px;
  height: 64px;
  border-radius: var(--aws-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  background: linear-gradient(135deg, var(--aws-primary), var(--aws-primary-hover));
}
.welcome-title {
  font-size: var(--aws-text-xl);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
  margin-bottom: 8px;
}
.welcome-sub {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  margin-bottom: 32px;
}
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
  max-width: 768px;
}
.suggestion-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: var(--aws-radius-lg);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  text-align: left;
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.15s;
}
.suggestion-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  border-color: var(--aws-border-strong);
  transform: translateY(-1px);
}
.suggestion-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.suggestion-title {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-foreground);
}
.suggestion-desc {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 4px;
}

/* ---------------- 对话态 ---------------- */
.conversation {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px 16px 8px;
  max-width: 820px;
  margin: 0 auto;
  width: 100%;
}
.msg-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.avatar-ai {
  background: linear-gradient(135deg, var(--aws-primary), var(--aws-primary-hover));
}
.avatar-user {
  border-radius: 50%;
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
}
.msg-main {
  min-width: 0;
  max-width: calc(100% - 44px);
  display: flex;
  flex-direction: column;
}
.msg-row.user .msg-main {
  align-items: flex-end;
}
.bubble {
  padding: 10px 14px;
  border-radius: var(--aws-radius-lg);
  font-size: var(--aws-text-sm);
  line-height: var(--aws-leading-relaxed);
  word-break: break-word;
}
.bubble.assistant {
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  color: var(--aws-foreground);
  border-top-left-radius: 4px;
}
.bubble.user {
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  border-top-right-radius: 4px;
}
.bubble-text {
  white-space: pre-wrap;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  min-height: 18px;
}
.msg-row.user .msg-meta {
  flex-direction: row-reverse;
}
.msg-time {
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}
.msg-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.msg-row:hover .msg-actions {
  opacity: 1;
}
.action-btn {
  width: 22px;
  height: 22px;
  border-radius: var(--aws-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: background-color 0.15s, color 0.15s;
}
.action-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}

/* 打字机思考态 */
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

/* ---------------- 输入栏 ---------------- */
.chat-input-bar {
  flex: none;
  width: 100%;
  max-width: 768px;
  margin: 0 auto;
  padding: 0 16px 24px;
}
.attach-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  padding: 4px 8px;
  border-radius: var(--aws-radius-md);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  font-size: var(--aws-text-xs);
  color: var(--aws-foreground);
}
.attach-name {
  max-width: 140px;
}
.attach-size {
  color: var(--aws-muted);
}
.attach-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: color 0.15s;
}
.attach-remove:hover {
  color: var(--aws-primary);
}
.input-wrap {
  position: relative;
}
.chat-input {
  width: 100%;
  height: 48px;
  padding-left: 16px;
  padding-right: 88px;
  border-radius: var(--aws-radius-xl);
  border: 1px solid var(--aws-border);
  background: var(--aws-input);
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  box-shadow: var(--aws-shadow-card);
  transition: box-shadow 0.15s, border-color 0.15s;
}
.chat-input::placeholder {
  color: var(--aws-placeholder);
}
.chat-input:focus {
  outline: none;
  border-color: var(--aws-primary);
  box-shadow: var(--aws-shadow-card), 0 0 0 3px rgba(59, 130, 246, 0.2);
}
.chat-input:disabled {
  background: var(--aws-sidebar);
  cursor: not-allowed;
}
.input-actions {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
}
.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: background-color 0.15s, color 0.15s;
}
.icon-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}
.send-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  transition: background-color 0.15s, opacity 0.15s;
}
.send-btn:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.send-btn.is-stop {
  background: var(--aws-foreground);
}
.send-btn.is-stop:hover {
  background: #374151;
}
.disclaimer {
  text-align: center;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 8px;
}

/* ---------------- 响应式 ---------------- */
@media (max-width: 768px) {
  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
