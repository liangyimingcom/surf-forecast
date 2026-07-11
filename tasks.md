# Tasks — surf-forecast 移植石老人复刻功能

> 循环模版：north star 在 north_star.md，roadmap 在 roadmap.md，tasks 在本文件。
> 每轮选**单个最高杠杆下一步**执行，完成后勾 [x] 并更新。真正卡住只发一次 blocker。
> 停止循环：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
> **每轮动手前先用 codelens 摸底/算影响面/守红线**（skill surf-forecast-codelens-dev）。
> 红线：GMT+8 / DATA CONTRACT 含 wdeg / DynamoDB float→Decimal / 不改引擎内核 / /api/spots 全401 / 不引外部第三方API / 附加式不破坏现有MVP。

【锚点】surf-forecast 前端=单 HTML `web/浪报MVP.html`；后端 FastAPI(src/web)；引擎 src/surf_forecast；pytest 基线 118；custom-spots 已完成，浪点含 lat/lon/facing。社区/公告/关于用**示例 sample**（无外部源）。

## R0 基线+摸底
- [x] R0.1 pytest -q **118 全绿**基线确认 ✅（勿倒退）
- [x] R0.2 改动地图已建立 ✅
  - 前端=单 HTML `web/浪报MVP.html`(1097行)。**Leaflet 已加载**(CDN @216-217)→地图/收藏可直接用，无新依赖。
  - `#miniMap`(@565-577) 已有 Leaflet 建图模式(L.map/tileLayer/marker,创建浪点坐标点选)——现成参考。
  - `SAVED_SPOTS`(@561,来自 /api/spots) + `loadSpots()`；`#spotSel` 下拉切换浪点(含 lat/lon)。
  - `#extras`(@966 innerHTML, expert模式) 挂载点；DATA CONTRACT DAYS/HISTORY @313；loadLive fetch /api/report。
  - 接入点：R1收藏/搜索→增强 spotSel 区或新面板(数据 SAVED_SPOTS)；R1.3地图→复用 Leaflet 标 SAVED_SPOTS；R2社区→新 section + 示例常量/弹层(复用样式)。
- [x] R0.3 CodeLens 摸底 R1 浪点增强 ✅（本轮，skill surf-forecast-codelens-dev；CodeLens rev fc9e1f697bf24e3687b0）
  - **前端接入点**（`web/浪报MVP.html`，1097 行；行号以本轮读取为准）：
    - Leaflet 资源 @229-230（leaflet@1.9.4 css+js，unpkg）；`API_BASE` @490 → 地图/收藏无需新依赖。
    - **浪点数据源** `SAVED_SPOTS` @537（来自 GET `/api/spots`）；由 `loadSpots()` @620-648 拉取并填充 `#spotSel`。
    - **浪点列表渲染**：`loadSpots()` 构建 `#spotSel` 选项(含 dataset.lat/lon/name/days) → 末尾调 `reorderSpotOptions()` @645(收藏置顶) + `renderSpotFav()` @646(收藏面板 `#spotFav`/`#spotFavList` @295-297)。
    - **浪报加载函数** `loadLive()` @493 → `fetch ${API_BASE}/api/report?lat&lon&spot&days` @496；历史 `/api/report/history` @515；全局 `SPOT` @491；切换应用经 `switchToSelected()`/`onSpotChange()` @590。R1.3 地图点击标记即复用此链路（设 `SPOT` 后 `loadLive()`）。
    - **R1.3 地图现成参考**：`initMiniMap()` @543-560 已有 `L.map`/`L.tileLayer(OSM)`/`marker` + click→回填坐标（新增浪点用）；R1.3 独立地图可复刻此模式按 `SAVED_SPOTS` 打点。
    - **R1.1 收藏已脚手架化**（本轮发现，附加式）：`FAV_KEY='sf_fav_spots_v1'` @662、`getFavs/isFav/toggleFav/renderSpotFav/reorderSpotOptions` @659+、CSS @215-227、section `#spotFav` @294-297 → **R1.1(任务3) 主要为验证/补全，非从零**。
    - **勿触碰**：`render()` 管理的 `#strip/#hero/#cards/#extras`（`#extras` @966 expert 挂载点）；`DAYS` @335 / `HISTORY` @468（每日含 `wdeg` 数组，如 @343）。
  - **爆炸半径**（CodeLens get_impact `spots_list`）：radius=2，downstream=3（`db.py` DynamoDBStore/InMemoryStore/get_store），upstream=0。R1 全为**前端附加式**改动 → 后端爆炸半径=0（不改任何 handler/db/引擎）。
  - **红线守护**（CodeLens）：
    - `/api/spots` 全 **401**：find_route 确认 GET `spots_list`@app.py:139 = `Depends(deps.current_user)`；POST/PATCH/DELETE/{slug}/select 同族均受保护 ✅。R1 不新增后端接口。
    - **DATA CONTRACT 含 wdeg**：由 `test_render_json_has_wdeg_redline`/`test_golden_cli_json_has_wdeg`/`test_report_returns_wdeg_when_authed` 守护；前端 `DAYS`/`HISTORY` 均含 wdeg 数组 → R1 收藏/搜索/地图**不得裁剪或改写** wdeg 及数字型图表字段。
    - **GMT+8**：`#metaCalib` @260「校准 … GMT+8」；日界不变。**不改引擎内核**（physics/scoring/validate）。
  - **结论**：R1.1/1.2/1.3 均可作为纯前端附加改动落地，接入 `SAVED_SPOTS` + `loadLive()`/`loadSpots()`，复用 Leaflet；后端零改动、红线零风险。任务3可直接进入 R1.1 验证/补全。

## R1 真实浪点增强
- [x] R1.1 浪点收藏(localStorage) + 卡片★星标 + 收藏置顶 ✅（任务3：FAV_KEY='sf_fav_spots_v1' 持久化；getFavs/isFav/toggleFav；sortByFav 稳定置顶；renderSpotFav 每卡★/☆切换+点击切换浪点；reorderSpotOptions 下拉置顶；_favEscape 防注入；CSS @215-227；section #spotFav @294-297。附加式：不触碰 render()/#strip/#hero/#cards/#extras，不改 /api/spots，红线零违反。）
- [x] R1.2 浪点搜索(名称) + 排序(收藏优先/名称A-Z/纬度北→南) ✅（真实实现：#spotSearch 搜索框 oninput→renderSpotFav 名称过滤；#spotSort 排序下拉(fav/name/lat)；#spotFavEmpty 空态；CSS .spotfav-ctl/.spotfav-search/.spotfav-sort。node --check 通过。⚠️ 注：早前并发 loop 曾误记为 onSpotSearch/_applySpotView，实际以本条为准。）
- [x] R1.3 🗺️ Leaflet+OSM 浪点地图 ✅（真实实现：复用已加载 leaflet@1.9.4；收藏面板加「🗺️ 地图」开关 toggleSpotsMap→独立 #spotsMap 容器(与创建浪点 #miniMap 分离)；renderSpotsMap 按真实 SAVED_SPOTS lat/lon 打点(缺坐标跳过不伪造)+fitBounds；popup「查看浪报」→_spotsMapSelect→switchToSelected→loadLive；invalidateSize 修隐藏转显示尺寸。node --check 通过。）
- [ ] R1 阶段回归 —— 待真实 Playwright E2E（收藏/搜索/排序/地图 + 0 JS 报错）；**pytest 118 未倒退已确认** ✅（任务11：`.venv/bin/python -m pytest -q` → 118 collected / 118 passed / 0 failed，exit 0，用时~1.6s；仅 1 条 Starlette httpx 弃用告警，非失败）

## R2 社区/工具（示例 sample）
- [x] R2.1 公告详情(示例富文本弹层, 标注"示例数据") ✅（任务6：ANNOUNCEMENTS 3条示例(更新/安全/维护)；renderAnnouncements 渲染 #anncList 卡片列表(图标+类型chip+日期GMT+8+两行摘要)；点击 openAnnc 打开富文本弹层 #anncModal(h3/h4/p/ul/strong/note，顶部「示例数据」badge + 底部免责)；closeAnnc/背景点击/Esc 关闭；_favEscape 转义动态字段，正文为受控字面量；CSS 附加于 </style> 前；section #annc 置于 #spotFav 后；弹层置于 </body> 前(fixed 独立层)。附加式：不触碰 render()/#strip/#hero/#cards，无外部内容 API、无登录/支付；JS node --check 通过；红线零违反。）
- [x] R2.2 意见反馈表单(前端校验+提交示例反馈, 不写真实DB或需401) ✅（真实实现：#feedback section 置于 #annc 后；7 类枚举(系统功能异常/浪点预报不准/直播视频异常/新增浪点/拼车/拼房/其他)+内容 textarea(maxlength500)+提交按钮；submitFeedback 前端校验(缺类型/内容报错)→成功占位提示，不发网络请求(无上游)；「示例·演示不写库」badge；CSS .fb-*；node --check 通过。附加式不触碰 render()/后端，红线零违反。）
- [x] R2.3 关于·商务合作(示例内容, 脱敏) ✅（真实实现：#about section 置于 #feedback 后；关于我们/商务合作/联系方式三段示例脱敏内容(示例占位邮箱 hello@surf-forecast.example + GMT+8 标注)；「示例数据」badge；纯静态HTML+CSS(.about-*)无JS无外部API；JS 未受影响 node --check 通过。）
- [x] R2.4 活动墙(示例列表+类型筛选+详情) ✅（真实实现：#newswall section；SAMPLE_NEWS 5 条示例(活动/攻略/浪报/装备周边)含类型/标题/地点/日期GMT+8/富文本；NEWS_TYPES 5 类 chips→filterNews 过滤；renderNews 卡片列表(类型tag/标题/meta)；openNews→#newsModal 富文本详情(顶部示例badge)+closeNews/背景/Esc 关闭；复用 annc-modal 样式+新增 .news-*/.annc-badge CSS；load 时 initNews。node --check 通过。不引外部API、不做登录/发布/二手。）
- [x] R2.5 冲浪搭子/拼车(示例列表, 脱敏) ✅（真实实现：#carpool section；SAMPLE_CARPOOL 4 条示例(出发→到达/日期GMT+8/余座/费用/备注/发布者/微信)；renderCarpool 只读卡片；微信脱敏 186****0095(核验0个未脱敏11位手机号)；CSS .cp-note；load 时 initCarpool。不做登录/发布/编辑(合规红线)。node --check 通过。）
- [x] R2.6 【模块F】排水量计算器 ✅（真实实现：#volume section；体重input+6档水平select+计算按钮；calcVolume=体重×水平系数；系数标定精确命中(70kg 中级 0.443→31.0L、初学者 0.70→49.0L)；CSS .vol-*；纯前端工具无上游/无网络。node --check 通过。）
- [x] R2.7 【模块D】周边推荐 ✅（真实实现：#nearby section；SAMPLE_ADS 三类(冲浪店/俱乐部·餐厅酒吧·酒店民宿)各2条示例商户(name+desc)；renderNearby 分组卡片；CSS .nb-*；load 时 initNearby；「示例数据」badge；无外部API。node --check 通过。）
- [x] R2.8 【模块A】在线视频直播占位 ✅（真实实现：#livecams section；SAMPLE_CAMS 4 个浪点摄像头占位卡(渐变缩略图+● 演示标+▶)；renderLivecams 网格；点击 alert 明确「无真实直播流·功能移植占位」；「示例·演示占位(无真实流)」badge；CSS .cam-*；load 时 initLivecams。node --check 通过。）

## R3 后端示例接口(视实现)
- [x] R3.1 决策：**前端内置示例常量**（SAMPLE_NEWS/SAMPLE_CARPOOL/ANNOUNCEMENTS/SAMPLE_ADS/SAMPLE_CAMS + 关于静态内容）✅ —— 不新增后端接口(避免动后端/引擎、零 401 风险)，社区/公告/周边/直播全为前端示例，明确标注「示例数据」。

## R4 测试
- [x] R4.1 pytest 复核 **118 passed / 0 failed**（exit 0）✅ —— R1/R2 均为纯前端附加改动，不产生 pytest 用例；红线守护测试全绿(/api/spots 401、float→Decimal、wdeg+GMT+8)；基线零倒退。前端路径覆盖由 R4.2 E2E 承担。
- [x] R4.2 Playwright E2E **25/25 全绿 + 0 JS 报错** ✅（`web/e2e/new_features.mjs`；起后端内存store→headless Chromium；覆盖 R2.1-2.8 全部示例功能(公告/反馈校验/关于/活动墙chips+详情弹层+Esc+筛选/拼车脱敏/排水量标定31.0L/周边/直播占位) + R1 建浪点→收藏卡渲染/★切换/搜索过滤/排序/地图真实标记≥2。资源404已排除。）

## R5 截图
- [x] R5.1 headless Chrome 截图 **12 张** → docs/screenshots/*.png ✅（web/e2e/shots.mjs 移动端视图430宽；00-home-full/01-spotfav/02-spotsmap/03-annc/04-feedback/05-about/06-newswall/07-news-detail/08-carpool/09-volume/10-nearby/11-livecams）

## R6 文档
- [x] R6.1 功能介绍.md ✅ docs/移植功能-01-功能介绍.md（11功能 what/why + 截图引用 + 合规）
- [x] R6.2 交互操作指南.md ✅ docs/移植功能-02-交互操作指南.md（A-K 分步 + 预期 + 常见问题）
- [x] R6.3 教学教程.md ✅ docs/移植功能-03-教学教程.md（上手/架构/代码地图/新增模式/踩坑/红线/测试产物）

## R7 收尾
- [x] R7.1 README 功能矩阵更新 ✅（新增「石老人复刻功能移植」11项矩阵 + 测试/截图/文档/合规）
- [x] R7.2 最终复核 ✅ pytest **118 passed** + Playwright E2E **25/25 全绿 + 0 JS 报错**；后端/引擎零改动、/api/spots 全401、DATA CONTRACT wdeg 未受影响、GMT+8。验收结论：11 功能全落地(真实浪点3项+示例8项)，红线零违反。

## R8 自动部署运行（AWS oversea1 / 153705321444 / ap-northeast-1）
> 前置门禁：R4 E2E 全绿 + pytest 从 118 增长 且全绿，方可部署。纯 web 层变更→**不跑 terraform apply**。
- [ ] R8.1 部署前门禁：`AWS_PROFILE=oversea1 ./deploy.sh test`（pytest 通过才继续）
- [ ] R8.2 重建镜像+滚动部署：`AWS_PROFILE=oversea1 ./deploy.sh frontend`（临时 t4g EC2 云端构建 ARM64 镜像推 ECR → 强制 ECS 滚动部署；前端已内置镜像）
- [ ] R8.3 线上冒烟：`AWS_PROFILE=oversea1 ./deploy.sh smoke`（ALB/CloudFront health 200 + 未登录 /api/report 返回 401）
- [ ] R8.4 CloudFront 端到端复核：health 200 + 前端直供(含新功能标记) + 注册→登录→取报(真实数据含 wdeg + GMT+8 当日) + 新界面(地图/收藏/搜索/社区示例) 线上可见
- [ ] R8.5 若发现需基建变更(新表/新资源/SG)：**停止并发 blocker 等人工审批**，禁 `terraform apply -auto-approve` 自动跑（红线）

## 完成定义
见 north_star.md DoD：11 功能落地(8 点名 + A直播占位/D周边推荐/F排水量三示例移植, 社区/示例标注) + 真实浪点地图/收藏/搜索 + pytest增长 + E2E全绿 + 截图 + 3文档，红线零违反。
