<template>
  <div class="chart-wrapper">
    <div ref="chartRef" class="chart-canvas"></div>
    <div class="chart-toolbar">
      <button class="chart-btn" @click="downloadPng">
        <Download :size="14" />
        下载图片
      </button>
      <button class="chart-btn" @click="downloadData">
        <FileSpreadsheet :size="14" />
        下载数据
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Download, FileSpreadsheet } from 'lucide-vue-next'

const props = defineProps<{
  option: Record<string, any>
  title?: string
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(props.option, true)
}

function resize() {
  chart?.resize()
}

/** 下载 PNG：利用 ECharts getDataURL */
function downloadPng() {
  if (!chart) return
  const url = chart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff',
  })
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.title || 'chart'}_${Date.now()}.png`
  a.click()
}

/** 下载数据：从 echarts option 提取 categories + values → CSV */
function downloadData() {
  const opt = props.option
  const series = opt.series as any[]
  if (!series?.length) return

  // 提取分类轴
  let categories: string[] = []
  if (opt.xAxis?.data) {
    categories = opt.xAxis.data.map(String)
  } else if (opt.angleAxis?.data) {
    categories = opt.angleAxis.data.map(String)
  }

  // 饼图特殊处理：series.data = [{name, value}]
  const isPie = series.some(s => s.type === 'pie')
  let csv = ''
  if (isPie) {
    const pieData = series[0].data as any[]
    csv = '分类,值\n'
    pieData.forEach(d => {
      csv += `${d.name},${d.value}\n`
    })
  } else {
    // 柱状图/折线图：分类 + 每个系列
    const header = ['分类', ...series.map(s => s.name || 'series')].join(',')
    csv = header + '\n'
    const maxLen = Math.max(categories.length, ...series.map(s => (s.data || []).length))
    for (let i = 0; i < maxLen; i++) {
      const row = [categories[i] || '', ...series.map(s => s.data?.[i] ?? '')].join(',')
      csv += row + '\n'
    }
  }

  // 加 BOM 防中文乱码
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.title || 'data'}_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  nextTick(initChart)
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

watch(() => props.option, () => {
  chart?.setOption(props.option, true)
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  margin-top: 8px;
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-md);
  overflow: hidden;
  background: var(--aws-card);
}
.chart-canvas {
  width: 100%;
  height: 320px;
}
.chart-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--aws-border);
  background: var(--aws-sidebar);
}
.chart-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border: 1px solid var(--aws-border);
  border-radius: var(--aws-radius-sm);
  background: var(--aws-card);
  color: var(--aws-foreground);
  font-size: var(--aws-text-xs);
  cursor: pointer;
  transition: all 0.2s;
}
.chart-btn:hover {
  border-color: var(--aws-primary);
  color: var(--aws-primary);
  background: color-mix(in srgb, var(--aws-primary) 6%, transparent);
}
</style>
