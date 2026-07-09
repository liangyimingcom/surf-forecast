# Roadmap — Custom Spots 实现 + E2E

> 依赖顺序；纯代码阶段无 AWS 副作用，apply/EC2 构建为人工授权点。对齐 `.kiro/specs/custom-spots/tasks.md`。

## R1 — 数据层与注册表（纯代码）
- db.py 补 saved_spots 访问 + 新增 spot_registry 模型/访问（upsert/list_active/ref 计数/set_enabled）。
- slug 生成器（slugify 冲突退化 geo-{lat4}-{lon4}）+ 去重键 + region/facing 推断。
- moto 离线测试。验证：pytest 增长。

## R2 — 浪点 CRUD API（纯代码）
- spots.py：GET/POST/PATCH/DELETE /api/spots + /select，全 401；坐标/名称校验转义；配额；软删；去重接 registry。
- app.py 挂载路由。验证：test_spot_crud + test_spots_auth。

## R3 — 查询切换与缓存读（纯代码）
- deps.get_report 扩展：按坐标查 registry 命中读缓存，未命中回退引擎；/select 记 last_viewed。
- 验证：test_select_persist + test_custom_contract（含 wdeg/GMT+8）。

## R4 — 动态刷新编排（纯代码）
- active_registry_spots 替代硬编码 DEFAULT_SPOTS；即时预算；频率上限 N；冷点回收。
- 验证：test_registry_refresh + test_instant_budget + test_cold_recycle。

## R5 — 前端浪点管理（纯代码，附加式）
- spotManager 下拉/新增面板/切换/管理；未登录/故障回退内嵌不白屏。
- 验证：node --check JS 语法。

## R6 — IaC（apply，人工授权）
- storage 加 spot_registry 表（on-demand/PITR/PK=slug，注意 replace 竞态）+ 后端 IAM 补即时预算权限。
- tf validate → plan 摘要 → echo yes apply。

## R7 — 镜像构建 + 部署（临时 EC2）
- ./deploy.sh build（t4g EC2 自终止）+ redeploy；refresh 重算缓存。

## R8 — 端到端 UI 验证（headless Chromium，循环至全绿）
- CloudFront HTTPS：新建浪点→切换→当日实时数据；控制台 0 SVG NaN/0 JS 报错；默认浪点回归无倒退。
- 逐一修复，循环直至全绿。

## R9 — 收尾
- 勾选 spec tasks.md + 根 tasks.md；安全复核（SG 无 0.0.0.0/0、/api/spots 全 401）；成本提示。

## 依赖
```
R1 ─> R2 ─> R3 ─┐
       └─> R4 ──┼─> R6(apply) ─> R7(镜像) ─> R8(E2E) ─> R9
R5(前端,可与R3/R4并行) ───────────┘
```
