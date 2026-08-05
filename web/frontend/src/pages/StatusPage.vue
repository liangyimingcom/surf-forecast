<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../api'
import { swr } from '../swr'

// R2 §3.2 公开状态页：站长运维仪表 + 用户信任背书（系统坦白数据健康）。
const st = ref(null)
const error = ref('')
const loading = ref(true)

// R1.2：失败点带原因（上游格点无数据 / validate 不过 / 取数异常），
// 光看 slug 列表判不出该找上游还是找代码。后端 failed_detail 缺失时降级为空（不编造）。
const failedDetail = computed(() => {
  const d = st.value && st.value.refresh && st.value.refresh.failed_detail
  return d ? Object.keys(d).sort().map(k => ({ slug: k, why: d[k] })) : []
})

// R2：坏数据必须能在这个页面被看见（本项目无推送告警，/status 是唯一发现渠道）。
// 后端未提供 data_issues 时返回 null → 整块不渲染（不编造"一切正常"）。
const dataIssues = computed(() => {
  const di = st.value && st.value.data_issues
  if (!di) return null
  return {
    coordInvalid: di.coord_invalid || [],
    coordDupes: di.coord_duplicates || [],
    benignN: di.coord_duplicates_benign_n || 0,
    compColl: di.coord_component_collisions || [],
  }
})

onMounted(() => {
  const has = swr('status', () => api.status(), (v, fresh, err) => {
    if (v) { st.value = v; loading.value = false }
    else if (err && !st.value) { error.value = '状态数据暂不可用'; loading.value = false }
  })
  loading.value = !has
})
</script>

<template>
  <main class="wrap">
    <p class="back"><router-link to="/">← 首页</router-link></p>
    <h1>📡 数据健康</h1>
    <p class="sub">先验证过去，再相信未来——预报系统的数据健康对你透明。</p>

    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="bad">⚠️ {{ error }}</p>

    <template v-else-if="st">
      <section class="card">
        <h2>今日评分刷新</h2>
        <p v-if="st.refresh && st.refresh.is_today">
          {{ st.refresh.run_at }}（{{ st.refresh.kind === 'retry' ? '06:00 补跑' : '主跑' }}）
          · 覆盖 <b>{{ st.refresh.succeeded }}/{{ st.refresh.expected }}</b>
          <span v-if="st.refresh.succeeded >= st.refresh.expected" class="ok">✅</span>
          <span v-else class="warn">⚠️</span>
        </p>
        <p v-else class="bad">⚠️ 今日刷新尚未运行（最近记录：{{ st.refresh ? st.refresh.date : '无' }}）</p>
        <p v-if="st.refresh && st.refresh.failed && st.refresh.failed.length" class="warn">
          失败点：{{ st.refresh.failed.join('、') }}
        </p>
        <ul v-if="failedDetail.length" class="faillist">
          <li v-for="f in failedDetail" :key="f.slug">
            <b>{{ f.slug }}</b> — {{ f.why }}
          </li>
        </ul>
      </section>

      <section v-if="dataIssues" class="card">
        <h2>数据治理待办</h2>
        <p v-if="!dataIssues.coordInvalid.length && !dataIssues.coordDupes.length && !dataIssues.compColl.length" class="ok">
          ✅ 未检出坐标非法或坐标重复
        </p>
        <template v-else>
          <div v-if="dataIssues.coordInvalid.length">
            <p class="warn">坐标非法（已隔离出刷新池，目录仍可见）：</p>
            <ul class="faillist">
              <li v-for="c in dataIssues.coordInvalid" :key="c.slug">
                <b>{{ c.slug }}</b> {{ c.spot }} — {{ c.why }}
              </li>
            </ul>
          </div>
          <div v-if="dataIssues.coordDupes.length">
            <p class="warn">坐标重复·可疑（跨海滩/跨区域同坐标，坐标→浪点解析有歧义）：</p>
            <ul class="faillist">
              <li v-for="d in dataIssues.coordDupes" :key="d.coord">
                {{ d.coord }} — {{ d.slugs.join('、') }}（{{ d.spots.join('、') }}）
                <span v-if="d.regions && d.regions.length > 1">· 跨区：{{ d.regions.join('/') }}</span>
              </li>
            </ul>
          </div>
          <div v-if="dataIssues.compColl.length">
            <p class="warn">坐标分量串行·可疑（不同区域的浪点共用同一个高精度经/纬度值）：</p>
            <ul class="faillist">
              <li v-for="c in dataIssues.compColl" :key="c.component + c.value">
                {{ c.component }}={{ c.value }} — {{ c.slugs.join('、') }}（{{ c.spots.join('、') }}）
                · 跨区：{{ c.regions.join('/') }}
              </li>
            </ul>
          </div>
        </template>
        <p v-if="dataIssues.benignN" class="hint">
          另有 {{ dataIssues.benignN }} 组同海滩不同机位的同坐标浪点，属预期，不计为故障。
        </p>
      </section>

      <section class="card">
        <h2>各地区推荐可用性</h2>
        <table>
          <thead><tr><th>地区</th><th>可推荐池</th><th>今日新鲜</th><th>推荐</th></tr></thead>
          <tbody>
            <tr v-for="r in st.regions" :key="r.region">
              <td>{{ r.region }}</td>
              <td>{{ r.pool }}</td>
              <td>{{ r.fresh }}</td>
              <td>{{ r.available ? '✅' : '❌' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card">
        <h2>最近刷新记录</h2>
        <table>
          <thead><tr><th>时间</th><th>类型</th><th>覆盖</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="h in st.history" :key="h.run_id + h.run_at">
              <td>{{ h.run_at }}</td>
              <td>{{ h.kind === 'retry' ? '补跑' : '主跑' }}</td>
              <td>{{ h.ok_n }}/{{ h.expected_n }}</td>
              <td>{{ h.duration_s }}s</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!st.history || !st.history.length" class="sub">暂无运行记录（manifest 尚未生成）。</p>
      </section>

      <p class="ts">{{ st.generated_at }}</p>
    </template>
  </main>
</template>

<style scoped>
h1 { font-size: 20px; color: var(--sea1); }
h2 { font-size: 14px; margin: 0 0 8px; }
.back { font-size: 13px; }
.sub { font-size: 12.5px; color: var(--ink2); }
.card { background: var(--card); border-radius: 16px; padding: 14px 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); }
th { color: var(--ink2); font-weight: 600; }
.ok { color: var(--ok); }
.warn { color: var(--warn); font-size: 13px; }
.hint { color: var(--ink2); font-size: 12px; margin-top: 6px; }
.faillist { margin: 4px 0 0; padding-left: 18px; color: var(--warn); font-size: 12.5px; line-height: 1.6; }
.bad { background: var(--warnbg); border: 1px solid var(--warnline); border-radius: 12px; padding: 10px; color: var(--bad); }
.ts { font-size: 11px; color: var(--ink2); }
</style>
