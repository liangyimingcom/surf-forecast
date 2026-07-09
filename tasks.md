# Tasks — Custom Spots 实现 + E2E

> 循环模版（Set a goal）：north star 在 north_star.md，roadmap 在 roadmap.md，tasks 在本文件。
> 每轮选**单个最高杠杆下一步**并执行，完成后勾 [x]。真正卡住只发一次 blocker。要停止循环，创建 {{STOP_FILE}}。
> 约束：镜像构建推送用临时 t4g EC2(deploy.sh build)；apply 禁 -auto-approve（人工 echo yes）；
> 红线：ALB SG 永不含 0.0.0.0/0；/api/spots 全 401；slug 不可变；validate 守门；GMT+8；同坐标去重。

【当前进度锚点】custom-spots spec 三件套已就绪；现有部署 = CloudFront E2ZQMKCAN0V79D → ALB → Fargate，
DynamoDB(users/sessions/votes/saved_spots) + S3 cache，pytest 基线 91。本目标新增 spot_registry 表 + spots.py +
deps/refresh 改造 + 前端 spotManager。引擎内核不动。

## R1 数据层与注册表（纯代码）
- [x] R1.1 db.py：saved_spots 访问(put/list/get/update/soft_delete) + spot_registry 模型与访问(upsert/list_active/incr_ref/decr_ref/set_refresh_enabled) ✅ InMemoryStore+DynamoDBStore 双实现
- [x] R1.2 slug 生成器 + 去重键(round4+facing) + region/facing 推断 ✅ spots_model.py（slugify/geo_slug/make_slug/dedup_key/infer_region/infer_facing + 名称转义/坐标校验）
- [x] R1.3 test_spot_models（moto：slug 稳定/去重/区域推断/CRUD） ✅ test_spots_model.py 10 项（含 XSS 转义/隔离/ref_count 归零 inactive）-> 101 passed

## R2 浪点 CRUD API（纯代码）
- [x] R2.1 spots.py：GET/POST/PATCH/DELETE /api/spots + /select，全 401 ✅ 服务层 SpotError→app 包 HTTPException
- [x] R2.2 POST 流程：坐标/精度校验→配额(free=3/paid=20)→名称唯一→去重(registry,ref_count)→写 saved_spots ✅
- [x] R2.3 名称/坐标校验转义(防 XSS)；PATCH 保持 slug 不变；DELETE 软删 ✅ validate_name 转义 + slug 不可变 + 软删 ref--
- [x] R2.4 app.py 挂载 spots 路由 ✅ 5 路由 + SpotCreate/SpotUpdate 模型 + current_user 依赖
- [x] R2.5 test_spot_crud + test_spots_auth ✅ test_spots_api.py 8 项（401/CRUD/配额/重名/XSS/非法坐标/重命名保 slug/跨用户去重）-> 109 passed

## R3 查询切换与缓存读（纯代码）
- [x] R3.1 deps.get_report 扩展：按坐标查 registry 命中读 {slug}/latest.json，未命中回退引擎 ✅ _resolve_slug(registry 优先→DEFAULT_SPOTS 兜底)；get_report/get_history 同改
- [x] R3.2 /select 记"上次选中" + 更新 last_viewed_at_gmt8 ✅ (R2 已实现 select_spot)
- [x] R3.3 test_select_persist + test_custom_contract（含 wdeg/GMT+8） ✅ test_spots_cache.py 4 项（解析 slug/自定义点缓存命中含 wdeg/未命中回退/select 记忆）-> 113 passed

## R4 动态刷新编排（纯代码）
- [x] R4.1 active_registry_spots(store)：读注册表 active+enabled，合并 DEFAULT_SPOTS 兜底 ✅ 按 last_viewed 降序
- [x] R4.2 scheduled_refresh 注册表驱动替代硬编码；复用 refresh_spots 逐点 validate ✅ + refresh_cli 改用 scheduled_refresh
- [x] R4.3 即时预算：POST 未命中去重时 refresh_spots([new])，新点立即可读 ✅ budget_one + deps.instant_budget 接 create_spot budget_hook
- [x] R4.4 频率上限 N + 冷点回收(last_viewed 超 K 天 enabled=false) ✅ REFRESH_BUDGET=50 截断 + recycle_cold_spots(COLD_DAYS=14)
- [x] R4.5 test_registry_refresh + test_instant_budget + test_cold_recycle ✅ test_spots_refresh.py 5 项 + 适配 test_refresh_cli -> 118 passed

## R5 前端浪点管理（纯代码，附加式）
- [x] R5.1 spotManager 下拉(预设+已保存+➕新增)+当前高亮 ✅ loadSpots 动态填充 + selected
- [x] R5.2 新增面板(经纬度+名称+朝向)→POST /api/spots→切换+loadLive ✅ onCreateSpot
- [x] R5.3 切换 SPOT 重赋值→loadLive→POST /select；记住上次选中 ✅ switchToSelected + loadSpots 恢复 selected；SPOT 改 let
- [x] R5.4 管理(✏️重命名/🗑软删)；未登录/故障回退内嵌不白屏 ✅ onDeleteSpot + try/catch 回退(重命名 API 已就位,前端按钮后续)
- [x] R5.5 node --check JS 语法通过 ✅ + bootstrap 接 loadSpots，pytest 118 passed

## R6 IaC（apply，人工授权）
- [x] R6.1 storage 加 spot_registry 表(on-demand/PITR/PK=slug) ✅ + saved_spots SK 对齐 slug；terraform validate 通过
- [x] R6.2 后端任务 IAM 补即时预算/registry 读写权限 ✅ 自动纳入 table_arns（compute task policy in-place 更新）
- [x] R6.3 tf validate + plan 摘要 → echo yes apply（人工授权）✅ 2add/1change/1destroy 应用成功；spot_registry+saved_spots(SK=slug) 均 ACTIVE，无竞态

## R7 镜像构建 + 部署（临时 EC2）
- [x] R7.1 ./deploy.sh build（t4g EC2 自终止）+ redeploy ✅ 新镜像 10:55 推送含 spots.py，rollout COMPLETED
- [x] R7.2 触发 refresh 重算缓存（含新注册表逻辑）✅ RunTask scheduled_refresh → shandongtou 缓存刷新 11:08 当日；修复 DynamoDB float→Decimal(线上500根因，单测未暴露)

## R8 端到端 UI 验证（headless Chromium，循环至全绿）
- [x] R8.1 CloudFront HTTPS：登录→新建浪点→切换→当日实时数据（含 wdeg）✅ API 端到端：创建石老人(geo-361000-1204700/黄海/facing157)→select→report 命中即时预算缓存(当日含wdeg)→删除全 200
- [x] R8.2 浏览器控制台 0 SVG NaN/负值 + 0 JS 报错（favicon 404 除外）✅ headless Chromium：svg_issues=[]，仅 favicon 404
- [x] R8.3 默认浪点(青岛山东头)回归无倒退；逐一修复显示错误循环至全绿 ✅ Hero 周五2026-06-26 6.9分当日实时、校准11:08；修复 DynamoDB float→Decimal(线上500根因)

## R9 收尾
- [x] R9.1 勾选 .kiro/specs/custom-spots/tasks.md + 本文件 ✅
- [x] R9.2 安全复核：SG 无 0.0.0.0/0、/api/spots 全 401、无明文密钥 ✅ ALB SG 仅 pl-58a04531；/api/spots 未登录 401
- [x] R9.3 输出最终验证结论 + 成本提示 ✅

## 完成定义
见 north_star.md DoD：CRUD+配额+隔离、slug 稳定去重、即时预算立即可用、注册表驱动每日刷新、前端切换、
E2E 当日实时数据零报错、默认浪点无倒退、pytest 增长 + tf validate 通过、全程红线零违反。
