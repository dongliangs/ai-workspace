/**
 * 对话会话状态管理（Pinia Store）
 * ===========================================================================
 * 职责：
 *   集中管理 AI Chat 的"对话记录"列表与当前选中的会话。
 *   Sidebar（显示会话列表 + 新建对话）和 Chat 页面（显示会话内容）共享此 store，
 *   避免在两个组件间通过 props/emit 或全局事件耦合。
 *
 * 当前为 mock 数据，联调真实后端时：
 *   - sessions 从后端 /chat/sessions 拉取
 *   - createSession 调 POST /chat/sessions
 *   - selectSession 加载该会话的历史消息
 * ===========================================================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

/** 一个对话会话。 */
export interface ChatSession {
  /** 会话 id */
  id: number
  /** 会话标题（取首条用户消息或自动生成） */
  title: string
  // 用户id
  user_id: number,
  //会话类型
  type: "chat"
}

// /** mock 初始对话记录（设计稿中的 8 条）。 */
// const MOCK_SESSIONS: ChatSession[] = [
//   { id: 1, title: '数据分析相关问题', lastActive: '刚刚' },
//   { id: 2, title: '帮我分析这份Excel文件', lastActive: '10分钟前' },
//   { id: 3, title: '生成市场调研报告', lastActive: '1小时前' },
//   { id: 4, title: 'Python代码优化建议', lastActive: '今天' },
//   { id: 5, title: '产品方案策划思路', lastActive: '今天' },
//   { id: 6, title: '会议纪要整理', lastActive: '昨天' },
//   { id: 7, title: '帮我写一份周报', lastActive: '昨天' },
//   { id: 8, title: '翻译这段英文内容', lastActive: '3天前' },
// ]

let _id = 100

export const useChatStore = defineStore('chat', () => {
  // ---- 状态 ----
  // 对话记录列表
  const sessions = ref<ChatSession[]>([])
  // 当前选中的会话 id；null 表示未选中（空对话态）
  const currentId = ref<number | null>(null)

  // ---- 计算属性 ----
  // 当前选中的会话对象
  const currentSession = computed(
    () => sessions.value.find((s) => s.id === currentId.value) ?? null,
  )

  // ---- 方法 ----

  /**
   * 新建对话。
   * 生成一个临时标题为"新对话"的会话并选中，切换到 /chat 页面时 chat 视图会显示欢迎态。
   */
  function createSession() {
    const session: ChatSession = {}
    sessions.value.unshift(session)
    currentId.value = session.id
    return session
  }

  /**
   * 选中某个会话。
   * chat 页面可 watch currentId 切换到该会话的历史消息。
   */
  function selectSession(id: number) {
    currentId.value = id
  }

  /**
   * 更新当前会话标题（用户发第一条消息后，用消息内容截断作为标题）。
   */
  function renameSession(id: number, title: string) {
    const s = sessions.value.find((x) => x.id === id)
    if (s) s.title = title
  }

  return {
    sessions,
    currentId,
    currentSession,
    createSession,
    selectSession,
    renameSession,
  }
})
