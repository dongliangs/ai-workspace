/**
 * 会话相关接口
 * 对应业务设计文档 V0.1：
 *   - POST   /conversations                  创建会话
 *   - GET    /conversations/recent           获取最近会话
 *   - POST   /conversations/{id}/messages    发送消息（非流式，后端调 LLM 后返回 assistant 消息）
 */
import { post, get } from '@/utils/request'

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

/** 创建一个新会话 */
export function conversationNew(options: ConversationCreate) {
  return post<Conversation>('/conversations/create', { ...options })
}

/** 获取当前用户最近使用的会话列表 */
export function getRecentConversations() {
  return get<Conversation[]>('/conversations/recent')
}

/** 发送消息：后端保存 user message → 调 LLM → 保存 assistant message → 返回 assistant 消息 */
export function sendMessage(conversationId: number, content: string) {
  return post<ChatMessageDTO>(`/conversations/${conversationId}/messages`, { content })
}
