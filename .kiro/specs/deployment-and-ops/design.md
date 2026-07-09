# Design — Deployment & Ops（生产部署与每日自动更新，v2）

> 回应 requirements.md。区域 ap-northeast-1。配套总览见 [docs/production-gap-analysis.md](../../../docs/production-gap-analysis.md)。

## 1. 总体架构

```
                          用户（浏览器，国内/青岛）
                                   │ HTTPS
                          Route53 + ACM(TLS)
                                   │
                            CloudFront (CDN/WAF)
                     ┌─────────────┴─────────────┐
                  /  │                            │ /api/*
        S3 静态站点桶(前端 SPA)              ALB → ECS Fargate (FastAPI 后端)
                                                  │  鉴权/查询/会员/缓存读
                                   ┌──────────────┼───────────────┐
                          RDS Postgres      S3/DynamoDB        Secrets Manager
                       (users/members/votes) (预算JSON缓存)     (DB/API key)

   ─── 每日自动更新链路（与在线请求读写解耦）─────────────────────────────
   EventBridge Scheduler (cron, GMT+8, 1-2次/日)
            │
            ▼
   ECS Scheduled Task / Lambda  ──Open-Meteo ECMWF WAM/IFS──>  引擎 build_context(+past_days=1)
            │                                                    → 评分 → validate
            ▼
   写预算 JSON → S3/DynamoDB（今天起预报 + 昨日历史，键=spot+date）
            │
            ▼  CloudFront 失效/短 TTL → 在线请求命中（<500ms）
   ───────────────────────────────────────────────────────────────────
                    CloudWatch Logs + Alarms + Dashboard（贯穿全栈）
```

**核心设计：读写解耦**。每日调度链路"写"（预算并落缓存），在线请求"读"（只命中缓存，不打 Open-Meteo）。好处：① Open-Meteo 调用量 = 浪点数 × 每日次数（而非每次查询），省钱且规避商用许可风险；② 在线延迟稳定 <500ms。

## 2. 部署形态选型（两套，按规模切换）

| | 方案 A 精益 Serverless（起步） | 方案 B 标准容器栈（演进） |
|---|---|---|
| 在线计算 | Lambda + API Gateway(HTTP API) | ECS Fargate + ALB |
| DB | DynamoDB on-demand | RDS Postgres db.t4g.micro |
| 缓存 | S3 预算 JSON + CloudFront | 同左（无需 Redis） |
| 刷新计算 | Lambda | ECS Scheduled Task |
| 估算月成本 | ~$10–25 | ~$50–75 |
| 适用 | 低流量、快速上线 | 用户增长、复杂查询、与 kiro-gateway 运维一致 |

> 默认 **方案 A 起步**（每日预算 + S3 缓存天然契合）；上量后迁 **方案 B**（复用 build-on-ec2 ARM64 构建经验）。引擎与后端代码两套通用，仅托管层不同。

## 3. 每日自动更新链路（本 spec 核心）

### 触发
- **EventBridge Scheduler**，`cron`，时区直接设 `Asia/Shanghai`（Scheduler 支持时区）；建议 02:00 与 14:00 GMT+8 两次（覆盖 ECMWF 00Z/12Z 同化后窗口）。

### 刷新作业（`refresh_job`）
```
for spot in 上架浪点列表:
    报告 = engine.build_context(lat, lon, days, spot, config)        # 今天起预报
    历史 = engine.build_context(..., past_days=1)                    # 昨日回算
    report_json = render_json(报告)   # 含 wdeg/tp2/tideEvents
    history_json = render_json(历史)  # 含 predict{}
    validate(报告, 历史)              # GMT+8 边界 + 历史/预报互斥 + 口径一致
    if validate 通过:
        put_cache(key=f"{spot}/{today}", report_json)
        put_cache(key=f"{spot}/history/{yesterday}", history_json)
        invalidate_cloudfront(paths)
    else:
        log + alarm; 保留上一版（不覆盖）        # R5.4
```
- **GMT+8 边界**：作业内部统一以 `Asia/Shanghai` 算 today/yesterday，预报区(今天起) 与历史区(昨天) 不重叠（复用引擎 `verify_history_forecast_disjoint`）。
- **失败降级**：Open-Meteo 故障或 validate 失败 → 不覆盖缓存 → 在线继续服务上一日结果并标注时效（web R4.3）。

### 缓存读（在线）
- 后端 `query.py` / `history.py` 先读缓存键；命中直接返回（<500ms）。未命中（理论上仅新浪点）回退即时计算并写缓存。

## 4. 存储

| 数据 | 存储 | 说明 |
|------|------|------|
| users/members/saved_spots/accuracy_votes | RDS Postgres（B）或 DynamoDB（A） | 关系/键值二选一；feedback votes 含 `created_at_gmt8` |
| 预算浪报 JSON（预报+历史） | S3 桶 `surf-forecast-cache-<acct>-apne1`（+CloudFront）或 DynamoDB | 键 `spot/date`、`spot/history/date` |
| 前端静态资源 | S3 桶 `surf-forecast-web-<acct>-apne1`（+CloudFront OAC） | |
| 密钥（DB/API key） | Secrets Manager | 容器 `valueFrom` 注入 |
| 容器镜像 | ECR `surf-forecast` | tag 含 commit |

## 5. 网络

- VPC：公有子网(ALB/NAT) + 私有子网(Fargate/RDS)。
- Fargate/RDS 在私有子网；出网经 NAT（或对 Open-Meteo 公网走 NAT；AWS 服务走 VPC Endpoint 省 NAT 流量）。
- 安全组最小化：ALB←CloudFront/公网 443；Fargate←ALB；RDS←Fargate；刷新任务←出网。

## 6. 可观测性

- **Logs**：后端 `/ecs/surf-forecast`、刷新 `/surf-forecast/refresh`。
- **Alarms**：刷新失败（自定义 metric 或 Logs metric filter）、ALB 5xx 率、UnhealthyHostCount、RDS 连接/CPU。
- **Dashboard** `surf-forecast-overview`：请求量、p50/p99 延迟、错误率、每日刷新最近状态、缓存命中率。

## 7. 安全

- 限流：HTTP API throttling 或 WAF rate-based rule（per-IP）。
- IAM：刷新任务角色仅 `s3:PutObject`(cache 桶)+`cloudfront:CreateInvalidation`+读 Secrets；后端角色仅读 cache+读写 DB+读 Secrets。
- WAF（可选，套 CloudFront）：rate limit + AWS 托管规则集。
- 无明文密钥（教训：kiro-gateway ADMIN_API_KEY 明文 env 的反例 → 一律 Secrets Manager valueFrom）。

## 8. IaC 与 CI/CD

- **Terraform**（与现有 kiro-gateway 经验一致；AgentCore 之外纯 AWS 资源用 aws provider）。模块：`network / ecr / data(rds|dynamo,s3) / compute(fargate|lambda) / cdn / scheduler / observability / security`。
- 环境参数化：`dev/staging/prod` tfvars（账号/区域/域名/规格）。
- 构建：偏好**云端 ARM64 t4g EC2 构建**镜像（耗时编译卸载到云端），推 ECR。
- 流水线：本地 `deploy.sh`（test→build→push→tf apply）起步；后续可上 CodePipeline。部署前跑 `pytest`（含 validate 测试），失败阻断。

## 9. 测试与验证

| 测试/验证 | D |
|-----------|---|
| `tf plan` 无漂移、资源齐全 | D1 |
| 部署后 `/api/health` 200、ALB 健康 | D2 |
| 自定义域 HTTPS 可达、证书有效 | D3 |
| DB 连通；预算 JSON 落 S3；Secrets 注入生效 | D4 |
| 手动触发 Scheduler → 缓存出现今天/昨天键、validate 通过、失败不覆盖 | D5 |
| 前端经 CDN 加载、`/api/*` 路由、命中缓存 <500ms | D6 |
| 制造刷新失败 → 告警触发、Dashboard 反映 | D7 |
| 限流生效；扫描无明文密钥；安全组最小 | D8 |
| 流水线一键部署、测试阻断生效 | D9 |

## ADR

- **ADR-D1** 读写解耦：每日预算落缓存，在线只读 → 控 Open-Meteo 调用量 + 稳定延迟。
- **ADR-D2** 缓存层用 S3+CloudFront 而非 ElastiCache：每日刷新场景写少读多，S3 足够且省去 Redis 常驻成本。
- **ADR-D3** 起步方案 A（Serverless）后迁方案 B（Fargate）：代码通用，按规模切托管层。
- **ADR-D4** EventBridge Scheduler 直接设 `Asia/Shanghai` 时区，但刷新逻辑内部仍按 GMT+8 算日界（不依赖触发时区，双保险）。
- **ADR-D5** 密钥一律 Secrets Manager `valueFrom`，禁明文 env（kiro-gateway 反例教训）。
- **ADR-D6** validate 不通过不覆盖缓存：数据诚实优先于"刷新成功"。
