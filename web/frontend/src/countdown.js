// 最佳窗口倒计时 + 通勤倒推（S3）——纯函数、无 DOM、无 I/O，便于用假时钟钉死边界。
// 时间口径：全程 GMT+8（Asia/Shanghai）。窗口取 day.windows[0] 的数字小时对
// （如 [[8.0, 11.0]]），比解析 day.window 字符串稳。
// 数据缺失时一律返回 null → 调用方不渲染，绝不猜。

const GMT8_OFFSET_MIN = 8 * 60

/** 把某个瞬间换算成 GMT+8 当天的「小时（含小数）」+ 日期串，避免依赖运行环境时区。 */
export function gmt8Parts(now = new Date()) {
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000
  const d = new Date(utcMs + GMT8_OFFSET_MIN * 60000)
  return {
    date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
    hour: d.getHours() + d.getMinutes() / 60 + d.getSeconds() / 3600,
    h: d.getHours(), m: d.getMinutes(), s: d.getSeconds(),
  }
}

/** 取当日最佳窗口 [起, 止]（数字小时）；无则 null。 */
export function windowHours(day) {
  const w = day && Array.isArray(day.windows) ? day.windows[0] : null
  if (!Array.isArray(w) || w.length < 2) return null
  const [a, b] = [Number(w[0]), Number(w[1])]
  if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return null
  return [a, b]
}

/**
 * 倒计时三态。返回 { state, text } 或 null（数据不足 → 不渲染）。
 *   'before'  窗口未开始 → 倒数「还有 Xh Ym Zs」
 *   'during'  窗口进行中 → 「窗口进行中 · 还剩 …」
 *   'after'   窗口已过   → 「今日窗口已过」（跨日的未来日期归 'before'）
 * 边界约定（双侧钉死）：hour === 起点 视为 during；hour === 终点 视为 after。
 */
export function countdown(day, now = new Date()) {
  const win = windowHours(day)
  if (!win || !day.date) return null
  const [start, end] = win
  const p = gmt8Parts(now)
  if (day.date > p.date) {                       // 未来日期：按整天差 + 窗口起点倒数
    const days = dayDiff(p.date, day.date)
    if (days === null) return null
    const secs = Math.round(((start - p.hour) + days * 24) * 3600)
    return { state: 'before', text: `距最佳窗口还有 ${fmt(secs)}` }
  }
  if (day.date < p.date) return { state: 'after', text: '该日窗口已过' }
  if (p.hour < start) return { state: 'before', text: `距最佳窗口还有 ${fmt(Math.round((start - p.hour) * 3600))}` }
  if (p.hour < end) return { state: 'during', text: `窗口进行中 · 还剩 ${fmt(Math.round((end - p.hour) * 3600))}` }
  return { state: 'after', text: '今日窗口已过' }
}

/**
 * 通勤倒推：出门时刻 = 窗口起点 − 车程 − 收拾装备。
 * 返回 { depart, water, total } 或 null。commuteMin 由用户调整并持久化（纯前端）。
 */
export function departure(day, commuteMin, gearMin = 15) {
  const win = windowHours(day)
  if (!win) return null
  const total = Math.max(0, Number(commuteMin) || 0) + Math.max(0, Number(gearMin) || 0)
  const startMin = Math.round(win[0] * 60)
  let d = startMin - total
  const prevDay = d < 0
  if (prevDay) d += 24 * 60                      // 早于零点 → 前一天出门，明确标注
  return { depart: hhmm(d), water: hhmm(startMin), total, prevDay }
}

function hhmm(mins) {
  const m = ((mins % 1440) + 1440) % 1440
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}

function fmt(secs) {
  if (secs < 0) secs = 0
  // ≥48h 用「天+小时」：最佳日常在数天后，实测会显示「114小时 18分 9秒」——数值对但没人这么读。
  if (secs >= 48 * 3600) {
    const d = Math.floor(secs / 86400), h = Math.floor((secs % 86400) / 3600)
    return h > 0 ? `${d}天 ${h}小时` : `${d}天`
  }
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60
  return h > 0 ? `${h}小时 ${m}分 ${s}秒` : (m > 0 ? `${m}分 ${s}秒` : `${s}秒`)
}

function dayDiff(fromISO, toISO) {
  const a = Date.parse(fromISO + 'T00:00:00Z'), b = Date.parse(toISO + 'T00:00:00Z')
  if (Number.isNaN(a) || Number.isNaN(b)) return null
  return Math.round((b - a) / 86400000)
}
