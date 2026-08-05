<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { swr, cached } from '../swr'
import { setFacing } from '../charts'
import ChartBox from '../components/ChartBox.vue'
import LiveCam from '../components/LiveCam.vue'
import LockBadge from '../components/LockBadge.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const report = ref(null)

// 可信度一等公民（tech.md）：浪高若由 best_match 备用模型救回（主模型该格点无数据），
// 必须显式告知——不能静默换源。缺 dataSource 字段（旧缓存）时不提示，也不编造。
const fallbackSource = computed(() => {
  const ds = (report.value?.days || []).flatMap(d => d.dataSource || [])
  return ds.some(s => String(s).includes('fallback'))
})
const history = ref(null)
const bias = ref(null)
const hasLive = ref(false)
const liveSrc = ref('')     // 登录后从 /api/cams 取到的 HLS 源（测试期账号解锁）
const sel = ref(0)          // 选中日索引
const loading = ref(true)
const error = ref('')

function applyReport(rep) {
  setFacing(rep.spotFacingDeg || 157)
  report.value = rep
  sel.value = (rep.ranking && rep.ranking[0]) || rep.days.findIndex(d => d.best) || 0
  if (sel.value < 0) sel.value = 0
  loading.value = false
}

async function load() {
  error.value = ''
  const slug = route.params.slug
  // catalog 走 SWR（目录页来过则 0 请求即得坐标）
  const catCached = cached('catalog')
  let cat = catCached?.catalog || null
  // report SWR：来过该浪点则秒渲染旧报告，后台刷新
  const repKey = `report|${slug}`
  const hasRep = swr(repKey, async () => {
    if (!cat) cat = ((await api.catalog()).catalog || [])
    const s = cat.find(x => x.slug === slug)
    if (!s) throw new Error('浪点不存在')
    hasLive.value = !!s.has_live
    const [rep, hist, b] = await Promise.all([
      api.report(s.lat, s.lon, s.name, 6),
      api.history(s.lat, s.lon, s.name).catch(() => null),
      api.bias(s.name).catch(() => null),
    ])
    return { rep, hist: hist?.history || null, bias: b, hasLive: !!s.has_live }
  }, (v, fresh, err) => {
    if (v) {
      applyReport(v.rep)
      history.value = v.hist
      bias.value = v.bias
      hasLive.value = v.hasLive
    } else if (err && !report.value) {
      error.value = '实时浪报暂不可用，请稍后重试'
      loading.value = false
    }
  })
  loading.value = !hasRep && !report.value
}

const day = computed(() => report.value?.days?.[sel.value] || null)

// 小白/高手模式（localStorage 记忆）
const mode = ref(localStorage.getItem('sf_mode_v1') || 'novice')
function setMode(m) { mode.value = m; localStorage.setItem('sf_mode_v1', m) }

// 昨日自评（best-effort：登录态落库，匿名/失败仅本地致谢，不阻塞）
// 直播解锁：登录且该浪点有摄像头 → 取 cams 目录里的 HLS 源
async function loadLive() {
  liveSrc.value = ''
  if (!hasLive.value || !auth.authenticated) return
  try {
    const { cams } = await api.cams()
    const cam = (cams || []).find(c => c.slug === route.params.slug)
    liveSrc.value = cam?.live_src || ''
  } catch { /* 未登录/接口失败 → 维持占位条 */ }
}
watch(() => [auth.authenticated, hasLive.value], loadLive)

const voted = ref('')
const VOTE_LABELS = { accurate: '准', optimistic: '偏乐观', conservative: '偏保守', nosurf: '没下水' }
async function vote(kind) {
  voted.value = kind
  if (!history.value) return
  try {
    await fetch('/api/accuracy/vote', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spot: report.value.spot, date: history.value.date, kind }),
    })
  } catch (_) { /* best-effort，失败不打断本地反馈 */ }
}
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
      <p v-if="fallbackSource" class="srcnote">
        ⓘ 本浪点浪高取自 <b>best_match</b> 备用模型（主模型 ECMWF WAM025 在该海洋格点无数据）。
        谱峰周期 Tp 仅主模型提供，此处留空而非估算。
      </p>

      <LiveCam v-if="liveSrc" :src="liveSrc" :key="liveSrc" />
      <div v-else-if="hasLive" class="livehint">
        📹 该浪点有实时直播——登录后可看（测试期：右上角 👤 账号登录；作校验预报的信任工具）
      </div>

      <div class="modes">
        <button :class="{ on: mode === 'novice' }" @click="setMode('novice')">
          🐣 小白模式<small>哪天能冲，一句话</small>
        </button>
        <button :class="{ on: mode === 'expert' }" @click="setMode('expert')">
          🏄 高手模式<small>为什么好，图解分析</small>
        </button>
        <LockBadge />
      </div>

      <!-- 日期条 -->
      <div class="strip">
        <button v-for="(d, i) in report.days" :key="d.date"
                :class="{ on: i === sel, best: d.best }" @click="sel = i">
          <span class="wk">{{ d.week }}</span>
          <span class="sc">{{ d.score }}</span>
          <span v-if="d.best" class="star">🏆</span>
        </button>
      </div>

      <!-- 选中日卡片：小白=一句话结论+窗口/板型+行动方案；
           高手=图表/五维/物理课堂全解（恢复旧版大差异，图表只在高手态渲染） -->
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

        <button v-if="mode === 'novice'" class="whybtn" @click="setMode('expert')">
          🤔 为什么是 {{ day.score }} 分？看图解分析 →
        </button>

        <template v-if="mode === 'expert'">
          <div v-if="day.dims" class="dims">
            <span v-for="(v, k) in day.dims" :key="k" class="dim">{{ k }} <b>{{ v }}</b></span>
          </div>
          <ChartBox :day="day" />
          <div v-if="day.lesson" class="lesson"><b>📖 {{ day.lesson[0] }}</b><p>{{ day.lesson[1] }}</p></div>
        </template>

        <!-- 行动建议与顶部结论(novice)同文时不重复渲染（遗留：文案一字不差出现两次） -->
        <div v-if="day.plan && day.plan[1] !== day.novice" class="plan"><b>{{ day.plan[0] }}</b><p>{{ day.plan[1] }}</p></div>
        <div v-if="day.safety && day.safety.length" class="safety"><b>{{ day.safety[0] }}</b><p>{{ day.safety[1] }}</p></div>
      </section>

      <!-- 一句话剧情 -->
      <p v-if="report.story" class="story" v-html="report.story" />

      <!-- 下水核对 + 免责（动态，去硬编码）-->
      <section v-if="report.checklist?.length" class="checklist">
        <h3>✅ 下水前核对</h3>
        <ul><li v-for="c in report.checklist" :key="c">{{ c }}</li></ul>
      </section>

      <!-- 昨日回看：边缘化处理——默认折叠，移到页面底部，展开才渲染图表 -->
      <details v-if="history" class="review">
        <summary>🔁 昨日回看（{{ history.week }} {{ history.date }}）· 校验预报准度<span class="hint">展开 ▾</span></summary>
        <p>系统当时预报：{{ history.predict?.height }} · {{ history.predict?.period }} · {{ history.predict?.wind }} · {{ history.predict?.verdict }}</p>
        <ChartBox :day="history" />
        <div class="vote">
          <p class="vq">昨天报得准吗？</p>
          <div class="vbtns">
            <button v-for="(lbl, k) in VOTE_LABELS" :key="k" :class="{ on: voted === k }" @click="vote(k)">{{ lbl }}</button>
          </div>
          <p v-if="voted" class="vthx">已记录「{{ VOTE_LABELS[voted] }}」——多次自评会校准本浪点的系统性偏差，越用越准。</p>
        </div>
        <p v-if="bias && bias.bias && bias.bias !== 'insufficient'" class="bias">
          📊 根据你 {{ bias.samples }} 次自评：本浪点预报<b>{{ bias.bias }}</b>——{{ bias.suggestion }}
        </p>
      </details>

      <p v-if="report.disclaimer" class="disclaimer">{{ report.disclaimer }}</p>
    </template>
  </main>
</template>

<style scoped>
.bar { display: flex; align-items: center; gap: 10px; }
h1 { font-size: 18px; color: var(--sea1); }
.ts { font-size: 11px; color: var(--ink2); }
.modes { display: flex; gap: 6px; margin: 6px 0; }
.livehint { font-size: 12.5px; background: var(--seabg); border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; margin: 6px 0; color: var(--sea); }
.modes button { display: flex; flex-direction: column; align-items: flex-start; padding: 6px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); font-size: 13.5px; font-weight: 600; }
.modes button small { font-size: 10.5px; font-weight: 400; color: var(--ink2); }
.modes button.on { background: var(--sea1); color: var(--card); border-color: var(--sea1); }
.modes button.on small { color: var(--seabg); }
.whybtn { display: block; width: 100%; margin-top: 10px; padding: 9px 12px; border: 1px dashed var(--sea2); border-radius: 10px; background: var(--seabg); color: var(--sea1); font-size: 13px; text-align: left; }
.vote { margin-top: 10px; }
.vq { font-size: 13px; font-weight: 600; }
.vbtns { display: flex; gap: 6px; flex-wrap: wrap; }
.vbtns button { padding: 6px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); font-size: 13px; }
.vbtns button.on { background: var(--ok); color: var(--card); border-color: var(--ok); }
.vthx { font-size: 12px; color: var(--ok); margin-top: 6px; }
.bias { font-size: 12.5px; background: var(--seabg); border-radius: 10px; padding: 8px 10px; margin-top: 8px; color: var(--sea); }
.strip { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; }
.strip button { display: flex; flex-direction: column; align-items: center; min-width: 52px; padding: 6px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); }
.strip button.on { border-color: var(--sea2); box-shadow: 0 0 0 2px rgba(14,165,233,.2); }
.strip .wk { font-size: 11px; color: var(--ink2); }
.strip .sc { font-size: 15px; font-weight: 700; color: var(--sea1); }
.daycard { background: var(--card); border-radius: 16px; padding: 14px; margin: 10px 0; }
.head { display: flex; align-items: baseline; gap: 10px; }
.score { font-size: 28px; font-weight: 800; color: var(--sea1); }
.tag { font-size: 14px; }
.verdict { color: var(--ink); margin: 8px 0; }
.kv { display: flex; gap: 12px; font-size: 13px; color: var(--ink2); }
.dims { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.dim { font-size: 12px; background: var(--soft); border-radius: 8px; padding: 3px 9px; color: var(--ink2); }
.dim b { color: var(--sea1); }
.plan, .lesson, .safety { margin-top: 10px; font-size: 13px; }
.plan { background: var(--okbg); border-radius: 10px; padding: 8px 10px; }
.lesson { background: var(--seabg); border-radius: 10px; padding: 8px 10px; }
.safety { background: var(--warnbg); border-radius: 10px; padding: 8px 10px; color: var(--bad); }
.story { background: var(--card); border-radius: 12px; padding: 10px; font-size: 13px; }
.review { background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; margin: 10px 0; }
.review summary { font-size: 13px; color: var(--ink2); cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center; }
.review summary::-webkit-details-marker { display: none; }
.review summary .hint { font-size: 11px; color: var(--sea2); }
.review[open] summary { color: var(--sea1); font-weight: 600; margin-bottom: 8px; }
.review[open] summary .hint { display: none; }
.srcnote { font-size: 12px; color: var(--ink2); background: var(--soft); border-radius: 8px; padding: 6px 10px; margin: 6px 0; line-height: 1.6; }
.checklist h3 { font-size: 14px; color: var(--sea1); }
.checklist { background: var(--warnbg); border: 1px solid var(--warnline); border-radius: 12px; padding: 10px 14px; margin: 10px 0; }
.checklist ul { padding-left: 18px; font-size: 12.5px; color: var(--bad); }
.disclaimer { font-size: 11px; color: var(--ink2); line-height: 1.6; }
.degraded { background: var(--warnbg); border: 1px solid var(--warnline); border-radius: 12px; padding: 10px; color: var(--bad); }
</style>
