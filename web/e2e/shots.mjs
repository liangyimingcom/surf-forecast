/* 浪报移植功能截图 —— headless Chromium 抓各新界面 → docs/screenshots/*.png
   用法：先起后端(uvicorn 内存 store)，再 node web/e2e/shots.mjs http://127.0.0.1:PORT
   本轮(UI 优化)新增：U1 加载态骨架屏/spinner、U2 tab/子视图记忆、空态友好提示。 */
import { chromium } from 'playwright';
import path from 'path';

const BASE = process.argv[2] || 'http://127.0.0.1:8848';
const OUT = path.resolve('docs/screenshots');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport:{ width:430, height:920 } });   // 移动端视图
await page.goto(BASE, { waitUntil:'networkidle', timeout:30000 });
await page.waitForTimeout(2500);

// 建两个浪点(demo 已登录)，供收藏面板/地图
await page.evaluate(async ()=>{
  const mk=(n,la,lo)=>fetch('/api/spots',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,lat:la,lon:lo,days:3})});
  await mk('石老人',36.10,120.47); await mk('流清河',36.15,120.65);
});
await page.reload({ waitUntil:'networkidle' });
await page.waitForTimeout(2500);

// 截图：sel 为空 → 整页；元素不存在/不可见/超时均静默跳过（不让脚本崩溃）
async function shot(name, sel){
  const file = path.join(OUT, name+'.png');
  try{
    if(sel){
      const el = page.locator(sel).first();
      if(await el.count() === 0){ console.log('  ⏭  跳过(无元素)', name, sel); return; }
      if(!await el.isVisible().catch(()=>false)){ console.log('  ⏭  跳过(不可见)', name, sel); return; }
      await el.scrollIntoViewIfNeeded({ timeout:4000 }).catch(()=>{});
      await el.screenshot({ path:file, timeout:8000 });
    } else {
      await page.screenshot({ path:file, fullPage:true });
    }
    console.log('  📸', name+'.png');
  }catch(e){ console.log('  ⚠  失败跳过', name, '-', String(e).split('\n')[0]); }
}
// 存在则点击，不存在静默跳过
async function clickIf(sel){ const l=page.locator(sel).first(); if(await l.count()>0){ await l.click().catch(()=>{}); return true; } return false; }
const setTab = async (t)=>{ await page.evaluate((tab)=>{ try{ showTab(tab); }catch(_){}} , t); await page.waitForTimeout(400); };

// ============ 既有界面（形态C + 社区/直播） ============
await shot('00-home-full', null);
await setTab('live'); await page.evaluate(()=>{ try{ showLiveView('catalog'); }catch(_){}} ); await page.waitForTimeout(300);
await shot('01-spotfav', '#spotFav');
if(await clickIf('#spotsMapBtn')){ await page.waitForTimeout(1200); await shot('02-spotsmap', '#spotFav'); await clickIf('#spotsMapBtn'); await page.waitForTimeout(300); }
// 形态C：全国浪点目录 + 直播
if(await page.locator('#catalog').first().isVisible().catch(()=>false)){
  await shot('12-catalog', '#catalog');
  await page.locator('#catList .cat-fav').first().click().catch(()=>{});   // 收藏首个浪点→★
  await page.waitForTimeout(300);
  await shot('27-catalog-fav', '#catalog');
  await page.locator('#catList .cat-fav').first().click().catch(()=>{});   // 复位
  await page.waitForTimeout(150);
  await page.locator('#catChips .cat-chip', { hasText:'海南' }).click().catch(()=>{});
  await page.waitForTimeout(300);
  await shot('13-catalog-hainan', '#catalog');
  await page.locator('#catChips .cat-chip', { hasText:'全部' }).click().catch(()=>{});
  await page.waitForTimeout(200);
  if(await page.locator('#catLiveBtn').count()>0){ await page.click('#catLiveBtn').catch(()=>{}); await page.waitForTimeout(250); await shot('28-catalog-liveonly', '#catalog'); await page.click('#catLiveBtn').catch(()=>{}); await page.waitForTimeout(150); }
  await shot('14-livecams', '#livecams');
  const liveItem = page.locator('#catList .cat-item', { has: page.locator('.cat-live') }).first();
  if(await liveItem.count() > 0){
    await liveItem.click(); await page.waitForTimeout(3500);
    if(await page.locator('#liveEntry').isVisible().catch(()=>false)) await shot('15-live-entry', '#liveEntry');
    await page.locator('#liveEntry').click().catch(()=>{}); await page.waitForTimeout(1500);
    await shot('16-live-modal', '#camModal .annc-modal-box');
    await page.keyboard.press('Escape'); await page.waitForTimeout(300);
    await setTab('report'); await page.waitForTimeout(600);
    await shot('26-report-layout', null);   // 新布局：浪点名条在标签栏下 + 直播入口在日期条下
  }
}
// 社区/周边等面板在「其他」tab 下
await setTab('other');
await shot('03-annc', '#annc');
await shot('04-feedback', '#feedback');
await shot('05-about', '#about');
await shot('06-newswall', '#newswall');
if(await clickIf('#newsList .news-item >> nth=0')){ await page.waitForTimeout(500); await shot('07-news-detail', '#newsModal .annc-modal-box'); await page.keyboard.press('Escape'); await page.waitForTimeout(300); }
await shot('08-carpool', '#carpool');
await shot('09-volume', '#volume');       // 排水量计算器已下线：无元素则自动跳过
await shot('10-nearby', '#nearby');
await setTab('live');
await shot('11-livecams', '#livecams');

// ============ 本轮 UI 优化新界面（U1 加载态 / U2 记忆 / 空态） ============
// 统一先回到「实时浪报」tab 的「全国目录」子视图
await page.evaluate(()=>{ try{ showTab('live'); showLiveView('catalog'); }catch(_){}} );
await page.waitForTimeout(400);

// U1-1 目录骨架屏（注入后立即截，趁真实内容未回填）
await page.evaluate(()=>{ const c=document.getElementById('catalog'); if(c) c.style.display=''; _sfSkel('catList','cat',8); });
await page.waitForTimeout(150);
await shot('17-skeleton-catalog', '#catalog');

// U1-2 直播骨架屏
await page.evaluate(()=>{ try{ showLiveView('cams'); }catch(_){}; _sfSkel('camGrid','cam',4); });
await page.waitForTimeout(150);
await shot('18-skeleton-cams', '#livecams');

// U1-3 顶部加载 spinner（fixed 浮层）
await page.evaluate(()=>{ try{ _sfLoadBar(true); }catch(_){}} );
await page.waitForTimeout(150);
await shot('19-loadbar-spinner', null);   // 整页含顶部浮层 spinner
await page.evaluate(()=>{ try{ _sfLoadBar(false); }catch(_){}} );
// 复位真实内容
await page.evaluate(()=>{ try{ renderCatalog(); renderLivecams(); }catch(_){}} );
await page.waitForTimeout(300);

// U2-1 记住主标签：写 localStorage(other) 后 reload → 恢复到「其他」tab
await page.evaluate(()=>{ try{ localStorage.setItem('sf_tab_v1','other'); }catch(_){}} );
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1800);
await shot('20-memory-tab-other', null);

// U2-2 记住子视图：写 localStorage(live + cams) 后 reload → 恢复到「直播」子视图
await page.evaluate(()=>{ try{ localStorage.setItem('sf_tab_v1','live'); localStorage.setItem('sf_liveview_v1','cams'); }catch(_){}} );
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1800);
await shot('21-memory-liveview-cams', '#livecams');

// 复位默认记忆（live + catalog）
await page.evaluate(()=>{ try{ localStorage.setItem('sf_tab_v1','live'); localStorage.setItem('sf_liveview_v1','catalog'); }catch(_){}} );
await page.reload({ waitUntil:'networkidle' }); await page.waitForTimeout(1800);

// 空态-1 目录搜索无结果
await page.evaluate(()=>{ try{ showTab('live'); showLiveView('catalog'); }catch(_){}} );
await page.waitForTimeout(300);
if(await page.locator('#catSearch').first().isVisible().catch(()=>false)){
  await page.fill('#catSearch', '不存在的浪点zzzz', { timeout:5000 }).catch(()=>{});
  await page.evaluate(()=>{ try{ renderCatalog(); }catch(_){}} );
  await page.waitForTimeout(300);
  await shot('22-empty-catalog', '#catalog');
  await page.fill('#catSearch', '', { timeout:5000 }).catch(()=>{});
  await page.evaluate(()=>{ try{ renderCatalog(); }catch(_){}} );
}

// 空态-2 收藏搜索无匹配（#spotFav 属「浪报详情」tab，有收藏才显示）
await setTab('report');
await page.waitForTimeout(400);
if(await page.locator('#spotSearch').first().isVisible().catch(()=>false)){
  await page.fill('#spotSearch', '不存在的浪点zzzz', { timeout:5000 }).catch(()=>{});
  await page.evaluate(()=>{ try{ renderSpotFav(); }catch(_){}} );
  await page.waitForTimeout(300);
  await shot('23-empty-spotfav', '#spotFav');
  await page.fill('#spotSearch', '', { timeout:5000 }).catch(()=>{});
  await page.evaluate(()=>{ try{ renderSpotFav(); }catch(_){}} );
} else {
  console.log('  ⏭  跳过(收藏面板不可见) 23-empty-spotfav');
}

// 目录排序（综合评分↓）
await page.evaluate(()=>{ try{ showTab('live'); showLiveView('catalog'); }catch(_){}} );
await page.waitForTimeout(300);
if(await page.locator('#catSort').first().isVisible().catch(()=>false)){
  await page.selectOption('#catSort','score').catch(()=>{});
  await page.waitForTimeout(300);
  await shot('24-catalog-sort', '#catalog');
  await page.selectOption('#catSort','default').catch(()=>{});
}

// 深色模式（整页）
await page.evaluate(()=>{ try{ showTab('live'); showLiveView('catalog'); }catch(_){}} );
await page.waitForTimeout(200);
if(await page.locator('#themeToggle').first().isVisible().catch(()=>false)){
  await page.click('#themeToggle').catch(()=>{});
  await page.waitForTimeout(400);
  await shot('25-dark-home', null);
  await page.click('#themeToggle').catch(()=>{});   // 复位浅色
  await page.waitForTimeout(200);
}

await browser.close();
console.log('截图完成 →', OUT);
