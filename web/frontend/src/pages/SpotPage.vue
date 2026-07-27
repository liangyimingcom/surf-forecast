<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { setFacing } from '../charts'
import ChartBox from '../components/ChartBox.vue'

const route = useRoute()
const report = ref(null)
const history = ref(null)
const sel = ref(0)          // 选中日索引
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true; error.value = ''
  try {
    // slug → 坐标（复用公开 catalog）
    const cat = (await api.catalog()).catalog || []
    const s = cat.find(x => x.slug === route.params.slug)
    if (!s) throw new Error('浪点不存在')
    // 并行取 report + history（沿用提速思路）
    const hp = api.history(s.lat, s.lon, s.name).catch(() => null)
    const rep = await api.report(s.lat, s.lon, s.name, 6)
    setFacing(rep.spotFacingDeg || 157)
    report.value = rep
    sel.value = (rep.ranking && rep.ranking[0]) || rep.days.findIndex(d => d.best) || 0
    if (sel.value < 0) sel.value = 0
    history.value = (await hp)?.history || null
  } catch (e) {
    error.value = '实时浪报暂不可用，请稍后重试'
  } finally { loading.value = false }
}

const day = computed(() => report.value?.days?.[sel.value] || null)
onMounted(load)
</script>

<template>
  <main class="wrap">
    <header class="bar">
      <router-link to="/spots">← 目录</router-link>
      <h1>{{ report?.spot || '浪点详情' }}</h1>
    </header>

    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="degraded">⚠️ {{ error }} <button @click="load">重试</button></p>

    <template v-else-if="report">
      <p class="ts">校准 {{ report.calibratedAt }}</p>

      <!-- 日期条 -->
      <div class="strip">
        <button v-for="(d, i) in report.days" :key="d.date"
                :class="{ on: i === sel, best: d.best }" @click="sel = i">
          <span class="wk">{{ d.week }}</span>
          <span class="sc">{{ d.score }}</span>
          <span v-if="d.best" class="star">🏆</span>
        </button>
      </div>

      <!-- 选中日卡片 -->
      <section v-if="day" class="daycard">
        <div class="head">
          <span class="score">{{ day.score }}<small>/10</small></span>
          <span class="tag">{{ day.tag }}</span>
        </div>
        <p class="verdict">{{ day.novice }}</p>
        <div class="kv">
          <span v-if="day.window">🕐 {{ day.window }}</span>
          <span v-if="day.board">🏄 {{ day.board }}</span>
        </div>

        <ChartBox :day="day" />

        <div v-if="day.dims" class="dims">
          <span v-for="(v, k) in day.dims" :key="k" class="dim">{{ k }} <b>{{ v }}</b></span>
        </div>

        <div v-if="day.plan" class="plan"><b>{{ day.plan[0] }}</b><p>{{ day.plan[1] }}</p></div>
        <div v-if="day.lesson" class="lesson"><b>📖 {{ day.lesson[0] }}</b><p>{{ day.lesson[1] }}</p></div>
        <div v-if="day.safety && day.safety.length" class="safety"><b>{{ day.safety[0] }}</b><p>{{ day.safety[1] }}</p></div>
      </section>

      <!-- 一句话剧情 -->
      <p v-if="report.story" class="story" v-html="report.story" />

      <!-- 昨日回看（P4d 接自评/偏差；此处先展示预报对照）-->
      <section v-if="history" class="review">
        <h3>🔁 昨日回看（{{ history.week }} {{ history.date }}）</h3>
        <p>系统当时预报：{{ history.predict?.height }} · {{ history.predict?.period }} · {{ history.predict?.wind }} · {{ history.predict?.verdict }}</p>
        <ChartBox :day="history" />
      </section>

      <!-- 下水核对 + 免责（动态，去硬编码）-->
      <section v-if="report.checklist?.length" class="checklist">
        <h3>✅ 下水前核对</h3>
        <ul><li v-for="c in report.checklist" :key="c">{{ c }}</li></ul>
      </section>
      <p v-if="report.disclaimer" class="disclaimer">{{ report.disclaimer }}</p>
    </template>
  </main>
</template>

<style scoped>
.bar { display: flex; align-items: center; gap: 10px; }
h1 { font-size: 18px; color: var(--sea1); }
.ts { font-size: 11px; color: var(--ink2); }
.strip { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; }
.strip button { display: flex; flex-direction: column; align-items: center; min-width: 52px; padding: 6px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
.strip button.on { border-color: var(--sea2); box-shadow: 0 0 0 2px rgba(14,165,233,.2); }
.strip .wk { font-size: 11px; color: var(--ink2); }
.strip .sc { font-size: 15px; font-weight: 700; color: var(--sea1); }
.daycard { background: #fff; border-radius: 16px; padding: 14px; margin: 10px 0; }
.head { display: flex; align-items: baseline; gap: 10px; }
.score { font-size: 28px; font-weight: 800; color: var(--sea1); }
.tag { font-size: 14px; }
.verdict { color: var(--ink); margin: 8px 0; }
.kv { display: flex; gap: 12px; font-size: 13px; color: var(--ink2); }
.dims { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.dim { font-size: 12px; background: #f1f5f9; border-radius: 8px; padding: 3px 9px; color: var(--ink2); }
.dim b { color: var(--sea1); }
.plan, .lesson, .safety { margin-top: 10px; font-size: 13px; }
.plan { background: #ecfdf5; border-radius: 10px; padding: 8px 10px; }
.lesson { background: #eff6ff; border-radius: 10px; padding: 8px 10px; }
.safety { background: #fff7ed; border-radius: 10px; padding: 8px 10px; color: #9a3412; }
.story { background: #fff; border-radius: 12px; padding: 10px; font-size: 13px; }
.review { background: #fff; border-radius: 12px; padding: 12px; margin: 10px 0; }
.review h3, .checklist h3 { font-size: 14px; color: var(--sea1); }
.checklist { background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 10px 14px; margin: 10px 0; }
.checklist ul { padding-left: 18px; font-size: 12.5px; color: #7c2d12; }
.disclaimer { font-size: 11px; color: var(--ink2); line-height: 1.6; }
.degraded { background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 10px; color: #9a3412; }
</style>
