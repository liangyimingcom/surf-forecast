<script setup>
import { useRoute } from 'vue-router'
// P4 浪点详情页迁移点位（日期条/逐日卡片/SVG图表/回看/模式/直播内嵌/偏差校准）。
const route = useRoute()
</script>

<template>
  <main class="wrap">
    <h1>浪点详情</h1>
    <p>slug：{{ route.params.slug }}（P4 迁移中……）</p>
    <router-link to="/">← 返回首页</router-link>
  </main>
</template>
