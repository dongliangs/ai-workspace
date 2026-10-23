<template>
  <div
    v-loading="kbStore.loading"
    class="kb-page"
  >
    <!-- ============ 页头：标题 + 说明 + 创建按钮 ============ -->
    <div class="page-header">
      <div>
        <h1 class="page-title">
          <BookOpen class="w-[22px] h-[22px] text-primary" />
          知识库
        </h1>
        <p class="page-desc">
          上传资料构建私有知识库，基于资料提问，获取有依据、可溯源的回答
        </p>
      </div>
      <button
        type="button"
        class="btn-primary"
        @click="openCreate()"
      >
        <Plus class="w-4 h-4" />
        创建知识库
      </button>
    </div>

    <!-- ============ 列表态：卡片网格 ============ -->
    <div
      v-if="kbStore.bases?.items.length"
      class="kb-grid"
    >
      <article
        v-for="(kb, i) in kbStore.bases.items"
        :key="kb.id"
        class="kb-card"
        :style="{ '--tint': palette[i % palette.length].color }"
        @click="enterDetail(kb.id)"
      >
        <!-- 悬浮操作：重命名 / 删除 -->
        <div
          class="kb-card-actions"
          @click.stop
        >
          <button
            type="button"
            class="icon-btn"
            title="重命名"
            @click.stop="openRename(kb)"
          >
            <Pencil class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            class="icon-btn danger"
            title="删除"
            @click.stop="confirmRemove(kb)"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- 图标：调色板循环取色，与设计稿一致 -->
        <div
          class="kb-icon"
          :style="palette[i % palette.length].iconStyle"
        >
          <component
            :is="palette[i % palette.length].icon"
            class="w-[22px] h-[22px]"
          />
        </div>

        <h3 class="kb-name">
          {{ kb.name }}
        </h3>
        <p class="kb-desc">
          {{ kb.description || '暂无描述' }}
        </p>

        <div class="kb-meta">
          <span class="item">
            <FileText class="w-[13px] h-[13px]" />
            {{ kb.doc_count }} 份文档
          </span>
          <!-- <span class="item">
            <Layers class="w-[13px] h-[13px]" />
            {{ kb.chunk_count }} 个片段
          </span> -->
        </div>

        <div class="kb-footer">
          <span class="kb-time">
            <Clock class="w-3 h-3" />
            更新于 {{ formatDate(kb.updated_at) }}
          </span>
          <span class="kb-open">
            进入
            <ArrowRight class="w-[13px] h-[13px]" />
          </span>
        </div>
      </article>
    </div>

    <!-- ============ 空状态 ============ -->
    <div
      v-else-if="!kbStore.loading"
      class="empty-state"
    >
      <div class="empty-visual">
        <span class="ring ring-1" />
        <span class="ring ring-2" />
        <span class="ring ring-3">
          <BookOpen class="w-[30px] h-[30px]" />
        </span>
        <span class="spark">
          <Sparkles class="w-4 h-4" />
        </span>
      </div>
      <h3 class="empty-title">
        创建你的第一个知识库
      </h3>
      <p class="empty-desc">
        上传 PDF、DOCX、TXT 资料，系统将自动解析、切分并向量化。之后即可针对资料自然语言提问，AI
        会基于检索到的片段作答，并标注来源出处。
      </p>
      <div class="empty-tags">
        <span class="empty-tag"><FileText class="w-3 h-3" />PDF</span>
        <span class="empty-tag"><FileText class="w-3 h-3" />DOCX</span>
        <span class="empty-tag"><FileText class="w-3 h-3" />TXT</span>
      </div>
      <button
        type="button"
        class="btn-primary"
        @click="openCreate()"
      >
        <Plus class="w-4 h-4" />
        创建知识库
      </button>
    </div>

    <!-- ============ 创建 / 重命名弹窗（Teleport 到 body，复刻设计稿） ============ -->
    <Teleport to="body">
      <Transition name="dialog-fade">
        <div
          v-if="dialogVisible"
          class="dialog-overlay"
          @click.self="closeDialog()"
          @keydown.esc="closeDialog()"
        >
          <Transition
            name="dialog-pop"
            appear
          >
            <div class="dialog">
              <div class="dialog-header">
                <h3 class="dialog-title">
                  {{ dialogMode === 'create' ? '创建知识库' : '重命名知识库' }}
                </h3>
                <button
                  type="button"
                  class="icon-btn"
                  @click="closeDialog()"
                >
                  <X class="w-3.5 h-3.5" />
                </button>
              </div>

              <div class="dialog-body">
                <label class="form-label">
                  知识库名称
                  <span class="required">*</span>
                </label>
                <input
                  ref="nameInputRef"
                  v-model="form.name"
                  type="text"
                  class="form-input"
                  :class="{ 'input-error': showNameError }"
                  placeholder="例如：产品设计规范"
                  maxlength="50"
                  @input="showNameError = false"
                  @keyup.enter="submitDialog()"
                >
                <p
                  v-if="showNameError"
                  class="form-error"
                >
                  请输入知识库名称
                </p>

                <label class="form-label">描述</label>
                <textarea
                  v-model="form.description"
                  rows="3"
                  class="form-textarea"
                  placeholder="简要描述知识库的用途与内容范围（可选）"
                  maxlength="200"
                />
                <p class="form-tip">
                  <Info class="w-3 h-3" />
                  支持上传 PDF、DOCX、TXT 文档，创建后可随时补充资料
                </p>
              </div>

              <div class="dialog-footer">
                <button
                  type="button"
                  class="btn-ghost"
                  @click="closeDialog()"
                >
                  取消
                </button>
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="kbStore.submitting"
                  @click="submitDialog()"
                >
                  {{ kbStore.submitting ? '提交中...' : dialogMode === 'create' ? '创建' : '保存' }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
/**
 * 知识库列表页（V0.3）
 * ===========================================================================
 * 还原 design/knowledge-base-list.html 设计稿，覆盖三个状态：
 *   列表态（卡片网格）/ 空状态（引导创建）/ 创建&重命名弹窗（复用一个弹窗）
 *
 * 交互清单：
 *   - 进入页面拉取列表（store.fetchAll，失败回退空状态）
 *   - 点击卡片 → 跳详情页 /knowledge/:id（详情页下期开发，当前为占位）
 *   - 悬浮卡片 → 重命名（弹窗）/ 删除（ElMessageBox 二次确认）
 *   - 创建/重命名弹窗：名称必填校验、Enter 提交、Esc/遮罩关闭、失败保留表单
 * ===========================================================================
 */
import { ref, reactive, nextTick, onMounted, type Component, type CSSProperties } from 'vue'
import {
  BookOpen,
  Plus,
  Pencil,
  Trash2,
  FileText,
  Clock,
  ArrowRight,
  Sparkles,
  X,
  Info,
  TrendingUp,
  Scale,
  Landmark,
  Briefcase,
} from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import type { KnowledgeBase } from '@/api/knowledgeBase'
// 多词组件名：满足 vue/multi-word-component-names，且便于 keep-alive / devtools 识别
defineOptions({ name: 'KnowledgeBaseList' })

const router = useRouter()
const kbStore = useKnowledgeBaseStore()

/* -------------------------------------------------------------------------- */
/*  卡片视觉：调色板循环（图标 + 主题色按索引取，与设计稿一致）                      */
/* -------------------------------------------------------------------------- */
interface Palette {
  color: string
  icon: Component
  iconStyle: CSSProperties
}

const palette: Palette[] = [
  { color: '#3b82f6', icon: BookOpen },
  { color: '#10b981', icon: FileText },
  { color: '#9333ea', icon: TrendingUp },
  { color: '#0d9488', icon: Scale },
  { color: '#d97706', icon: Landmark },
  { color: '#6b7280', icon: Briefcase },
].map((p) => ({
  ...p,
  iconStyle: {
    background: `color-mix(in srgb, ${p.color} 10%, #ffffff)`,
    color: p.color,
  },
}))

/* -------------------------------------------------------------------------- */
/*  时间格式化：当年显示 MM-DD，跨年显示 YYYY-MM-DD                              */
/* -------------------------------------------------------------------------- */
function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '--'
  const pad = (n: number) => String(n).padStart(2, '0')
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return sameYear
    ? `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    : `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/* -------------------------------------------------------------------------- */
/*  创建 / 重命名弹窗（一个弹窗两种模式）                                        */
/* -------------------------------------------------------------------------- */
type DialogMode = 'create' | 'rename'

const dialogVisible = ref(false)
const dialogMode = ref<DialogMode>('create')
/** 重命名时记录当前操作的知识库，提交时用 */
const editingKb = ref<KnowledgeBase | null>(null)
const showNameError = ref(false)
const nameInputRef = ref<HTMLInputElement | null>(null)
const form = reactive({ name: '', description: '' })
// const {bases} = storeToRefs(kbStore)
function openCreate() {
  dialogMode.value = 'create'
  editingKb.value = null
  form.name = ''
  form.description = ''
  showNameError.value = false
  showDialog()
}

function openRename(kb: KnowledgeBase) {
  dialogMode.value = 'rename'
  editingKb.value = kb
  form.name = kb.name
  form.description = kb.description
  showNameError.value = false
  showDialog()
}

/** 打开弹窗并聚焦名称输入框 */
function showDialog() {
  dialogVisible.value = true
  nextTick(() => nameInputRef.value?.focus())
}

function closeDialog() {
  dialogVisible.value = false
}

/** 提交（创建/保存）：名称必填，成功关弹窗，失败保留表单 */
async function submitDialog() {
  const name = form.name.trim()
  if (!name) {
    showNameError.value = true
    nameInputRef.value?.focus()
    return
  }
  try {
    if (dialogMode.value === 'create') {
      await kbStore.create({ name, description: form.description.trim() })
      ElMessage.success('知识库创建成功')
    } else if (editingKb.value) {
      await kbStore.rename(editingKb.value.id, { name, description: form.description.trim() })
      ElMessage.success('已保存')
    }
    // 创建或修改知识库名称后，获取知识库列表
    await kbStore.fetchAll()
    closeDialog()
  } catch {
    // 网络错误已由拦截器 toast；这里保持弹窗开启，保留用户填写的表单
  }
}

/* -------------------------------------------------------------------------- */
/*  删除：二次确认后调 store.remove                                            */
/* -------------------------------------------------------------------------- */
async function confirmRemove(kb: KnowledgeBase) {
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
    // 删除后调用
    await kbStore.fetchAll()
    ElMessage.success('已删除')
  } catch {
    // 网络错误已由拦截器 toast
  }
}

/* -------------------------------------------------------------------------- */
/*  卡片点击 → 详情页                                                          */
/* -------------------------------------------------------------------------- */
function enterDetail(id: number) {
  router.push(`/knowledge/${id}`)
}

onMounted(() => {
  kbStore.fetchAll()
})
</script>

<style scoped>
/* ---------- 页头 ---------- */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.page-title {
  font-size: var(--aws-text-xl);
  font-weight: var(--aws-weight-semibold);
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-desc {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  margin-top: 6px;
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
  height: 34px;
  padding: 0 16px;
  border-radius: var(--aws-radius-md);
  border: 1px solid var(--aws-border);
  background: var(--aws-card);
  color: var(--aws-foreground);
  font-size: var(--aws-text-sm);
  transition: border-color 0.15s, color 0.15s;
}
.btn-ghost:hover {
  border-color: var(--aws-primary);
  color: var(--aws-primary);
}
.icon-btn {
  width: 26px;
  height: 26px;
  border-radius: var(--aws-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  background: var(--aws-card);
  transition: background-color 0.15s, color 0.15s;
}
.icon-btn:hover {
  background: var(--aws-sidebar-active);
  color: var(--aws-primary);
}
.icon-btn.danger:hover {
  background: #fef2f2;
  color: #ef4444;
}

/* ---------- 卡片网格 ---------- */
.kb-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.kb-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  box-shadow: var(--aws-shadow-card);
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;
  animation: card-in 0.45s ease both;
}
.kb-card:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--tint) 35%, var(--aws-border));
}
@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.kb-card-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 2px;
  opacity: 0;
  transform: translateY(-2px);
  transition: opacity 0.15s, transform 0.15s;
}
.kb-card:hover .kb-card-actions {
  opacity: 1;
  transform: none;
}
.kb-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.kb-name {
  font-size: 15px;
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-desc {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  line-height: var(--aws-leading-relaxed);
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.kb-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
}
.kb-meta .item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.kb-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--aws-divider);
}
.kb-time {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
}
.kb-open {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-primary);
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s, transform 0.2s;
}
.kb-card:hover .kb-open {
  opacity: 1;
  transform: none;
}

/* ---------- 空状态 ---------- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 72px 24px;
  background: var(--aws-card);
  border: 1px dashed var(--aws-border-strong);
  border-radius: var(--aws-radius-xl);
  text-align: center;
  animation: card-in 0.45s ease both;
}
.empty-visual {
  position: relative;
  width: 96px;
  height: 96px;
  margin-bottom: 24px;
}
.empty-visual .ring {
  position: absolute;
  border-radius: 50%;
}
.empty-visual .ring-1 {
  inset: 0;
  background: color-mix(in srgb, var(--aws-primary) 6%, transparent);
}
.empty-visual .ring-2 {
  inset: 14px;
  background: color-mix(in srgb, var(--aws-primary) 10%, transparent);
}
.empty-visual .ring-3 {
  inset: 28px;
  background: color-mix(in srgb, var(--aws-primary) 14%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-primary);
}
.empty-visual .spark {
  position: absolute;
  top: 6px;
  right: 8px;
  color: var(--aws-success);
}
.empty-title {
  font-size: var(--aws-text-lg);
  font-weight: var(--aws-weight-semibold);
  margin-bottom: 8px;
}
.empty-desc {
  font-size: var(--aws-text-sm);
  color: var(--aws-muted);
  max-width: 420px;
  line-height: var(--aws-leading-relaxed);
  margin-bottom: 24px;
}
.empty-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 28px;
}
.empty-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  background: var(--aws-sidebar);
  border: 1px solid var(--aws-border);
}

/* ---------- 弹窗（Teleport 到 body，样式为全局作用域） ---------- */
:global(.dialog-overlay) {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
:global(.dialog) {
  width: 480px;
  max-width: calc(100vw - 32px);
  background: var(--aws-card);
  border-radius: var(--aws-radius-lg);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}
:global(.dialog-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 0;
}
:global(.dialog-title) {
  font-size: var(--aws-text-lg);
  font-weight: var(--aws-weight-semibold);
}
:global(.dialog-body) {
  padding: 20px 24px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
:global(.form-label) {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  margin-top: 8px;
}
:global(.form-label .required) {
  color: #ef4444;
  margin-left: 2px;
}
:global(.form-input),
:global(.form-textarea) {
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
:global(.form-input:focus),
:global(.form-textarea:focus) {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
:global(.form-input::placeholder),
:global(.form-textarea::placeholder) {
  color: var(--aws-placeholder);
}
:global(.form-textarea) {
  resize: none;
}
:global(.form-input.input-error) {
  border-color: #ef4444;
}
:global(.form-input.input-error:focus) {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
}
:global(.form-error) {
  font-size: var(--aws-text-xs);
  color: #ef4444;
}
:global(.form-tip) {
  font-size: var(--aws-text-xs);
  color: var(--aws-placeholder);
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}
:global(.dialog-footer) {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px 20px;
}

/* ---------- 弹窗过渡动画 ---------- */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
:global(.dialog-pop-enter-active) {
  transition: opacity 0.25s cubic-bezier(0.2, 0.9, 0.3, 1.2), transform 0.25s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}
:global(.dialog-pop-enter-from) {
  opacity: 0;
  transform: translateY(16px) scale(0.97);
}

@media (max-width: 1024px) {
  .kb-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
