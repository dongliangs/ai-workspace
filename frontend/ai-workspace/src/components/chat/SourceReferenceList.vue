<template>
  <div class="sources">
    <div class="sources-head">
      <BookMarked class="icon" />
      <span>参考来源</span>
      <span class="count">来自 {{ docCount }} 份文档的 {{ sources.length }} 个片段</span>
    </div>

    <div
      v-for="s in sources"
      :key="`${s.document_id}-${s.chunk_index ?? s.index}`"
      class="src-item"
    >
      <div class="src-main">
        <span class="src-badge">{{ s.index }}</span>
        <span
          class="src-file"
          :class="extClass(s.filename)"
        >
          <FileText class="icon" />
          <span class="src-name">{{ s.filename }}</span>
        </span>
        <span
          v-if="location(s)"
          class="src-loc"
        >{{ location(s) }}</span>
      </div>
      <!-- 后端返回片段原文时展示引用内容（当前契约未提供，预留） -->
      <div
        v-if="s.quote"
        class="src-quote"
      >
        <span class="mark">"</span>{{ s.quote }}<span class="mark">"</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BookMarked, FileText } from 'lucide-vue-next'
import type { KnowledgeSource } from '@/api/knowledgeChat'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'SourceReferenceList' })

const props = defineProps<{
  /** 检索命中的来源片段（来自 retrieval_result / done 事件） */
  sources: KnowledgeSource[]
}>()

/** 命中来源涉及的文档数（按 document_id 去重） */
const docCount = computed(() => new Set(props.sources.map((s) => s.document_id)).size)

/** 文件后缀 → 图标配色类 */
function extClass(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'pdf') return 'pdf'
  if (ext === 'docx' || ext === 'doc') return 'docx'
  if (ext === 'txt' || ext === 'md') return 'txt'
  return 'other'
}

/** 位置标签：P12 · 片段 #86（无页码时只显示片段序号） */
function location(s: KnowledgeSource): string {
  const parts: string[] = []
  if (s.page_number > 0) parts.push(`P${s.page_number}`)
  if (s.chunk_index != null) parts.push(`片段 #${s.chunk_index}`)
  return parts.join(' · ')
}
</script>

<style scoped>
.sources {
  margin-top: 12px;
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-lg);
  background: var(--aws-card);
  overflow: hidden;
}
.sources-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 14px;
  font-size: var(--aws-text-xs);
  font-weight: var(--aws-weight-semibold);
  color: var(--aws-muted);
  background: var(--aws-sidebar);
  border-bottom: 1px solid var(--aws-divider);
}
.sources-head .icon {
  width: 13px;
  height: 13px;
  color: var(--aws-primary);
}
.sources-head .count {
  font-weight: 400;
  color: var(--aws-placeholder);
}
.src-item {
  border-bottom: 1px solid var(--aws-divider);
}
.src-item:last-child {
  border-bottom: none;
}
.src-main {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}
.src-badge {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--aws-primary) 12%, var(--aws-card));
  color: var(--aws-primary);
  font-size: 11px;
  font-weight: var(--aws-weight-semibold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.src-file {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.src-file .icon {
  width: 15px;
  height: 15px;
  flex: none;
}
.src-file.pdf {
  color: #dc2626;
}
.src-file.docx {
  color: #2563eb;
}
.src-file.txt {
  color: #4b5563;
}
.src-file.other {
  color: var(--aws-muted);
}
.src-name {
  font-size: var(--aws-text-sm);
  font-weight: var(--aws-weight-medium);
  color: var(--aws-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.src-loc {
  flex: none;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  background: var(--aws-sidebar);
  border-radius: 999px;
  padding: 2px 9px;
}
.src-quote {
  padding: 0 14px 12px 46px;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  line-height: var(--aws-leading-relaxed);
}
.src-quote .mark {
  color: var(--aws-border-strong);
  margin-right: 4px;
}
</style>
