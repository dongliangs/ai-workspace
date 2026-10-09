/**
 * 对话会话状态管理（Pinia Store）
 * ===========================================================================
 * 职责：
 *   集中管理 AI Chat / Agent 的"会话列表"与"当前选中的会话"。
 *   Sidebar（显示会话列表）和 Chat 页面（显示会话内容）共享此 store。
 *
 * V0.2 扩展：
 *   - 会话支持 type: 'chat' | 'agent'，Agent 模式独立会话列表
 *   - createSession / fetchRecent 支持 type 参数
 *   - currentMode 从 currentSession.type 推导，回退到路由判断
 *
 * 对接接口：
 *   - createSession  → POST /conversations/create（含 type 字段）
 *   - fetchRecent    → GET  /conversations/recent?type=xxx（分页 + 类型过滤）
 *   - loadMore       → GET  /conversations/recent（下一页，sidebar 无限滚动）
 *   - 发送消息 / 历史消息由 chat 视图直接调 API（不放在 store，避免消息状态耦合）
 * ===========================================================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  conversationNew,
  getRecentConversations,
  type ConversationType,
} from '@/api/conversation'

/**
 * 会话实体（取分页 items 与完整 Conversation 的公共字段）。
 * sidebar 列表与 workspace 最近使用都只需要 id + title + type；
 * createSession 返回的 Conversation 字段更多，结构兼容可安全赋值。
 */
export interface ChatSession {
  id: number
  title: string
  type: ConversationType
}

export const useChatStore = defineStore('chat', () => {
  // ---- 状态 ----
  /** 对话记录列表（按 updated_at DESC 排序，分页累加） */
  const sessions = ref<ChatSession[]>([])
  /** 当前选中的会话 id；null 表示未选中（新会话欢迎态） */
  const currentId = ref<number | null>(null)
  /** 当前会话列表的类型过滤（chat / agent），切换模式时变化 */
  const listType = ref<ConversationType>('chat')
  /** 分页参数 */
  const page = ref(1)
  const pageSize = ref(20)
  /** 后端返回的总条数 */
  const total = ref(0)
  /** 首次加载中（fetchRecent 重置时） */
  const loading = ref(false)
  /** 加载更多中（loadMore 时） */
  const loadingMore = ref(false)
  /** 新建会话标记：chat 页面 watch(currentId) 据此跳过历史加载 */
  const justCreated = ref(false)
  /** 待发送的提示词（workspace → chat 跨页传递） */
  const pendingPrompt = ref<string | null>(null)

  // ---- 计算属性 ----
  /** 当前选中的会话对象 */
  const currentSession = computed(
    () => sessions.value.find((s) => s.id === currentId.value) ?? null,
  )
  /** 当前模式：优先从 currentSession.type 推导，无选中会话时回退到 listType */
  const currentMode = computed<ConversationType>(
    () => currentSession.value?.type ?? listType.value,
  )
  /** 是否还有更多可加载 */
  const hasMore = computed(() => sessions.value.length < total.value)

  // ---- 方法 ----

  /**
   * 新建会话。
   * 调 POST /conversations/create，后端通过 JWT 绑定 user_id，返回完整 Conversation。
   * type 区分普通 chat 和 agent 模式。成功后插入列表头部并设为当前会话。
   */
  async function createSession(title: string, type: ConversationType = 'chat') {
    loading.value = true
    try {
      const session = await conversationNew({ title, type })
      sessions.value.unshift(session)
      total.value += 1
      justCreated.value = true
      currentId.value = session.id
      return session
    } finally {
      loading.value = false
    }
  }

  /**
   * 拉取最近会话列表（重置分页，加载第一页）。
   * 调 GET /conversations/recent?page=1&page_size=20&type=xxx。
   * type 可选，不传则拉取所有类型。通常在进入 chat/agent 页面、切换模式时调用。
   */
  async function fetchRecent(type?: ConversationType) {
    loading.value = true
    try {
      page.value = 1
      if (type) listType.value = type
      const res = await getRecentConversations({
        page: page.value,
        page_size: pageSize.value,
        type: type ?? listType.value,
      })
      sessions.value = res.items ?? []
      total.value = res.total ?? 0
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载下一页（sidebar 无限滚动触底时调用）。
   * 已无更多或正在加载时直接返回，避免重复请求。
   */
  async function loadMore() {
    if (!hasMore.value || loadingMore.value || loading.value) return
    loadingMore.value = true
    try {
      page.value += 1
      const res = await getRecentConversations({
        page: page.value,
        page_size: pageSize.value,
        type: listType.value,
      })
      const items = res.items ?? []
      // 追加到列表尾部
      sessions.value.push(...items)
      total.value = res.total ?? 0
    } finally {
      loadingMore.value = false
    }
  }

  /**
   * 选中某个会话（sidebar 点击对话记录时调用）。
   * 传 null 表示取消选中（新对话欢迎态）。
   */
  function selectSession(id: number | null) {
    justCreated.value = false
    currentId.value = id
  }

  return {
    sessions,
    currentId,
    currentSession,
    currentMode,
    listType,
    loading,
    loadingMore,
    justCreated,
    pendingPrompt,
    page,
    pageSize,
    total,
    hasMore,
    createSession,
    fetchRecent,
    loadMore,
    selectSession,
  }
})
