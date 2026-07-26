# Roadmap — 前端体验提速

单一驱动器(auto-nudge,禁 task_run)。每轮 codelens-dev 摸底+爆炸半径+守红线;改后 pytest/E2E/bash -n。
真部署留 G 门。排序:先见效最快的前端(甲)→后端(乙)。

## R0 摸底 + 实测
- codelens/grep：loadLive/onSpotChange/showTab 切换链;client 有无缓存;串行 fetch 点。
- 实测：demo 登录后 time /api/report(已缓存 vs 未缓存浪点) + /api/report/history,量化各环节耗时,确认瓶颈。

## P1 前端并行（甲，最快见效）
- loadLive：/api/report 与 /api/report/history **Promise.all 并行**（现为串行,history 等 report 完）。
- [随层] E2E 断言并行不破坏渲染;冻结 E2E 64/0 不倒退。

## P2 客户端缓存（甲，秒切核心）
- REPORT/HISTORY 会话内 Map 缓存(键 lat,lon,days,spot);切换命中即用(先渲染缓存再后台校验可选);切回已访问浪点秒开。
- 缓存内容渲染仍显真实 calibratedAt(数据诚实);容量上限+简单淘汰。
- [随层] E2E:切到 A→切到 B→切回 A 秒开(无 loading spinner 长等)断言。

## P3 预取（甲，可选增强）
- 收藏/当前相邻浪点后台预取到客户端缓存,切换即命中。

## P4 后端 TTL memo（乙）
- 部署环境开 SF_REPORT_TTL/SF_HISTORY_TTL(如 900/21600);确认 deps memo 生效(W3 已实现)。 ← env 改动,部署时
- [验证] 重复请求同浪点后端只算一次(日志/计时)。

## P5 缓存覆盖 + 收尾（乙）
- 确认 58 上架浪点全有 latest.json(缺的补刷新覆盖);custom 坐标固有实算(标注)。
- 全量 pytest + 冻结 E2E 64/0 + bash -n;据实勾选;STOP。

## [生产写操作门 G]（停下发 blocker 等人工确认）
- G.1 部署(前端 + task def 加 SF_REPORT_TTL/SF_HISTORY_TTL env + build+redeploy+canary+tag+CHANGELOG)
- G.2 (若需)刷新覆盖补齐生产缓存
