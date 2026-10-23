/**
 * 知识库相关接口（V0.3）
 * ===========================================================================
 * 接口契约（后端按此实现即可联调）：
 *   - listKnowledgeBases    → GET    /knowledge-bases           返回当前用户全部知识库
 *   - createKnowledgeBase   → POST   /knowledge-bases           { name, description }
 *   - updateKnowledgeBase   → PUT    /knowledge-bases/:id       { name, description }
 *   - deleteKnowledgeBase   → DELETE /knowledge-bases/:id
 *
 * 实体字段说明：
 *   doc_count   文档数量（仅统计索引成功的文档，失败/处理中不计入）
 *   chunk_count 可检索片段总数（仅统计索引已完成文档的片段）
 *   updated_at  最近一次变更（创建/重命名/文档增删/索引完成均会刷新）
 * ===========================================================================
 */
import { get, post, del, patch, upload, type UploadProgress } from '@/utils/request'

/** 知识库实体 */
export interface KnowledgeBase {
  id: number
  name: string
  description: string
  status: string
  user_id: number
  /** 文档数量 */
  doc_count: number
  /** 可检索片段总数 */
  chunk_count: number
  /** 绑定的问答会话 id（服务端持久化，重进问答页据此恢复历史） */
  conversation_id: number | null
  created_at: string
  updated_at: string
}

/** 创建/更新知识库的请求参数 */
export interface KnowledgeBasePayload {
  name: string
  description: string
}

// 知识库列表类型
export interface knowledgeBaseList {
  items: KnowledgeBase[],
  page:number,
  page_size: number,
  total: number
}


/** 获取当前用户的知识库列表（按 updated_at DESC） */
export function listKnowledgeBases() {
  return get<knowledgeBaseList>('/knowledge-bases')
}

/** 创建知识库 */
export function createKnowledgeBase(data: KnowledgeBasePayload) {
  return post<KnowledgeBase>('/knowledge-bases', { ...data })
}

/** 更新知识库（重命名/修改描述） */
export function updateKnowledgeBase(id: number, data: KnowledgeBasePayload) {
  return patch<KnowledgeBase>(`/knowledge-bases/${id}`, { ...data })
}

/** 删除知识库（级联删除其文档与索引数据） */
export function deleteKnowledgeBase(id: number) {
  return del(`/knowledge-bases/${id}`)
}

/* ===========================================================================
 * 详情页：知识库文档接口（V0.3）
 * ---------------------------------------------------------------------------
 * 接口契约（后端按此实现即可联调）：
 *   - getKnowledgeBase    → GET    /knowledge-bases/:id                        单个知识库详情
 *   - listKnowledgeDocs   → GET    /knowledge-bases/:id/documents              文档列表（created_at DESC）
 *   - uploadKnowledgeDoc  → POST   /knowledge-bases/:id/documents              multipart(file) 直传，入索引队列
 *   - deleteKnowledgeDoc  → DELETE /knowledge-bases/:id/documents/:docId       删文档及其索引片段
 *   - retryKnowledgeDoc   → POST   /knowledge-bases/:id/documents/:docId/retry 重新索引失败文档
 *
 * 文档索引状态机：pending（排队）→ processing（解析/分块/向量化）→ indexed | failed
 * =========================================================================== */

/** 文档索引状态 */
export type DocStatus = 'pending' | 'processing' | 'indexed' | 'failed'

/** 知识库文档实体 */
export interface KnowledgeDoc {
  id: number
  /** 文件名（含扩展名） */
  name: string
  /** 文件字节数 */
  size: number
  /** 扩展名（小写不含点）：pdf / docx / txt */
  ext: string
  status: DocStatus
  /** 可检索片段数（status=indexed 时有值，其余为 0） */
  chunk_count: number
  /** 失败原因（status=failed 时有值，需可读、面向用户） */
  error_msg?: string
  /** 处理进度百分比 0-100（status=processing 时可选；后端不返回则前端显示不定进度文案） */
  progress?: number
  created_at: string
}

/** 获取单个知识库详情（头卡信息 + 统计） */
export function getKnowledgeBase(id: number) {
  return get<KnowledgeBase>(`/knowledge-bases/${id}`)
}

/** 获取知识库文档列表 */
export function listKnowledgeDocs(kbId: number) {
  return get<KnowledgeDoc[]>(`/knowledge-bases/${kbId}/documents`)
}

/**
 * 上传文档到知识库：multipart 直传（复用 request.ts 的 upload 封装，
 * 自带 60s 超时与进度回调），成功后服务端将其置为 pending 进入索引队列。
 */
export function uploadKnowledgeDoc(
  kbId: number,
  file: File,
  onProgress?: (p: UploadProgress) => void,
) {
  return upload<KnowledgeDoc>(`/knowledge-bases/${kbId}/documents`, file, 'file', {
    onProgress,
    // 后端同步构建索引（模型加载+解析+向量化）可能超过默认 60s，单独放宽到 5 分钟
    config: { timeout: 300_000 },
  })
}

/** 删除文档（连同其索引片段） */
export function deleteKnowledgeDoc(docId: number) {
  return del(`/documents/${docId}`)
}

/** 重试索引失败的文档（成功后状态回到 processing） */
export function retryKnowledgeDoc(kbId: number, docId: number) {
  return post<KnowledgeDoc>(`/knowledge-bases/${kbId}/documents/${docId}/retry`)
}
