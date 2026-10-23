<template>
  <div
    v-loading="kbStore.docsLoading"
    class="kb-detail"
  >
    <!-- ============ 返回列表 ============ -->
    <div class="back-row">
      <a
        class="back-btn"
        @click="router.push('/knowledge')"
      >
        <ArrowLeft class="w-[15px] h-[15px]" />
        返回知识库
      </a>
    </div>

    <!-- ============ 加载失败 / 知识库不存在空态 ============ -->
    <div
      v-if="!kbStore.current && !kbStore.docsLoading"
      class="notfound-state"
    >
      <AlertCircle class="w-10 h-10" />
      <p>知识库不存在或已被删除</p>
      <button
        type="button"
        class="btn-ghost"
        @click="router.push('/knowledge')"
      >
        返回列表
      </button>
    </div>

    <template v-if="kbStore.current">
      <!-- ============ 知识库信息头卡 ============ -->
      <section class="kb-header">
        <div class="kb-icon-lg">
          <BookOpen class="w-7 h-7" />
        </div>
        <div class="kb-info">
          <h1>{{ kbStore.current.name }}</h1>
          <p class="kb-desc">
            {{ kbStore.current.description || '暂无描述' }}
          </p>
          <div class="kb-stats">
            <span class="kb-stat">
              <FileText class="w-[13px] h-[13px]" />
              <b>{{ kbStore.current.doc_count }}</b>份文档
            </span>
            <span class="kb-stat-sep" />
            <span class="kb-stat">
              <Layers class="w-[13px] h-[13px]" />
              <b>{{ kbStore.current.chunk_count }}</b>个可检索片段
            </span>
            <span class="kb-stat-sep" />
            <span class="kb-stat">
              <Clock class="w-[13px] h-[13px]" />
              更新于 {{ formatDateTime(kbStore.current.updated_at) }}
            </span>
          </div>
        </div>
        <div class="kb-actions">
          <button
            type="button"
            class="btn-primary"
            @click="enterChat"
          >
            <MessageSquare class="w-4 h-4" />
            进入问答
          </button>
          <button
            type="button"
            class="icon-btn-border"
            title="重命名"
            @click="openRename()"
          >
            <Pencil class="w-4 h-4" />
          </button>
          <button
            type="button"
            class="icon-btn-border danger"
            title="删除知识库"
            @click="confirmRemoveKb()"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </section>

      <!-- ============ 上传区：点击 + 拖拽 ============ -->
      <div
        class="upload-zone"
        :class="{ 'is-empty': !kbStore.docs.length, 'is-dragover': dragover }"
        @click="openPicker()"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="onDrop"
      >
        <!-- 阻止点击冒泡：上传中列表的移除按钮不触发选文件 -->
        <input
          ref="fileInputRef"
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.txt"
          @change="onFileChange"
        >
        <div class="upload-icon">
          <CloudUpload class="w-6 h-6" />
        </div>
        <div class="upload-title">
          {{ kbStore.docs.length ? '点击或拖拽文件到此处上传' : '上传第一份文档，开始构建知识库' }}
        </div>
        <div class="upload-sub">
          支持 <b>PDF / DOCX / TXT</b> 格式，单文件不超过 20MB；上传后自动解析并建立索引
        </div>
      </div>

      <!-- ============ 上传中进度列表（本地状态，不入 store） ============ -->
      <div
        v-if="uploadingFiles.length"
        class="uploading-list"
      >
        <div
          v-for="u in uploadingFiles"
          :key="u.uid"
          class="uploading-row"
          :class="{ 'is-error': u.error }"
        >
          <FileText class="w-4 h-4 shrink-0" />
          <span class="uploading-name">{{ u.name }}</span>
          <div class="progress">
            <div
              class="progress-bar"
              :style="{ width: u.percent + '%' }"
            />
          </div>
          <span class="uploading-meta">
            <template v-if="u.error">上传失败</template>
            <template v-else>{{ u.percent }}%</template>
          </span>
          <button
            type="button"
            class="uploading-remove"
            title="移除"
            @click="removeUploading(u.uid)"
          >
            <X class="w-3 h-3" />
          </button>
        </div>
      </div>

      <!-- ============ 文档列表（四态） ============ -->
      <section
        v-if="kbStore.docs.length"
        class="doc-panel"
      >
        <div class="doc-panel-head">
          <h2 class="doc-panel-title">
            <FileText class="w-[17px] h-[17px]" />
            文档列表
          </h2>
          <div class="doc-panel-side">
            <span class="doc-count">共 {{ kbStore.docs.length }} 份</span>
            <span class="doc-tip">
              <Info class="w-3 h-3" />
              仅"已完成"索引的文档参与问答检索
            </span>
          </div>
        </div>

        <el-table
          :data="kbStore.docs"
          row-key="id"
          class="doc-table"
        >
          <!-- 文件名 + 大小 -->
          <el-table-column
            label="文件"
            min-width="240"
          >
            <template #default="{ row }">
              <div class="doc-file">
                <div
                  class="ext-badge"
                  :class="extClass(row.ext)"
                >
                  <FileText class="w-[17px] h-[17px]" />
                </div>
                <div class="doc-file-info">
                  <div class="doc-name">{{ row.filename }}</div>
                  <div class="doc-size">{{ formatSize(row.size) }}</div>
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- 索引状态 tag + 附加信息 -->
          <el-table-column
            label="索引状态"
            width="210"
          >
            <template #default="{ row }">
              <span
                class="tag"
                :class="{
                  'tag-pending': row.status === 'pending',
                  'tag-processing': row.status === 'processing',
                  'tag-indexed': row.status === 'indexed',
                  'tag-failed': row.status === 'failed',
                }"
              >
                <Loader
                  v-if="row.status === 'processing'"
                  class="w-3 h-3 spin"
                />
                <CheckCircle
                  v-else-if="row.status === 'indexed'"
                  class="w-3 h-3"
                />
                <AlertCircle
                  v-else-if="row.status === 'failed'"
                  class="w-3 h-3"
                />
                <Clock
                  v-else
                  class="w-3 h-3"
                />
                {{ statusText(row.status) }}
              </span>
              <div
                v-if="row.status === 'pending'"
                class="tag-note"
              >
                排队等待索引
              </div>
              <!-- processing：进度条 -->
              <div
                v-if="row.status === 'processing'"
                class="proc-cell"
              >
                <div class="progress">
                  <div
                    class="progress-bar"
                    :style="{ width: (row.progress ?? 0) + '%' }"
                  />
                </div>
                <span class="progress-text">
                  {{ row.progress != null ? `正在处理 ${row.progress}%` : '正在解析并建立索引...' }}
                </span>
              </div>
              <!-- failed：错误摘要 -->
              <div
                v-if="row.status === 'failed'"
                class="doc-sub-error"
              >
                <AlertCircle class="w-3.5 h-3.5 shrink-0" />
                <span class="msg">索引失败：{{ row.error_msg || '未知原因，请重试或重新上传' }}</span>
              </div>
            </template>
          </el-table-column>

          <!-- 片段数：仅已完成有值 -->
          <el-table-column
            label="片段数"
            width="120"
            align="center"
          >
            <template #default="{ row }">
              <span
                class="doc-chunks"
                :class="{ 'is-muted': row.status !== 'indexed' }"
              >
                <template v-if="row.status === 'indexed'">
                  {{ row.chunk_count }} <span class="unit">个</span>
                </template>
                <template v-else>--</template>
              </span>
            </template>
          </el-table-column>

          <el-table-column
            label="上传时间"
            width="150"
          >
            <template #default="{ row }">
              <span class="doc-time">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>

          <!-- 操作：失败行有重试，全部可删除 -->
          <el-table-column
            label="操作"
            width="110"
            align="center"
          >
            <template #default="{ row }">
              <div class="doc-ops">
                <button
                  v-if="row.status === 'failed'"
                  type="button"
                  class="op-btn retry"
                  title="重新索引"
                  @click="onRetry(row)"
                >
                  <RefreshCw class="w-[13px] h-[13px]" />
                  重试
                </button>
                <button
                  type="button"
                  class="op-btn danger"
                  title="删除"
                  @click="confirmRemoveDoc(row)"
                >
                  <Trash2 class="w-[13px] h-[13px]" />
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <!-- ============ 空知识库：索引流水线示意 ============ -->
      <div
        v-else-if="!kbStore.docsLoading && !uploadingFiles.length"
        class="pipeline"
      >
        <div class="pipe-step">
          <span class="pipe-dot"><CloudUpload class="w-4 h-4" /></span>
          <span class="pipe-label">上传文件</span>
        </div>
        <span class="pipe-arrow"><ChevronsRight class="w-4 h-4" /></span>
        <div class="pipe-step">
          <span class="pipe-dot"><FileSearch class="w-4 h-4" /></span>
          <span class="pipe-label">文本解析</span>
        </div>
        <span class="pipe-arrow"><ChevronsRight class="w-4 h-4" /></span>
        <div class="pipe-step">
          <span class="pipe-dot"><Scissors class="w-4 h-4" /></span>
          <span class="pipe-label">智能分块</span>
        </div>
        <span class="pipe-arrow"><ChevronsRight class="w-4 h-4" /></span>
        <div class="pipe-step">
          <span class="pipe-dot"><Database class="w-4 h-4" /></span>
          <span class="pipe-label">向量化索引</span>
        </div>
      </div>
      <p
        v-if="!kbStore.docs.length && !kbStore.docsLoading"
        class="empty-doc-hint"
      >
        索引完成后即可进入问答，AI 将基于资料内容作答并标注来源出处
      </p>
    </template>

    <!-- ============ 重命名弹窗（与列表页同款自绘样式） ============ -->
    <Teleport to="body">
      <Transition name="dialog-fade">
        <div
          v-if="renameVisible"
          class="kb-dialog-overlay"
          @click.self="closeRename()"
        >
          <div class="kb-dialog">
            <div class="kb-dialog-header">
              <h3 class="kb-dialog-title">
                重命名知识库
              </h3>
              <button
                type="button"
                class="kb-dialog-close"
                @click="closeRename()"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
            <div class="kb-dialog-body">
              <label class="kb-form-label">
                知识库名称
                <span class="required">*</span>
              </label>
              <input
                v-model="renameForm.name"
                type="text"
                class="kb-form-input"
                placeholder="例如：产品设计规范"
                maxlength="50"
              >
              <label class="kb-form-label">描述</label>
              <textarea
                v-model="renameForm.description"
                rows="3"
                class="kb-form-textarea"
                placeholder="简要描述知识库的用途与内容范围（可选）"
                maxlength="200"
              />
            </div>
            <div class="kb-dialog-footer">
              <button
                type="button"
                class="btn-ghost"
                @click="closeRename()"
              >
                取消
              </button>
              <button
                type="button"
                class="btn-primary"
                :disabled="kbStore.submitting"
                @click="submitRename()"
              >
                {{ kbStore.submitting ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
/**
 * 知识库详情页（V0.3）
 * ===========================================================================
 * 还原 design/knowledge-base-detail.html 设计稿，覆盖：
 *   - 信息头卡：名称/描述/统计（文档数/片段数/更新时间）+ 进入问答 + 重命名/删除
 *   - 上传区：点击选择 + 拖拽，前端校验（格式 PDF/DOCX/TXT、大小 ≤20MB），
 *     上传中逐文件显示进度条（本地状态），失败保留可移除
 *   - 文档列表四态：待处理（排队）/ 处理中（进度条）/ 已完成（片段数）/ 失败（错误摘要+重试）
 *   - 空知识库：上传区放大 + 索引流水线示意（上传→解析→分块→向量化）
 *   - 索引状态轮询：存在 pending/processing 文档时每 5s 静默刷新（store 管理，自停）
 *
 * 轮询触发点：进页加载后 / 每次上传成功 / 重试成功；页面卸载统一 stopPolling。
 * ===========================================================================
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  ArrowLeft,
  BookOpen,
  MessageSquare,
  Pencil,
  Trash2,
  FileText,
  Layers,
  Clock,
  CloudUpload,
  X,
  Info,
  Loader,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  FileSearch,
  Scissors,
  Database,
  ChevronsRight,
} from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import type { KnowledgeDoc } from '@/api/knowledgeBase'

// 多词组件名：满足 vue/multi-word-component-names，且便于 keep-alive / devtools 识别
defineOptions({ name: 'KnowledgeBaseDetail' })

const route = useRoute()
const router = useRouter()
const kbStore = useKnowledgeBaseStore()

/** 路由参数中的知识库 id（组件内多处使用，解析一次） */
const kbId = computed(() => Number(route.params.id))

/* -------------------------------------------------------------------------- */
/*  展示辅助：状态文案 / 扩展名配色 / 格式化                                    */
/* -------------------------------------------------------------------------- */
const STATUS_TEXT: Record<KnowledgeDoc['status'], string> = {
  pending: '待处理',
  processing: '处理中',
  indexed: '已完成',
  failed: '失败',
}

function statusText(status: KnowledgeDoc['status']): string {
  return STATUS_TEXT[status] ?? status
}

/** 扩展名徽标配色：pdf 红 / docx 蓝 / 其余灰 */
function extClass(ext: string): string {
  if (ext === 'pdf') return 'ext-pdf'
  if (ext === 'docx') return 'ext-docx'
  return 'ext-txt'
}

/** 时间格式化：YYYY-MM-DD HH:mm */
function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '--'
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`
  )
}

/** 文件大小格式化：B / KB / MB */
function formatSize(bytes: number): string {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

/* -------------------------------------------------------------------------- */
/*  文件上传：选择 / 拖拽 / 校验 / 逐个上传（进度为页面本地状态）                */
/* -------------------------------------------------------------------------- */
const fileInputRef = ref<HTMLInputElement | null>(null)
const dragover = ref(false)

/** 上传中的进度项（本地状态：上传完成即移除，失败保留供用户查看/移除） */
interface UploadingItem {
  uid: number
  name: string
  percent: number
  error: boolean
}
const uploadingFiles = ref<UploadingItem[]>([])
let uidSeq = 0

function openPicker() {
  if (kbStore.uploading) return // 上传中不允许重复选文件
  fileInputRef.value?.click()
}

/** 文件选择回调 */
function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files) handleFiles(Array.from(target.files))
  target.value = '' // 允许重复选择同一文件
}

/** 拖拽释放回调 */
function onDrop(e: DragEvent) {
  dragover.value = false
  const files = e.dataTransfer?.files
  if (files) handleFiles(Array.from(files))
}

/** 移除一条上传进度项（失败项的手动移除入口） */
function removeUploading(uid: number) {
  uploadingFiles.value = uploadingFiles.value.filter((u) => u.uid !== uid)
}

/**
 * 逐个上传（串行：避免并发请求争抢上传通道，且进度条逐条推进更直观）。
 * 前端校验：扩展名白名单 + 20MB 上限；校验失败直接 toast 跳过该文件。
 */
async function handleFiles(files: File[]) {
  for (const f of files) {
    const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      ElMessage.error(`「${f.name}」格式不支持，仅支持 PDF / DOCX / TXT`)
      continue
    }
    if (f.size > 20 * 1024 * 1024) {
      ElMessage.error(`「${f.name}」超过 20MB 限制`)
      continue
    }

    const uid = ++uidSeq
    const item = reactive<UploadingItem>({ uid, name: f.name, percent: 0, error: false })
    uploadingFiles.value.push(item)
    try {
      await kbStore.uploadDoc(kbId.value, f, (p) => {
        item.percent = p.percent
      })
      // 成功：文档已由 store 插入列表顶部，进度项短暂展示后移除
      ElMessage.success(`「${f.name}」上传成功，已进入索引队列`)
      removeUploading(uid)
      kbStore.startPolling(kbId.value) // 有新文档进入队列，启动/续期轮询
    } catch {
      item.error = true // 失败：保留进度项并标红，用户可移除后重试
    }
  }
}

/* -------------------------------------------------------------------------- */
/*  文档操作：删除（二次确认）/ 重试索引                                        */
/* -------------------------------------------------------------------------- */
async function confirmRemoveDoc(doc: KnowledgeDoc) {
  try {
    await ElMessageBox.confirm(
      `删除后「${doc.filename}」及其 ${doc.status === 'indexed' ? `${doc.chunk_count} 个索引片段` : '索引数据'}将一并删除。`,
      '删除文档',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return // 用户点取消
  }
  try {
    await kbStore.removeDoc(doc.id)
    ElMessage.success('已删除')
  } catch {
    // 网络错误已由拦截器 toast
  }
}

/** 重试索引失败的文档：成功后状态回 processing，续期轮询 */
async function onRetry(doc: KnowledgeDoc) {
  try {
    await kbStore.retryDoc(kbId.value, doc.id)
    ElMessage.success(`已重新开始索引「${doc.name}」`)
    kbStore.startPolling(kbId.value)
  } catch {
    // 网络错误已由拦截器 toast
  }
}

/* -------------------------------------------------------------------------- */
/*  知识库级操作：进入问答 / 重命名 / 删除                                      */
/* -------------------------------------------------------------------------- */
/**
 * 进入问答：跳转知识库问答页，并通过 ?kb= 携带当前知识库 id，
 * 问答页据此限定检索范围并展示知识库上下文头卡。
 */
function enterChat() {
  router.push({ path: '/knowledge/chat', query: { kb: String(kbId.value) } })
}

const renameVisible = ref(false)
const renameForm = reactive({ name: '', description: '' })

function openRename() {
  renameForm.name = kbStore.current?.name ?? ''
  renameForm.description = kbStore.current?.description ?? ''
  renameVisible.value = true
}

function closeRename() {
  renameVisible.value = false
}

async function submitRename() {
  const name = renameForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    const kb = await kbStore.rename(kbId.value, {
      name,
      description: renameForm.description.trim(),
    })
    kbStore.current = kb // 就地更新头卡
    ElMessage.success('已保存')
    closeRename()
  } catch {
    // 失败保持弹窗开启，保留用户输入
  }
}

/** 删除整个知识库：二次确认后删除并返回列表 */
async function confirmRemoveKb() {
  const kb = kbStore.current
  if (!kb) return
  try {
    await ElMessageBox.confirm(
      `删除后「${kb.name}」中的 ${kb.doc_count} 份文档及索引数据将一并删除，且无法恢复。`,
      '删除知识库',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return // 用户点取消
  }
  try {
    await kbStore.remove(kb.id)
    ElMessage.success('已删除')
    router.replace('/knowledge')
  } catch {
    // 网络错误已由拦截器 toast
  }
}

/* -------------------------------------------------------------------------- */
/*  生命周期：加载详情 + 按需轮询；卸载时停轮询                                  */
/* -------------------------------------------------------------------------- */
onMounted(async () => {
  await kbStore.fetchDetail(kbId.value)
  kbStore.startPolling(kbId.value) // 进页时已有索引中的文档（如别处上传后切进来）则续期轮询
})

onBeforeUnmount(() => {
  kbStore.stopPolling()
})
</script>

<style scoped>
/* ---------- 返回 ---------- */
.back-row {
  margin-bottom: 16px;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  padding: 6px 10px;
  border-radius: var(--aws-radius-md);
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}
.back-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}

/* ---------- 不存在空态 ---------- */
.notfound-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 72px 24px;
  color: var(--aws-muted);
  background: var(--aws-card);
  border: 1px dashed var(--aws-border-strong);
  border-radius: var(--aws-radius-xl);
}

/* ---------- 信息头卡 ---------- */
.kb-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-xl);
  box-shadow: var(--aws-shadow-card);
}
.kb-icon-lg {
  width: 56px;
  height: 56px;
  border-radius: var(--aws-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  background: color-mix(in srgb, var(--aws-primary) 10%, #ffffff);
  color: var(--aws-primary);
}
.kb-info {
  flex: 1;
  min-width: 0;
}
.kb-info h1 {
  font-size: var(--aws-text-xl);
  font-weight: var(--aws-weight-semibold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-desc {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  margin-top: 4px;
  line-height: var(--aws-leading-relaxed);
}
.kb-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.kb-stat {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.kb-stat b {
  font-size: var(--aws-text-base);
  color: var(--aws-foreground);
  font-weight: var(--aws-weight-semibold);
  margin-right: 2px;
}
.kb-stat-sep {
  width: 1px;
  height: 12px;
  background: var(--aws-divider);
}
.kb-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

/* ---------- 按钮 ---------- */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 16px;
  border-radius: var(--aws-radius-md);
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  transition: background-color 0.15s;
  flex: none;
  cursor: pointer;
  border: none;
}
.btn-primary:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 16px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border);
  background: var(--aws-card);
  color: var(--aws-foreground);
  font-size: var(--aws-text-sm);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-ghost:hover {
  border-color: var(--aws-primary);
  color: var(--aws-primary);
}
.icon-btn-border {
  width: 38px;
  height: 38px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border);
  background: var(--aws-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.icon-btn-border:hover {
  border-color: var(--aws-primary);
  color: var(--aws-primary);
}
.icon-btn-border.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
}

/* ---------- 上传区 ---------- */
.upload-zone {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 24px;
  border: 1.5px dashed var(--aws-border-strong);
  border-radius: var(--aws-radius-xl);
  background: var(--aws-card);
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 3%, var(--aws-card));
}
.upload-zone.is-empty {
  padding: 48px 24px;
}
.upload-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--aws-primary) 10%, #ffffff);
  color: var(--aws-primary);
  margin-bottom: 12px;
}
.upload-title {
  font-size: var(--aws-text-base);
  font-weight: var(--aws-weight-medium);
}
.upload-zone.is-empty .upload-title {
  font-size: var(--aws-text-lg);
}
.upload-sub {
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
  margin-top: 6px;
}
.upload-sub b {
  color: var(--aws-muted);
  font-weight: var(--aws-weight-medium);
}

/* ---------- 上传进度列表 ---------- */
.uploading-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.uploading-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-md);
  color: var(--aws-muted);
}
.uploading-row.is-error {
  border-color: #fecaca;
  color: #ef4444;
}
.uploading-name {
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uploading-meta {
  font-size: var(--aws-text-xs);
  flex: none;
  min-width: 52px;
  text-align: right;
}
.uploading-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  cursor: pointer;
  flex: none;
}
.uploading-remove:hover {
  color: var(--aws-primary);
}
.uploading-row.is-error .uploading-remove:hover {
  color: #ef4444;
}

/* ---------- 通用进度条（上传中 / 处理中） ---------- */
.progress {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: var(--aws-border);
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: var(--aws-primary);
  position: relative;
  overflow: hidden;
  transition: width 0.3s ease;
}
.proc-cell .progress-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.45), transparent);
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

/* ---------- 文档列表 ---------- */
.doc-panel {
  margin-top: 16px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-xl);
  box-shadow: var(--aws-shadow-card);
  overflow: hidden;
}
.doc-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--aws-divider);
}
.doc-panel-title {
  font-size: var(--aws-text-lg);
  font-weight: var(--aws-weight-semibold);
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-panel-title svg {
  color: var(--aws-primary);
}
.doc-panel-side {
  display: flex;
  align-items: center;
  gap: 10px;
}
.doc-count {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.doc-tip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  background: var(--aws-sidebar);
  border: 1px solid var(--aws-border);
  border-radius: 999px;
  padding: 4px 10px;
}

/* 文档列表表格：el-table 主题适配（沿用面板配色） */
.doc-table {
  --el-table-border-color: var(--aws-divider);
  --el-table-header-bg-color: #fafbfc;
  --el-table-header-text-color: var(--aws-placeholder);
  --el-table-row-hover-bg-color: var(--aws-sidebar-active);
  --el-table-text-color: var(--aws-foreground);
  --el-table-bg-color: var(--aws-card);
  --el-table-tr-bg-color: var(--aws-card);
  font-size: var(--aws-text-base);
}
.doc-table :deep(.el-table__cell) {
  padding: 5px 16px;
}
.doc-table :deep(.el-table__header-wrapper .el-table__cell) {
  font-weight: var(--aws-weight-medium);
  font-size: var(--aws-text-xs);
}
.doc-file {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.doc-file-info {
  min-width: 0;
}
.ext-badge {
  width: 36px;
  height: 36px;
  border-radius: var(--aws-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.ext-pdf {
  background: color-mix(in srgb, #ef4444 10%, #ffffff);
  color: #dc2626;
}
.ext-docx {
  background: color-mix(in srgb, #3b82f6 10%, #ffffff);
  color: #2563eb;
}
.ext-txt {
  background: color-mix(in srgb, #6b7280 10%, #ffffff);
  color: #4b5563;
}
.doc-name {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-size {
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
  margin-top: 2px;
}

/* 状态标签 */
.tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
}
.tag-pending {
  background: #f3f4f6;
  color: #6b7280;
}
.tag-processing {
  background: color-mix(in srgb, var(--aws-primary) 10%, #ffffff);
  color: #2563eb;
}
.tag-indexed {
  background: color-mix(in srgb, var(--aws-success) 10%, #ffffff);
  color: #059669;
}
.tag-failed {
  background: #fef2f2;
  color: #ef4444;
}
.tag-note {
  font-size: 11px;
  color: var(--aws-placeholder);
  margin-top: 4px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.doc-chunks {
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  font-weight: var(--aws-weight-medium);
}
.doc-chunks.is-muted {
  color: var(--aws-placeholder);
}
.doc-chunks .unit {
  font-weight: 400;
  color: var(--aws-placeholder);
  font-size: var(--aws-text-xs);
}
.doc-time {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.doc-ops {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: center;
}
.op-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  border-radius: var(--aws-radius-sm);
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  cursor: pointer;
  background: none;
  border: none;
  transition: background-color 0.15s, color 0.15s;
}
.op-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}
.op-btn.danger:hover {
  background: #fef2f2;
  color: #ef4444;
}
.op-btn.retry {
  color: #2563eb;
}
.op-btn.retry:hover {
  background: color-mix(in srgb, var(--aws-primary) 10%, #ffffff);
}

/* 处理中：状态列内进度条 */
.proc-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}
.progress-text {
  font-size: 11px;
  color: var(--aws-muted);
  flex: none;
}

/* 失败：状态列内错误摘要（重试入口在操作列） */
.doc-sub-error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: var(--aws-radius-md);
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #ef4444;
}
.doc-sub-error .msg {
  flex: 1;
  min-width: 0;
  font-size: var(--aws-text-xs);
  line-height: 1.5;
  color: #b91c1c;
  word-break: break-all;
}

/* ---------- 空知识库流水线 ---------- */
.pipeline {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 16px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-xl);
  box-shadow: var(--aws-shadow-card);
}
.pipe-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 96px;
}
.pipe-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--aws-primary) 10%, #ffffff);
  color: var(--aws-primary);
}
.pipe-label {
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  font-weight: var(--aws-weight-medium);
}
.pipe-arrow {
  color: var(--aws-border-strong);
  margin: 0 4px 24px;
}
.empty-doc-hint {
  margin-top: 16px;
  text-align: center;
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}

/* ---------- 重命名弹窗（Teleport 到 body） ---------- */
:global(.kb-dialog-overlay) {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
:global(.kb-dialog) {
  width: 480px;
  max-width: calc(100vw - 32px);
  background: var(--aws-card);
  border-radius: var(--aws-radius-lg);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}
:global(.kb-dialog-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 0;
}
:global(.kb-dialog-title) {
  font-size: var(--aws-text-lg);
  font-weight: var(--aws-weight-semibold);
}
:global(.kb-dialog-close) {
  width: 26px;
  height: 26px;
  border-radius: var(--aws-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  cursor: pointer;
  background: none;
  border: none;
}
:global(.kb-dialog-close:hover) {
  color: var(--aws-primary);
}
:global(.kb-dialog-body) {
  padding: 20px 24px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
:global(.kb-form-label) {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  margin-top: 8px;
}
:global(.kb-form-label .required) {
  color: #ef4444;
  margin-left: 2px;
}
:global(.kb-form-input),
:global(.kb-form-textarea) {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border-strong);
  background: var(--aws-input);
  font-size: var(--aws-text-sm);
  color: var(--aws-foreground);
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}
:global(.kb-form-input:focus),
:global(.kb-form-textarea:focus) {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
:global(.kb-form-input::placeholder),
:global(.kb-form-textarea::placeholder) {
  color: var(--aws-placeholder);
}
:global(.kb-form-textarea) {
  resize: none;
}
:global(.kb-dialog-footer) {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px 20px;
}

/* 弹窗过渡动画 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
