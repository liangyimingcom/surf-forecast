# Tasks — surf-forecast UI 交互布局持续优化（第三轮）

> north star 在 north_star.md，roadmap 在 roadmap.md。每轮选**单个最高杠杆下一步**执行，完成后勾 [x]。真正卡住只发一次 blocker。
> 停止：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
> **纪律（防并发冲突复发，已 3 次事故）**：单一驱动器（仅 dashboard auto-nudge，**绝不调 task_run**）；改前先 grep 实际 HTML 确认函数/元素是否已存在；勾选必须与文件一致，禁止记录未落地的完成项。
> **红线**：GMT+8 / wdeg / float→Decimal / 不改引擎内核 / 全 401 / 附加式不破坏 MVP / pytest 145 勿倒退 / terraform 禁 -auto-approve / 合规示例+免责 / 严禁用不存在的数据。

## 已完成（前两轮，勿重复）
- [x] 第一轮：3 标签页/吸顶/回顶 · 目录/直播子视图 · hero 动态浪点名 · 目录排序(5档) · 深色模式 · 加载骨架屏/spinner · tab·子视图记忆 · 空态提示
- [x] 第二轮：布局重定位(#spotbar 浪点名+#liveEntry) · U-a 目录卡片★收藏 · U-b 地图收藏着色 · U-c 可达性(ARIA/focus-visible) · U-d chips 横滑 · U-e 分享深链(#spot=)
- 基线：pytest **145** · Playwright E2E **56/56** + 0 JS 报错 · 28 截图 · docs/UI优化-01~03(两轮)

## V 第三轮候选（每轮挑单个最高杠杆，据 grep 摸底后填具体项；避免重复上面已完成项）
- [x] V-a 目录「仅看有直播」快捷开关 ✅（cat-ctl 加 #catLiveBtn 📹仅直播 toggle(aria-pressed)，_catLiveOnly 过滤 has_live，与区域/搜索/排序叠加；红色选中态+深色。node --check + E2E 58/58：过滤后数量减少且全含 LIVE）
- [x] V-b 目录「收藏优先」排序档 ✅（catSort 增 fav 档，renderCatalog 按 isFav 置顶，复用 FAV_KEY。node --check + E2E 59/59：收藏后选 fav→首项为已收藏★）
- [x] V-c 浪报详情锚点快捷条 ✅（#reportNav 4 按钮 评分/图表/昨日回看/直播 → scrollToEl 平滑滚动，TAB_OF:report，横滑+深色。node --check + E2E 60/60：4 按钮+点击跳转）
- [~] V-d 直播卡片懒加载占位 — 跳过（直播卡为占位缩略图无重负载，懒加载收益低；如后续真播放流再做）
- [x] V-e 首访引导提示 ✅（#onboard 一次性横幅，localStorage sf_onboarded_v1，指引三标签页/★收藏/🔗分享，dismissOnboard 关闭持久化，深色适配。node --check + E2E 62/62：首访显示+关闭隐藏）
> loop 自行按价值/风险选取；每项：grep 确认→实现→node --check→E2E 断言→pytest 不倒退。

## V2 E2E 全绿
- [ ] V2.1 扩 `web/e2e/new_features.mjs` 覆盖第三轮新交互
- [ ] V2.2 全绿 + 0 JS 报错（排除资源404/直播流）；pytest 不倒退

## W 截图
- [x] W.1 ✅ 刷新全部 + 新增 28-catalog-liveonly；V 系列新界面：28 仅直播过滤 · 00-home 含首访引导横幅 · 26-report 含锚点快捷条 · 12/27 目录★收藏 → `docs/screenshots/`

## X 三份文档
- [x] X.1/X.2/X.3 ✅ docs/UI优化-01~03 追加「第三轮」小节（V-a 仅看直播/V-b 收藏优先/V-c 锚点条/V-e 首访引导 + V-d 跳过说明：功能表 16-19 + 操作 N~Q + 代码地图增量）

## Y 收尾
- [x] Y.1 README 更新(+第三轮 4 行 · E2E 56→62 · 截图 30) + 最终复核 ✅ pytest **145** · E2E **62/62** + 0 JS 报错。第三轮 UI 目标达成(V-a/b/c/e + V/W/X)。→ 创建 STOP_LOOP，heartbeat 接手提交+部署。

## Z 部署（可选, 高风险, 停下等确认）
- [x] Z.1 人工确认后提交并部署上线 ✅ 2026-07-13: commit a0dafa5(已推origin) · pytest 145 门禁 · t4g镜像09:52推ECR · ECS滚动COMPLETED 1/1 · CloudFront验证(toggleCatFav/spotsMapLegend/tablist/shareSpot/收藏优先/锚点/sf_onboard 全命中 · home 200 · api/health 200 · 未登录 report/catalog/cams=401)
