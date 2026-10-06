/**
 * 对话会话状态管理（Pinia Store）
 * ===========================================================================
 * 职责：
 *   集中管理 AI Chat 的"会话列表"与"当前选中的会话"。
 *   Sidebar（显示会话列表）和 Chat 页面（显示会话内容）共享此 store。
 *
 * 对接接口（业务设计文档 V0.1）：
 *   - createSession  → POST /conversations/create
 *   - fetchRecent    → GET  /conversations/recent
 *   - 发送消息 / 历史消息由 chat 视图直接调 API（不放在 store，避免消息状态耦合）
 * ===========================================================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  conversationNew,
  getRecentConversations,
  type Conversation,
} from '@/api/conversation'

/** 复用后端 Conversation 类型作为会话实体 */
export type ChatSession = Conversation

export const useChatStore = defineStore('chat', () => {
  // ---- 状态 ----
  /** 对话记录列表（按 updated_at DESC 排序） */
  const sessions = ref<ChatSession[]>([])
  /** 当前选中的会话 id；null 表示未选中（新会话欢迎态） */
  const currentId = ref<number | null>(null)
  /**
   * 标记 currentId 的变化是否由 createSession 触发。
   * 新建的会话没有历史消息，chat 页面 watch(currentId) 时据此跳过历史加载，
   * 避免 loadMessages 返回空数组覆盖掉刚 push 的用户消息和 assistant 占位消息。
   */
  const justCreated = ref(false)
  /** 加载中标记（创建会话 / 拉取列表时） */
  const loading = ref(false)
  /**
   * 待发送的提示词（workspace 输入框内容）。
   * workspace 创建会话后把用户输入存到这里，跳转 /chat 后由 chat 页面消费：
   * 自动作为首条消息发送给 LLM，实现"工作台提问 → 跳转 chat → 直接开始对话"。
   */
  const pendingPrompt = ref<string | null>(null)

  // ---- 计算属性 ----
  /** 当前选中的会话对象 */
  const currentSession = computed(
    () => sessions.value.find((s) => s.id === currentId.value) ?? null,
  )

  // ---- 方法 ----

  /**
   * 新建会话。
   * 调 POST /conversations/create，后端通过 JWT 绑定 user_id，返回完整 Conversation。
   * 成功后插入列表头部并设为当前会话。
   *
   * @param title 会话标题（workspace 输入框截取前 30 字符传入）
   * @returns 创建成功的会话对象
   */
  async function createSession(title: string) {
    loading.value = true
    try {
      const session = await conversationNew({ title, type: 'chat' })
      sessions.value.unshift(session)
      // 标记为新建会话，chat 页面 watch 会据此跳过历史消息加载
      justCreated.value = true
      currentId.value = session.id
      return session
    } finally {
      loading.value = false
    }
  }

  /**
   * 拉取最近会话列表。
   * 调 GET /conversations/recent，后端按 updated_at DESC 返回。
   * 通常在 workspace 页面 onMounted 时调用。
   */
  async function fetchRecent() {
    loading.value = true
    try {
      const list = await getRecentConversations()
      sessions.value = list ?? []
    } finally {
      loading.value = false
    }
  }

  /**
   * 选中某个会话（sidebar 点击对话记录时调用）。
   * 传 null 表示取消选中（新对话欢迎态）。
   * chat 页面 watch currentId 切换会话内容。
   */
  function selectSession(id: number | null) {
    // 切换已有会话需要加载历史消息，清除新建标记
    justCreated.value = false
    currentId.value = id
  }

  return {
    sessions,
    currentId,
    currentSession,
    loading,
    justCreated,
    pendingPrompt,
    createSession,
    fetchRecent,
    selectSession,
  }
})
