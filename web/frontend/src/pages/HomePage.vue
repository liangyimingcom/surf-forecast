<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useRegionStore } from '../stores/region'

const region = useRegionStore()
const regions = ref([])
const rec = ref(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true; error.value = ''
  try {
    if (!regions.value.length) regions.value = (await api.regions()).regions || []
    rec.value = await api.recommend(region.region)
  } catch (e) {
    error.value = '实时数据暂不可用，请稍后重试'
  } finally { loading.value = false }
}
function pick(r) { region.set(r); load() }
const firstVisit = computed(() => !region.region)   // 首访(未选地区)引导
onMounted(load)
</script>

<template>
  <main class="wrap">
    <h1>🏄 浪报 · 决策助手</h1>
    <p v-if="firstVisit" class="onboard">👋 选一个地区，一屏告诉你<b>这周该去哪冲、哪天去</b>：</p>
    <div class="regions">
      <button v-for="r in regions" :key="r.region"
              :class="{ on: r.region === region.region }" @click="pick(r.region)">
        {{ r.region }} ({{ r.count }})
      </button>
    </div>

    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="degraded">⚠️ {{ error }}</p>

    <section v-else-if="rec">
      <div v-if="rec.best" class="answer">
        <div class="verdict">✅ {{ rec.best.week }} {{ rec.best.day }} · {{ rec.best.spot_name }}｜{{ rec.best.score }} 分</div>
        <div class="headline">「{{ rec.best.headline }}」</div>
        <div class="factors"><span v-for="f in rec.best.key_factors" :key="f">{{ f }}</span></div>
        <div class="entries">
          <router-link :to="`/spot/${rec.best.spot_slug}`">为什么是这天？▾</router-link>
          <router-link :to="`/spot/${rec.best.spot_slug}`">昨天报得准吗？▾</router-link>
          <router-link to="/spots">看全国浪况 ▸</router-link>
        </div>
      </div>
      <p v-else class="degraded">
        本区域暂无「当日新鲜」评分（{{ rec.fresh_count }}/{{ rec.total_count }}），不展示陈旧数据。
      </p>
      <ul v-if="rec.alternatives && rec.alternatives.length" class="alts">
        <li v-for="a in rec.alternatives" :key="a.spot_slug">
          <router-link :to="`/spot/${a.spot_slug}`">{{ a.week }} {{ a.spot_name }} · {{ a.score }} 分</router-link>
        </li>
      </ul>
      <p v-if="rec.degraded && rec.best" class="note">
        ⓘ 本区域今日 {{ rec.fresh_count }}/{{ rec.total_count }} 个浪点评分可用。
      </p>
      <p class="ts">{{ rec.generated_at }}</p>
    </section>
  </main>
</template>

<style scoped>
h1 { font-size: 20px; color: var(--sea1); }
.onboard { font-size: 13.5px; color: var(--ink); margin: 4px 0 8px; }
.regions button { margin: 3px; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 999px; background: #fff; font-size: 13px; }
.regions button.on { background: var(--sea2); color: #fff; border-color: var(--sea2); }
.answer { background: #fff; border-radius: 16px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.verdict { font-size: 16px; font-weight: 700; }
.headline { color: var(--sea1); margin: 6px 0; }
.factors span { display: inline-block; margin-right: 8px; font-size: 12px; color: var(--ink2); }
.entries { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; font-size: 13px; }
.degraded { background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 10px; color: #9a3412; }
.note, .ts { font-size: 11px; color: var(--ink2); }
.alts { padding-left: 18px; }
</style>
