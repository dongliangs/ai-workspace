<template>
  <!-- 附件 chip 列表：渲染在组件放置位置 -->
  <div
    v-if="files.length"
    class="attach-chips"
  >
    <span
      v-for="f in files"
      :key="f.uid"
      class="attach-chip"
      :class="{ 'is-error': f.status === 'error' }"
    >
      <FileSpreadsheet class="w-3.5 h-3.5 shrink-0" />
      <span class="attach-name truncate">{{ f.name }}</span>
      <span class="attach-meta">
        <template v-if="f.status === 'uploading'">{{ f.progress }}%</template>
        <template v-else>{{ f.size }}</template>
      </span>
      <button
        type="button"
        class="attach-remove"
        :disabled="f.status === 'uploading'"
        @click="removeFile(f.uid)"
      >
        <X class="w-3 h-3" />
      </button>
    </span>
  </div>

  <!-- 隐藏的文件输入，由 openPicker() 触发 -->
  <input
    ref="inputRef"
    type="file"
    multiple
    hidden
    :accept="accept"
    @change="onFileChange"
  >
</template>

<script setup lang="ts">
/**
 * FileUploader —— 通用文件上传组件（支持多文件）
 * ===========================================================================
 * 职责：
 *   封装文件选择、上传、进度追踪、删除等完整流程，可在 Chat / Agent /
 *   知识库等多场景复用。
 *
 * 设计思路：
 *   - 组件只负责"文件 chip 列表 + 隐藏 input + 上传逻辑"，
 *     触发按钮（+ / 回形针）由父组件自行放置，通过 ref 调用 openPicker()。
 *   - 上传状态通过 v-model:files 双向绑定，父组件可直接读取 file_id。
 *   - 上传中状态通过 uploading-change 事件通知父组件（用于禁用发送按钮）。
 *
 * 用法示例：
 *   <FileUploader
 *     ref="uploaderRef"
 *     :disabled="loading"
 *     v-model:files="attachments"
 *     @uploading-change="(v) => hasUploading = v"
 *   />
 *   <button @click="uploaderRef?.openPicker()">+</button>
 * ===========================================================================
 */
import { ref, watch } from 'vue'
import { FileSpreadsheet, X } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { uploadFile } from '@/api/file'
import type { UploadProgress } from '@/utils/request'

/** 单个附件的状态 */
export interface UploadFile {
  /** 前端自增 id，用作 v-for key */
  uid: number
  /** 原始文件名 */
  name: string
  /** 格式化后的大小显示文本（如 "1.2MB"） */
  size: string
  /** 原始字节数 */
  rawSize: number
  /** 上传状态 */
  status: 'uploading' | 'done' | 'error'
  /** 上传进度百分比 0-100 */
  progress: number
  /** 后端返回的文件 id，上传成功后有值 */
  file_id?: number
}

const props = defineProps<{
  /** 接受的文件类型（input accept 属性），如 ".xlsx,.xls,.csv" */
  accept?: string
  /** 禁用（正在加载时不允许选文件） */
  disabled?: boolean
  /** v-model:files 绑定值 */
  files?: UploadFile[]
}>()

const emit = defineEmits<{
  /** v-model:files 更新事件 */
  'update:files': [files: UploadFile[]]
  /** 上传状态变化：true 表示有文件正在上传中 */
  'uploading-change': [uploading: boolean]
}>()

const inputRef = ref<HTMLInputElement | null>(null)

/** 内部文件列表（与 props.files 双向同步） */
const internalFiles = ref<UploadFile[]>([])

// 同步外部 v-model 值到内部
watch(
  () => props.files,
  (val) => {
    if (val !== undefined) {
      internalFiles.value = val
    }
  },
  { immediate: true },
)

/** 自增 id 计数器 */
let _uid = 0
const nextUid = () => ++_uid

/** 暴露给父组件：打开文件选择器 */
function openPicker() {
  if (props.disabled) return
  inputRef.value?.click()
}

defineExpose({ openPicker })

/** 文件选择回调 */
async function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files) return

  for (const f of Array.from(target.files)) {
    const uid = nextUid()
    const file: UploadFile = {
      uid,
      name: f.name,
      size: formatSize(f.size),
      rawSize: f.size,
      status: 'uploading',
      progress: 0,
    }
    internalFiles.value.push(file)
    syncToParent()
    emitUploading()

    // 真实上传
    try {
      const res = await uploadFile(f, (p: UploadProgress) => {
        const item = internalFiles.value.find((x) => x.uid === uid)
        if (item) item.progress = p.percent
      })
      const item = internalFiles.value.find((x) => x.uid === uid)
      if (item) {
        item.status = 'done'
        item.file_id = res.id
        item.progress = 100
      }
      syncToParent()
    } catch {
      const item = internalFiles.value.find((x) => x.uid === uid)
      if (item) {
        item.status = 'error'
      }
      syncToParent()
      ElMessage.error(`文件 ${f.name} 上传失败`)
    }
  }

  target.value = '' // 允许重复选同一文件
  emitUploading()
}

/** 删除附件 */
function removeFile(uid: number) {
  internalFiles.value = internalFiles.value.filter((f) => f.uid !== uid)
  syncToParent()
  emitUploading()
}

/** 同步内部状态到父组件（v-model） */
function syncToParent() {
  emit('update:files', [...internalFiles.value])
}

/** 通知父组件上传状态变化 */
function emitUploading() {
  const uploading = internalFiles.value.some((f) => f.status === 'uploading')
  emit('uploading-change', uploading)
}

/** 格式化文件大小 */
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}
</script>

<style scoped>
.attach-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 240px;
  padding: 6px 10px;
  border-radius: var(--aws-radius-md);
  background: var(--aws-card);
  border: 1px solid var(--aws-border);
  font-size: var(--aws-text-xs);
  color: var(--aws-foreground);
  transition: border-color 0.15s;
}
.attach-chip.is-error {
  border-color: #ef4444;
  color: #ef4444;
}
.attach-name {
  max-width: 140px;
}
.attach-meta {
  color: var(--aws-muted);
}
.attach-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  transition: color 0.15s;
}
.attach-remove:hover:not(:disabled) {
  color: var(--aws-primary);
}
.attach-remove:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
