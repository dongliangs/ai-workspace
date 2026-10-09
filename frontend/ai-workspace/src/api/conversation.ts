/**
 * 会话相关接口
 */
import { post, get, stream, type StreamOptions } from '@/utils/request'

/** 会话类型：普通聊天 / Agent 模式 */
export type ConversationType = 'chat' | 'agent'

/** 创建会话的请求参数 */
export interface ConversationCreate {
  title: string
  type: ConversationType
}

/** 会话对象（后端 conversations 表） */
export interface Conversation {
  id: number
  user_id: number
  title: string
  type: ConversationType
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
  type: ConversationType
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

/** 获取当前用户最近使用的会话列表（分页，可按 type 过滤） */
export function getRecentConversations(query: {
  page: number
  page_size: number
  type?: ConversationType
}) {
  return get<RecentConversation>('/conversations/recent', query as Record<string, unknown>)
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

/* -------------------------------------------------------------------------- */
/*  Agent 模式流式接口                                                         */
/* -------------------------------------------------------------------------- */

/** Agent SSE 事件类型 */
export type AgentEvent =
  | { type: 'agent_start' }
  | { type: 'text'; content: string }
  | { type: 'tool_start'; tool: string; arguments?: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; status: 'success' | 'error'; result?: unknown }
  | { type: 'done'; message_id: number }

/**
 * Agent 流式发送消息：后端 Agent Runtime 执行工具调用，通过 SSE 推送事件。
 *
 * 事件类型见 AgentEvent：
 * - agent_start: Agent 开始执行
 * - text: 增量文本内容（追加到消息）
 * - tool_start: 工具开始执行（含工具名和参数）
 * - tool_result: 工具执行完成（含状态和结果）
 * - done: Agent 执行完成（含最终 message_id）
 *
 * @param conversationId 会话 ID
 * @param content 用户输入
 * @param fileIds 已上传文件的 ID 列表
 * @param tools 指定使用的工具列表（可选，不传则由 Agent 自行决定）
 * @param options 流式中断/超时控制
 */
export async function* sendAgentMessageStream(
  conversationId: number,
  content: string,
  fileIds?: number[],
  tools?: string[],
  options?: StreamOptions,
): AsyncGenerator<AgentEvent, void, unknown> {
  const payload: Record<string, unknown> = { content }
  if (fileIds && fileIds.length) payload.file_ids = fileIds
  if (tools && tools.length) payload.tools = tools

  for await (const raw of stream(`/agent/${conversationId}/messages`, payload, options)) {
    try {
      const obj = JSON.parse(raw) as Record<string, unknown>
      const eventType = obj.type as string

      if (eventType === 'agent_start') {
        yield { type: 'agent_start' }
      } else if (eventType === 'text') {
        yield { type: 'text', content: (obj.content as string) ?? '' }
      } else if (eventType === 'tool_start') {
        yield {
          type: 'tool_start',
          tool: (obj.tool as string) ?? '',
          arguments: obj.arguments as Record<string, unknown> | undefined,
        }
      } else if (eventType === 'tool_result') {
        yield {
          type: 'tool_result',
          tool: (obj.tool as string) ?? '',
          status: (obj.status as 'success' | 'error') ?? 'success',
          result: obj.result,
        }
      } else if (eventType === 'done') {
        yield { type: 'done', message_id: (obj.message_id as number) ?? 0 }
      }
      // 未知事件类型忽略
    } catch {
      // 非 JSON 格式，当作纯文本内容
      yield { type: 'text', content: raw }
    }
  }
}
