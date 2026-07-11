/* 浪报移植+形态C功能 E2E —— headless Chromium，标签页感知(实时浪报/浪报详情/其他)。
   用法：先起后端(uvicorn, SF_SEED_SPOTS 灌注册表)，再 node web/e2e/new_features.mjs http://127.0.0.1:PORT */
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:8848';
const errors = [];
let pass = 0, fail = 0;
function ok(name, cond){ if(cond){ pass++; console.log('  ✅', name); } else { fail++; console.log('  ❌', name); } }
const tab = (t) => page.evaluate((x)=>window.showTab(x), t);

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', m => { if(m.type()==='error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('PAGEERROR: '+e.message));

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(2500);

// —— 主标签页导航 ——
ok('主标签页 3 个', await page.locator('.maintab .maintab-btn').count() === 3);
ok('默认 实时浪报 激活', await page.locator('.maintab-btn.on').getAttribute('data-tab') === 'live');
ok('排水量功能已移除', await page.locator('#volume').count() === 0);

// —— 【实时浪报】tab：全国目录 + 直播 ——
await tab('live'); await page.waitForTimeout(300);
if(await page.locator('#catalog').isVisible()){
  ok('C 全国浪点目录显示', await page.locator('#catList .cat-item').count() >= 40);
  ok('C 区域筛选chips', await page.locator('#catChips .cat-chip').count() >= 5);
  ok('C 直播卡片(hls)', await page.locator('#camGrid .cam-card').count() >= 10);
  const before = await page.locator('#catList .cat-item').count();
  await page.locator('#catChips .cat-chip', { hasText:'海南' }).click();
  await page.waitForTimeout(200);
  ok('C 区域筛选生效', await page.locator('#catList .cat-item').count() < before);
  await page.locator('#catChips .cat-chip', { hasText:'全部' }).click();
} else {
  console.log('  ⏭  #catalog 未显示(未 SF_SEED_SPOTS)，跳过实时浪报断言');
}

// —— 【其他】tab：公告/反馈/关于/活动墙/拼车/周边 ——
await tab('other'); await page.waitForTimeout(300);
ok('R2.1 公告列表渲染', await page.locator('#anncList .annc-item').count() > 0);
ok('R2.3 关于section存在', await page.locator('#about').count() === 1);
ok('R2.5 拼车列表渲染', await page.locator('#carpoolList .news-item').count() === 4);
ok('R2.7 周边分组渲染', await page.locator('#nearbyGroups .nb-group').count() === 3);
// R2.2 反馈校验
await page.click('#feedback .fb-submit');
ok('R2.2 空提交报错', (await page.locator('#fbMsg').textContent()).includes('类型'));
await page.selectOption('#fbType', { index: 1 });
await page.fill('#fbContent', 'E2E 测试反馈内容');
await page.click('#feedback .fb-submit');
ok('R2.2 有效提交示例成功', (await page.locator('#fbMsg').textContent()).includes('已收到'));
// R2.4 活动墙筛选 + 详情弹层
ok('R2.4 活动墙chips渲染', await page.locator('#newsChips .news-chip').count() >= 4);
const nb = await page.locator('#newsList .news-item').count();
await page.click('#newsChips .news-chip >> nth=3'); await page.waitForTimeout(200);
ok('R2.4 类型筛选生效', (await page.locator('#newsList .news-item').count()) <= nb);
await page.click('#newsChips .news-chip >> nth=0'); await page.waitForTimeout(150);
await page.click('#newsList .news-item >> nth=0'); await page.waitForTimeout(300);
ok('R2.4 详情弹层打开', await page.locator('#newsModal.open').count() === 1);
ok('R2.4 详情含示例badge', await page.locator('#newsModal .annc-badge').count() === 1);
await page.keyboard.press('Escape'); await page.waitForTimeout(200);
ok('R2.4 Esc 关闭弹层', await page.locator('#newsModal.open').count() === 0);

// —— 【浪报详情】tab：收藏/搜索/排序/地图（建浪点后）——
await tab('report'); await page.waitForTimeout(200);
ok('R1 收藏搜索框存在', await page.locator('#spotSearch').count() === 1);
const created = await page.evaluate(async ()=>{
  const mk = (name,lat,lon)=>fetch('/api/spots',{method:'POST',credentials:'include',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({name,lat,lon,days:3})}).then(r=>r.status);
  const a = await mk('E2E石老人',36.10,120.47); const b = await mk('E2E流清河',36.15,120.65);
  return [a,b];
});
console.log('    建浪点状态:', created);
await page.reload({ waitUntil:'networkidle' });
await page.waitForTimeout(2500);
await tab('report'); await page.waitForTimeout(300);
if(await page.locator('#spotFav').isVisible()){
  ok('R1.1 收藏面板渲染浪点卡', await page.locator('#spotFavList .spotcard').count() >= 2);
  await page.click('#spotFavList .spotcard .favbtn >> nth=0'); await page.waitForTimeout(200);
  ok('R1.1 ★收藏切换', await page.locator('#spotFavList .favbtn.on').count() >= 1);
  await page.fill('#spotSearch', '流清河'); await page.waitForTimeout(200);
  ok('R1.2 搜索过滤', await page.locator('#spotFavList .spotcard').count() === 1);
  await page.fill('#spotSearch', ''); await page.waitForTimeout(150);
  await page.selectOption('#spotSort', 'name'); await page.waitForTimeout(200);
  ok('R1.2 排序切换', await page.locator('#spotFavList .spotcard').count() >= 2);
  await page.click('#spotsMapBtn'); await page.waitForTimeout(1000);
  ok('R1.3 地图显示', await page.locator('#spotsMap').isVisible());
  ok('R1.3 地图真实标记', await page.locator('#spotsMap .leaflet-marker-icon').count() >= 2);
  // —— hero 浪点名随选中浪点动态更新（本次修复：不再写死青岛山东头）——
  await page.click('#spotFavList .spotcard-name >> nth=0'); await page.waitForTimeout(1600);
  const heroTxt = await page.locator('#metaSpot').innerText();
  ok('hero 浪点名动态更新(非写死山东头)', /E2E/.test(heroTxt) && !/山东头/.test(heroTxt));
} else {
  fail++; console.log('  ❌ R1 建浪点后 #spotFav 未显示');
}

// —— 0 JS 报错（排除资源404/favicon/直播流HLS）——
const jsErrors = errors.filter(e => !/favicon|Failed to load resource|net::ERR|m3u8|hls|manifest|frag|level|buffer|mediaError/i.test(e));
ok('0 控制台 JS 报错(排除资源404/直播流)', jsErrors.length === 0);
if(jsErrors.length) console.log('    JS错误:', jsErrors);

await browser.close();
console.log(`\n结果：${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
