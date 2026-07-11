/* 浪报移植功能 E2E —— headless Chromium 加载前端，断言 R1/R2 新功能 + 0 JS 报错。
   用法：先起后端(uvicorn, 内存 store)，再 node web/e2e/new_features.mjs http://127.0.0.1:PORT */
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:8848';
const errors = [];
let pass = 0, fail = 0;
function ok(name, cond){ if(cond){ pass++; console.log('  ✅', name); } else { fail++; console.log('  ❌', name); } }

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', m => { if(m.type()==='error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('PAGEERROR: '+e.message));

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(2500);   // 等 demoAuth + loadLive + 各 init

// —— R2 静态/示例功能（load 即渲染，不依赖后端）——
ok('R2.1 公告列表渲染', await page.locator('#anncList .annc-item').count() > 0);
ok('R2.2 反馈表单存在', await page.locator('#feedback #fbType').count() === 1);
ok('R2.3 关于section存在', await page.locator('#about').count() === 1);
ok('R2.4 活动墙chips渲染', await page.locator('#newsChips .news-chip').count() >= 4);
ok('R2.4 活动墙卡片渲染', await page.locator('#newsList .news-item').count() > 0);
ok('R2.5 拼车列表渲染', await page.locator('#carpoolList .news-item').count() === 4);
ok('R2.6 排水量section存在', await page.locator('#volume #volWeight').count() === 1);
ok('R2.7 周边分组渲染', await page.locator('#nearbyGroups .nb-group').count() === 3);
ok('R2.8→C 直播卡片(真实cams, 升级自占位)', await page.locator('#camGrid .cam-card').count() >= 10);

// —— R2.2 反馈校验交互 ——
await page.click('#feedback .fb-submit');
ok('R2.2 空提交报错', (await page.locator('#fbMsg').textContent()).includes('类型'));
await page.selectOption('#fbType', { index: 1 });
await page.fill('#fbContent', 'E2E 测试反馈内容');
await page.click('#feedback .fb-submit');
ok('R2.2 有效提交示例成功', (await page.locator('#fbMsg').textContent()).includes('已收到'));

// —— R2.4 活动墙详情弹层 ——
await page.click('#newsList .news-item >> nth=0');
await page.waitForTimeout(300);
ok('R2.4 详情弹层打开', await page.locator('#newsModal.open').count() === 1);
ok('R2.4 详情含示例badge', await page.locator('#newsModal .annc-badge').count() === 1);
await page.keyboard.press('Escape');
await page.waitForTimeout(200);
ok('R2.4 Esc 关闭弹层', await page.locator('#newsModal.open').count() === 0);

// —— R2.4 类型筛选 ——
const before = await page.locator('#newsList .news-item').count();
await page.click('#newsChips .news-chip >> nth=3');   // 选某类型
await page.waitForTimeout(200);
const after = await page.locator('#newsList .news-item').count();
ok('R2.4 类型筛选生效', after >= 1 && after <= before);

// —— R2.6 排水量计算标定 ——
await page.fill('#volWeight', '70');
await page.selectOption('#volLevel', '0.443');
await page.click('#volume .vol-btn');
ok('R2.6 70kg中级≈31.0L', (await page.locator('#volResult').textContent()).includes('31.0 L'));

// —— R1 真实浪点（依赖后端 demoAuth + /api/spots）——
ok('R1 收藏面板控件存在(搜索框)', await page.locator('#spotSearch').count() === 1);
ok('R1.3 地图开关按钮存在', await page.locator('#spotsMapBtn').count() === 1);
// 经 API 建两个浪点(demo 已登录, 同源 cookie)，再刷新加载收藏面板
const created = await page.evaluate(async ()=>{
  const mk = (name,lat,lon)=>fetch('/api/spots',{method:'POST',credentials:'include',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({name,lat,lon,days:3})}).then(r=>r.status);
  const a = await mk('E2E石老人',36.10,120.47); const b = await mk('E2E流清河',36.15,120.65);
  return [a,b];
});
console.log('    建浪点状态:', created);
await page.reload({ waitUntil:'networkidle' });
await page.waitForTimeout(2500);
if(await page.locator('#spotFav').isVisible()){
  ok('R1.1 收藏面板渲染浪点卡', await page.locator('#spotFavList .spotcard').count() >= 2);
  // R1.1 收藏切换
  await page.click('#spotFavList .spotcard .favbtn >> nth=0');
  await page.waitForTimeout(200);
  ok('R1.1 ★收藏状态切换', await page.locator('#spotFavList .favbtn.on').count() >= 1);
  // R1.2 搜索过滤
  await page.fill('#spotSearch', '流清河');
  await page.waitForTimeout(200);
  ok('R1.2 搜索过滤生效', await page.locator('#spotFavList .spotcard').count() === 1);
  await page.fill('#spotSearch', '');
  await page.waitForTimeout(150);
  // R1.2 排序切换
  await page.selectOption('#spotSort', 'name');
  await page.waitForTimeout(200);
  ok('R1.2 排序切换不报错', await page.locator('#spotFavList .spotcard').count() >= 2);
  // R1.3 地图渲染标记
  await page.click('#spotsMapBtn');
  await page.waitForTimeout(1000);
  ok('R1.3 地图容器显示', await page.locator('#spotsMap').isVisible());
  ok('R1.3 地图渲染真实标记', await page.locator('#spotsMap .leaflet-marker-icon').count() >= 2);
} else {
  fail++; console.log('  ❌ R1 建浪点后 #spotFav 仍未显示');
}

// —— 形态C：58浪点目录 / 直播 / 详情直播入口（需 SF_SEED_SPOTS 灌注册表）——
if(await page.locator('#catalog').isVisible()){
  ok('C 全国浪点目录显示', await page.locator('#catList .cat-item').count() >= 40);
  ok('C 区域筛选chips', await page.locator('#catChips .cat-chip').count() >= 5);
  ok('C 直播卡片(hls)', await page.locator('#camGrid .cam-card').count() >= 10);
  // 点一个有 LIVE 的目录项 → 详情直播入口
  const liveItem = page.locator('#catList .cat-item', { has: page.locator('.cat-live') }).first();
  if(await liveItem.count() > 0){
    await liveItem.click();
    await page.waitForTimeout(3500);
    ok('C 详情直播入口横幅', await page.locator('#liveEntry').isVisible());
    await page.locator('#liveEntry').click();
    await page.waitForTimeout(1000);
    ok('C 直播弹层打开', await page.locator('#camModal.open').count() === 1);
    await page.keyboard.press('Escape');
  } else { console.log('  ⏭  无 LIVE 目录项'); }
} else {
  console.log('  ⏭  #catalog 未显示(未 SF_SEED_SPOTS 灌注册表)，跳过形态C断言');
}

// —— 0 JS 报错（排除资源404/favicon/直播流HLS）——
const jsErrors = errors.filter(e => !/favicon|Failed to load resource|net::ERR|m3u8|hls|manifest|frag|level|buffer|mediaError/i.test(e));
ok('0 控制台 JS 报错(排除资源404/直播流)', jsErrors.length === 0);
if(jsErrors.length) console.log('    JS错误:', jsErrors);

await browser.close();
console.log(`\n结果：${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
