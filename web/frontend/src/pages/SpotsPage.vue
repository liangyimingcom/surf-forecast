<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { scoreColor } from '../charts'
import SpotsMap from '../components/SpotsMap.vue'

const FAV_KEY = 'sf_fav_v1'
const spots = ref([])
const scores = ref({})
const region = ref('全部')
const q = ref('')
const liveOnly = ref(false)
const view = ref('list')   // list | map
const loading = ref(true)
const error = ref('')
const favs = ref(new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]')))

async function load() {
  loading.value = true; error.value = ''
  try {
    spots.value = (await api.catalog()).catalog || []
    try { scores.value = (await api.catalogScores()).scores || {} }
    catch { scores.value = {} }
  } catch (e) { error.value = '目录加载失败，请稍后重试' }
  finally { loading.value = false }
}

const regions = computed(() => ['全部', ...Array.from(new Set(spots.value.map(s => s.region))).filter(Boolean)])

const list = computed(() => {
  let rows = spots.value
  if (region.value !== '全部') rows = rows.filter(s => s.region === region.value)
  if (liveOnly.value) rows = rows.filter(s => s.has_live)
  const kw = q.value.trim().toLowerCase()
  if (kw) rows = rows.filter(s => (s.name || '').toLowerCase().includes(kw) || (s.city || '').toLowerCase().includes(kw))
  // 收藏优先，其次有分降序
  return [...rows].sort((a, b) => {
    const fa = favs.value.has(a.slug) ? 1 : 0, fb = favs.value.has(b.slug) ? 1 : 0
    if (fa !== fb) return fb - fa
    return (scores.value[b.slug] ?? -1) - (scores.value[a.slug] ?? -1)
  })
})

function toggleFav(slug) {
  favs.value.has(slug) ? favs.value.delete(slug) : favs.value.add(slug)
  favs.value = new Set(favs.value)
  localStorage.setItem(FAV_KEY, JSON.stringify([...favs.value]))
}
onMounted(load)
</script>

<template>
  <main class="wrap">
    <header class="bar">
      <router-link to="/">← 首页</router-link>
      <h1>全国浪点目录</h1>
    </header>

    <input v-model="q" class="search" placeholder="搜索浪点名 / 城市…" />
    <div class="chips">
      <button v-for="r in regions" :key="r" :class="{ on: r === region }" @click="region = r">{{ r }}</button>
    </div>
    <label class="liveonly"><input type="checkbox" v-model="liveOnly" /> 仅看有直播</label>
    <div class="viewtoggle">
      <button :class="{ on: view === 'list' }" @click="view = 'list'">☰ 列表</button>
      <button :class="{ on: view === 'map' }" @click="view = 'map'">🗺️ 地图</button>
    </div>

    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="degraded">⚠️ {{ error }}</p>

    <SpotsMap v-else-if="view === 'map'" :spots="list" :favs="favs" />

    <p v-else-if="!list.length" class="empty">没有匹配的浪点，换个筛选或搜索词试试。</p>

    <ul v-else class="cards">
      <li v-for="s in list" :key="s.slug" class="card">
        <button class="fav" :class="{ on: favs.has(s.slug) }" @click.stop="toggleFav(s.slug)" :aria-label="favs.has(s.slug) ? '取消收藏' : '收藏'">★</button>
        <router-link :to="`/spot/${s.slug}`" class="link">
          <span class="name">{{ s.name }}</span>
          <span class="meta">{{ s.region }}<template v-if="s.city"> · {{ s.city }}</template></span>
        </router-link>
        <span v-if="s.slug in scores" class="badge" :style="{ background: scoreColor(scores[s.slug]) }">{{ scores[s.slug] }}</span>
        <span v-if="s.has_live" class="live">📹</span>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.bar { display: flex; align-items: center; gap: 10px; }
h1 { font-size: 18px; color: var(--sea1); }
.search { width: 100%; padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 12px; margin: 8px 0; }
.chips { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; }
.chips button { white-space: nowrap; padding: 5px 11px; border: 1px solid #cbd5e1; border-radius: 999px; background: #fff; font-size: 13px; }
.chips button.on { background: var(--sea2); color: #fff; border-color: var(--sea2); }
.liveonly { display: inline-block; font-size: 13px; color: var(--ink2); margin: 6px 0; }
.viewtoggle { display: flex; gap: 6px; margin: 6px 0; }
.viewtoggle button { padding: 5px 12px; border: 1px solid #cbd5e1; border-radius: 999px; background: #fff; font-size: 13px; }
.viewtoggle button.on { background: var(--sea1); color: #fff; border-color: var(--sea1); }
.cards { list-style: none; padding: 0; }
.card { display: flex; align-items: center; gap: 8px; background: #fff; border-radius: 12px; padding: 10px 12px; margin: 6px 0; }
.fav { border: none; background: none; font-size: 18px; color: #cbd5e1; cursor: pointer; }
.fav.on { color: #f59e0b; }
.link { flex: 1; display: flex; flex-direction: column; text-decoration: none; }
.name { font-weight: 600; color: var(--ink); }
.meta { font-size: 12px; color: var(--ink2); }
.badge { color: #fff; font-weight: 700; font-size: 13px; border-radius: 8px; padding: 2px 8px; }
.degraded { background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 10px; color: #9a3412; }
.empty { color: var(--ink2); text-align: center; padding: 20px; }
</style>
