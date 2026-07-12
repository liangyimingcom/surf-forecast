# Tasks — surf-forecast UI 交互布局持续优化（第二轮）

> north star 在 north_star.md，roadmap 在 roadmap.md。每轮选**单个最高杠杆下一步**执行，完成后勾 [x]。真正卡住只发一次 blocker。
> 停止：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
> **纪律（防并发冲突复发，已 3 次事故）**：单一驱动器（仅 dashboard auto-nudge，**绝不调 task_run**）；改前先 grep 实际 HTML 确认函数/元素是否已存在；勾选必须与文件一致，禁止记录未落地的完成项。
> **红线**：GMT+8 / wdeg / float→Decimal / 不改引擎内核 / 全 401 / 附加式不破坏 MVP / pytest 145 勿倒退 / terraform 禁 -auto-approve / 合规示例+免责。

## 已完成（本轮起点，勿重复）
- [x] 3 主标签页(实时浪报/浪报详情/其他) + 吸顶导航 + 回到顶部按钮
- [x] 实时浪报「目录/直播」子视图切换(默认目录)
- [x] hero 浪点名动态(#metaSpot 绑 data.spot) + 删写死日出/水温/月相
- [x] 目录排序下拉(推荐/综合评分↓/有直播优先/名称/地区)
- [x] 深色模式(body.dark CSS变量 + prefers-color-scheme + localStorage 'sf_theme')
- [x] 加载骨架屏 + 顶部 spinner(loadCatalog/loadLive/loadCams)
- [x] tab/子视图记忆(localStorage sf_tab_v1/sf_liveview_v1 + 脏值白名单回退)
- [x] 空态友好提示(目录/收藏搜索无结果「没有匹配」)
- [x] 布局微调：浪点名条(#spotbar)移到标签栏下 + 直播入口(#liveEntry)移到日期条下
- 基线：pytest **145** · Playwright E2E **47/47** + 0 JS 报错 · 26 截图 · docs/UI优化-01~03

## U 新一轮候选（每轮挑单个最高杠杆，据 grep 摸底后填具体项；避免重复上面已完成项）
- [x] U-a 目录卡片直接收藏 ★ ✅（cat-item 加 .cat-fav 星标，toggleCatFav 复用 FAV_KEY+stopPropagation 不触发加载，同步 renderSpotFav/下拉；node --check + E2E 49/49：点星切换+不跳转）
- [x] U-b 浪点地图标记着色 ✅（按**收藏状态**着色：金=已收藏/蓝=未收藏，L.divIcon(.sf-mk) 保留 .leaflet-marker-icon 不破坏原断言 + 图例。诚实备注：评分/离岸风着色因该图数据源=SAVED_SPOTS 无 per-spot 评分、按红线不伪造，故本轮按收藏高亮；如需评分着色须先给 SAVED_SPOTS 补 day0 score。node --check + E2E 51/51）
- [x] U-c 可达性 ✅（主标签 role=tablist/tab + aria-selected(showTab 同步)；全局 :focus-visible 键盘焦点态(浅/深色)；cat-fav 星标补 aria-label。node --check + E2E 53/53）
- [x] U-d 移动端触控优化 ✅（区域 chips(#catChips)/活动 chips(#newsChips) 改横向滚动 nowrap+overflow-x:auto+隐藏滚动条+chip 不压缩，窄屏不再多行堆叠。node --check + E2E 56/56：overflowX=auto）
- [x] U-e 分享当前浪点（深链）✅（spotbar 🔗分享按钮→shareSpot 复制 `#spot=lat,lon,name` 链接(clipboard,失败 prompt 兜底)；打开该链接经 _parseSpotHash 恢复 SPOT+进浪报详情；bootstrap 调整为 loadLive 末位执行避免 loadSpots 自动选点覆盖深链。node --check + E2E 55/55：深链恢复浪点名+进详情）
> loop 自行按价值/风险选取；每项：grep 确认→实现→node --check→E2E 断言→pytest 不倒退。

## V E2E 全绿
- [ ] V.1 扩 `web/e2e/new_features.mjs` 覆盖本轮新交互
- [ ] V.2 全绿 + 0 JS 报错（排除资源404/直播流）；pytest 不倒退

## W 截图
- [x] W.1 headless Chrome 截图 ✅ 刷新全部 + 新增 27-catalog-fav；关键新界面：12/27 目录★收藏、02 地图彩色标记+图例、26 浪报详情(浪点名条+🔗分享) → `docs/screenshots/`

## X 三份文档
- [x] X.1/X.2/X.3 ✅ docs/UI优化-01~03 追加「第二轮」小节（布局重定位 + U-a 目录收藏/U-b 地图着色/U-c 可达性/U-d 触控/U-e 深链：功能表+分步操作 H~M+代码地图增量+踩坑）

## Y 收尾
- [x] Y.1 README 更新（UI 矩阵 +第二轮 6 行 + E2E 47→56 + 截图 28 张）+ 最终复核 ✅ pytest **145** · E2E **56/56** + 0 JS 报错。第二轮 UI 目标达成（U-a~U-e + 布局 + V/W/X）。剩 Z 部署为可选高风险，停等人工确认。

## Z 部署（可选, 高风险, 停下等确认）
- [ ] Z.1 到部署步骤发一次 blocker 等人工确认，禁在 loop 内自动推生产
