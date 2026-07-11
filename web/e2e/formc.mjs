/* 形态C · Task 8 E2E —— 58+目录 / 地区筛选 / 直播弹层 / 详情融合 / 多浪点回看 + 0 JS 报错。
   需后端以 SF_SEED_SPOTS 灌注册表启动（否则 /api/catalog 空、#catalog 隐藏 → 断言失败）。
   用法：node web/e2e/formc.mjs http://127.0.0.1:PORT */
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:8849';
const errors = [];
let pass = 0, fail = 0;
function ok(name, cond){ if(cond){ pass++; console.log('  ✅', name); } else { fail++; console.log('  ❌', name); } }

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', m => { if(m.type()==='error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('PAGEERROR: '+e.message));

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(2800);   // 等 demoAuth + loadCatalog + loadCams + loadLive

// —— 前置：形态C 目录必须已注入（SF_SEED_SPOTS）——
const catVisible = await page.locator('#catalog').isVisible();
ok('C0 目录区块显示(SF_SEED_SPOTS 已灌)', catVisible);
if(!catVisible){
  console.log('  ✖ #catalog 未显示——后端未 SF_SEED_SPOTS 灌注册表，无法继续形态C E2E');
  await browser.close(); console.log(`\n结果：${pass} passed / ${fail} failed`); process.exit(1);
}

// —— C1 列表 58+ 浪点 ——
const total = await page.locator('#catList .cat-item').count();
ok(`C1 列表 58+ 浪点(实得 ${total})`, total >= 58);
ok('C1 目录计数文本存在', /浪点/.test(await page.locator('#catCount').textContent()));

// —— C2 地区筛选 chips + 过滤生效 ——
const chips = await page.locator('#catChips .cat-chip').count();
ok(`C2 地区筛选 chips ≥ 8(实得 ${chips})`, chips >= 8);
// 点「海南」→ 列表收窄到该区（快照海南=15）
const hainan = page.locator('#catChips .cat-chip', { hasText: /^海南$/ });
ok('C2 海南 chip 存在', await hainan.count() === 1);
await hainan.click();
await page.waitForTimeout(300);
const hainanCount = await page.locator('#catList .cat-item').count();
ok(`C2 海南筛选收窄(1..${total}, 实得 ${hainanCount})`, hainanCount >= 1 && hainanCount < total);
// 回「全部」→ 复位 58+
await page.locator('#catChips .cat-chip', { hasText: /^全部$/ }).click();
await page.waitForTimeout(300);
ok('C2 全部复位 58+', await page.locator('#catList .cat-item').count() >= 58);

// —— C3 搜索过滤 ——
await page.fill('#catSearch', '海');
await page.waitForTimeout(250);
const searched = await page.locator('#catList .cat-item').count();
ok(`C3 搜索过滤生效(1..${total})`, searched >= 1 && searched < total);
await page.fill('#catSearch', '');
await page.waitForTimeout(200);

// —— C4 直播卡片 + 弹层(hls) ——
const camCards = await page.locator('#camGrid .cam-card').count();
ok(`C4 直播卡片(真实 cams, 实得 ${camCards})`, camCards >= 40);
await page.locator('#camGrid .cam-card >> nth=0').click();
await page.waitForTimeout(1200);
ok('C4 直播弹层打开', await page.locator('#camModal.open').count() === 1);
ok('C4 弹层含 <video id=camVideo>', await page.locator('#camModal #camVideo').count() === 1);
ok('C4 弹层含来源免责', /研究用途|免责|直连/.test(await page.locator('#camModal').textContent()));
await page.keyboard.press('Escape');
await page.waitForTimeout(200);
ok('C4 Esc 关闭直播弹层', await page.locator('#camModal.open').count() === 0);

// —— C5 详情融合：点有 LIVE 的目录项 → 引擎自算 + 直播入口 ——
const liveItem = page.locator('#catList .cat-item', { has: page.locator('.cat-live') }).first();
ok('C5 存在含 LIVE 的目录项', await liveItem.count() > 0);
const firstTitle = (await liveItem.textContent()).trim().slice(0, 12);
await liveItem.click();
await page.waitForTimeout(3800);              // 等 loadLive 引擎自算
ok('C5 详情直播入口横幅显示', await page.locator('#liveEntry').isVisible());
const detailText = await page.evaluate(()=>document.body.innerText);
ok('C5 详情含「离岸」叙事(离岸风加成/物理课堂)', detailText.includes('离岸'));
ok('C5 详情含「双周期」标签', detailText.includes('双周期'));
// 详情直播入口 → 打开弹层
await page.locator('#liveEntry').click();
await page.waitForTimeout(1000);
ok('C5 详情直播入口打开弹层', await page.locator('#camModal.open').count() === 1);
await page.keyboard.press('Escape');
await page.waitForTimeout(200);

// —— C6 多浪点回看：切到另一个有 LIVE 的浪点，入口/详情随之更新 ——
const liveItems = page.locator('#catList .cat-item', { has: page.locator('.cat-live') });
const liveN = await liveItems.count();
ok('C6 至少两个 LIVE 浪点(支持多浪点)', liveN >= 2);
if(liveN >= 2){
  await liveItems.nth(1).click();
  await page.waitForTimeout(3800);
  ok('C6 切浪点后直播入口仍显示', await page.locator('#liveEntry').isVisible());
  const t2 = await page.evaluate(()=>document.body.innerText);
  ok('C6 切浪点后详情重算(含昨日回看)', t2.includes('昨日回看') || t2.includes('回看'));
}

// —— 0 JS 报错（排除资源404/直播流HLS）——
const jsErrors = errors.filter(e => !/favicon|Failed to load resource|net::ERR|m3u8|hls|manifest|frag|level|buffer|mediaError|EXT-X/i.test(e));
ok('0 控制台 JS 报错(排除资源404/直播流)', jsErrors.length === 0);
if(jsErrors.length) console.log('    JS错误:', jsErrors);

await browser.close();
console.log(`\n形态C E2E 结果：${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
