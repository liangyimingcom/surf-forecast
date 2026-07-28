<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

// R2 §3.2 公开状态页：站长运维仪表 + 用户信任背书（系统坦白数据健康）。
const st = ref(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try { st.value = await api.status() }
  catch (e) { error.value = '状态数据暂不可用' }
  finally { loading.value = false }
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
.card { background: #fff; border-radius: 16px; padding: 14px 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid #e2e8f0; }
th { color: var(--ink2); font-weight: 600; }
.ok { color: #15803d; }
.warn { color: #b45309; font-size: 13px; }
.bad { background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 10px; color: #9a3412; }
.ts { font-size: 11px; color: var(--ink2); }
</style>
