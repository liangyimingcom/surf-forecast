/* B2 守卫：PAGE_SCHEMA 的 tab 键必须与 maintab 的 data-tab 集合一致（防 page-schema 漂移）。
   纯 node、无浏览器、无网络 → 可靠、可作自动门。用法：node web/e2e/schema_check.mjs */
import { readFileSync } from 'fs';
const html = readFileSync(new URL('../浪报MVP.html', import.meta.url), 'utf8');

const dataTabs = [...new Set([...html.matchAll(/data-tab="([a-z]+)"/g)].map(m => m[1]))].sort();
const m = html.match(/const PAGE_SCHEMA\s*=\s*\{([\s\S]*?)\n\};/);
if (!m) { console.error('❌ 未找到 PAGE_SCHEMA'); process.exit(1); }
const schemaKeys = [...m[1].matchAll(/^\s*([a-z]+):\s*\{/gm)].map(x => x[1]).sort();

const same = dataTabs.length === schemaKeys.length && dataTabs.every((t, i) => t === schemaKeys[i]);
if (same) {
  console.log('✅ page-schema 同步：', schemaKeys.join(','));
  process.exit(0);
}
console.error('❌ page-schema 漂移！maintab data-tab=[' + dataTabs + '] vs PAGE_SCHEMA=[' + schemaKeys + ']');
process.exit(1);
