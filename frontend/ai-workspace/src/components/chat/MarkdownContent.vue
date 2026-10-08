<template>
  <div class="md-content">
    <template
      v-for="(seg, i) in segments"
      :key="i"
    >
      <!-- 代码块 -->
      <div
        v-if="seg.type === 'code'"
        class="md-code-block"
      >
        <div class="md-code-header">
          <span class="md-code-lang">{{ seg.lang || 'code' }}</span>
          <button
            type="button"
            class="md-code-copy"
            :title="'复制代码'"
            @click="onCopyCode(seg.code)"
          >
            <Check
              v-if="copiedIndex === i"
              class="w-3.5 h-3.5"
            />
            <Copy
              v-else
              class="w-3.5 h-3.5"
            />
            <span class="md-code-copy-text">{{ copiedIndex === i ? '已复制' : '复制' }}</span>
          </button>
        </div>
        <pre class="md-code-pre"><code>{{ seg.code }}</code></pre>
      </div>

      <!-- 文本段（标题/加粗/列表/普通段落） -->
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div
        v-else
        class="md-text"
        v-html="seg.html"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Copy, Check } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'

type Segment =
  | { type: 'text'; html: string }
  | { type: 'code'; lang: string; code: string }

const props = defineProps<{
  content: string
}>()

const copiedIndex = ref<number | null>(null)

/**
 * 将 markdown 内容解析为段落/代码块序列。
 * 代码块用 ``` 围栏提取，剩余部分按行处理标题、加粗、列表等。
 */
const segments = computed<Segment[]>(() => parse(props.content))

/**
 * 轻量级 markdown → HTML 转换（无需第三方库）。
 * 流程：转义 HTML → 提取代码块占位 → 处理行级标记 → 段落包裹 → 还原代码块。
 */
function parse(src: string): Segment[] {
  if (!src) return [{ type: 'text', html: '' }]

  const segs: Segment[] = []
  const lines = src.split('\n')
  let buf: string[] = []
  let i = 0

  /** 先把缓冲的文本行批量转 HTML 推入 segs */
  const flushText = () => {
    if (buf.length === 0) return
    const html = renderTextBlock(buf.join('\n'))
    if (html) segs.push({ type: 'text', html })
    buf = []
  }

  while (i < lines.length) {
    const line = lines[i]
    // 检测代码围栏 ```lang
    const fence = line.match(/^\s*```([\w-]*)\s*$/)
    if (fence) {
      flushText()
      const lang = fence[1] ?? ''
      const codeBuf: string[] = []
      i++
      // 收集直到结束围栏
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
        codeBuf.push(lines[i])
        i++
      }
      // 跳过结束围栏
      if (i < lines.length) i++
      segs.push({ type: 'code', lang, code: codeBuf.join('\n') })
      continue
    }
    buf.push(line)
    i++
  }
  flushText()

  return segs.length ? segs : [{ type: 'text', html: '' }]
}

/**
 * 把一段文本（可能含多行）转为 HTML。
 * 处理：标题、加粗、斜体、行内代码、无序/有序列表、段落。
 */
function renderTextBlock(text: string): string {
  // 1. 先转义 HTML，防止 XSS
  let safe = escapeHtml(text)

  // 2. 按行处理
  const lines = safe.split('\n')
  const out: string[] = []
  let inUl = false
  let inOl = false
  /** 无显式编号的加粗标题计数器（自动加序号） */
  let autoHeadingNum = 0

  const closeLists = () => {
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inOl) { out.push('</ol>'); inOl = false }
  }

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li].trimEnd()

    // 空行 → 段落分隔
    if (line === '') {
      closeLists()
      continue
    }

    // ── 表格检测：连续以 | 开头的行，且第二行是 |---| 分隔符 ──
    if (line.startsWith('|') && li + 1 < lines.length && /^\|[\s:|-]+\|/.test(lines[li + 1])) {
      closeLists()
      // 收集表格所有行
      const tableLines: string[] = []
      while (li < lines.length && lines[li].trim().startsWith('|')) {
        tableLines.push(lines[li])
        li++
      }
      // 回退一行，因为 for 循环会 li++
      li--
      out.push(renderTable(tableLines))
      continue
    }

    // 标题 ### / ## / #
    const h = line.match(/^(#{1,3})\s+(.*)$/)
    if (h) {
      closeLists()
      const level = h[1].length
      out.push(`<h${level}>${inlineFmt(h[2])}</h${level}>`)
      continue
    }

    // ── 优先检测"编号+加粗标题"：如 1. **体验方式不同** ──
    // 这类行 NOT 有序列表，而是带编号的标题行。
    const numBold = line.match(/^(\d+)\.\s+\*\*(.+)\*\*$/)
    if (numBold) {
      closeLists()
      const num = numBold[1]
      const title = numBold[2]
      out.push(
        `<p class="md-heading"><span class="md-heading-num">${num}.</span><strong>${title}</strong></p>`,
      )
      continue
    }

    // ── 纯加粗行：判断是"标题"还是"强调句" ──
    // 标题特征：短（≤20字）且不以句末标点结尾
    // 强调句特征：长或以 。，！？。 结尾 → 不加序号
    const pureBold = line.match(/^\*\*(.+)\*\*$/)
    if (pureBold) {
      const content = pureBold[1]
      const isSentence = content.length > 20 || /[。，！？；]$/.test(content)
      if (!isSentence) {
        // 标题：自动加序号
        closeLists()
        autoHeadingNum++
        out.push(
          `<p class="md-heading"><span class="md-heading-num">${autoHeadingNum}.</span><strong>${content}</strong></p>`,
        )
        continue
      }
      // 强调句：不加序号，走普通段落
    }

    // 无序列表 - 开头（注意：** 开头的不匹配，因为有 \s+ 要求）
    const ul = line.match(/^-\s+(.*)$/)
    if (ul) {
      if (!inUl) { closeLists(); out.push('<ul>'); inUl = true }
      out.push(`<li>${inlineFmt(ul[1])}</li>`)
      continue
    }

    // 有序列表 N. 普通文本（不含 ** 包裹的）
    const ol = line.match(/^(\d+)\.\s+(.*)$/)
    if (ol) {
      if (!inOl) { closeLists(); out.push('<ol>'); inOl = true }
      // ol[1] 是序号，ol[2] 是文本内容
      out.push(`<li>${inlineFmt(ol[2])}</li>`)
      continue
    }

    // 引用 >
    const bq = line.match(/^>\s?(.*)$/)
    if (bq) {
      closeLists()
      out.push(`<blockquote>${inlineFmt(bq[1])}</blockquote>`)
      continue
    }

    // 普通段落
    closeLists()
    out.push(`<p>${inlineFmt(line)}</p>`)
  }
  closeLists()

  // 3. 末尾段落标记为重点
  let html = out.join('\n')
  html = emphasizeLast(html)

  return html
}

/**
 * 将 markdown 表格行解析为 HTML <table>。
 * 输入格式：
 * | 列1 | 列2 | 列3 |
 * |---|---|---|
 * | 数据 | 数据 | 数据 |
 */
function renderTable(tableLines: string[]): string {
  if (tableLines.length < 2) return tableLines.join('\n')

  // 解析一行单元格
  const parseRow = (row: string): string[] => {
    const trimmed = row.trim()
    // 去掉首尾的 |
    const inner = trimmed.replace(/^\|/, '').replace(/\|$/, '')
    return inner.split('|').map((c) => c.trim())
  }

  // 第一行是表头
  const headers = parseRow(tableLines[0])
  // 第二行是分隔符（跳过）
  // 第三行起是数据行
  const bodyRows = tableLines.slice(2).map(parseRow)

  let html = '<div class="md-table-wrap"><table class="md-table"><thead><tr>'
  for (const h of headers) {
    html += `<th>${inlineFmt(h)}</th>`
  }
  html += '</tr></thead><tbody>'
  for (const row of bodyRows) {
    html += '<tr>'
    for (let ci = 0; ci < headers.length; ci++) {
      const cell = row[ci] ?? ''
      html += `<td>${inlineFmt(cell)}</td>`
    }
    html += '</tr>'
  }
  html += '</tbody></table></div>'
  return html
}

/**
 * 行内格式：加粗 **text**、斜体 *text*、行内代码 `code`。
 * 注意：转义后的 `**` 已变成 `**`（星号不会被转义），直接替换即可。
 */
function inlineFmt(text: string): string {
  return text
    // 行内代码 `code`
    .replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')
    // 加粗 **text** 或 __text__
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    // 斜体 *text* 或 _text_
    .replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/(^|[^_])_([^_]+)_(?!_)/g, '$1<em>$2</em>')
}

/**
 * 将最后一个段落标记为"重点内容"，加粗加大。
 */
function emphasizeLast(html: string): string {
  // 找到最后一个 <p>...</p>，替换为 <p class="md-key">...</p>
  const idx = html.lastIndexOf('<p>')
  if (idx === -1) return html
  const before = html.slice(0, idx)
  const after = html.slice(idx)
  return before + after.replace('<p>', '<p class="md-key">')
}

/** 转义 HTML 特殊字符，防止 XSS */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** 复制代码块内容 */
async function onCopyCode(code: string) {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success('已复制')
    copiedIndex.value = segments.value.findIndex((s) => s.type === 'code' && s.code === code)
    setTimeout(() => { copiedIndex.value = null }, 2000)
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.md-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  /* 整体字号增大一号（从默认 14px → 15px） */
  font-size: 15px;
  line-height: 1.7;
}

/* 文本段 */
.md-text :deep(p) {
  margin: 0 0 8px;
  font-size: 1em;
}
.md-text :deep(p:last-child) {
  margin-bottom: 0;
}

/* 加粗标题行：序号用品牌色 + 黑体加粗加大 */
.md-text :deep(.md-heading) {
  margin: 8px 0 4px;
}
.md-text :deep(.md-heading-num) {
  color: var(--aws-primary);
  font-weight: 700;
  font-size: 1.05em;
  margin-right: 4px;
}
.md-text :deep(.md-heading strong) {
  font-size: 1.05em;
}

.md-text :deep(h1) {
  font-size: 1.25em;
  font-weight: 700;
  margin: 8px 0 6px;
}
.md-text :deep(h2) {
  font-size: 1.15em;
  font-weight: 700;
  margin: 8px 0 6px;
}
.md-text :deep(h3) {
  font-size: 1.05em;
  font-weight: 700;
  margin: 6px 0 4px;
}
.md-text :deep(strong) {
  font-weight: 700;
}
.md-text :deep(em) {
  font-style: italic;
}

/* 修复 Tailwind Preflight 导致的列表标记丢失 */
.md-text :deep(ul) {
  margin: 4px 0;
  padding-left: 20px;
  list-style: disc;
}
.md-text :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
  list-style: decimal;
}
.md-text :deep(li) {
  margin: 2px 0;
}

/* 表格 */
.md-text :deep(.md-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
  border-radius: 8px;
  border: 1px solid var(--aws-border);
}
.md-text :deep(.md-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95em;
}
.md-text :deep(.md-table th) {
  background: var(--aws-sidebar-active);
  font-weight: 700;
  text-align: left;
  padding: 8px 12px;
  border-bottom: 2px solid var(--aws-border);
  white-space: nowrap;
}
.md-text :deep(.md-table td) {
  padding: 6px 12px;
  border-bottom: 1px solid var(--aws-border);
  vertical-align: top;
}
.md-text :deep(.md-table tbody tr:last-child td) {
  border-bottom: none;
}
.md-text :deep(.md-table tbody tr:hover) {
  background: var(--aws-sidebar-active);
}

.md-text :deep(blockquote) {
  border-left: 3px solid var(--aws-primary);
  padding-left: 10px;
  color: var(--aws-muted);
  margin: 4px 0;
}
.md-text :deep(.md-inline-code) {
  background: var(--aws-sidebar-active);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}

/* 重点内容（最后一句话）：加粗加大 */
.md-text :deep(.md-key) {
  font-weight: 700;
  font-size: 1.05em;
  color: var(--aws-foreground);
}

/* 代码块 */
.md-code-block {
  background: #1e293b;
  border-radius: 8px;
  overflow: hidden;
  margin: 4px 0;
}
.md-code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #334155;
  color: #cbd5e1;
  font-size: 12px;
}
.md-code-lang {
  text-transform: lowercase;
  letter-spacing: 0.5px;
}
.md-code-copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: none;
  color: #cbd5e1;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.15s, color 0.15s;
}
.md-code-copy:hover {
  background: #475569;
  color: #fff;
}
.md-code-copy-text {
  font-size: 12px;
}
.md-code-pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
}
.md-code-pre code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #e2e8f0;
  white-space: pre;
}
</style>
