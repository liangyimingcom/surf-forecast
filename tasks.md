# Tasks — surf-forecast UI 交互布局持续优化

> north star 在 north_star.md，roadmap 在 roadmap.md。每轮选**单个最高杠杆下一步**执行，完成后勾 [x]。真正卡住只发一次 blocker。
> 停止：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
> **纪律（防并发冲突复发）**：单一驱动器；改前先 grep 实际 HTML 确认函数/元素是否已存在；勾选必须与文件一致，禁止记录未落地的完成项。
> **红线**：GMT+8 / wdeg / float→Decimal / 不改引擎内核 / 全 401 / 附加式不破坏 MVP / pytest 145 勿倒退 / terraform 禁 -auto-approve / 合规示例+免责。

## 已完成（本轮起点，勿重复）
- [x] hero 元信息随浪点动态(#metaSpot 可点跳详情) + 删写死日出/水温/月相
- [x] 实时浪报「目录/直播」子视图切换(默认目录) + 主导航吸顶(sticky) + 回到顶部按钮
- 基线：pytest 145 · E2E 29/29 + 0 JS 报错

## U0 基线 + 摸底
- [x] U0.1 pytest 145 + E2E 基线复确认（起点未倒退）✅
- [x] U0.2 codelens/grep 摸底 ✅（2026-07-11）：
  - **grep 现状（web/浪报MVP.html, 1916 行）**：`loadLive`@758 `renderSpotFav`@956 `loadCams`@1172 `loadCatalog`@1216 `loadCatalogScores`@1224 `renderCatalog`@1239 `TAB_OF`@1281 `showLiveView`@1295 `showTab`@1297 均已存在。
  - **加载态=0**：`loadCatalog/loadCams/loadLive` 无 skeleton/spinner；grep `skeleton|spinner` 命中 0（仅有 `*-empty` 空态样式），首屏/切浪点期间会短暂空列表/白屏。→ **最高杠杆**。
  - **tab/子视图记忆=无**：`_curTab`(@1290)、`_liveView`(@1291) 仅内存变量；`load` 事件恒 `showTab('live')`+默认 `catalog`。localStorage 仅用于收藏(`FAV_KEY`@932)，无 tab/view 键。→ **次高杠杆**。
  - **空态部分已有**：`spotFavEmpty`(#468 收藏空态“无匹配浪点”)、`cat-empty`/`news-empty`/`cam-empty` 均存在，但收藏 0 项与搜索 0 结果的文案未区分、直播/目录未登录占位可再友好化。
  - **CodeLens 守红线/爆炸半径**：`find_route` 确认 `/api/catalog`(app.py:183)、`/api/catalog/scores`(:204)、`/api/cams`(cams.py:31)、`/api/report`(:83) 均为后端 FastAPI 路由；引擎内核 `analyze.py`(_score_point/analyze_day/build_context→scoring/physics/validate) 为独立调用图。本轮改动仅在单个 HTML 文件内（loaders 只 fetch 这些路由），**不触碰任何路由/契约(wdeg)/引擎内核**，爆炸半径=浪报MVP.html 自身。
  - **本轮选定（1–2 项最高杠杆）**：U1=加载态骨架屏/spinner；U2=tab/子视图记忆 + 空态友好提示。

## U1..Un UI 优化批次（每轮 1–2 项，据摸底填具体项）
- [x] 目录排序下拉 ✅（#catSort 5档: 推荐/综合评分↓/有直播优先/名称/地区；renderCatalog 排序未知分置底；.cat-ctl 搜索+排序并排。**已落 HTML**，E2E 有直播优先→首项含LIVE）
- [x] 深色模式切换 ✅（header #themeToggle 🌙/☀️；body.dark 覆盖变量(--bg/--card/--ink*/--line/--accent)+白底面&输入映射；toggleTheme+localStorage('sf_theme')持久化+prefers-color-scheme 初始化。**已落 HTML**，E2E 开/关）
- [x] 加载态骨架屏/spinner（loadCatalog/loadLive/loadCams 期间，避免首屏/切浪点白屏）✅ **已落 HTML**（U1：`.sf-skel`/`.sk-cat`/`.sk-cam` 骨架屏 + `.sf-spinner` + `_sfSkel`/`_sfLoadBar` 助手；loadLive 顶部 spinner 条、loadCams 骨架卡片、loadCatalog 乐观展开骨架并 401 回滚隐藏；node --check 通过；E2E 全绿由 U1 校验步骤复核）
- [x] tab/子视图记忆 + 空态强化 ✅ **已落 HTML**（showTab→localStorage `sf_tab_v1`、showLiveView→`sf_liveview_v1`；load 恢复上次主 tab+子视图，脏值/缺失回退 live/catalog 不破坏 E2E 首断言；目录空态「没有匹配的浪点，换个关键词或地区试试」、收藏空态「没有匹配「q」的浪点」。对齐上一 cycle 预写的 U2 E2E 契约。）

> **当前真实基线**：pytest **145** · E2E **47/47** + 0 JS 报错（U1 骨架屏 + U2 tab记忆/子视图记忆/脏值回退/空态 + 目录排序 + 深色模式 全覆盖）。已完成 UI 优化项：目录排序 / 深色模式 / 加载骨架屏 / tab·子视图记忆 / 空态强化。下一步可选：V 汇总 E2E 收口 → W 截图 → X 文档。
> ⚠️ **并发冲突事故(2026-07-11 23:32)**：本 loop(chat-3 auto-nudge) 与我启动的 task_run 后台 loop(surf-forecast-ui-optimize-goal) **双驱动**，并发写同一 tasks.md/HTML。后台 loop 曾把本段重写为它的计划(U1=骨架屏/U2=tab记忆)并写详细 U0.2 摸底；我 cycle2 的 strReplace 因此两次失败。已 STOP_LOOP + autonudge_stop 停双方并 reconcile 回真实状态。**恢复须单一驱动器。**

## V E2E 全绿
- [x] V.1 `web/e2e/new_features.mjs` 已覆盖全部新交互（目录排序/深色模式/骨架屏/tab·子视图记忆/脏值回退/空态）✅
- [x] V.2 全绿 + 0 JS 报错 ✅ **E2E 47/47**（排除资源404/直播流）；pytest 145 未倒退

## W 截图
- [x] W.1 headless Chrome 截图 ✅ 扩 `web/e2e/shots.mjs`（+24-catalog-sort/25-dark-home）→ `docs/screenshots/` 共 24 张（00-08/10/12-25；含骨架屏 17-18/spinner 19/tab记忆 20/子视图记忆 21/空态 22-23/目录排序 24/深色模式 25）

## X 三份文档
- [x] X.1 功能介绍 ✅ `docs/UI优化-01-功能介绍.md`（9 项优化总览表 + 逐项 what/why + 截图引用）
- [x] X.2 交互操作指南 ✅ `docs/UI优化-02-交互操作指南.md`（A-G 分步操作 + 预期 + 常见问题）
- [x] X.3 教学教程 ✅ `docs/UI优化-03-教学教程.md`（代码地图/设计原则/新增交互模式/踩坑含并发教训/验证基线）

## Y 收尾
- [x] Y.1 README 更新 ✅（新增「会员视图 UI 交互布局优化」9 项矩阵 + 测试/截图/文档/合规）
- [x] Y.2 最终复核 ✅ pytest **145** + E2E **47/47** + 0 JS 报错；UI 优化目标（优化5项+V/W/X）全达成
- 目标达成：继续优化 UI 交互布局 + 迭代配套功能 + E2E 无误 + 截图 + 三文档 ✅。剩 Z 部署为可选高风险步骤，停等人工确认。

## Z 部署（可选, 高风险, 停下等确认）
- [ ] Z.1 到部署步骤发一次 blocker 等人工确认，禁在 loop 内自动推生产
