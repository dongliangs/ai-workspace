<template>
  <div class="chat-input-bar">
    <!-- 断网警告条：网络恢复后自动消失 -->
    <div
      v-if="offline"
      class="offline-banner"
    >
      <WifiOff class="w-3.5 h-3.5 shrink-0" />
      <span>网络连接已断开，消息无法发送</span>
    </div>

    <!-- 通用文件上传组件：管理附件 chip 列表 + 隐藏 input + 上传逻辑（暂不支持上传的视图不渲染） -->
    <FileUploader
      v-if="allowUpload"
      ref="uploaderRef"
      v-model:files="attachmentsModel"
      :disabled="loading"
      @uploading-change="$emit('uploading-change', $event)"
    />

    <!-- 输入框上方插槽：知识库上下文 chip / 模式切换器等 -->
    <slot name="before-input" />

    <!-- 胶囊形输入框：+ 加号 | textarea | 圆形发送按钮 -->
    <div class="input-pill">
      <button
        v-if="allowUpload"
        type="button"
        class="plus-icon"
        title="上传文件"
        :disabled="loading"
        @click="triggerFile"
      >
        <Plus class="w-5 h-5" />
      </button>

      <textarea
        ref="textareaRef"
        v-model="inputModel"
        class="chat-textarea"
        :placeholder="placeholder"
        :disabled="loading"
        rows="1"
        @input="autoResize"
        @keydown.enter.exact.prevent="onEnter"
      />

      <!-- 输入框内部 chips 插槽（Agent 已选工具等，跟在文字后面展示） -->
      <slot name="pill-chips" />

      <button
        type="button"
        class="send-circle"
        :class="{ 'is-stop': loading }"
        :disabled="!loading && !canSend"
        @click="onSendClick"
      >
        <Square
          v-if="loading"
          class="w-4 h-4"
        />
        <ArrowUp
          v-else
          class="w-[18px] h-[18px]"
        />
      </button>
    </div>

    <!-- 输入框下方行动区插槽：Agent 选择工具 / knowledge 知识库 chip / chat 模式切换器 -->
    <slot name="actions" />

    <p class="disclaimer">
      AI 生成内容仅供参考
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { Plus, ArrowUp, Square, WifiOff } from 'lucide-vue-next'
import FileUploader from '@/components/common/FileUploader.vue'
import type { UploadFile } from '@/components/common/FileUploader.vue'

// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'ChatInputBar' })

const props = withDefaults(
  defineProps<{
    /** 是否断网（显示警告条，网络恢复后自动消失） */
    offline: boolean
    /** 是否有流式请求正在生成中（发送按钮变停止按钮） */
    loading: boolean
    /** 输入框占位符 */
    placeholder: string
    /** 是否能发送（父组件计算：有输入内容等） */
    canSend: boolean
    /** 输入框文本（v-model） */
    input: string
    /** 附件列表（v-model，透传给 FileUploader） */
    attachments: UploadFile[]
    /** 是否允许上传附件（knowledge 模式暂不支持，隐藏加号与上传组件） */
    allowUpload?: boolean
  }>(),
  { allowUpload: true },
)

const emit = defineEmits<{
  'update:input': [value: string]
  'update:attachments': [value: UploadFile[]]
  submit: []
  stop: []
  'uploading-change': [value: boolean]
}>()

const uploaderRef = ref<InstanceType<typeof FileUploader>>()
const textareaRef = ref<HTMLTextAreaElement>()

const inputModel = computed({
  get: () => props.input,
  set: (v) => emit('update:input', v),
})
const attachmentsModel = computed({
  get: () => props.attachments,
  set: (v) => emit('update:attachments', v),
})

/** 点击 + 加号触发文件选择 */
function triggerFile() {
  uploaderRef.value?.openPicker()
}

/** textarea 随内容自适应高度，最高 160px */
function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  })
}

// 内容变化（含发送后父组件清空 input）时同步自适应高度
watch(() => props.input, () => autoResize())

/** Enter 发送（发送前置校验在父组件 onSubmit 内） */
function onEnter() {
  if (!props.canSend || props.loading) return
  emit('submit')
}

/** 发送按钮：loading 中点击 = 停止，否则 = 发送 */
function onSendClick() {
  if (props.loading) emit('stop')
  else emit('submit')
}

defineExpose({ triggerFile, autoResize })
</script>

<style scoped>
.offline-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 6px 12px;
  border-radius: var(--aws-radius-md);
  background: color-mix(in srgb, #f59e0b 10%, var(--aws-card));
  border: 1px solid color-mix(in srgb, #f59e0b 30%, var(--aws-border));
  color: #b45309;
  font-size: var(--aws-text-xs);
}

.chat-input-bar {
  flex: none;
  width: 100%;
  max-width: 768px;
  margin: 0 auto;
  /* 底部 10px：flex-col 布局下输入栏天然贴住页面底部 */
  padding: 0 16px 10px;
}

/* 胶囊形输入框：回形针 | textarea | 圆形发送按钮 */
.input-pill {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 8px 8px 16px;
  border-radius: 28px;
  border: 1px solid var(--aws-border);
  background: var(--aws-input);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.input-pill:focus-within {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

/* 左侧 + 加号图标 */
.plus-icon {
  flex: none;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--aws-muted);
  background: transparent;
  border: none;
  border-radius: 50%;
  transition: color 0.15s, background-color 0.15s;
  align-self: flex-end;
  margin-bottom: 2px;
}
.plus-icon:hover:not(:disabled) {
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 8%, transparent);
}
.plus-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 多行文本输入 */
.chat-textarea {
  flex: 1;
  min-height: 36px;
  max-height: 160px;
  padding: 8px 0;
  border: none;
  background: transparent;
  font-size: var(--aws-text-base);
  color: var(--aws-foreground);
  line-height: var(--aws-leading-relaxed);
  resize: none;
  font-family: inherit;
}
.chat-textarea::placeholder {
  color: var(--aws-placeholder);
}
.chat-textarea:focus {
  outline: none;
}
.chat-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 右侧圆形蓝色发送按钮 */
.send-circle {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  transition: background-color 0.15s, opacity 0.15s;
  align-self: flex-end;
  margin-bottom: 2px;
}
.send-circle:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.send-circle:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.send-circle.is-stop {
  background: var(--aws-foreground);
}
.send-circle.is-stop:hover {
  background: #374151;
}

.disclaimer {
  text-align: center;
  font-size: var(--aws-text-xs);
  color: var(--aws-muted);
  margin-top: 8px;
}
</style>