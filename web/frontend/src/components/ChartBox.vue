<script setup>
// 每日图表盒：风质条 + 浪高/双周期图 + 风潮图（复用 charts.js 手绘 SVG，零依赖）。
// v-html 渲染的是本方生成的数字 SVG（后端 numeric 契约，无用户内容）→ 无注入风险。
import { computed } from 'vue'
import { windQualityStrip, waveChart, windTideChart } from '../charts'

const props = defineProps({ day: { type: Object, required: true } })

const strip = computed(() => windQualityStrip(props.day))
const wave = computed(() => waveChart(props.day))
const tide = computed(() => windTideChart(props.day))
</script>

<template>
  <div class="chartbox">
    <div class="chart" v-html="strip" />
    <div class="chart" v-html="wave" />
    <div class="chart" v-html="tide" />
  </div>
</template>

<style scoped>
.chartbox { background: #fff; border-radius: 14px; padding: 10px; margin: 10px 0; }
.chart :deep(svg) { width: 100%; height: auto; display: block; }
.chart :deep(.windq) { display: flex; gap: 2px; }
.chart :deep(.seg) { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 4px 0; border-radius: 5px; color: #fff; }
.chart :deep(.wq-ar) { font-size: 13px; }
.chart :deep(.wq-k) { font-size: 11px; font-weight: 700; }
.chart :deep(.wq-h) { font-size: 8px; opacity: .9; }
.chart :deep(.windq-key) { display: flex; flex-wrap: wrap; gap: 8px; font-size: 10px; margin-top: 6px; color: #475569; }
.chart :deep(.windq-key i) { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 3px; vertical-align: middle; }
</style>
