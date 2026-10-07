/**
 * 会话相关接口
 */
import { post, get, stream, type StreamOptions } from '@/utils/request'

/** 创建会话的请求参数 */
export interface ConversationCreate {
  title: string
  type: 'chat'
}

/** 会话对象（后端 conversations 表） */
export interface Conversation {
  id: number
  user_id: number
  title: string
  type: 'chat'
}

/** 消息对象（后端 messages 表，发送消息接口返回的 assistant 消息） */
export interface ChatMessageDTO {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

interface itemsType {
  id: number
  title: string
}

/** 最近会话分页响应（GET /conversations/recent） */
export interface RecentConversation {
  items: itemsType[]
  page: number
  page_size: number
  total: number
}

/** 创建一个新会话 */
export function conversationNew(options: ConversationCreate) {
  return post<Conversation>('/conversations/create', { ...options })
}

/** 获取当前用户最近使用的会话列表（分页） */
export function getRecentConversations(query: { page: number; page_size: number }) {
  return get<RecentConversation>('/conversations/recent', query)
}

/** 查询某个会话的基本信息 */
export function getConversation(conversationId: number) {
  return get<Conversation>(`/conversations/${conversationId}`)
}

/** 查询某个会话的历史消息（按 created_at ASC 排序） */
export function getMessages(conversationId: number) {
  return get<ChatMessageDTO[]>(`/conversations/${conversationId}/messages`)
}

/** 发送消息：后端保存 user message → 调 LLM → 保存 assistant message → 返回 assistant 消息 */
export function sendMessage(conversationId: number, content: string) {
  return post<ChatMessageDTO>(`/conversations/${conversationId}/messages`, { content })
}

/**
 * 流式发送消息：后端保存 user message → 调 LLM → 逐块返回 assistant 内容（SSE/NDJSON）。
 * 内部对每个 SSE/NDJSON 数据块做 JSON.parse，提取 content 字段后 yield 出去，
 * 调用方可直接 `chunk.content` 增量拼接，无需自行解析。
 *
 * @returns AsyncGenerator，每次 yield { content: string } 对象
 */
export async function* sendMessageStream(
  conversationId: number,
  content: string,
  options?: StreamOptions,
) {
  for await (const raw of stream(
    `/conversations/${conversationId}/messages`,
    { content },
    options,
  )) {
    // 后端 SSE data 通常是 JSON，如 {"content":"..."} 或 {"delta":{"content":"..."}}
    try {
      const obj = JSON.parse(raw) as Record<string, unknown>
      const delta = obj.delta as Record<string, unknown> | undefined
      const choices = obj.choices as { delta?: { content?: string } }[] | undefined
      const text =
        (obj.content as string) ??
        (delta?.content as string) ??
        (choices?.[0]?.delta?.content as string) ??
        ''
      yield { content: text }
    } catch {
      // 非 JSON 格式（如纯文本增量），直接当作内容返回
      yield { content: raw }
    }
  }
}
