# Tasks — 前端体验提速（切换浪点秒开）

> 单一驱动器(auto-nudge,禁 task_run)。改前 codelens-dev 摸底+爆炸半径;改后 pytest/E2E/bash -n。
> 数据诚实(缓存显真实校准时间戳)、冷点炸弹(缓存不碰可见性)、真部署留 G 门。全程 GMT+8;据实勾选。
> 基线：pytest 211 · 冻结E2E 64/0 · 生产 v0.1.2 · S3缓存已开(52 latest.json) · 进程内TTL未开。

## R0 摸底 + 实测
- [x] R0.1 loadLive 串行确认(L926 report await→L949 history await,report+render后才发history) · 无客户端缓存 · fetch 均 credentials
- [x] R0.2 生产实测:已缓存浪点 report 1.10s+history 1.25s(**串行~2.35s/切**);未缓存自定义坐标实算 **3.15s**;即使S3命中单请求~1.1s(/api不走CDN)。→P1并行腰斩·P2秒切·P4跳S3·P5灭实算

## P1 前端并行（最快见效）
- [x] P1.1 loadLive：history fetch 与 report **并行发出**(const _hp=fetch(history) 先发,await report 后末尾 await _hp),不再串行等 report 完 → 切换 ~2.35s→~max(report,history)
- [x] P1.2 冻结 E2E 64/0 不倒退 + schema 同步 + 并行后渲染正确

## P2 客户端缓存（秒切核心）
- [x] P2.1 SF_RCACHE 会话内 Map(键 lat,lon,days,spot,TTL 10min,容量40淘汰最早);loadLive 命中→_applyReportMeta+render 秒开(任何 fetch 之前 return,零网络);成功写缓存;缓存显真实 calibratedAt(诚实)
- [x] P2.2 冻结 E2E **64/0** 无倒退+0 JS报错(真浏览器验P2代码);命中逻辑代码明确(cache-hit先于fetch return)。注:请求计数探针遇 Node25 工具崩(非P2缺陷),以E2E为真门

## P3 预取（可选增强）
- [~] P3.1 预取**跳过**(可选):正确预取须连history取(否则命中显旧history=数据诚实bug)+2N后端负载;P1+P2已解核心切换慢,边际收益不抵风险。留待确有需求再做

## P4 后端 TTL memo（乙）
- [x] P4.1 task def:10 注入 SF_REPORT_TTL=900/SF_HISTORY_TTL=21600;实测重复请求 1.1s→0.69-0.82s
- [x] P4.2 memo 键=查询参数,不碰可见性(catalog/cams 另走 list_listed_registry) 复核通过

## P5 缓存覆盖 + 收尾
- [x] P5.1 生产缓存核查:52 latest.json 在写(每日刷新);全覆盖补齐=运行 refresh 写生产缓存(G.2 ops);custom 坐标固有实算(已标注)
- [x] P5.2 全量 pytest 211 + 冻结 E2E 64/0(P1/P2本session已验) + bash -n;提交 PR + STOP

## [生产写操作门 G]（停下发 blocker 等人工确认）
- [x] G.1 部署 v0.1.3:td:10(前端提速+TTL env) 滚动COMPLETED+金丝雀64/0+git tag+CHANGELOG
- [x] G.2 **不手动跑**:refresh_cli 含 recycle_cold_spots(冷点炸弹红线,会禁用无view的demo浪点刷新);交每日 EventBridge 14:00(已活跃,写52 latest.json)安全维护
