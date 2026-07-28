// 轻量 SWR（stale-while-revalidate）会话缓存：切页秒出上次数据，后台静默刷新。
// 内存 Map 存本会话；sessionStorage 存跨刷新（TTL 内）。「加载中…」只在真正无数据时出现。
const mem = new Map()
const TTL_MS = 5 * 60 * 1000   // 与后端 SF_AGG_TTL 同步：每日预算数据 5min 陈旧零风险

function ssGet(key) {
  try {
    const raw = sessionStorage.getItem('swr:' + key)
    if (!raw) return null
    const { t, v } = JSON.parse(raw)
    if (Date.now() - t > TTL_MS) return null
    return v
  } catch { return null }
}

function ssSet(key, v) {
  try { sessionStorage.setItem('swr:' + key, JSON.stringify({ t: Date.now(), v })) }
  catch { /* 配额满等忽略 */ }
}

export function cached(key) {
  if (mem.has(key)) return mem.get(key)
  const v = ssGet(key)
  if (v !== null) mem.set(key, v)
  return v
}

// swr(key, fetcher, onData)：有缓存先回调一次缓存值（fresh=false），
// 然后总是后台重取，成功再回调新值（fresh=true）。返回「是否有缓存立即可用」。
export function swr(key, fetcher, onData) {
  const hit = cached(key)
  if (hit !== null && hit !== undefined) onData(hit, false)
  fetcher().then(v => {
    mem.set(key, v); ssSet(key, v)
    onData(v, true)
  }).catch(err => { if (hit === null || hit === undefined) onData(null, true, err) })
  return hit !== null && hit !== undefined
}
