/* P8 新 E2E —— Vue SPA(甲重建)。route 拦截 /api 灌 canned 数据(不依赖网络/后端引擎)。
   用法：先起后端挂 SF_SPA_DIST(服 dist + history 回退)，再 node web/e2e/vue_spa.mjs http://127.0.0.1:PORT
   甲-b 护栏：本套全绿是切 / 到 Vue 的前置门。*/
import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:8851'
const errors = []
let pass = 0, fail = 0
const ok = (n, c) => { if (c) { pass++; console.log('  ✅', n) } else { fail++; console.log('  ❌', n) } }

const DAY = {
  date: '2026-07-27', week: '周一', today: true, best: true, score: 7.6, stars: 4, tag: '🔥 必冲',
  window: '早7-9点', board: '鱼板', novice: '本周王者，早上近1米干净浪',
  dims: { 浪高: 8, 周期: 7, 风况: 6, 纯度: 5, 潮汐: 7 }, weakest: 'purity',
  times: [6, 9, 12, 15, 18], hs: [0.4, 0.6, 0.8, 0.9, 0.7], swell: [0.3, 0.5, 0.6, 0.7, 0.5],
  tp: [5, 5.5, 6, 6.5, 6], tp2: [6, 6.5, 7, 7.5, 7], wind: [3, 5, 8, 10, 6], gust: [5, 8, 12, 14, 9],
  wdeg: [337, 337, 160, 160, 300], tideEvents: [[3, 0.9], [9, -0.8], [15, 1.1], [21, -0.6]], windows: [[6, 9]],
  plan: ['🏄 行动建议', '早7点入水，鱼板抓推力'], lesson: ['纯度决定浪面', '涌浪占比低则起毛'],
  safety: [],
}
const REPORT = {
  spot: '测试浪点', coord: [36.09, 120.47], spotFacingDeg: 157, calibratedAt: '2026-07-27 02:00 GMT+8',
  ranking: [0], days: [DAY, { ...DAY, date: '2026-07-28', week: '周二', best: false, today: false, score: 6.1, tag: '👍 推荐' }],
  story: '<b>一句话剧情：</b>本周最佳周一。', checklist: ['潮汐为模型推算，核对当地官方潮汐表。', '本周有大浪日（最高约 0.9m）：结伴、系脚绳。'],
  disclaimer: '数据源 Open-Meteo；周期 Tm/Tp 双口径；GMT+8。水温约 22-24°C。',
  history: { ...DAY, date: '2026-07-26', week: '周日', today: false, best: false, predict: { height: '0.8m', period: '7.0s', wind: '8kn', verdict: '干净小涌' } },
}
const CATALOG = { catalog: [
  { slug: 'sl74', name: '石老人', city: '青岛', region: '山东', lat: 36.1, lon: 120.5, has_live: true, facing: 157 },
  { slug: 'sl50', name: '某滩', city: '三亚', region: '海南', lat: 18.2, lon: 109.5, has_live: false, facing: 180 },
] }

const browser = await chromium.launch()
const page = await browser.newPage()
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message))

// —— /api route 拦截 ——
await page.route('**/api/regions', r => r.fulfill({ json: { regions: [{ region: '山东', count: 1 }, { region: '海南', count: 1 }] } }))
await page.route('**/api/recommend*', r => r.fulfill({ json: {
  region: '山东', generated_at: '2026-07-27 10:00 GMT+8', fresh_count: 1, total_count: 1, degraded: false,
  best: { spot_slug: 'sl74', spot_name: '石老人', day: '2026-07-27', week: '周一', score: 7.6, headline: '早7-9点到，带鱼板', key_factors: ['0.9m浪', '离岸风', 'Tp7s'] },
  alternatives: [] } }))
await page.route('**/api/flags', r => r.fulfill({ json: { member_lock_enabled: false } }))
await page.route('**/api/catalog/scores', r => r.fulfill({ json: { scores: { sl74: 7.6, sl50: 5.2 }, cached: true } }))
await page.route('**/api/catalog', r => r.fulfill({ json: CATALOG }))
await page.route('**/api/report/history*', r => r.fulfill({ json: { history: REPORT.history } }))
await page.route('**/api/report*', r => r.fulfill({ json: REPORT }))
await page.route('**/api/accuracy/bias*', r => r.fulfill({ json: { bias: 'insufficient', samples: 0, min: 3 } }))
await page.route('**/api/accuracy/vote', r => r.fulfill({ json: { ok: true } }))
await page.route('**/api/status', r => r.fulfill({ json: {
  generated_at: '2026-07-27 10:00 GMT+8',
  refresh: { date: '2026-07-27', kind: 'main', run_at: '2026-07-27 02:00 GMT+8', expected: 3, succeeded: 2,
             failed: ['sl82'], failed_detail: { sl82: 'skipped: empty_report(upstream grid all-null)' }, is_today: true },
  coverage: { pool: 2, fresh: 2 },
  data_issues: {
    coord_invalid: [{ slug: 'sl75', spot: '石梅湾九里', why: 'lat 超范围: 110.363232' }],
    coord_duplicates: [{ coord: '22.6017,114.9073', slugs: ['sl54', 'sl84'], spots: ['虹海湾山海里', 'Kirra'], severity: 'suspect', regions: ['国外', '广东'] }],
    coord_duplicates_benign_n: 2,
  },
  regions: [{ region: '山东', spots: 1, pool: 1, fresh: 1, available: true, degraded: false },
            { region: '海南', spots: 1, pool: 1, fresh: 1, available: true, degraded: false }],
  history: [{ run_id: '2026-07-27-main', run_at: '2026-07-27 02:00 GMT+8', kind: 'main', expected_n: 2, ok_n: 2, duration_s: 60 }],
} }))

// —— 首页 ——
await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(500)
ok('首页 标题', (await page.locator('h1').first().innerText()).includes('决策助手'))
ok('首页 一屏答案 verdict', await page.locator('.verdict').count() === 1)
ok('首页 headline 行动首句', (await page.locator('.headline').innerText()).includes('鱼板'))
ok('首页 三渐进入口', await page.locator('.entries a').count() === 3)
ok('首页 区域 chips', await page.locator('.regions button').count() >= 2)

// —— 目录页 ——
await page.goto(BASE + '/spots', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(500)
ok('目录 卡片渲染', await page.locator('.card').count() === 2)
ok('目录 评分徽标', await page.locator('.badge').count() >= 1)
ok('目录 直播标', await page.locator('.live').count() === 1)
await page.fill('.search', '石老人')
await page.waitForTimeout(200)
ok('目录 搜索过滤', await page.locator('.card').count() === 1)

// —— 详情页 ——
await page.goto(BASE + '/spot/sl74', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(600)
ok('详情 浪点名', (await page.locator('h1').first().innerText()).includes('测试浪点'))
ok('详情 日期条', await page.locator('.strip button').count() === 2)
ok('详情 日卡评分', (await page.locator('.score').innerText()).includes('7.6'))
ok('详情 动态checklist(无青岛硬编码)', !(await page.locator('.checklist').innerText()).includes('青岛官方'))
ok('详情 直播占位入口', await page.locator('.livehint').count() === 1)
// 小白模式：无图表/五维，有「为什么」引导（模式差异恢复旧版）
await page.click('.modes button:has-text("小白")')
await page.waitForTimeout(200)
ok('详情 小白无图表', await page.locator('.daycard .chartbox svg').count() === 0)
ok('详情 小白引导按钮', await page.locator('.whybtn').count() === 1)
// 点「为什么」→ 进高手模式：图表+五维+课堂全出
await page.click('.whybtn')
await page.waitForTimeout(300)
ok('详情 高手模式五维', await page.locator('.dims').count() === 1)
ok('详情 高手 ChartBox SVG(浪高+风潮≥2图)', await page.locator('.daycard .chartbox svg').count() >= 2)
ok('详情 风质条', await page.locator('.windq').count() >= 1)
ok('详情 物理课堂', await page.locator('.lesson').count() === 1)
// 昨日回看：默认折叠（边缘化），展开后可自评
ok('详情 回看默认折叠', !(await page.locator('.review[open]').count()))
await page.click('.review summary')
await page.waitForTimeout(300)
await page.click('.vbtns button:has-text("准")')
await page.waitForTimeout(200)
ok('详情 回看展开自评致谢', await page.locator('.vthx').count() === 1)

// —— 状态页（R2 §3.2）——
await page.goto(BASE + '/status', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(500)
ok('状态页 标题', (await page.locator('h1').first().innerText()).includes('数据健康'))
ok('状态页 今日覆盖', (await page.locator('.card').first().innerText()).includes('2/3'))
ok('状态页 区域可用性表', await page.locator('table').count() >= 2)
// R1.2：失败点必须带原因（光有 slug 判不出该找上游还是找代码）
const failTxt = await page.locator('.faillist').first().innerText().catch(() => '')
ok('状态页 失败点列出 slug', failTxt.includes('sl82'))
ok('状态页 失败点说明原因', failTxt.includes('empty_report') || failTxt.includes('upstream'))
// R2：坏数据必须能在这个页面被看见（无推送告警 → /status 是唯一发现渠道）
const cards = await page.locator('.card').allInnerTexts()
const govTxt = cards.find(t => t.includes('数据治理待办')) || ''
ok('状态页 数据治理区块存在', govTxt.length > 0)
ok('状态页 报出坐标非法点', govTxt.includes('sl75') && govTxt.includes('超范围'))
ok('状态页 报出可疑重复组', govTxt.includes('sl54') && govTxt.includes('Kirra'))
ok('状态页 合理重复只计数不报故障', govTxt.includes('2 组同海滩'))

// —— S1 夜读模式（设计令牌切换 + localStorage 持久化）——
await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(400)
ok('夜读 开关存在', await page.locator('.nightbtn').count() === 1)
const bgDay = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
ok('夜读 日态背景取自 --bg', bgDay === 'rgb(250, 249, 245)')
await page.locator('.nightbtn').click(); await page.waitForTimeout(500)
ok('夜读 body.night 已挂', await page.evaluate(() => document.body.classList.contains('night')))
const bgNight = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
ok('夜读 夜态背景已切换（靠变量，非写死色）', bgNight === 'rgb(25, 23, 19)')
await page.reload({ waitUntil: 'networkidle' }); await page.waitForTimeout(600)
ok('夜读 刷新后仍生效（localStorage 持久化）', await page.evaluate(() => document.body.classList.contains('night')))

ok('0 控制台/页面 JS 报错', errors.length === 0)
if (errors.length) console.log('  JS errors:', errors.slice(0, 5))

console.log(`\n结果：${pass} passed / ${fail} failed`)
await browser.close()
process.exit(fail === 0 && errors.length === 0 ? 0 : 1)
