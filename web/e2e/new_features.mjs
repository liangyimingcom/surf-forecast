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
ok('U-c tablist 角色', await page.locator('#maintab').getAttribute('role') === 'tablist');
ok('U-c aria-selected 同步激活标签', await page.locator('.maintab-btn[aria-selected="true"]').getAttribute('data-tab') === 'live');
ok('V-e 首访引导显示', await page.locator('#onboard').isVisible());
await page.click('#onboard .onboard-x'); await page.waitForTimeout(150);
ok('V-e 引导关闭后隐藏', !(await page.locator('#onboard').isVisible()));
ok('排水量功能已移除', await page.locator('#volume').count() === 0);

// —— 【实时浪报】tab：全国目录 + 直播 ——
await tab('live'); await page.waitForTimeout(300);
if(await page.locator('#catalog').isVisible()){
  ok('C 全国浪点目录显示', await page.locator('#catList .cat-item').count() >= 40);
  ok('C 区域筛选chips', await page.locator('#catChips .cat-chip').count() >= 5);
  ok('U-d 区域chips横向滚动', (await page.evaluate(()=>getComputedStyle(document.getElementById('catChips')).overflowX)) === 'auto');
  ok('C 直播卡片(hls)', await page.locator('#camGrid .cam-card').count() >= 10);
  const before = await page.locator('#catList .cat-item').count();
  await page.locator('#catChips .cat-chip', { hasText:'海南' }).click();
  await page.waitForTimeout(200);
  ok('C 区域筛选生效', await page.locator('#catList .cat-item').count() < before);
  await page.locator('#catChips .cat-chip', { hasText:'全部' }).click();
  // 子视图切换：目录 <-> 直播（默认目录，直播折叠避免超长）
  await page.locator('#liveSubnav .livesub-btn', { hasText:'直播' }).click();
  await page.waitForTimeout(300);
  ok('子视图 切直播(直播显/目录隐)', (await page.locator('#livecams').isVisible()) && !(await page.locator('#catalog').isVisible()));
  await page.locator('#liveSubnav .livesub-btn', { hasText:'目录' }).click();
  await page.waitForTimeout(300);
  ok('子视图 切回目录', await page.locator('#catalog').isVisible());
  // 目录排序：有直播优先 → 首项含 LIVE 徽标
  await page.selectOption('#catSort', 'live'); await page.waitForTimeout(250);
  ok('目录排序 有直播优先(首项LIVE)', await page.locator('#catList .cat-item').first().locator('.cat-live').count() === 1);
  await page.selectOption('#catSort', 'default'); await page.waitForTimeout(150);
  // U-a 目录卡片直接收藏（点星切换 + 不触发加载跳转）
  const _favWasOff = ((await page.locator('#catList .cat-fav').first().getAttribute('class'))||'').includes('off');
  await page.locator('#catList .cat-fav').first().click(); await page.waitForTimeout(200);
  const _favNowOff = ((await page.locator('#catList .cat-fav').first().getAttribute('class'))||'').includes('off');
  ok('U-a 目录收藏点星切换', _favNowOff !== _favWasOff);
  ok('U-a 点星不跳转(仍在实时浪报)', (await page.locator('.maintab-btn.on').getAttribute('data-tab')) === 'live');
  await page.locator('#catList .cat-fav').first().click(); await page.waitForTimeout(150);  // 复位
  // V-a 仅看直播 toggle
  const _beforeLive = await page.locator('#catList .cat-item').count();
  await page.click('#catLiveBtn'); await page.waitForTimeout(250);
  const _afterLive = await page.locator('#catList .cat-item').count();
  ok('V-a 仅直播过滤(数量减少)', _afterLive < _beforeLive && _afterLive >= 1);
  ok('V-a 仅直播项全含LIVE', _afterLive === (await page.locator('#catList .cat-item .cat-live').count()));
  await page.click('#catLiveBtn'); await page.waitForTimeout(150);  // 复位
  // V-b 收藏优先排序：收藏某项→选 fav→首项为已收藏
  await page.locator('#catList .cat-fav').first().click(); await page.waitForTimeout(200);
  const _favSlugName = await page.locator('#catList .cat-item').first().locator('.cat-name').innerText();
  await page.selectOption('#catSort', 'fav'); await page.waitForTimeout(200);
  ok('V-b 收藏优先(首项为已收藏★)', ((await page.locator('#catList .cat-item').first().locator('.cat-fav').getAttribute('class'))||'').includes('off') === false);
  await page.selectOption('#catSort', 'default'); await page.waitForTimeout(120);
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
ok('V-c 详情锚点条 4 按钮', await page.locator('#reportNav .rnav-btn').count() === 4);
await page.locator('#reportNav .rnav-btn', { hasText:'图表' }).click(); await page.waitForTimeout(200);
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
  ok('U-b 地图图例显示', await page.locator('#spotsMapLegend').isVisible());
  ok('U-b 彩色标记(sf-mk)', await page.locator('#spotsMap .sf-mk').count() >= 2);
  // —— hero 浪点名随选中浪点动态更新（本次修复：不再写死青岛山东头）——
  await page.click('#spotFavList .spotcard-name >> nth=0'); await page.waitForTimeout(1600);
  const heroTxt = await page.locator('#metaSpot').innerText();
  ok('hero 浪点名动态更新(非写死山东头)', /E2E/.test(heroTxt) && !/山东头/.test(heroTxt));
} else {
  fail++; console.log('  ❌ R1 建浪点后 #spotFav 未显示');
}

// ═══════════ 本轮 UI 优化新交互断言（V.1：U1 加载态 / U2 记忆+空态）═══════════

// —— U1 加载态：骨架屏出现/消失 + 顶部 spinner ——
ok('U1 骨架屏/ spinner 助手已接线', await page.evaluate(()=>
  typeof _sfSkel==='function' && typeof _sfSkelRows==='function' && typeof _sfLoadBar==='function'));
await tab('live'); await page.evaluate(()=>window.showLiveView('catalog')); await page.waitForTimeout(150);
// 目录骨架：手动注入 → 出现；重渲染 → 消失
await page.evaluate(()=>_sfSkel('catList','cat',8));
ok('U1 目录骨架屏出现', await page.locator('#catList .sf-skel').count() >= 8);
await page.evaluate(()=>renderCatalog());
ok('U1 目录骨架屏消失(渲染后)', await page.locator('#catList .sf-skel').count() === 0);
// 直播骨架
await page.evaluate(()=>_sfSkel('camGrid','cam',4));
ok('U1 直播骨架屏出现', await page.locator('#camGrid .sf-skel').count() >= 4);
await page.evaluate(()=>renderLivecams());
ok('U1 直播骨架屏消失(渲染后)', await page.locator('#camGrid .sf-skel').count() === 0);
// loadLive 顶部细 spinner：显示 → 隐藏
await page.evaluate(()=>_sfLoadBar(true));
ok('U1 顶部 spinner 出现', await page.locator('#sfLoadBar').isVisible());
await page.evaluate(()=>_sfLoadBar(false));
ok('U1 顶部 spinner 隐藏', !(await page.locator('#sfLoadBar').isVisible()));

// —— U2 tab / 子视图 记忆持久化（localStorage + 刷新恢复 + 脏值回退）——
await tab('other'); await page.waitForTimeout(150);
ok('U2 主标签写入 localStorage(other)', (await page.evaluate(()=>localStorage.getItem('sf_tab_v1'))) === 'other');
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1600);
ok('U2 刷新后恢复上次主标签(other)', (await page.locator('.maintab-btn.on').getAttribute('data-tab')) === 'other');
// 子视图记忆：切到直播 → 写入 → 刷新恢复
await tab('live'); await page.waitForTimeout(150);
await page.evaluate(()=>window.showLiveView('cams')); await page.waitForTimeout(150);
ok('U2 子视图写入 localStorage(cams)', (await page.evaluate(()=>localStorage.getItem('sf_liveview_v1'))) === 'cams');
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1600);
ok('U2 刷新后恢复子视图(直播显/目录隐)', (await page.locator('#livecams').isVisible()) && !(await page.locator('#catalog').isVisible()));
// 脏值/非法值 → 回退默认（不影响后端契约）
await page.evaluate(()=>{ localStorage.setItem('sf_tab_v1','__bad__'); localStorage.setItem('sf_liveview_v1','__bad__'); });
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1600);
ok('U2 脏值回退默认主标签(live)', (await page.locator('.maintab-btn.on').getAttribute('data-tab')) === 'live');
ok('U2 脏值回退默认子视图(目录显)', await page.locator('#catalog').isVisible());

// —— 空态友好提示：目录搜索无结果 / 收藏搜索无结果 ——
await tab('live'); await page.evaluate(()=>window.showLiveView('catalog')); await page.waitForTimeout(150);
await page.fill('#catSearch', 'zzz不存在的浪点xyz'); await page.waitForTimeout(200);
ok('空态 目录无结果提示渲染', (await page.locator('#catList .cat-empty').count()) === 1
  && (await page.locator('#catList .cat-empty').innerText()).includes('没有匹配'));
await page.fill('#catSearch', ''); await page.waitForTimeout(150);
await tab('report'); await page.waitForTimeout(150);
if(await page.locator('#spotFav').isVisible()){
  await page.fill('#spotSearch', 'zzz不存在xyz'); await page.waitForTimeout(200);
  ok('空态 收藏无匹配提示渲染', (await page.locator('#spotFavEmpty').isVisible())
    && (await page.locator('#spotFavEmpty').innerText()).includes('没有匹配'));
  await page.fill('#spotSearch', ''); await page.waitForTimeout(150);
} else {
  fail++; console.log('  ❌ 空态 收藏面板 #spotFav 未显示，无法验证收藏空态');
}

// —— U-e 分享深链：#spot 恢复浪点 + 直接进浪报详情 ——
await page.evaluate(()=>{ location.hash='#spot=30.50,122.10,E2E深链浪点'; });
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(3500);
ok('U-e 深链恢复浪点名', ((await page.locator('#metaSpot').innerText().catch(()=>''))||'').includes('深链'));
ok('U-e 深链进浪报详情', (await page.locator('.maintab-btn.on').getAttribute('data-tab')) === 'report');
await page.evaluate(()=>{ location.hash=''; });

// —— 深色模式切换 ——
await page.click('#themeToggle'); await page.waitForTimeout(200);
ok('深色模式 开启(body.dark)', await page.locator('body.dark').count() === 1);
await page.click('#themeToggle'); await page.waitForTimeout(200);
ok('深色模式 关闭', await page.locator('body.dark').count() === 0);

// —— 图表悬浮 tooltip：高手模式下 hover 命中列 → #chartTip 显示数值 ——
await tab('report'); await page.evaluate(()=>window.setMode&&window.setMode(true)); await page.waitForTimeout(400);
const hit0 = page.locator('.chartbox svg .ctHit').first();
if(await hit0.count()){
  await hit0.scrollIntoViewIfNeeded(); await page.waitForTimeout(200);
  await hit0.hover(); await page.waitForTimeout(150);
  ok('图表 tooltip 悬浮显示', (await page.locator('#chartTip').getAttribute('class')||'').includes('show')
    && ((await page.locator('#chartTip').innerText())||'').length > 0);
} else {
  fail++; console.log('  ❌ 图表 tooltip 未找到 .ctHit 命中列');
}

// —— 0 JS 报错（排除资源404/favicon/直播流HLS）——
const jsErrors = errors.filter(e => !/favicon|Failed to load resource|net::ERR|m3u8|hls|manifest|frag|level|buffer|mediaError/i.test(e));
ok('0 控制台 JS 报错(排除资源404/直播流)', jsErrors.length === 0);
if(jsErrors.length) console.log('    JS错误:', jsErrors);

await browser.close();
console.log(`\n结果：${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
