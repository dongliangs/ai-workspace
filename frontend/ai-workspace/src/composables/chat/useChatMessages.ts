import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import {
  getConversation,
  getMessages,
  type ChatMessageDTO,
  type Conversation,
} from '@/api/conversation'
import type { UploadFile } from '@/components/common/FileUploader.vue'
import type { ChatMessage } from '@/components/chat/types'

/**
 * 聊天消息状态：消息列表、输入框内容、附件、上传中标记，
 * 以及历史会话加载与消息 DTO → 前端模型的映射。
 */
export function useChatMessages(scrollToBottom: () => void) {
  const chatStore = useChatStore()

  const messages = ref<ChatMessage[]>([])
  const input = ref('')
  const attachments = ref<UploadFile[]>([])
  const hasUploading = ref(false)
  /** 历史消息加载中：此时禁止发送，避免历史响应覆盖/错位正在发送的消息 */
  const historyLoading = ref(false)

  // 历史加载序号：快速切换会话时只允许最后一次请求写入消息（丢弃过期响应）
  let loadSeq = 0

  // 自增 id，避免用 index 作 key 在删除/重排时复用错乱。
  let _id = 0
  const uid = () => ++_id

  const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

  /** 把后端 ISO 时间字符串格式化为 HH:mm 显示 */
  function formatTime(iso: string): string {
    try {
      return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } catch {
      return iso
    }
  }

  /** 把文件字节数格式化为 B/KB/MB 显示文本（与 FileUploader 的展示格式一致） */
  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  }

  /**
   * 进入会话时加载：调 GET /conversations/{id} 刷新会话元信息，
   * 再调 GET /conversations/{id}/messages 加载历史消息。
   *
   * onMeta：会话元信息加载成功后的回调（如 Agent 会话恢复知识库绑定状态），
   * 携带最新 loadSeq 判断，避免快速切换会话时旧响应写入。
   */
  async function loadConversation(
    conversationId: number,
    onMeta?: (conv: Conversation) => void,
  ) {
    const seq = ++loadSeq
    historyLoading.value = true
    try {
      try {
        const conv = await getConversation(conversationId)
        if (seq !== loadSeq) return
        const idx = chatStore.sessions.findIndex((s) => s.id === conv.id)
        if (idx !== -1) {
          chatStore.sessions[idx] = conv
        } else {
          chatStore.sessions.unshift(conv)
        }
        onMeta?.(conv)
      } catch {
        // 会话信息加载失败不阻塞消息加载，拦截器已弹错
      }

      await loadMessages(conversationId, seq)
    } finally {
      if (seq === loadSeq) historyLoading.value = false
    }
  }

  /**
   * 加载会话历史消息（GET /conversations/{id}/messages）。
   * 后端按 created_at ASC 返回，直接映射为前端 ChatMessage 渲染。
   *
   * seq 用于丢弃过期响应；若期间用户已发送新消息（或流式生成中），
   * 则不覆盖当前消息列表，避免流式写入的 index 错位。
   */
  async function loadMessages(conversationId: number, seq?: number) {
    const mySeq = seq ?? loadSeq
    try {
      const list = await getMessages(conversationId)
      if (mySeq !== loadSeq) return
      // 已有未完成/新发送的消息：放弃本次历史覆盖（典型场景：历史还在加载时用户抢先提问）
      if (messages.value.some((m) => m.pending || m.role === 'user')) return
      messages.value = (list ?? []).map((m: ChatMessageDTO) => {
        const results = m.tool_results ?? []
        // 知识库问答：来源记录（rag_sources）单独提取为 sources，不当作 Agent 工具卡片
        const ragSources = results.find((tr) => tr.type === 'rag_sources')?.sources
        const tools = results
          .filter((tr) => tr.type !== 'rag_sources' && tr.tool)
          .map((tr, i) => ({
            id: Date.now() + i,
            tool: tr.tool as string,
            status: tr.status as 'running' | 'success' | 'error',
            result: tr.result,
          }))

        return {
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          time: formatTime(m.created_at),
          // 历史消息附件：后端返回 files（id/name/size），映射为附件 chip 展示
          attachments: m.files?.length
            ? m.files.map((f) => ({ id: f.id, name: f.name, size: formatFileSize(f.size) }))
            : undefined,
          // 历史知识库问答的来源片段（刷新后仍可展示参考来源）
          sources: ragSources?.length ? ragSources : undefined,
          tools: tools.length ? tools : undefined,
        }
      })
      scrollToBottom()
    } catch {
      // 请求失败时拦截器已弹错，消息列表保持空（欢迎态）
    }
  }

  return {
    messages,
    input,
    attachments,
    hasUploading,
    historyLoading,
    uid,
    now,
    loadConversation,
    loadMessages,
  }
}