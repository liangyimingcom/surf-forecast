<script setup>
// 晨报决策首页（S2）——视觉规格：docs/design-v4-update1.html 第①屏。
// 数据全部取自现有接口，后端零改动：
//   /api/regions   → 地区 chips
//   /api/recommend → verdict / 覆盖计数 / 亚军
//   /api/catalog + /api/report → 本周走势（渐进增强，见 loadTrend）
// 🚫 原型①里的「今日注意告警」「现场众报」「三点横评的人流/车程列」本轮不做：
//    无数据源（降水/流场、众报投票表、车程矩阵），做了就是编造 —— 见 north_star 围栏 2。
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { swr } from '../swr'
import { sparkline, WIND_META } from '../charts'
import { convertHeights } from '../units'
import { useRegionStore } from '../stores/region'

const region = useRegionStore()
const regions = ref([])
const rec = ref(null)
const trend = ref(null)          // 最佳浪点的逐日报告（仅用于走势 + tag）
const loading = ref(true)
const error = ref('')

const GMT8 = 'Asia/Shanghai'
// 报头日期：GMT+8 日界（禁用 UTC 推星期——v1 星期错一天的教训）
const todayLine = computed(() => {
  const f = new Intl.DateTimeFormat('zh-CN', {
    timeZone: GMT8, month: 'long', day: 'numeric', weekday: 'long',
  })
  return f.format(new Date())
})

function load() {
  error.value = ''
  const hasRegions = swr('regions', () => api.regions(), (v, fresh, err) => {
    if (v) regions.value = v.regions || []
    else if (err && !regions.value.length) error.value = '实时数据暂不可用，请稍后重试'
  })
  const key = `recommend|${region.region || ''}`
  const hasRec = swr(key, () => api.recommend(region.region), (v, fresh, err) => {
    if (v) { rec.value = v; loading.value = false; loadTrend() }
    else if (err) { error.value = '实时数据暂不可用，请稍后重试'; loading.value = false }
  })
  loading.value = !(hasRegions || hasRec) && !rec.value
  if (hasRec) loading.value = false
}

// 后端 `_key_factors` 直接把 `dawnWind` 的**原始枚举**（off/cross/on）与 `Tp{n}s` 塞进 chips。
// 零上下文用户评审实测：`off` 会被读成「关闭/没风」，而它其实是**最好**的风况（离岸=梳面）；
// `Tp` 对非物理背景用户是纯噪音。这里只做**显示层翻译**，标签复用 charts.WIND_META
// （与风质条/罗盘同一个标签来源，不新造口径）；认不出的 chip 一律原样透出，不猜。
// 🔒 根治应在后端 `src/web/recommend.py` 出人话，本轮后端零改动故先在前端兜。
const factorChips = computed(() => {
  const kf = rec.value?.best?.key_factors
  if (!Array.isArray(kf)) return []
  return kf.map((f) => {
    const s = String(f)
    if (WIND_META[s]) return `晨风${WIND_META[s].label}·${WIND_META[s].desc}`
    const m = s.match(/^Tp(\d+(?:\.\d+)?)s$/)
    if (m) return `峰周期 ${m[1]}s`
    return convertHeights(s)        // 「1.4m浪」随单位设置走
  })
})

// 走势 = 最佳浪点 days[].score。recommend 只给一天，故要取该点 report；
// 但**不让它阻塞首屏**：verdict 先渲染，走势卡等数据到了再出现（渐进增强）。
function loadTrend() {
  trend.value = null
  const b = rec.value && rec.value.best
  if (!b || !b.spot_slug) return
  swr('catalog', () => api.catalog(), (cat) => {
    const row = ((cat && cat.catalog) || []).find(s => s.slug === b.spot_slug)
    if (!row) return                                  // 解析不到坐标就不画（不猜）
    // ⚠️ 键名必须与 SpotPage 区分开：SpotPage 用 `report|<slug>` 存的是
    // { rep, hist, bias, hasLive } 包装对象；这里只要裸 report。
    // 同键不同形状会让详情页 applyReport(v.rep) 拿到 undefined → 整页白（本轮实测踩到）。
    swr(`trend|${row.slug}`, () => api.report(row.lat, row.lon, row.name), (rep) => {
      if (rep && (rep.days || []).length) trend.value = rep
    })
  })
}

function pick(r) { region.set(r); rec.value = null; trend.value = null; load() }

const firstVisit = computed(() => !region.region)
const spark = computed(() => (trend.value ? sparkline(trend.value.days) : ''))
// tag（必冲/值得等）只在 report 到位时显示——recommend 不含此字段，不编造
const bestTag = computed(() => {
  const b = rec.value && rec.value.best
  if (!b || !trend.value) return ''
  const d = (trend.value.days || []).find(x => x.date === b.day) || null
  return d ? (d.tag || '') : ''
})
const calibratedAt = computed(() => (trend.value && trend.value.calibratedAt) || '')

onMounted(load)
</script>

<template>
  <main class="wrap">
    <div class="brand">
      <span>浪报 SURF DAILY · {{ todayLine }}</span>
    </div>

    <p v-if="firstVisit" class="onboard">👋 选一个地区，一屏告诉你<b>这周该去哪冲、哪天去</b>：</p>
    <div class="regions">
      <button v-for="r in regions" :key="r.region"
              :class="{ on: r.region === region.region }" @click="pick(r.region)">
        {{ r.region }} ({{ r.count }})
      </button>
    </div>

    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="degraded">⚠️ {{ error }}</p>

    <template v-else-if="rec">
      <template v-if="rec.best">
        <!-- verdict：报纸头条式一句话结论 -->
        <h1 class="verdict paper-title">
          这周去<em>{{ rec.best.spot_name }}</em>，<br>{{ rec.best.week }}最值得。
        </h1>
        <p class="sub">
          {{ rec.region || '全区' }} · {{ rec.fresh_count }}/{{ rec.total_count }} 浪点今日评分可用
          <span v-if="rec.degraded" class="warnnote">· 部分点非当日新鲜，已排除</span>
        </p>

        <section class="paper-card answer">
          <span class="score paper-num">{{ rec.best.score }}<small>/10</small></span>
          <span v-if="bestTag" class="tag">{{ bestTag }}</span>
          <div class="headline">「{{ rec.best.headline }}」</div>
          <span v-for="f in factorChips" :key="f" class="chip">{{ f }}</span>
          <div class="entries">
            <router-link :to="`/spot/${rec.best.spot_slug}`">为什么是这天？</router-link>
            <router-link :to="`/spot/${rec.best.spot_slug}#review`">昨天报得准吗？</router-link>
            <router-link to="/spots">看全国浪况 ▸</router-link>
          </div>
        </section>

        <template v-if="(rec.alternatives || []).length">
          <div class="paper-sect">同区其他选择</div>
          <section class="paper-card alts">
            <router-link v-for="a in rec.alternatives" :key="a.spot_slug"
                         :to="`/spot/${a.spot_slug}`" class="alt">
              <span>{{ a.week }} {{ a.spot_name }}</span><b>{{ a.score }}</b>
            </router-link>
          </section>
        </template>

        <!-- 本周走势：数据到位才出现（渐进增强，不阻塞首屏） -->
        <template v-if="spark">
          <div class="paper-sect">📈 本周走势 · {{ rec.best.spot_name }}</div>
          <section class="paper-card trend" v-html="spark" />
        </template>
      </template>

      <p v-else class="degraded">
        本区域暂无「当日新鲜」评分（{{ rec.fresh_count }}/{{ rec.total_count }}），不展示陈旧数据。
        <router-link to="/status">查看数据健康 ▸</router-link>
      </p>

      <p class="foot">
        <template v-if="calibratedAt">数据 {{ calibratedAt }} 校准 · </template>
        先验证过去，再相信未来 → <router-link to="/status">数据健康</router-link>
      </p>
    </template>
  </main>
</template>

<style scoped>
.brand { display: flex; justify-content: space-between; align-items: center;
         padding-right: 96px;   /* 让位给右上固定的 🌙/👤 悬浮按钮 */
         font-size: 12px; letter-spacing: 2px; color: var(--ink2);
         padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.onboard { font-size: 13px; color: var(--ink2); margin: 12px 0 8px; }
.onboard b { color: var(--ink); }
.regions { display: flex; flex-wrap: wrap; gap: 7px; margin: 12px 0 4px; }
.regions button { padding: 6px 13px; border: 1px solid var(--line); border-radius: 999px;
                  background: var(--card); color: var(--ink2); font-size: 13px; cursor: pointer; }
.regions button.on { background: var(--sea); border-color: var(--sea); color: var(--card); font-weight: 600; }

.verdict { margin: 16px 0 2px; }
.verdict em { font-style: normal; color: var(--sea); border-bottom: 3px solid var(--sea2); }
.sub { font-size: 12.5px; color: var(--ink2); margin: 0 0 10px; }
.warnnote { color: var(--warn); }

.answer { padding: 13px 15px; margin: 10px 0; }
.score { font-size: 38px; font-weight: 800; color: var(--sea); }
.score small { font-size: 14px; color: var(--ink2); font-weight: 400; }
.tag { font-size: 13px; color: var(--hot); font-weight: 700; margin-left: 6px; }
.headline { font-family: var(--serif); font-size: 15px; margin: 8px 0 4px; }
.chip { display: inline-block; font-size: 11.5px; background: var(--soft); border-radius: 999px;
        padding: 3px 10px; margin: 3px 4px 0 0; color: var(--ink2); }
.entries { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 10px;
           border-top: 1px dashed var(--line); padding-top: 9px; font-size: 13px; }

.alts { padding: 2px 14px; margin: 6px 0 0; }
.alt { display: flex; justify-content: space-between; align-items: center;
       font-size: 13px; padding: 9px 0; text-decoration: none; color: var(--ink);
       border-top: 1px dashed var(--line); }
.alt:first-child { border-top: 0; }
.alt b { color: var(--sea); }

.trend { padding: 8px 12px 2px; margin: 6px 0 0; }
.degraded { background: var(--warnbg); border: 1px solid var(--warnline); color: var(--warn);
            border-radius: var(--radius); padding: 11px 13px; font-size: 13px; line-height: 1.7; }
.muted { color: var(--ink2); font-size: 13px; }
.foot { font-size: 11px; color: var(--ink2); margin-top: 16px; }
</style>
