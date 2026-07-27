// P2.3 SVG 图表逻辑（从 web/浪报MVP.html 忠实移植，零依赖·手绘 SVG·不引 ECharts）。
// 纯函数：输入 day 对象（times/hs/swell/tp/tp2/wind/gust/wdeg/tideEvents/windows）→ SVG 字符串。
// 视觉与口径与原单 HTML 一致（Tm 橙实线 / Tp 红虚线 / 离岸蓝-侧岸紫-向岸橙）。

let SPOT_FACING = 157 // 山东头 SSE；详情页按 report.spotFacingDeg 调 setFacing()
export function setFacing(f) { if (typeof f === 'number' && !Number.isNaN(f)) SPOT_FACING = f }

export function windKind(deg) {
  const diff = Math.abs((((deg - SPOT_FACING + 180) % 360) + 360) % 360 - 180)
  if (diff < 60) return 'on'
  if (diff > 120) return 'off'
  return 'cross'
}

export const WIND_META = {
  off: { label: '离岸', color: '#0ea5e9', desc: '梳面' },
  cross: { label: '侧岸', color: '#a78bfa', desc: '尚可' },
  on: { label: '向岸', color: '#fb923c', desc: '吹乱' },
}

export function windArrow(deg) {
  const to = (deg + 180) % 360
  const arrows = ['↑', '↗', '→', '↘', '↓', '↙', '←', '↖']
  return arrows[Math.round(to / 45) % 8]
}

export function scoreColor(score) {
  if (score >= 8) return '#10b981'
  if (score >= 6.5) return '#3b82f6'
  if (score >= 5) return '#f59e0b'
  if (score >= 3) return '#f97316'
  return '#94a3b8'
}

// 浪高柱 + 双周期线(Tm/Tp) + 最佳窗口高亮 + tooltip 命中列
export function waveChart(d) {
  const W = 360, H = 200, L = 34, R = 12, T = 18, B = 30, HSMAX = 1.2, TPMAX = 7.6
  const X0 = Math.min(...d.times) - 1.5, X1 = Math.max(...d.times) + 1.5
  const pw = W - L - R, ph = H - T - B
  const sx = h => L + (h - X0) / (X1 - X0) * pw
  const syH = v => T + ph - (v / HSMAX) * ph
  const syT = v => T + ph - (v / TPMAX) * ph
  let s = ''
  ;(d.windows || []).forEach(w => {
    s += `<rect x="${sx(w[0])}" y="${T}" width="${sx(w[1]) - sx(w[0])}" height="${ph}" fill="#10b981" opacity="0.13" rx="4"/>`
    s += `<text x="${(sx(w[0]) + sx(w[1])) / 2}" y="${T + 11}" font-size="9" fill="#059669" text-anchor="middle" font-weight="700">最佳窗口</text>`
  })
  ;[0.5, 1.0].forEach(g => {
    s += `<line x1="${L}" y1="${syH(g)}" x2="${W - R}" y2="${syH(g)}" stroke="#e2e8f0" stroke-dasharray="3,3"/>`
    s += `<text x="${L - 4}" y="${syH(g) + 3}" font-size="9" fill="#94a3b8" text-anchor="end">${g.toFixed(1)}m</text>`
  })
  s += `<line x1="${L}" y1="${T + ph}" x2="${W - R}" y2="${T + ph}" stroke="#cbd5e1"/>`
  const bw = d.times.length > 5 ? 12 : 15
  const LBL = Math.max(1, Math.ceil(d.times.length / 7))
  const showLbl = i => (i % LBL === 0) || (i === d.times.length - 1)
  d.times.forEach((t, i) => {
    const x = sx(t) - bw / 2
    const hTot = ph * (d.hs[i] / HSMAX), hSw = ph * (Math.min(d.swell[i], d.hs[i]) / HSMAX)
    s += `<rect x="${x}" y="${T + ph - hTot}" width="${bw}" height="${hTot}" fill="#bae6fd" rx="3"/>`
    s += `<rect x="${x}" y="${T + ph - hSw}" width="${bw}" height="${hSw}" fill="#0284c7" rx="3"/>`
    if (showLbl(i)) s += `<text x="${sx(t)}" y="${T + ph - hTot - 4}" font-size="9" fill="#0c4a6e" text-anchor="middle" font-weight="700">${d.hs[i]}</text>`
    if (showLbl(i)) s += `<text x="${sx(t)}" y="${H - 14}" font-size="9.5" fill="#64748b" text-anchor="middle">${String(t).padStart(2, '0')}时</text>`
  })
  if (d.tp2) {
    const pts2 = []
    d.times.forEach((t, i) => { if (d.tp2[i] != null) pts2.push([sx(t), syT(d.tp2[i]), d.tp2[i], t, i]) })
    s += `<polyline points="${pts2.map(p => p[0] + ',' + p[1]).join(' ')}" fill="none" stroke="#dc2626" stroke-width="1.8" stroke-dasharray="5,3"/>`
    pts2.forEach(p => {
      s += `<circle cx="${p[0]}" cy="${p[1]}" r="2.8" fill="#fff" stroke="#dc2626" stroke-width="1.8"/>`
      if (showLbl(p[4])) s += `<text x="${p[0]}" y="${p[1] - 6}" font-size="8.5" fill="#dc2626" text-anchor="middle" font-weight="700">${p[2]}s</text>`
    })
  }
  const pts = d.times.map((t, i) => `${sx(t)},${syT(d.tp[i])}`).join(' ')
  s += `<polyline points="${pts}" fill="none" stroke="#f97316" stroke-width="2.2" stroke-linejoin="round"/>`
  d.times.forEach((t, i) => {
    s += `<circle cx="${sx(t)}" cy="${syT(d.tp[i])}" r="3.2" fill="#fff" stroke="#f97316" stroke-width="2"/>`
    if (showLbl(i)) s += `<text x="${sx(t)}" y="${syT(d.tp[i]) + 13}" font-size="8.5" fill="#ea580c" text-anchor="middle" font-weight="600">${d.tp[i]}</text>`
  })
  const cwW = pw / Math.max(1, d.times.length)
  d.times.forEach((t, i) => {
    const tp2v = (d.tp2 && d.tp2[i] != null) ? ` · Tp ${d.tp2[i]}s` : ''
    const tip = `${String(t).padStart(2, '0')}时 · 浪高 <b>${d.hs[i]}m</b> · 涌 ${d.swell[i]}m · Tm ${d.tp[i]}s${tp2v}`
    s += `<rect class="ctHit" x="${sx(t) - cwW / 2}" y="${T}" width="${cwW}" height="${ph}" fill="transparent" data-tip="${tip}"/>`
  })
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${s}</svg>`
}

// 离岸风质条：每白天时段一格（背景=风质色/箭头=风去向/数字=风速）
export function windQualityStrip(d) {
  let segs = ''
  d.times.forEach((t, i) => {
    const m = WIND_META[windKind(d.wdeg[i])]
    segs += `<div class="seg" style="background:${m.color}"><span class="wq-ar">${windArrow(d.wdeg[i])}</span><span class="wq-k">${d.wind[i]}<small style="font-weight:400;font-size:8px">kn</small></span><span class="wq-h">${String(t).padStart(2, '0')}时</span></div>`
  })
  return `<div class="windq">${segs}</div><div class="windq-key"><b><i style="background:#0ea5e9"></i>离岸·梳面(最佳)</b> <b><i style="background:#a78bfa"></i>侧岸·尚可</b> <b><i style="background:#fb923c"></i>向岸·吹乱</b></div>`
}

// 风速 + 潮位（按风质着色·箭头标风向）+ tooltip
export function windTideChart(d) {
  const W = 360, H = 180, L = 30, R = 32, T = 18, B = 24, X0 = 0, X1 = 24, WMAX = 24, TIDE = 2.1
  const pw = W - L - R, ph = H - T - B
  const sx = h => L + (h - X0) / (X1 - X0) * pw
  const syW = v => T + ph - (v / WMAX) * ph
  const syTd = v => T + ph / 2 - (v / TIDE) * (ph / 2)
  let s = ''
  ;(d.windows || []).forEach(w => { s += `<rect x="${sx(w[0])}" y="${T}" width="${sx(w[1]) - sx(w[0])}" height="${ph}" fill="#10b981" opacity="0.12" rx="4"/>` })
  s += `<line x1="${L}" y1="${syTd(0)}" x2="${W - R}" y2="${syTd(0)}" stroke="#e2e8f0" stroke-dasharray="3,3"/>`
  s += `<text x="${W - R + 4}" y="${syTd(0) + 3}" font-size="8.5" fill="#0d9488">0</text>`
  s += `<line x1="${L}" y1="${T + ph}" x2="${W - R}" y2="${T + ph}" stroke="#cbd5e1"/>`
  ;[5, 15].forEach(g => {
    s += `<line x1="${L}" y1="${syW(g)}" x2="${W - R}" y2="${syW(g)}" stroke="#f1f5f9"/>`
    s += `<text x="${L - 4}" y="${syW(g) + 3}" font-size="8.5" fill="#94a3b8" text-anchor="end">${g}</text>`
  })
  const ev = d.tideEvents || []; const tpArr = []
  for (let i = 0; i < ev.length - 1; i++) {
    for (let k = 0; k <= 14; k++) {
      const t = k / 14, h = ev[i][0] + (ev[i + 1][0] - ev[i][0]) * t
      const v = ev[i][1] + (ev[i + 1][1] - ev[i][1]) * (1 - Math.cos(Math.PI * t)) / 2
      if (h >= X0 && h <= X1) tpArr.push(`${sx(h)},${syTd(v)}`)
    }
  }
  s += `<polyline points="${tpArr.join(' ')}" fill="none" stroke="#14b8a6" stroke-width="2" opacity="0.8"/>`
  ev.forEach(e => {
    if (e[0] < X0 || e[0] > X1) return
    const hi = e[1] > 0
    s += `<circle cx="${sx(e[0])}" cy="${syTd(e[1])}" r="2.6" fill="#14b8a6"/>`
    s += `<text x="${sx(e[0])}" y="${syTd(e[1]) + (hi ? -6 : 12)}" font-size="8" fill="#0f766e" text-anchor="middle">${hi ? '高' : '低'}${String(e[0]).padStart(2, '0')}</text>`
  })
  const gp = d.times.map((t, i) => `${sx(t)},${syW(Math.min(d.gust[i], WMAX))}`).join(' ')
  s += `<polyline points="${gp}" fill="none" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4,3"/>`
  const wp = d.times.map((t, i) => `${sx(t)},${syW(d.wind[i])}`).join(' ')
  s += `<polyline points="${wp}" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linejoin="round"/>`
  const WPT = Math.max(1, Math.ceil(d.times.length / 8))
  d.times.forEach((t, i) => {
    if (i % WPT !== 0 && i !== d.times.length - 1) return
    const col = WIND_META[windKind(d.wdeg[i])].color, y = syW(d.wind[i])
    s += `<circle cx="${sx(t)}" cy="${y}" r="6" fill="${col}"/>`
    s += `<text x="${sx(t)}" y="${y + 3.2}" font-size="8.5" fill="#fff" text-anchor="middle" font-weight="700">${windArrow(d.wdeg[i])}</text>`
  })
  ;[0, 6, 12, 18, 24].forEach(t => { s += `<text x="${sx(t)}" y="${H - 9}" font-size="9" fill="#64748b" text-anchor="middle">${t}时</text>` })
  const cwWT = pw / Math.max(1, d.times.length)
  d.times.forEach((t, i) => {
    const kn = WIND_META[windKind(d.wdeg[i])].label
    const tip = `${String(t).padStart(2, '0')}时 · 风 <b>${d.wind[i]}kn</b> · 阵风 ${d.gust[i]}kn · ${kn}`
    s += `<rect class="ctHit" x="${sx(t) - cwWT / 2}" y="${T}" width="${cwWT}" height="${ph}" fill="transparent" data-tip="${tip}"/>`
  })
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${s}</svg>`
}

// 7 日涌浪事件生命周期（日最大 Hs × 阶段 × 周期 × 晨风风质）
export function lifecycleChart(days) {
  const W = 360, H = 224, L = 30, R = 10, T = 24, B = 66, HSMAX = 1.2
  const pw = W - L - R, ph = H - T - B, n = days.length, slot = pw / n
  let s = ''
  ;[0.5, 1.0].forEach(g => {
    const y = T + ph - (g / HSMAX) * ph
    s += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" stroke="#e2e8f0" stroke-dasharray="3,3"/>`
    s += `<text x="${L - 4}" y="${y + 3}" font-size="9" fill="#94a3b8" text-anchor="end">${g.toFixed(1)}</text>`
  })
  s += `<line x1="${L}" y1="${T + ph}" x2="${W - R}" y2="${T + ph}" stroke="#cbd5e1"/>`
  days.forEach((d, i) => {
    const hsMax = Math.max(...d.hs)
    const x = L + slot * i + slot / 2, bw = 26, bh = ph * (hsMax / HSMAX)
    s += `<rect x="${x - bw / 2}" y="${T + ph - bh}" width="${bw}" height="${bh}" fill="${scoreColor(d.score)}" rx="5" opacity="0.88"/>`
    s += `<text x="${x}" y="${T + ph - bh - 5}" font-size="9.5" fill="#0f172a" text-anchor="middle" font-weight="700">${hsMax.toFixed(2)}</text>`
    s += `<text x="${x}" y="${T + ph + 13}" font-size="9.5" fill="#334155" text-anchor="middle" font-weight="600">${d.week}</text>`
    s += `<text x="${x}" y="${T + ph + 25}" font-size="8.5" fill="#94a3b8" text-anchor="middle">${d.date}</text>`
    s += `<text x="${x}" y="${T + ph + 39}" font-size="8.5" fill="#0369a1" text-anchor="middle">${d.phase || ''}</text>`
    const tpShow = d.tp2 ? Math.max(...d.tp2.filter(v => v != null)) : d.tp[Math.floor(d.tp.length / 2)]
    s += `<text x="${x}" y="${T + ph + 51}" font-size="8.5" fill="${d.tp2 ? '#dc2626' : '#64748b'}" text-anchor="middle">${d.tp2 ? 'Tp ' : 'Tm '}${tpShow}s</text>`
    const dawnK = windKind(d.wdeg[0])
    s += `<text x="${x}" y="${T + ph + 63}" font-size="8.5" fill="${WIND_META[dawnK].color}" text-anchor="middle" font-weight="${dawnK === 'off' ? '700' : '400'}">${windArrow(d.wdeg[0])}${d.wind[0]} ${WIND_META[dawnK].label}</text>`
  })
  s += `<text x="${L}" y="12" font-size="10" fill="#475569" font-weight="700">日最大浪高 Hs(m) × 阶段 × 周期 × 晨风风质</text>`
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${s}</svg>`
}
