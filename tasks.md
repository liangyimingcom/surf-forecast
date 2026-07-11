# Tasks — 石老人 × surf-forecast 形态C整合

> 循环模版：north star 在 north_star.md，roadmap 在 roadmap.md，tasks 在本文件。
> 每轮选**单个最高杠杆下一步**执行，完成后勾 [x] 并更新。真正卡住只发一次 blocker。
> 停止：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
> **每轮动手前先用 codelens 摸底/算影响面/守红线**（skill surf-forecast-codelens-dev）。
> **纪律（防上次并发冲突复发）**：单一驱动器；改前先 grep 实际文件确认函数是否已存在；勾选必须与实际文件一致，禁止记录未落地的完成项。
> 红线：GMT+8 / wdeg / float→Decimal / 不改引擎内核 / 401策略 / 合规(直播门禁+免责) / 附加式不破坏MVP / pytest 118 勿倒退 / terraform 禁 -auto-approve。

【方案】docs/石老人整合方案-formC.md。【已有基础】前端已含收藏/搜索/地图/社区示例(R1/R2)、排水量/周边/直播占位；后端 spot_registry + get_report(引擎自算) + /api/spots(401)。形态C=把占位直播升级为真实58浪点+live_src，预报统一引擎。

## P0 摸底+基线
- [x] P0.1 pytest **118 passed** 基线确认 ✅
- [x] P0.2 codelens 摸底 + 改动地图 ✅：`_to_decimal`(db.py:13) 上游4写路径 add_vote/put_spot/put_user/**upsert_registry**(db.py:226)——P1 导入复用 put_spot/upsert_registry(已过Decimal)，**无需新写函数**；`/api/spots` 全套路由已存在(GET/POST/PATCH/DELETE/select @app.py:139-175)，P2 /api/cams 照此401；石老人上游 getCategories 200 可达→P1 导入可行。

## P1 浪点导入(58+)
- [x] P1.1 tools/import_shilaoren_spots.py（getCamera/all + getNewForecast/{cId} 拉 58 浪点 name/city/坐标/live_src/post_url，标准库urllib，温和限速）✅ 产出 reference/data/shilaoren_spots.json
- [x] P1.2 facing 按区域粗估(REGION_FACING, 石老人=157 与 domain-knowledge 一致)+标 facing_calibrated:false 待校准 ✅ **58/58 含坐标 + live_src**
- [x] P1.3 导入注册表 ✅（src/web/seed.py: build_registry_rows(纯函数,快照→注册表行含live_src/facing_calibrated) + seed_store/seed_from_file；get_store 内存路径接 SF_SEED_SPOTS env 一次性灌入；tools/load_registry.py 生产灌 DynamoDB(SF_STORE=dynamo,走_to_decimal)。验证：58 浪点全入注册表(active+refresh_enabled=58)，sl74石老人 facing157/live_src保留/source=shilaoren；pytest 118 未倒退。）

## P2 直播 /api/cams + 前端弹层
- [x] P2.1 后端 /api/cams 只读目录 ✅（app.py: current_user 门禁 401，从 list_active_registry 返回含 live_src 的浪点，lat/lon 兼容 Decimal/float；验证 未登录401 / 登录42直播源）
- [x] P2.2 前端 hls.js 直播弹层 ✅（head 加 hls.js@1.5.13 CDN；重写 renderLivecams→loadCams 拉 /api/cams；openCam：Safari 原生HLS / 其他 Hls.js(lowLatency+liveDurationInfinity) 播 #camVideo；#camModal 弹层+closeCam+Esc；bootstrap 登录后 loadCams。E2E：42卡片+弹层开关+0 JS报错。视频直连上游不经后端。）

## P3 列表升级(多浪点+地区筛选+评分)
- [x] P3.1 列表扩 58+ + 地区筛选 Tab ✅（后端 /api/catalog(401,58浪点含region_cn/has_live)；导入脚本增强按 getCategories+getCamera/{ctId} 打官方区域(广东22/海南15/福建5/山东3/广西3/浙江2/国外7/其他1)；前端 #catalog section: 区域chips+搜索+58列表+点击 pickCatalogSpot→设SPOT→loadLive引擎自算+LIVE标+朝向待校准标注。E2E:58项/9chips/海南15/点击加载/0报错;pytest118。）
- [x] P3.2 每点综合评分(缓存回批,避58×实时) ✅（后端 /api/catalog/scores：有缓存桶则批量读 {slug}/latest.json 的 day0 score，本地无桶返回 cached=false；前端目录评分徽标(色阶 绿≥7/黄≥5/橙≥3/红)+点击已看浪点从 DAYS[0].score 回填(已核实 render_json day0 含 score=8.25)。E2E: scores端点200 cached=false、58目录、0报错；pytest118。注：58点地图着色未做(目录用列表评分徽标呈现;saved-spot 地图不变)——如需可后续补。）

## P4 详情融合
- [x] P4.1 详情融合 ✅（浪报主体本就是 surf-forecast 引擎渲染=评分/离岸风质/双周期Tm-Tp/物理叙事/最佳窗口/板型，已具备；本轮新增**直播入口联动**：hero 后 #liveEntry 横幅，当前浪点有直播(CAMS含slug)时显示→openCurrentCam 打开 #camModal；updateLiveEntry 在 pickCatalogSpot 触发。E2E:有LIVE项→加载→横幅显示→弹层打开、0报错;pytest118。周边推荐 R2.7 已在页内。）

## P5 昨日回看多浪点
- [x] P5.1 昨日回看多浪点 ✅（loadLive 已对当前 SPOT 拉 /api/report/history，切目录浪点即更新；引擎历史模式对任意坐标可用。E2E 验证：海南三亚 history 端点返回 date=2026-07-10(昨日,GMT+8)/score7.6/含predict，切浪点后 #verify 昨日回看渲染302字、0报错。历史区与预报区日期互斥红线由引擎保证。）

## P6 测试(部署前)
- [x] P6.1 pytest 新增契约测试 ✅ tests/test_formc.py 8项(seed纯函数shape/缺坐标跳过/catalog+cams+scores 401/catalog列举/cams仅含live_src/scores无缓存)；**全量 118→126 passed**（基线增长零倒退）
- [x] P6.2 Playwright 汇总 E2E ✅ **30/30 全绿 + 0 JS报错**（web/e2e/new_features.mjs 扩形态C：58目录/区域chips/直播卡片(hls)/详情直播入口横幅/直播弹层；修过时 R2.8 占位断言→真实cams；直播流HLS错误纳入排除）

## P7 部署+部署后E2E+截图+文档
- [x] P7.1 部署门禁 ✅ pytest 126 passed
- [x] P7.2 灌生产 DynamoDB(58浪点) + frontend 部署 ✅ tools/load_registry.py(SF_STORE=dynamo,AWS_REGION修正)灌58浪点; t4g构建ARM64镜像推ECR(21:05) + ECS强制滚动(部署21:07 COMPLETED 1/1)
- [x] P7.3 线上冒烟 ✅ CloudFront 首页200/health/未登录保护；ALB直连超时=预期(SG仅CloudFront前缀)
- [x] P7.4 部署后线上 E2E ✅ CloudFront: 注册/登录200 · /api/catalog=58(8区域全含) · /api/cams=42 · 三亚取报3天含wdeg+calibratedAt 2026-07-11 21:11 GMT+8 · 前端含catalog/cams/livecams
- [x] P7.5 headless Chrome 截图 ✅ 17张 → docs/screenshots/*.png（含形态C新界面：12-catalog全国目录/13-catalog-hainan区域筛选/14-livecams直播列表/15-live-entry详情直播入口/16-live-modal直播弹层）
- [x] P7.6 3 文档 ✅ docs/形态C-01-功能介绍.md / 形态C-02-交互操作指南.md / 形态C-03-教学教程.md（引用截图，含架构/代码地图/扩展模式/踩坑/红线合规/测试产物）
- [ ] P7.7 若需基建变更 → 停下发 blocker 等人工审批，禁 -auto-approve
- [ ] P7.8 README/功能矩阵更新 + 验收结论

## 完成定义
见 north_star.md DoD：58+浪点(引擎自算预报)+真实直播+列表/详情融合评分离岸风双周期+昨日回看 + pytest增长 + 部署前后E2E全绿 + 自动部署上线 + 截图 + 3文档，红线与合规零违反。
