<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { swr, cached } from '../swr'
import { countdown, departure } from '../countdown'
import { compass, windKind, WIND_META, setFacing } from '../charts'
import { unit, toggleUnit, convertHeights } from '../units'
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
const facingMeta = ref({ spot: null, calibrated: false })
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
    // 目录里带该点的朝向估计与校准标记 —— 只用于诚实标注，**不**拿来改判定源：
    // 判定必须与后端风向评分同源（thresholds.yaml 的全站 spot_facing_deg），否则口径分叉。
    facingMeta.value = { spot: typeof s.facing === 'number' ? s.facing : null, calibrated: !!s.facing_calibrated }
    const [rep, hist, b] = await Promise.all([
      api.report(s.lat, s.lon, s.name, 6),
      api.history(s.lat, s.lon, s.name).catch(() => null),
      api.bias(s.name).catch(() => null),
    ])
    return { rep, hist: hist?.history || null, bias: b, hasLive: !!s.has_live,
             facingMeta: { spot: typeof s.facing === 'number' ? s.facing : null, calibrated: !!s.facing_calibrated } }
  }, (v, fresh, err) => {
    if (v) {
      applyReport(v.rep)
      history.value = v.hist
      bias.value = v.bias
      hasLive.value = v.hasLive
      // 缓存命中时 fetcher 不跑 → 这里必须一并回填（旧缓存无此字段则保持默认）
      if (v.facingMeta) facingMeta.value = v.facingMeta
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

// —— S3 倒计时 + 通勤倒推（纯前端，逻辑在 countdown.js，便于用假时钟钉边界）——
const nowTick = ref(Date.now())
let timer = null
onMounted(() => { timer = setInterval(() => { nowTick.value = Date.now() }, 1000) })
onUnmounted(() => { if (timer) clearInterval(timer) })

const COMMUTE_KEY = 'sf_commute_v1'
const commute = ref(Number(localStorage.getItem(COMMUTE_KEY) || 45))
function setCommute(delta) {
  commute.value = Math.min(240, Math.max(0, commute.value + delta))
  try { localStorage.setItem(COMMUTE_KEY, String(commute.value)) } catch (e) { /* 隐私模式忽略 */ }
}
const cdown = computed(() => (day.value ? countdown(day.value, new Date(nowTick.value)) : null))
const depart = computed(() => (day.value ? departure(day.value, commute.value) : null))

// 🧭 罗盘（高手模式）。晨风结论也走 windKind，避免与罗盘/风质条口径分叉。
// 单位切换只影响**显示**。后端已格式化的高度文本里，当前 UI 只渲染了昨日回看的 predict.height
// （`pa` 五维解释与 `tideText` 原型和现有页面都不呈现 → 不为它们预留死代码）。
const histHeight = computed(() => convertHeights(history.value && history.value.predict && history.value.predict.height))

const facingDeg = computed(() => {
  const f = report.value && report.value.spotFacingDeg
  return typeof f === 'number' && !Number.isNaN(f) ? Math.round(f) : null
})
// 🔍 诚实标注：`spotFacingDeg` 来自 config/thresholds.yaml 的**全站统一** spot_facing_deg，
//    不是逐点实测朝向（注册表里另有逐点估计 `facing`，但 facing_calibrated 全为 false，
//    且引擎并未采用它）。既然离岸/向岸是一等参数，就不能把这个度数说得像测量值。
const facingNote = computed(() => {
  if (facingDeg.value == null) return null
  if (facingMeta.value.calibrated) return null      // 真校准过 → 无需附注
  const spot = facingMeta.value.spot
  const differs = typeof spot === 'number' && Math.abs(spot - facingDeg.value) >= 10
  return differs
    ? `分析口径，未逐点校准（目录另记该点约 ${Math.round(spot)}°，引擎暂未采用）`
    : '分析口径，未逐点校准'
})
const compassSvg = computed(() => (day.value ? compass(day.value) : ''))
const dawnKind = computed(() => {
  const d = day.value
  if (!d || !Array.isArray(d.times) || !Array.isArray(d.wdeg)) return null
  const i = d.times.indexOf(6)
  if (i < 0 || typeof d.wdeg[i] !== 'number') return null
  const k = windKind(d.wdeg[i])
  return { kind: k, label: WIND_META[k].label, desc: WIND_META[k].desc }
})
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
        <button v-if="mode === 'expert'" class="unitbtn" @click="toggleUnit()"
                :aria-label="'切换浪高单位，当前 ' + unit">{{ unit === 'm' ? 'm ⇄ ft' : 'ft ⇄ m' }}</button>
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
          <!-- 明写「下水」：引擎 window=最佳可冲时段，而通勤卡另有「出门」时刻，
               不标注会被读成到达时间（零上下文评审实测：可能整整迟到一小时）。 -->
          <span v-if="day.window">🕐 下水窗口 {{ day.window }}</span>
          <span v-if="day.board">🏄 {{ day.board }}</span>
        </div>

        <p v-if="cdown" class="cdown" :class="cdown.state">⏳ {{ cdown.text }}</p>

        <button v-if="mode === 'novice'" class="whybtn" @click="setMode('expert')">
          🤔 为什么是 {{ day.score }} 分？看图解分析 →
        </button>

        <template v-if="mode === 'expert'">
          <div v-if="day.dims" class="dims">
            <span v-for="(v, k) in day.dims" :key="k" class="dim">{{ k }} <b>{{ v }}</b></span>
          </div>
          <ChartBox :day="day" />

          <!-- 🧭 风向罗盘：扇区=浪点朝向，三支箭=06/12/18 时风矢量；判定复用 windKind -->
          <div v-if="compassSvg" class="compasscard">
            <div class="cmp" v-html="compassSvg" />
            <div class="cmptext">
              <b>🧭 风向罗盘</b>
              <p>扇区＝接浪朝向<template v-if="facingDeg != null">（{{ facingDeg }}°<template v-if="facingNote"><abbr :title="facingNote">*</abbr></template>）</template>。三支箭＝06/12/18 时风矢量。<br>
                <template v-if="facingNote"><small class="fnote">＊{{ facingNote }}</small><br></template>
                <template v-if="dawnKind">晨风<b :class="'wk-' + dawnKind.kind">{{ dawnKind.label }}</b>·{{ dawnKind.desc }}<template v-if="dawnKind.kind === 'off'">——箭头指向海面即离岸，梳面最佳。</template></template>
                <template v-else>晨 06 时无风向数据，未作判定。</template>
              </p>
            </div>
          </div>

          <div v-if="day.lesson" class="lesson"><b>📖 {{ day.lesson[0] }}</b><p>{{ day.lesson[1] }}</p></div>
        </template>

        <!-- 行动建议与顶部结论(novice)同文时不重复渲染（遗留：文案一字不差出现两次） -->
        <div v-if="day.plan && day.plan[1] !== day.novice" class="plan"><b>{{ day.plan[0] }}</b><p>{{ day.plan[1] }}</p></div>
        <div v-if="day.safety && day.safety.length" class="safety"><b>{{ day.safety[0] }}</b><p>{{ day.safety[1] }}</p></div>
      </section>

      <!-- 几点出门（通勤倒推）：纯前端推算，不依赖后端字段；仅小白模式（原型②） -->
      <section v-if="mode === 'novice' && depart" class="daycard departcard">
        <div class="paper-sect">🚗 几点出门（按你的通勤自动倒推）</div>
        <p class="departline">
          <b class="paper-num">{{ depart.depart }}</b>
          <span v-if="depart.prevDay" class="prevday">前一天</span>
          <span class="arrow">出门 →</span>
          <span>{{ depart.water }} 下水</span>
        </p>
        <p class="commuterow">
          车程
          <button @click="setCommute(-5)" title="车程 −5 分钟" aria-label="车程减 5 分钟">−</button>
          <b>{{ commute }}min</b>
          <button @click="setCommute(5)" title="车程 ＋5 分钟" aria-label="车程加 5 分钟">＋</button>
          ＋ 收拾装备 15min ＝ 提前 {{ depart.total }}min
        </p>
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
        <p>系统当时预报：{{ histHeight }} · {{ history.predict?.period }} · {{ history.predict?.wind }} · {{ history.predict?.verdict }}</p>
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
.strip button.on { border-color: var(--sea2); box-shadow: 0 0 0 2px var(--halo); }
.strip .wk { font-size: 11px; color: var(--ink2); }
.strip .sc { font-size: 15px; font-weight: 700; color: var(--sea1); }
.daycard { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px; margin: 10px 0; }
.modes .unitbtn { margin-left: auto; align-self: center; font-size: 11.5px; color: var(--sea);
                  border: 1px solid var(--line); background: var(--card); border-radius: 999px;
                  padding: 4px 12px; cursor: pointer; font-weight: 600; }
.compasscard { display: flex; gap: 12px; align-items: center; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 12px; margin: 10px 0; }
.compasscard .cmp { width: 124px; flex-shrink: 0; }
.compasscard .cmp :deep(svg) { width: 124px; height: auto; display: block; }
.compasscard .cmptext { font-size: 12px; color: var(--ink2); line-height: 1.7; }
.compasscard .cmptext b { color: var(--ink); }
.compasscard .fnote { font-size: 10.5px; color: var(--ink2); opacity: .85; }
.compasscard abbr { text-decoration: none; color: var(--warn); cursor: help; }
.compasscard .wk-off { color: var(--ch-off); }
.compasscard .wk-cross { color: var(--ch-cross); }
.compasscard .wk-on { color: var(--ch-on); }
.cdown { font-family: var(--serif); font-size: 13px; color: var(--hot); margin: 8px 0 0; }
.cdown.during { color: var(--ok); font-weight: 700; }
.cdown.after { color: var(--ink2); }
.departcard .departline { display: flex; align-items: baseline; gap: 8px; margin: 6px 0 4px; font-size: 13px; }
.departcard .departline b { font-size: 26px; color: var(--sea); }
.departcard .prevday { font-size: 10.5px; background: var(--warnbg); color: var(--warn); border-radius: 5px; padding: 1px 5px; }
.departcard .arrow { color: var(--ink2); }
.departcard .commuterow { font-size: 11.5px; color: var(--ink2); margin: 0; }
.departcard .commuterow b { color: var(--ink); font-variant-numeric: tabular-nums; margin: 0 2px; }
.departcard .commuterow button { width: 24px; height: 24px; border: 1px solid var(--line); border-radius: 50%;
                                 background: var(--card); color: var(--ink); font-size: 14px; line-height: 1; cursor: pointer; }
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
