/**
 * Chat 模块共享类型（views/chat 三视图与 components/chat 区域组件共用）
 */
import type { Component } from 'vue'
import type { AgentStep, ToolInvocation } from './AgentMessageBubble.vue'
import type { KnowledgeSource } from '@/api/knowledgeChat'

/** 用户消息上的附件展示（id/名称/格式化后的大小文本） */
export interface MessageAttachment {
  id: number
  name: string
  size: string
}

/** 前端聊天消息（user / assistant 统一结构） */
export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  /** 流式生成中（打字机/工具运行态） */
  pending?: boolean
  /** 流式异常（断网/超时/HTTP错误）时的提示文案；有值时气泡下方渲染错误条 + 重试按钮 */
  error?: string
  /** Agent 执行步骤（Agent 模式） */
  steps?: AgentStep[]
  /** 工具调用卡片（Agent 模式） */
  tools?: ToolInvocation[]
  /** 知识库问答：检索命中的来源片段（回答正文 [1][2] 角标对应 index） */
  sources?: KnowledgeSource[]
  /** 知识库问答：正在检索文档片段（retrieval_start 后、首个 text 前） */
  retrieving?: boolean
  /** 附件（用户消息） */
  attachments?: MessageAttachment[]
}

/** 欢迎态建议卡 */
export interface Suggestion {
  title: string
  desc: string
  icon: Component
  tint: 'primary' | 'success'
}