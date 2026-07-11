/* 浪报移植功能截图 —— headless Chromium 抓各新界面 → docs/screenshots/*.png
   用法：先起后端(uvicorn 内存 store)，再 node web/e2e/shots.mjs http://127.0.0.1:PORT */
import { chromium } from 'playwright';
import path from 'path';

const BASE = process.argv[2] || 'http://127.0.0.1:8850';
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

async function shot(name, sel){
  const file = path.join(OUT, name+'.png');
  if(sel){ const el = page.locator(sel).first(); await el.scrollIntoViewIfNeeded(); await el.screenshot({ path:file }); }
  else { await page.screenshot({ path:file, fullPage:true }); }
  console.log('  📸', name+'.png');
}

await shot('00-home-full', null);
await shot('01-spotfav', '#spotFav');
await page.click('#spotsMapBtn'); await page.waitForTimeout(1200);
await shot('02-spotsmap', '#spotFav');
await page.click('#spotsMapBtn'); await page.waitForTimeout(300);
await shot('03-annc', '#annc');
await shot('04-feedback', '#feedback');
await shot('05-about', '#about');
await shot('06-newswall', '#newswall');
await page.click('#newsList .news-item >> nth=0'); await page.waitForTimeout(500);
await shot('07-news-detail', '#newsModal .annc-modal-box');
await page.keyboard.press('Escape'); await page.waitForTimeout(300);
await shot('08-carpool', '#carpool');
await shot('09-volume', '#volume');
await shot('10-nearby', '#nearby');
await shot('11-livecams', '#livecams');

await browser.close();
console.log('截图完成 →', OUT);
