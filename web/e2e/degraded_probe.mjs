/* W2.3 故障降级探针：拦截 /api/report* 使其失败 → 断言 #sfDegraded 可见 + metaCalib 诚实标注。
   用法：起后端(SF_FRONTEND+SF_SEED_SPOTS) → node web/e2e/degraded_probe.mjs http://127.0.0.1:PORT */
import { chromium } from 'playwright';
const BASE = process.argv[2] || 'http://127.0.0.1:8848';
let pass=0, fail=0;
const ok=(n,c)=>{ c?(pass++,console.log('  ✅',n)):(fail++,console.log('  ❌',n)); };
const browser = await chromium.launch();
const page = await browser.newPage();
await page.route('**/api/report*', r => r.abort());   // 模拟 Open-Meteo/后端故障
await page.goto(BASE, { waitUntil:'domcontentloaded', timeout:30000 });
await page.waitForFunction(()=>window.__SF_READY__===true, {timeout:30000}).catch(()=>{});
await page.waitForTimeout(500);
ok('故障下页面非白屏(有 hero/主标签)', await page.locator('.maintab .maintab-btn').count() === 3);
ok('降级 banner 可见', await page.locator('#sfDegraded').isVisible());
ok('metaCalib 诚实标注示例数据', (await page.locator('#metaCalib').innerText()).includes('示例数据'));
await browser.close();
console.log(`\n结果：${pass} passed / ${fail} failed`);
process.exit(fail?1:0);
