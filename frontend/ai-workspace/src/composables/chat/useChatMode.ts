import { ref, computed } from 'vue'
import {
  BarChart2,
  FileText,
  PieChart,
  Code,
  ClipboardList,
  Languages,
  FileSpreadsheet,
  Calculator,
  BarChart3,
} from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import type { ConversationType } from '@/api/conversation'
import type { Suggestion } from '@/components/chat/types'

/** 聊天视图模式：普通聊天 / Agent / 知识库问答 */
export type ChatMode = 'chat' | 'agent' | 'knowledge'

/** 各模式的欢迎态文案 */
const MODE_WELCOME: Record<ChatMode, { title: string; sub: string }> = {
  chat: {
    title: '你好！我是你的 AI 助手',
    sub: '你可以向我提问，或让我帮你完成各类任务',
  },
  agent: {
    title: '你好！我是你的 Agent 助手',
    sub: '上传文件、提出任务，我将调用工具帮你分析数据、生成图表和报告',
  },
  knowledge: {
    title: '基于知识库提问',
    sub: 'AI 将在已索引文档中检索相关片段后作答，回答会标注来源',
  },
}

/** 各模式输入框占位符 */
const MODE_PLACEHOLDER: Record<ChatMode, string> = {
  chat: '输入你的问题，或上传文件...',
  agent: '请输入你的问题，或上传文件让 Agent 帮你分析...',
  knowledge: '基于知识库提问，例如：分块策略是什么？',
}

/** 各模式建议卡数据 */
const MODE_SUGGESTIONS: Record<ChatMode, Suggestion[]> = {
  chat: [
    { title: '帮我分析这份Excel文件', desc: '数据分析 / 表格处理', icon: BarChart2, tint: 'primary' },
    { title: '写一份产品方案', desc: '文档写作 / 方案策划', icon: FileText, tint: 'success' },
    { title: '分析市场趋势', desc: '行业分析 / 竞品调研', icon: PieChart, tint: 'primary' },
    { title: '代码优化建议', desc: '编程辅助 / 代码审查', icon: Code, tint: 'success' },
    { title: '生成一份图表', desc: '数据可视化', icon: ClipboardList, tint: 'primary' },
    { title: '翻译中英文内容', desc: '语言翻译 / 润色优化', icon: Languages, tint: 'success' },
  ],
  agent: [
    { title: '分析 Excel 销售数据并生成报告', desc: '上传 Excel → 数据清洗 → 分析 → 报告', icon: FileSpreadsheet, tint: 'primary' },
    { title: '生成销售排名柱状图', desc: '数据可视化 / 图表生成', icon: BarChart3, tint: 'success' },
    { title: '计算数据汇总指标', desc: '求和 / 均值 / 占比 / 统计', icon: Calculator, tint: 'primary' },
    { title: '上传文件进行数据分析', desc: '文件解析 / 结构化输出', icon: FileText, tint: 'success' },
    { title: '生成市场调研报告', desc: '行业分析 / 竞品对比', icon: ClipboardList, tint: 'primary' },
    { title: '多步骤任务规划与执行', desc: '任务拆解 / 工具编排', icon: Code, tint: 'success' },
  ],
  knowledge: [
    { title: '文档分块的策略和参数是什么？', desc: '检索 · 分块策略', icon: FileText, tint: 'primary' },
    { title: '索引失败有哪些常见原因？', desc: '检索 · 索引排错', icon: ClipboardList, tint: 'success' },
    { title: '支持哪些文件格式与大小限制？', desc: '检索 · 文档规范', icon: FileSpreadsheet, tint: 'primary' },
    { title: '知识库问答的流程是怎样的？', desc: '检索 · 问答流程', icon: Code, tint: 'success' },
  ],
}

/**
 * 聊天模式相关状态：由视图显式传入 mode（ChatView / AgentView / KnowledgeView），
 * 提供该模式下的会话类型、欢迎文案、建议卡、占位符与 Agent 工具选择状态。
 */
export function useChatMode(mode: ChatMode) {
  const chatStore = useChatStore()

  /** 是否走 Agent 链路（仅 agent 模式；知识库问答走独立 RAG 端点，按普通气泡渲染） */
  const isAgentMode = computed(() => mode === 'agent')

  /** 当前模式对应的会话类型（新建会话时写入） */
  const currentType = computed<ConversationType>(() => mode)

  /** 当前会话的真实类型（无选中会话时回退到当前模式） */
  const sessionType = computed<ConversationType>(
    () => chatStore.currentSession?.type ?? mode,
  )

  const suggestions = computed(() => MODE_SUGGESTIONS[mode])
  const welcome = MODE_WELCOME[mode]
  const placeholder = MODE_PLACEHOLDER[mode]

  /* ---------------- 可用工具（Agent 模式） ---------------- */
  const availableTools = [
    { id: 'calculator', name: '计算器', desc: '数学计算', icon: Calculator },
    { id: 'analyze_excel', name: 'Excel 分析', desc: '数据表格分析', icon: FileSpreadsheet },
    { id: 'generate_chart', name: '图表生成', desc: '可视化图表', icon: BarChart3 },
  ]

  const selectedTools = ref<string[]>([])
  const toolPopoverOpen = ref(false)

  return {
    isAgentMode,
    currentType,
    sessionType,
    suggestions,
    welcome,
    placeholder,
    availableTools,
    selectedTools,
    toolPopoverOpen,
  }
}
