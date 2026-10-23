/**
 * 知识库状态管理（Pinia Store）
 * ===========================================================================
 * 职责：
 *   集中管理"知识库列表"的加载与增删改，供知识库列表页消费。
 *   详情页（下期开发）将复用本 store 的 bases 缓存与 fetchAll 能力。
 *
 * 对接接口：
 *   - fetchAll  → GET    /knowledge-bases
 *   - create    → POST   /knowledge-bases
 *   - rename    → PUT    /knowledge-bases/:id
 *   - remove    → DELETE /knowledge-bases/:id
 *
 * 错误处理约定：
 *   网络错误统一由 axios 拦截器弹 ElMessage（见 request.ts），store 不重复提示；
 *   fetchAll 失败时静默回退为空列表（页面展示空状态，用户可重试），
 *   增删改失败时抛回调用方（页面据此保持弹窗开启，避免用户填写的表单丢失）。
 * ===========================================================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  listKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBase,
  listKnowledgeDocs,
  uploadKnowledgeDoc,
  deleteKnowledgeDoc,
  retryKnowledgeDoc,
  type knowledgeBaseList,
  type KnowledgeBase,
  type KnowledgeBasePayload,
  type KnowledgeDoc,
} from '@/api/knowledgeBase'
import type { UploadProgress } from '@/utils/request'

export const useKnowledgeBaseStore = defineStore('knowledgeBase', () => {
  // ---- 状态 ----
  /** 知识库列表（按 updated_at DESC） */
  const bases = ref<knowledgeBaseList>()
  /** 列表首次加载中 */
  const loading = ref(false)
  /** 增删改请求进行中（供弹窗按钮 loading、防重复提交） */
  const submitting = ref(false)

  // ---- 计算属性 ----
  /** 是否为空知识库（加载完成后无任何数据） */
  const isEmpty = computed(() => !loading.value && bases.value?.items.length === 0)

  // ---- 方法 ----

  /**
   * 拉取知识库列表。
   * 失败时静默回退为空列表：拦截器已 toast 错误，页面展示空状态即可；
   * 后端接口尚未上线（V0.3 联调前）也走这条路径，页面可正常浏览。
   */
  async function fetchAll() {
    loading.value = true
    try {
      bases.value = (await listKnowledgeBases()) ?? []
      console.log('bases',bases.value)
    } catch {
      bases.value = {
        items:[],
        page:1,
        page_size:10,
        total:0
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建知识库，成功后插入列表头部（新建的 updated_at 最新）。
   * @throws 失败原样抛出，页面保持弹窗开启并保留用户输入。
   */
  async function create(payload: KnowledgeBasePayload) {
    submitting.value = true
    try {
      const kb = await createKnowledgeBase(payload)
      bases.value?.items.unshift(kb)
      return kb
    } finally {
      submitting.value = false
    }
  }

  /**
   * 重命名/修改描述，成功后就地替换列表项。
   * @throws 失败原样抛出，页面保持弹窗开启并保留用户输入。
   */
  async function rename(id: number, payload: KnowledgeBasePayload) {
    submitting.value = true
    try {
      const kb = await updateKnowledgeBase(id, payload)
      console.log('kb',kb)
      if (bases.value) {
        const idx = bases.value.items.findIndex((b) => b.id === id)
        if (idx !== -1) {
          bases.value.items[idx] = kb
        }
      }
      return kb
    } finally {
      submitting.value = false
    }
  }

  /**
   * 删除知识库，成功后从列表移除。
   * 删除由页面 ElMessageBox 二次确认后才调用，无需重复确认。
   */
  async function remove(id: number) {
    submitting.value = true
    try {
      await deleteKnowledgeBase(id)
      if (bases.value) {
        bases.value.items = bases.value.items.filter((b) => b.id !== id)
      }
    } finally {
      submitting.value = false
    }
  }

  /** 按 id 查找知识库（详情页跳转回退时使用） */
  function getById(id: number) {
    return bases.value?.items.find((b) => b.id === id) ?? null
  }

  /* ======================================================================== */
  /*  详情页（V0.3）：当前知识库 + 文档列表 + 上传/删除/重试 + 索引状态轮询      */
  /* ======================================================================== */

  /** 当前知识库（详情页头卡数据来源；接口失败为 null，页面据此显示异常空态） */
  const current = ref<KnowledgeBase | null>(null)
  /** 当前知识库的文档列表（created_at DESC） */
  const docs = ref<KnowledgeDoc[]>([])
  /** 详情首次加载中 */
  const docsLoading = ref(false)
  /** 有文档正在上传（供上传区禁用重复选择） */
  const uploading = ref(false)

  /** 是否存在索引中的文档（pending/processing），存在则需要轮询 */
  function hasActiveDocs(): boolean {
    return docs.value.some((d) => d.status === 'pending' || d.status === 'processing')
  }

  /**
   * 文档列表归一化：后端可能返回纯数组或分页结构 { items: [...] }，
   * 统一转为数组，避免 docs 被赋成对象后 .some/.filter 等数组方法报错。
   */
  function normalizeDocs(list: KnowledgeDoc[] | { items?: KnowledgeDoc[] } | null | undefined): KnowledgeDoc[] {
    if (Array.isArray(list)) return list
    return Array.isArray(list?.items) ? list.items : []
  }

  /**
   * 加载详情：并行拉取知识库信息与文档列表。
   * 失败时回退为空（拦截器已 toast），页面显示"不存在或已删除"空态。
   */
  async function fetchDetail(id: number) {
    docsLoading.value = true
    try {
      const [kb, docList] = await Promise.all([getKnowledgeBase(id), listKnowledgeDocs(id)])
      current.value = kb
      docs.value = normalizeDocs(docList)
    } catch {
      current.value = null
      docs.value = []
    } finally {
      docsLoading.value = false
    }
  }

  /**
   * 静默刷新详情与文档列表（轮询专用）。
   * 同时刷新 kb 是为了让头卡的 doc_count / chunk_count 统计跟随索引进度更新。
   * 失败不处理：轮询下一轮会重试，不打扰用户。
   */
  async function refresh(id: number) {
    try {
      const [kb, docList] = await Promise.all([getKnowledgeBase(id), listKnowledgeDocs(id)])
      current.value = kb
      docs.value = normalizeDocs(docList)
    } catch {
      // 静默：轮询失败下轮重试
    }
  }

  /**
   * 上传文档（multipart 直传，带进度回调），成功后插入列表头部（最新）。
   * @throws 失败抛回页面，页面在上传进度条上标记失败并保留错误项。
   */
  async function uploadDoc(id: number, file: File, onProgress?: (p: UploadProgress) => void) {
    uploading.value = true
    try {
      const doc = await uploadKnowledgeDoc(id, file, onProgress)
      docs.value.unshift(doc)
      return doc
    } finally {
      uploading.value = false
    }
  }

  /** 删除文档，成功后就地从列表移除（页面已做二次确认） */
  async function removeDoc(docId: number) {
    await deleteKnowledgeDoc(docId)
    docs.value = docs.value.filter((d) => d.id !== docId)
  }

  /** 重试索引失败文档，成功后就地替换（状态回到 processing） */
  async function retryDoc(kbId: number, docId: number) {
    const doc = await retryKnowledgeDoc(kbId, docId)
    const idx = docs.value.findIndex((d) => d.id === docId)
    if (idx !== -1) docs.value[idx] = doc
    return doc
  }

  /* ---- 索引状态轮询 ------------------------------------------------------ */
  /**
   * 为什么轮询而不是 WebSocket/SSE：V0.3 索引为分钟级异步任务，轮询实现最简单、
   * 后端零改造成本；5s 间隔对服务端压力可忽略。后续量大可平滑升级 SSE。
   *
   * 自愈设计：每轮检查，一旦没有 pending/processing 文档（全部到达终态）自动停止；
   * startPolling 可重复调用（先清旧定时器），上传/重试后调用即"续期"。
   */
  const POLL_INTERVAL = 5_000
  let pollTimer: ReturnType<typeof setInterval> | undefined

  function startPolling(id: number) {
    if (!hasActiveDocs()) return // 没有索引中的文档，无需轮询
    stopPolling()
    pollTimer = setInterval(async () => {
      if (!hasActiveDocs()) {
        stopPolling()
        return
      }
      await refresh(id)
    }, POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = undefined
    }
  }

  return {
    bases,
    loading,
    submitting,
    isEmpty,
    fetchAll,
    create,
    rename,
    remove,
    getById,
    // 详情页
    current,
    docs,
    docsLoading,
    uploading,
    hasActiveDocs,
    fetchDetail,
    refresh,
    uploadDoc,
    removeDoc,
    retryDoc,
    startPolling,
    stopPolling,
  }
})
