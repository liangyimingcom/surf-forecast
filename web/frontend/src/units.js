// 浪高单位（m / ft）单一真源（S4.5）。
// 为什么放 ref 而不是普通变量：charts.js 的图表函数在 Vue computed 里被调用，
// 函数内读 `unit.value` 会让那些 computed 追踪到它 → 切换单位后图表自动重绘，
// 不需要给每个图表函数加参数、也不需要手动触发 re-render。
// 换算取原型 mLab/mMax 的口径：1m = 3.281ft。
import { ref } from 'vue'

const KEY = 'sf_unit_v1'
const FT = 3.281

export const unit = ref(localStorage.getItem(KEY) === 'ft' ? 'ft' : 'm')

export function setUnit(u) {
  unit.value = u === 'ft' ? 'ft' : 'm'
  try { localStorage.setItem(KEY, unit.value) } catch (e) { /* 隐私模式忽略 */ }
}
export function toggleUnit() { setUnit(unit.value === 'm' ? 'ft' : 'm') }

/** 数值换算（不带单位）。米进，当前单位出。 */
export function hv(m) {
  const v = Number(m)
  if (!Number.isFinite(v)) return null
  return unit.value === 'ft' ? v * FT : v
}

/** 带单位的显示串。米制默认 2 位（浪高常见 0.52m），英尺 1 位。 */
export function fmtH(m, mDigits = 2) {
  const v = Number(m)
  if (!Number.isFinite(v)) return '—'
  return unit.value === 'ft' ? `${(v * FT).toFixed(1)}ft` : `${v.toFixed(mDigits)}m`
}

/** 轴刻度等只需 1 位米制的场合。 */
export function fmtHShort(m) { return fmtH(m, 1) }

/**
 * 把后端已格式化文本里的「N.Nm」换成当前单位。
 * ⚠️ 只用于**已核实语义是高度**的字段（`tideText`、五维解释 `pa[i][2]`、
 *    `history.predict.height`）。绝不全局套在任意后端文案上——那会把
 *    「km」「mm」「m/s」「5min」之类误伤，也会篡改叙事含义。
 * 米制时原样返回（零风险）。
 */
export function convertHeights(text) {
  if (unit.value === 'm' || typeof text !== 'string') return text
  // 前面不能紧跟字母/数字/点（避开 km、mm、0.5km）；后面不能紧跟字母或 /（避开 m/s、min、mm）
  return text.replace(/(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)m(?![A-Za-z/])/g,
    (_, n) => `${(Number(n) * FT).toFixed(1)}ft`)
}
