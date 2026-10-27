import { ref } from 'vue'
import type { Ref } from 'vue'
import {
  sendMessageStream,
  sendAgentMessageStream,
} from '@/api/conversation'
import { sendKnowledgeMessageStream } from '@/api/knowledgeChat'
import { StreamError } from '@/utils/request'
import type { ChatMessage } from '@/components/chat/types'
import type { ChatMode } from './useChatMode'

/**
 * 流式回复：普通 Chat / Agent / 知识库问答三条链路，统一管理 loading / 中断状态，
 * 以及断网 / 流中断 / 超时 / HTTP 错误的异常收尾。
 */
export function useStreamReply(opts: {
  messages: Ref<ChatMessage[]>
  uid: () => number
  now: () => string
  scrollToBottom: () => void
  /** 当前视图模式（决定调用哪条流式接口） */
  mode: ChatMode
  selectedTools: Ref<string[]>
  /** 知识库问答：当前检索范围（knowledge 视图提供，其余模式返回 null） */
  knowledgeBaseId?: () => number | null
  /** 知识库问答：后端在首次提问时创建会话，通过 done 事件回传 id */
  onKnowledgeConversation?: (id: number) => void
  /** Agent 模式：当前绑定的知识库 id（Agent 视图提供，随消息发送供 knowledge_search 检索） */
  agentKnowledgeBaseId?: () => number | null
}) {
  const {
    messages,
    uid,
    now,
    scrollToBottom,
    mode,
    selectedTools,
    knowledgeBaseId,
    onKnowledgeConversation,
    agentKnowledgeBaseId,
  } = opts

  /** 是否走 Agent 链路（仅 agent 模式；知识库问答走独立 RAG 端点） */
  const isAgentMode = mode === 'agent'

  const loading = ref(false)
  const cancelled = ref(false)
  /** 当前流式请求的 AbortController，停止按钮用它中断流 */
  let abortCtrl: AbortController | null = null

  /** 停止当前流式生成（输入栏停止按钮回调） */
  function stop() {
    cancelled.value = true
    abortCtrl?.abort()
  }

  /**
   * 流式回复：根据模式分流到普通 Chat / Agent / 知识库问答。
   * conversationId 为 null 仅允许出现在知识库问答首次提问（由后端创建会话）。
   */
  async function runReply(
    conversationId: number | null,
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
      ...(mode === 'agent' ? { steps: [], tools: [] } : {}),
      // 知识库问答：进入检索阶段
      ...(mode === 'knowledge' ? { retrieving: true } : {}),
    }
    messages.value.push(placeholder)
    const idx = messages.value.length - 1
    scrollToBottom()

    abortCtrl = new AbortController()

    if (mode === 'knowledge') {
      await runKnowledgeReply(conversationId, userText, idx)
    } else if (conversationId == null) {
      // 非知识库模式必须已有会话（onSend 负责创建），兜底避免以空 id 发请求
      const msg = messages.value[idx]
      msg.pending = false
      msg.error = '会话已失效，请重新选择会话'
      loading.value = false
      abortCtrl = null
    } else if (isAgentMode) {
      await runAgentReply(conversationId, userText, fileIds, idx)
    } else {
      await runChatReply(conversationId, userText, idx)
    }
  }

  /**
   * 流式异常 → 用户可读文案。
   * StreamError（断网/流中断/超时/HTTP错误）自带针对性 message；
   * 其他未知异常统一兜底，避免把技术性错误信息直接抛给用户。
   */
  function streamErrorMessage(err: unknown): string {
    return err instanceof StreamError ? err.message : '请求失败，请重试'
  }

  /** Agent 消息收尾：运行中的步骤标记 done、工具卡片标记指定终态（success/stopped） */
  function finalizeAgentMessage(msg: ChatMessage, toolStatus: 'success' | 'stopped') {
    if (msg.steps) {
      msg.steps.forEach((s) => {
        if (s.status === 'running') s.status = 'done'
      })
    }
    if (msg.tools) {
      msg.tools.forEach((t) => {
        if (t.status === 'running') t.status = toolStatus
      })
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
      const msg = messages.value[idx]
      msg.pending = false
      msg.time = now()
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 用户主动中断：保留已接收内容（空内容时模板显示"已停止生成"）
      } else {
        // 断网/流中断/超时/HTTP错误：保留已接收的部分内容，标记错误供错误条展示
        msg.error = streamErrorMessage(err)
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
    // Agent 绑定的知识库：服务端校验归属后注入 AgentContext（kb_id 对 LLM 不可见）
    // 显式携带当前状态（含 null=解绑），服务端按会话持久化绑定
    const kbId = agentKnowledgeBaseId?.() ?? null

    try {
      for await (const evt of sendAgentMessageStream(
        conversationId,
        userText,
        {
          fileIds: fileIds.length ? fileIds : undefined,
          tools,
          kbId,
        },
        { signal: abortCtrl?.signal },
      )) {
        if (cancelled.value) break
        const msg = messages.value[idx]

        switch (evt.type) {
          case 'agent_start':
            // Agent 开始，可以添加一个初始"理解任务"步骤
            if (msg.steps) {
              msg.steps.push({ id: uid(), label: '思考任务', status: 'running' })
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
        finalizeAgentMessage(msg, 'success')
      }
    } catch (err) {
      const msg = messages.value[idx]
      msg.pending = false
      msg.time = now()
      // 中断/异常都要把运行中的步骤与工具收尾，避免卡片一直转圈
      finalizeAgentMessage(msg, 'stopped')
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 用户主动中断：保留已接收内容
      } else {
        // 断网/流中断/超时/HTTP错误：保留已接收内容，标记错误供错误条展示
        msg.error = streamErrorMessage(err)
      }
    } finally {
      loading.value = false
      abortCtrl = null
    }
  }

  /**
   * 知识库问答流式回复：
   * start → retrieval_start → retrieval_result → text(多次) → done
   */
  async function runKnowledgeReply(
    conversationId: number | null,
    question: string,
    idx: number,
  ) {
    const kbId = knowledgeBaseId?.() ?? null
    if (kbId == null) {
      const msg = messages.value[idx]
      msg.pending = false
      msg.retrieving = false
      msg.error = '未选择知识库，无法进行问答'
      loading.value = false
      abortCtrl = null
      return
    }

    try {
      for await (const evt of sendKnowledgeMessageStream(
        kbId,
        question,
        conversationId,
        { signal: abortCtrl?.signal },
      )) {
        if (cancelled.value) break
        const msg = messages.value[idx]

        switch (evt.type) {
          case 'start':
            break

          case 'retrieval_start':
            msg.retrieving = true
            break

          case 'retrieval_result':
            // 检索完成：记录来源（可能为空，表示知识库中没有相关资料）
            msg.retrieving = false
            msg.sources = evt.sources
            break

          case 'text':
            // 首个增量到达，结束检索态，进入边生成边渲染
            msg.retrieving = false
            msg.content += evt.content
            break

          case 'done':
            msg.pending = false
            msg.retrieving = false
            msg.time = now()
            if (evt.messageId) msg.id = evt.messageId
            // 首次提问由后端创建会话：回传 id 供后续消息复用
            if (evt.conversationId) onKnowledgeConversation?.(evt.conversationId)
            // done 的 sources 只有 4 个字段（无 chunk_index/score），
            // 仅在 retrieval_result 没拿到来源时兜底，避免覆盖更完整的来源信息
            if (!msg.sources?.length && evt.sources?.length) msg.sources = evt.sources
            break

          case 'error':
            // 后端业务级错误（检索失败/AI 服务失败）：保留已有内容并展示错误条
            msg.error = evt.message
            break
        }
        scrollToBottom()
      }

      // 流结束：收尾（正常 done 已在事件里处理，这里兜底未收到 done 的情况）
      const msg = messages.value[idx]
      msg.pending = false
      msg.retrieving = false
      if (!msg.error) msg.time = now()
    } catch (err) {
      const msg = messages.value[idx]
      msg.pending = false
      msg.retrieving = false
      msg.time = now()
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 用户主动中断：保留已接收内容
      } else {
        // 断网/流中断/超时/HTTP错误：保留已接收内容，标记错误供错误条展示
        msg.error = streamErrorMessage(err)
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
      knowledge_search: '检索知识库',
    }
    return map[tool] ?? tool
  }

  return { loading, stop, runReply }
}