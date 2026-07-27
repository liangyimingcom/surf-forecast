<script setup>
// P3 Leaflet 地图（懒加载 leaflet；标记 金=已收藏/蓝=未收藏；popup→详情）。
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  spots: { type: Array, required: true },
  favs: { type: Object, required: true }, // Set
})
const el = ref(null)
const router = useRouter()
let map = null

onMounted(async () => {
  const L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')
  const pts = props.spots.filter(s => Number.isFinite(s.lat) && Number.isFinite(s.lon))
  const center = pts.length ? [pts[0].lat, pts[0].lon] : [32, 118]
  map = L.map(el.value, { scrollWheelZoom: false }).setView(center, 5)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap', maxZoom: 18,
  }).addTo(map)
  pts.forEach(s => {
    const gold = props.favs.has(s.slug)
    const m = L.circleMarker([s.lat, s.lon], {
      radius: 6, color: gold ? '#d97706' : '#0ea5e9',
      fillColor: gold ? '#f59e0b' : '#38bdf8', fillOpacity: 0.9, weight: 2,
    }).addTo(map)
    const btn = `<b>${s.name || s.slug}</b><br>${s.region || ''}<br><a href="#/spot/${s.slug}" data-slug="${s.slug}" class="mpop">看详情 ▸</a>`
    m.bindPopup(btn)
    m.on('popupopen', () => {
      const a = document.querySelector(`.mpop[data-slug="${s.slug}"]`)
      if (a) a.onclick = (e) => { e.preventDefault(); router.push(`/spot/${s.slug}`) }
    })
  })
})
onBeforeUnmount(() => { if (map) map.remove() })
</script>

<template>
  <div ref="el" class="map" />
  <div class="legend"><span class="g">●</span> 已收藏 <span class="b">●</span> 未收藏</div>
</template>

<style scoped>
.map { height: 360px; border-radius: 12px; overflow: hidden; }
.legend { font-size: 11px; color: var(--ink2); margin-top: 4px; }
.legend .g { color: #f59e0b; } .legend .b { color: #38bdf8; }
</style>
