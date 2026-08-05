<script setup>
// 直播播放器（信任工具：看实时画面对照今日评分）。
// hls.js 动态 import（路由级懒加载，未点开不下载）；Safari 走原生 HLS。
// 视频流前端直连上游、不经本后端（形态C 合规约定）。
import { ref, onBeforeUnmount } from 'vue'

const props = defineProps({ src: { type: String, required: true } })
const video = ref(null)
const playing = ref(false)
const error = ref('')
let hls = null

async function start() {
  error.value = ''
  playing.value = true
  await new Promise(r => setTimeout(r))       // 等 video 元素挂载
  const el = video.value
  if (!el) { error.value = '播放器初始化失败'; playing.value = false; return }
  if (el.canPlayType('application/vnd.apple.mpegurl')) {
    el.src = props.src
    el.play().catch(() => {})
    return
  }
  try {
    const { default: Hls } = await import('hls.js')
    if (!Hls.isSupported()) { error.value = '当前浏览器不支持 HLS 播放'; playing.value = false; return }
    hls = new Hls({ lowLatencyMode: true, liveDurationInfinity: true })
    hls.loadSource(props.src)
    hls.attachMedia(el)
    hls.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) { error.value = '直播源暂不可用（可能离线）'; stop() }
    })
    el.play().catch(() => {})
  } catch {
    error.value = '播放器加载失败'
    playing.value = false
  }
}

function stop() {
  if (hls) { try { hls.destroy() } catch { /* noop */ } hls = null }
  if (video.value) { video.value.pause(); video.value.removeAttribute('src') }
  playing.value = false
}

onBeforeUnmount(stop)
</script>

<template>
  <div class="livecam">
    <template v-if="!playing">
      <button class="playbtn" @click="start">▶ 播放实时直播</button>
      <p v-if="error" class="err">⚠️ {{ error }}</p>
    </template>
    <template v-else>
      <video ref="video" controls muted playsinline autoplay></video>
      <button class="stopbtn" @click="stop">✕ 关闭直播</button>
    </template>
    <p class="disc">直播画面来自公开上游、前端直连（研究用途）；对照今日评分校验预报。</p>
  </div>
</template>

<style scoped>
.livecam { background: var(--ink); border-radius: 12px; padding: 10px; margin: 6px 0; }
video { width: 100%; border-radius: 8px; background: #000; aspect-ratio: 16 / 9; }
.playbtn { width: 100%; padding: 14px; border: 1px dashed var(--ink2); border-radius: 8px; background: var(--ink); color: var(--line); font-size: 14px; }
.stopbtn { margin-top: 6px; padding: 5px 12px; border: none; border-radius: 8px; background: var(--ink2); color: var(--line); font-size: 12.5px; }
.err { color: var(--bad); font-size: 12.5px; margin: 6px 0 0; }
.disc { color: var(--ink2); font-size: 11px; margin: 6px 0 0; }
</style>
