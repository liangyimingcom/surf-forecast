# North Star — Custom Spots 浪点自定义与管理（实现 + E2E）

## 业务目标
落地 `.kiro/specs/custom-spots/` 全部功能：会员能**用经纬度/地图自定义命名浪点 → 多点管理(CRUD) → 一键切换 → 自动纳入每日定时抓取与缓存刷新**，并端到端验证全部新增功能 + 现有 UI 数据/报表显示正常（当日 GMT+8 实时数据、零控制台报错）。

## 目标架构（在现有之上增量）
```
会员浏览器 ─HTTPS─> CloudFront(E2ZQMKCAN0V79D) ─> ALB ─> Fargate(FastAPI 前端内置)
                                                          │
  新增: spots.py(CRUD) ──> DynamoDB saved_spots + spot_registry(新表)
  改造: deps.get_report 按坐标命中缓存; refresh 注册表驱动(替代硬编码 DEFAULT_SPOTS)
  EventBridge(GMT+8 02:00/14:00) ─> refresh active 浪点 ─> S3 缓存
```

## 成功判据（DoD）
1. **CRUD**：`/api/spots` 增/查/改/删全 401 保护、用户隔离、free=3/paid=20 配额；名称/坐标校验转义。
2. **slug 稳定**：重命名不漂移缓存键；同坐标全局去重共享 slug 与缓存。
3. **即时预算**：新建浪点触发一次预算，立即可读（缓存命中）；下一调度窗口起纳入定时刷新。
4. **动态刷新**：每日刷新从硬编码 `DEFAULT_SPOTS` 升级为 `spot_registry` 注册表驱动；逐点 validate 守门、失败保留上一版。
5. **前端**：spotManager 下拉/新增面板/切换/管理（附加式不破坏现有 MVP）；切换即时 loadLive。
6. **E2E**：CloudFront HTTPS 全链路——新建浪点→切换→当日实时数据；浏览器 **0 SVG NaN/负值、0 JS 报错**（favicon 404 除外）；默认浪点回归无倒退。
7. `pytest` 基线从 91 增长（新增 custom-spots 测试全绿）；`terraform validate` 通过。

## 安全不变量（红线）
- ALB SG 永不含 0.0.0.0/0（保持仅 CloudFront 前缀列表 pl-58a04531）。
- 鉴权全后端、前端零信任；`/api/spots` 全 401 保护；名称转义防 XSS。
- 数据诚实：validate 守门、GMT+8 日界、历史预报互斥、离岸判定按该点 spot_facing_deg、未标定海域标注"按黄海近似"。
- slug 不可变作缓存键；读写解耦；同坐标去重控 Open-Meteo 调用量。

## 约束
- 区域 ap-northeast-1，profile oversea1，account 153705321444。
- **镜像编译/推送用临时 ARM64 t4g EC2**（deploy.sh build，自终止）加速。
- `terraform apply` 禁 `-auto-approve`（YOLO 红线）；本目标人工授权用 `echo yes | terraform apply`。
- 新增 `spot_registry` 表注意 DynamoDB 同名表 replace 竞态（教训）：用 create_before_destroy 或确认删除完成。
- 不改动确定性引擎内核（physics/scoring/validate）；新功能在 web 层 + IaC。
