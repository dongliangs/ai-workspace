/**
 * 知识库问答流式接口
 * ===========================================================================
 * 后端契约（backend/api/knowledge_chat.py）：
 *   POST /knowledge-bases/{kb_id}/chat   { question, conversation_id? }
 *
 * SSE 事件序列：
 *   start            → 开始
 *   retrieval_start  → 正在检索（{ kb_id }）
 *   retrieval_result → 检索到的来源元数据（{ sources, message? }，sources 可能为空）
 *   text             → LLM 回答增量（多次）
 *   done             → 结束（{ message_id, conversation_id, sources? }）
 *   error            → 异常（{ message }）
 * ===========================================================================
 */
import { stream, type StreamOptions } from '@/utils/request'

/** 检索命中的来源片段元数据（字段与后端保持一致） */
export interface KnowledgeSource {
  /** 引用角标序号（从 1 开始，对应回答正文里的 [1]、[2]） */
  index: number
  document_id: number
  /** 文档文件名 */
  filename: string
  /** 页码；-1 表示该文档类型无页码（如 txt/docx） */
  page_number: number
  /** 片段在文档内的序号（retrieval_result 事件提供） */
  chunk_index?: number
  /** 检索相似度得分（retrieval_result 事件提供） */
  score?: number
  /** 片段原文（后端后续提供时用于来源展开，当前不返回） */
  quote?: string
}

/** 知识库问答 SSE 事件 */
export type KnowledgeChatEvent =
  | { type: 'start' }
  | { type: 'retrieval_start'; kbId: number }
  | { type: 'retrieval_result'; sources: KnowledgeSource[]; message?: string }
  | { type: 'text'; content: string }
  | {
    type: 'done'
    messageId: number
    conversationId: number
    sources?: KnowledgeSource[]
  }
  | { type: 'error'; message: string }

/**
 * 知识库问答：基于指定知识库检索文档片段，再交给 LLM 融合回答。
 *
 * @param kbId 知识库 ID（问答检索范围）
 * @param question 用户问题
 * @param conversationId 会话 ID；为空时后端会自动创建 knowledge 类型会话
 * @param options 流式中断/超时控制
 */
export async function* sendKnowledgeMessageStream(
  kbId: number,
  question: string,
  conversationId: number | null,
  options?: StreamOptions,
): AsyncGenerator<KnowledgeChatEvent, void, unknown> {
  const payload: Record<string, unknown> = { question }
  if (conversationId != null) payload.conversation_id = conversationId

  for await (const raw of stream(`/knowledge-bases/${kbId}/chat`, payload, options)) {
    try {
      const obj = JSON.parse(raw) as Record<string, unknown>
      const eventType = obj.type as string

      if (eventType === 'start') {
        yield { type: 'start' }
      } else if (eventType === 'retrieval_start') {
        yield { type: 'retrieval_start', kbId: Number(obj.kb_id) || kbId }
      } else if (eventType === 'retrieval_result') {
        yield {
          type: 'retrieval_result',
          sources: (obj.sources as KnowledgeSource[] | undefined) ?? [],
          message: obj.message as string | undefined,
        }
      } else if (eventType === 'text') {
        yield { type: 'text', content: (obj.content as string) ?? '' }
      } else if (eventType === 'done') {
        yield {
          type: 'done',
          messageId: Number(obj.message_id) || 0,
          conversationId: Number(obj.conversation_id) || conversationId || 0,
          sources: obj.sources as KnowledgeSource[] | undefined,
        }
      } else if (eventType === 'error') {
        yield { type: 'error', message: (obj.message as string) ?? '知识库问答失败' }
      }
    } catch {
      // 非 JSON 帧：按文本增量兜底，避免整条流因一帧解析失败而中断
      yield { type: 'text', content: raw }
    }
  }
}
