<script setup>
import { useRoute } from 'vue-router'
import ChartBox from '../components/ChartBox.vue'
// P4 浪点详情页迁移点位（日期条/逐日卡片/回看/模式/直播内嵌/偏差校准）。
// ChartBox 已就位（P2.3），P4 接 /api/report 后按 day 渲染。
const route = useRoute()
</script>

<template>
  <main class="wrap">
    <h1>浪点详情</h1>
    <p>slug：{{ route.params.slug }}（P4 迁移中，图表组件 ChartBox 已就位）</p>
    <!-- P4 将以 v-for day in report.days 渲染 <ChartBox :day="day" /> -->
    <ChartBox v-if="false" :day="{}" />
    <router-link to="/">← 返回首页</router-link>
  </main>
</template>
