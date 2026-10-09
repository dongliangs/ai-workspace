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
          {{ isAgentMode ? '你好！我是你的 Agent 助手' : '你好！我是你的 AI 助手' }}
        </h2>
        <p class="welcome-sub">
          {{ isAgentMode
            ? '上传文件、提出任务，我将调用工具帮你分析数据、生成图表和报告'
            : '你可以向我提问，或让我帮你完成各类任务' }}
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
            <!-- 用户消息：含文件附件 -->
            <div
              v-if="m.role === 'user'"
              class="user-bubble-wrap"
            >
              <!-- 附件预览 -->
              <div
                v-if="m.attachments?.length"
                class="msg-attachments"
              >
                <span
                  v-for="a in m.attachments"
                  :key="a.id"
                  class="msg-attach-chip"
                >
                  <FileSpreadsheet class="w-3.5 h-3.5 shrink-0" />
                  <span class="truncate">{{ a.name }}</span>
                  <span class="msg-attach-size">{{ a.size }}</span>
                </span>
              </div>
              <div class="bubble user">
                <span class="bubble-text">{{ m.content }}</span>
              </div>
            </div>

            <!-- Agent 模式 AI 消息：AgentMessageBubble 组合渲染 -->
            <AgentMessageBubble
              v-else-if="isAgentMode || m.steps || m.tools"
              :content="m.content"
              :steps="m.steps ?? []"
              :tools="m.tools ?? []"
              :pending="m.pending"
            />

            <!-- 普通 Chat 模式 AI 消息 -->
            <div
              v-else
              class="bubble assistant"
            >
              <span
                v-if="m.pending && !m.content"
                class="typing-dots"
              >
                <i /><i /><i />
              </span>
              <MarkdownContent
                v-else
                :content="m.content"
              />
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
          :class="{ 'is-error': a.status === 'error' }"
        >
          <FileSpreadsheet class="w-3.5 h-3.5 shrink-0" />
          <span class="attach-name truncate">{{ a.name }}</span>
          <!-- 上传中显示进度，完成显示大小 -->
          <span class="attach-meta">
            <template v-if="a.status === 'uploading'">
              {{ a.progress }}%
            </template>
            <template v-else>{{ a.size }}</template>
          </span>
          <button
            type="button"
            class="attach-remove"
            :disabled="a.status === 'uploading'"
            @click="removeAttachment(a.id)"
          >
            <X class="w-3 h-3" />
          </button>
        </span>
      </div>

      <!-- 胶囊形输入框：+ 加号 | textarea | 圆形发送按钮 -->
      <div class="input-pill">
        <!-- 左侧：+ 加号（点击上传文件） -->
        <button
          type="button"
          class="plus-icon"
          title="上传文件"
          :disabled="loading"
          @click="triggerFile"
        >
          <Plus class="w-5 h-5" />
        </button>

        <!-- 中间：多行文本输入 -->
        <textarea
          ref="textareaRef"
          v-model="input"
          class="chat-textarea"
          :placeholder="placeholder"
          :disabled="loading"
          rows="1"
          @input="autoResize"
          @keydown.enter.exact.prevent="onEnter"
        />

        <!-- 右侧：圆形蓝色发送按钮 -->
        <button
          type="button"
          class="send-circle"
          :class="{ 'is-stop': loading }"
          :disabled="!loading && !canSend"
          @click="onSendClick"
        >
          <Square
            v-if="loading"
            class="w-4 h-4"
          />
          <ArrowUp
            v-else
            class="w-[18px] h-[18px]"
          />
        </button>
      </div>

      <!-- 输入框下方：选择工具（仅 Agent 模式） -->
      <div
        v-if="isAgentMode"
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

    <!-- 点击外部关闭工具弹出层 -->
    <div
      v-if="toolPopoverOpen"
      class="popover-backdrop"
      @click="toolPopoverOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, type Component, type CSSProperties } from 'vue'
import { h, defineComponent } from 'vue'
import { useRoute } from 'vue-router'
import {
  Plus,
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
  FileSpreadsheet,
  Wrench,
  ChevronDown,
  Calculator,
  BarChart3,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import {
  sendMessageStream,
  sendAgentMessageStream,
  getMessages,
  getConversation,
  type ConversationType,
} from '@/api/conversation'
import { uploadFile } from '@/api/file'
import type { ChatMessageDTO } from '@/api/conversation'
import type { UploadProgress } from '@/utils/request'
import MarkdownContent from '@/components/chat/MarkdownContent.vue'
import AgentMessageBubble from '@/components/chat/AgentMessageBubble.vue'
import type { AgentStep, ToolInvocation } from '@/components/chat/AgentMessageBubble.vue'

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
interface Attachment {
  id: number
  name: string
  size: string
  file_id?: number
  status: 'uploading' | 'done' | 'error'
  progress: number
  rawSize: number
}

interface MessageAttachment {
  id: number
  name: string
  size: string
}

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  pending?: boolean
  steps?: AgentStep[]
  tools?: ToolInvocation[]
  attachments?: MessageAttachment[]
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
const route = useRoute()
const authStore = useAuthStore()
const chatStore = useChatStore()
const userInitial = computed(() => authStore.user?.nickname?.substring(0, 1) || '我')

/** Agent 模式：路由 /agent 或当前会话 type=agent */
const isAgentMode = computed(() => {
  if (chatStore.currentSession?.type === 'agent') return true
  return route.path === '/agent'
})

/** 当前会话类型 */
const currentType = computed<ConversationType>(() =>
  isAgentMode.value ? 'agent' : 'chat',
)

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const attachments = ref<Attachment[]>([])
const cancelled = ref(false)
const toolPopoverOpen = ref(false)
const selectedTools = ref<string[]>([])
/** 当前流式请求的 AbortController，停止按钮用它中断流 */
let abortCtrl: AbortController | null = null

const bodyRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// 自增 id，避免用 index 作 key 在删除/重排时复用错乱。
let _id = 0
const uid = () => ++_id

const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

/* ------------------------------------------------------------------ */
/*  可用工具（Agent 模式）                                            */
/* ------------------------------------------------------------------ */
const availableTools = [
  { id: 'calculator', name: '计算器', desc: '数学计算', icon: Calculator },
  { id: 'analyze_excel', name: 'Excel 分析', desc: '数据表格分析', icon: FileSpreadsheet },
  { id: 'generate_chart', name: '图表生成', desc: '可视化图表', icon: BarChart3 },
]

/* ------------------------------------------------------------------ */
/*  建议卡数据（按模式区分）                                          */
/* ------------------------------------------------------------------ */
const chatSuggestions: Suggestion[] = [
  { title: '帮我分析这份Excel文件', desc: '数据分析 / 表格处理', icon: BarChart2, tint: 'primary' },
  { title: '写一份产品方案', desc: '文档写作 / 方案策划', icon: FileText, tint: 'success' },
  { title: '分析市场趋势', desc: '行业分析 / 竞品调研', icon: PieChart, tint: 'primary' },
  { title: '代码优化建议', desc: '编程辅助 / 代码审查', icon: Code, tint: 'success' },
  { title: '生成一份图表', desc: '数据可视化', icon: ClipboardList, tint: 'primary' },
  { title: '翻译中英文内容', desc: '语言翻译 / 润色优化', icon: Languages, tint: 'success' },
]

const agentSuggestions: Suggestion[] = [
  { title: '分析 Excel 销售数据并生成报告', desc: '上传 Excel → 数据清洗 → 分析 → 报告', icon: FileSpreadsheet, tint: 'primary' },
  { title: '生成销售排名柱状图', desc: '数据可视化 / 图表生成', icon: BarChart3, tint: 'success' },
  { title: '计算数据汇总指标', desc: '求和 / 均值 / 占比 / 统计', icon: Calculator, tint: 'primary' },
  { title: '上传文件进行数据分析', desc: '文件解析 / 结构化输出', icon: FileText, tint: 'success' },
  { title: '生成市场调研报告', desc: '行业分析 / 竞品对比', icon: ClipboardList, tint: 'primary' },
  { title: '多步骤任务规划与执行', desc: '任务拆解 / 工具编排', icon: Code, tint: 'success' },
]

const suggestions = computed(() =>
  isAgentMode.value ? agentSuggestions : chatSuggestions,
)

// 建议卡图标底色
function tintStyle(tint: 'primary' | 'success'): CSSProperties {
  const c = tint === 'primary' ? 'var(--aws-primary)' : 'var(--aws-success)'
  return {
    backgroundColor: `color-mix(in srgb, ${c} 12%, var(--aws-card))`,
    color: c,
  }
}

/* ------------------------------------------------------------------ */
/*  placeholder 按模式变化                                            */
/* ------------------------------------------------------------------ */
const placeholder = computed(() =>
  isAgentMode.value
    ? '请输入你的问题，或上传文件让 Agent 帮你分析...'
    : '输入你的问题，或上传文件...',
)

/** 是否可发送：有内容且无上传中的附件 */
const canSend = computed(() => {
  const hasUploading = attachments.value.some((a) => a.status === 'uploading')
  if (hasUploading) return false
  return input.value.trim().length > 0
})

/* ------------------------------------------------------------------ */
/*  textarea 自动高度                                                 */
/* ------------------------------------------------------------------ */
function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  })
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
/*  会话切换监听                                                      */
/* ------------------------------------------------------------------ */
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
    chatStore.pendingPrompt = null
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

/* ------------------------------------------------------------------ */
/*  发送消息                                                          */
/* ------------------------------------------------------------------ */
async function onSend(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return

  // 有附件仍在上传中，阻止发送
  if (attachments.value.some((a) => a.status === 'uploading')) {
    ElMessage.warning('文件上传中，请稍候...')
    return
  }

  // 若当前无选中会话，用消息前 30 字符作 title 创建会话
  if (chatStore.currentId == null) {
    await chatStore.createSession(content.slice(0, 30), currentType.value)
  }
  const conversationId = chatStore.currentId
  if (conversationId == null) return

  // 收集已上传文件的 file_id
  const fileIds = attachments.value
    .filter((a) => a.status === 'done' && a.file_id)
    .map((a) => a.file_id!)

  // 用户消息（含附件预览）
  const userAttachments: MessageAttachment[] = attachments.value
    .filter((a) => a.status === 'done')
    .map((a) => ({ id: a.id, name: a.name, size: a.size }))

  messages.value.push({
    id: uid(),
    role: 'user',
    content,
    time: now(),
    attachments: userAttachments.length ? userAttachments : undefined,
  })
  input.value = ''
  attachments.value = []
  autoResize()
  scrollToBottom()

  await runReply(conversationId, content, fileIds)
}

/**
 * 流式回复：根据模式分流到普通 Chat 或 Agent。
 */
async function runReply(
  conversationId: number,
  userText: string,
  fileIds: number[] = [],
) {
  loading.value = true
  cancelled.value = false

  // 预占位一条 assistant 消息
  const placeholder: ChatMessage = {
    id: uid(),
    role: 'assistant',
    content: '',
    time: now(),
    pending: true,
    // Agent 模式预初始化 steps/tools 数组
    ...(isAgentMode.value ? { steps: [], tools: [] } : {}),
  }
  messages.value.push(placeholder)
  const idx = messages.value.length - 1
  scrollToBottom()

  abortCtrl = new AbortController()

  if (isAgentMode.value) {
    await runAgentReply(conversationId, userText, fileIds, idx)
  } else {
    await runChatReply(conversationId, userText, idx)
  }
}

/** 普通 Chat 流式回复 */
async function runChatReply(
  conversationId: number,
  userText: string,
  idx: number,
) {
  try {
    for await (const chunk of sendMessageStream(conversationId, userText, {
      signal: abortCtrl?.signal,
    })) {
      if (cancelled.value) break
      messages.value[idx].content += chunk.content
      scrollToBottom()
    }
    if (!cancelled.value) {
      messages.value[idx].pending = false
      messages.value[idx].time = now()
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      messages.value[idx].pending = false
    } else {
      messages.value.splice(idx, 1)
    }
  } finally {
    loading.value = false
    abortCtrl = null
  }
}

/** Agent 流式回复：处理 agent_start / text / tool_start / tool_result / done 事件 */
async function runAgentReply(
  conversationId: number,
  userText: string,
  fileIds: number[],
  idx: number,
) {
  const tools = selectedTools.value.length ? selectedTools.value : undefined

  try {
    for await (const evt of sendAgentMessageStream(
      conversationId,
      userText,
      fileIds.length ? fileIds : undefined,
      tools,
      { signal: abortCtrl?.signal },
    )) {
      if (cancelled.value) break
      const msg = messages.value[idx]

      switch (evt.type) {
        case 'agent_start':
          // Agent 开始，可以添加一个初始"理解任务"步骤
          if (msg.steps) {
            msg.steps.push({ id: uid(), label: '理解任务', status: 'running' })
          }
          break

        case 'text':
          msg.content += evt.content
          break

        case 'tool_start': {
          // 把上一个 running 步骤标记为 done
          if (msg.steps && msg.steps.length) {
            const lastRunning = [...msg.steps].reverse().find((s) => s.status === 'running')
            if (lastRunning) lastRunning.status = 'done'
          }
          // 添加工具调用步骤
          if (msg.steps) {
            msg.steps.push({
              id: uid(),
              label: toolLabel(evt.tool),
              status: 'running',
            })
          }
          // 添加工具卡片
          if (msg.tools) {
            msg.tools.push({
              id: uid(),
              tool: evt.tool,
              status: 'running',
              arguments: evt.arguments,
            })
          }
          break
        }

        case 'tool_result': {
          // 更新对应工具卡片状态（按 tool 名匹配最后一个 running 的）
          if (msg.tools) {
            const target = [...msg.tools]
              .reverse()
              .find((t) => t.tool === evt.tool && t.status === 'running')
            if (target) {
              target.status = evt.status
              target.result = evt.result
            }
          }
          break
        }

        case 'done':
          // 标记所有 running 步骤为 done
          if (msg.steps) {
            msg.steps.forEach((s) => {
              if (s.status === 'running') s.status = 'done'
            })
          }
          msg.pending = false
          msg.time = now()
          if (evt.message_id) msg.id = evt.message_id
          break
      }
      scrollToBottom()
    }

    // 流结束但没收到 done 事件：收尾
    if (!cancelled.value) {
      const msg = messages.value[idx]
      msg.pending = false
      msg.time = now()
      if (msg.steps) {
        msg.steps.forEach((s) => {
          if (s.status === 'running') s.status = 'done'
        })
      }
      if (msg.tools) {
        msg.tools.forEach((t) => {
          if (t.status === 'running') t.status = 'success'
        })
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      // 用户中断：把运行中的 tool 卡片标记为 stopped
      const msg = messages.value[idx]
      msg.pending = false
      if (msg.tools) {
        msg.tools.forEach((t) => {
          if (t.status === 'running') t.status = 'stopped'
        })
      }
      if (msg.steps) {
        msg.steps.forEach((s) => {
          if (s.status === 'running') s.status = 'done'
        })
      }
    } else {
      messages.value.splice(idx, 1)
    }
  } finally {
    loading.value = false
    abortCtrl = null
  }
}

/** 工具名 → 中文标签 */
function toolLabel(tool: string): string {
  const map: Record<string, string> = {
    calculator: '执行计算',
    analyze_excel: '分析 Excel',
    generate_chart: '生成图表',
  }
  return map[tool] ?? tool
}

function onEnter() {
  if (!canSend.value || loading.value) return
  onSend()
}

function onSendClick() {
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
/*  重新生成 / 复制                                                   */
/* ------------------------------------------------------------------ */
async function onRegenerate(m: ChatMessage) {
  if (loading.value) return
  const idx = messages.value.findIndex((x) => x.id === m.id)
  let userText = ''
  let fileIds: number[] = []
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

/* ------------------------------------------------------------------ */
/*  附件 / 文件上传                                                   */
/* ------------------------------------------------------------------ */
function triggerFile() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files) return
  for (const f of Array.from(target.files)) {
    const attachId = uid()
    const attach: Attachment = {
      id: attachId,
      name: f.name,
      size: formatSize(f.size),
      rawSize: f.size,
      status: 'uploading',
      progress: 0,
    }
    attachments.value.push(attach)

    // 真实上传
    try {
      const res = await uploadFile(f, (p: UploadProgress) => {
        const item = attachments.value.find((a) => a.id === attachId)
        if (item) item.progress = p.percent
      })
      const item = attachments.value.find((a) => a.id === attachId)
      if (item) {
        item.status = 'done'
        item.file_id = res.id
        item.progress = 100
      }
    } catch {
      const item = attachments.value.find((a) => a.id === attachId)
      if (item) {
        item.status = 'error'
      }
      ElMessage.error(`文件 ${f.name} 上传失败`)
    }
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

/* ------------------------------------------------------------------ */
/*  工具弹出层外部点击关闭                                            */
/* ------------------------------------------------------------------ */
// 通过 popover-backdrop 实现，无需额外监听
</script>

<style scoped>
/* 整体容器：用负边距抵消 AppLayout .app-stage 的 24px padding */
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
  max-width: 480px;
  text-align: center;
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
.user-bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
.msg-attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  padding: 4px 8px;
  border-radius: var(--aws-radius-md);
  background: color-mix(in srgb, var(--aws-primary) 10%, var(--aws-card));
  border: 1px solid color-mix(in srgb, var(--aws-primary) 20%, var(--aws-border));
  font-size: var(--aws-text-xs);
  color: var(--aws-foreground);
}
.msg-attach-size {
  color: var(--aws-muted);
}
.bubble {
  padding: 10px 14px;
  border-radius: var(--aws-radius-lg);
  font-size: var(--aws-text-sm);
  line-height: var(--aws-leading-relaxed);
  word-break: break-word;
}
.bubble.assistant {
  background: transparent;
  border: none;
  color: var(--aws-foreground);
  border-top-left-radius: 4px;
  padding: 0;
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
  position: relative;
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
  max-width: 240px;
  padding: 6px 10px;
  border-radius: var(--aws-radius-md);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  font-size: var(--aws-text-xs);
  color: var(--aws-foreground);
  transition: border-color 0.15s;
}
.attach-chip.is-error {
  border-color: #ef4444;
  color: #ef4444;
}
.attach-name {
  max-width: 140px;
}
.attach-meta {
  color: var(--aws-muted);
}
.attach-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: color 0.15s;
}
.attach-remove:hover:not(:disabled) {
  color: var(--aws-primary);
}
.attach-remove:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 胶囊形输入框：回形针 | textarea | 圆形发送按钮 */
.input-pill {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 8px 8px 16px;
  border-radius: 28px;
  border: 1px solid var(--aws-border);
  background: var(--aws-input);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.input-pill:focus-within {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

/* 左侧 + 加号图标 */
.plus-icon {
  flex: none;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  background: transparent;
  border: none;
  border-radius: 50%;
  transition: color 0.15s, background-color 0.15s;
  align-self: flex-end;
  margin-bottom: 2px;
}
.plus-icon:hover:not(:disabled) {
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 8%, transparent);
}
.plus-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 多行文本输入 */
.chat-textarea {
  flex: 1;
  min-height: 36px;
  max-height: 160px;
  padding: 8px 0;
  border: none;
  background: transparent;
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  line-height: var(--aws-leading-relaxed);
  resize: none;
  font-family: inherit;
}
.chat-textarea::placeholder {
  color: var(--aws-placeholder);
}
.chat-textarea:focus {
  outline: none;
}
.chat-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 右侧圆形蓝色发送按钮 */
.send-circle {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  transition: background-color 0.15s, opacity 0.15s;
  align-self: flex-end;
  margin-bottom: 2px;
}
.send-circle:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.send-circle:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.send-circle.is-stop {
  background: var(--aws-foreground);
}
.send-circle.is-stop:hover {
  background: #374151;
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

.disclaimer {
  text-align: center;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 8px;
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

/* ---------------- 响应式 ---------------- */
@media (max-width: 768px) {
  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
