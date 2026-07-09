# Requirements — Deployment & Ops（生产部署与每日自动更新，v2 新增）

> EARS 格式。本 spec 填补原三个 spec 的盲区：**IaC / 计算托管 / 存储 / 每日定时刷新 / CDN / 可观测性 / 安全 / CI-CD**。
> 前置：analyzer 能 `build_context→render(JSON 含 wdeg)` 且支持 `--past-days`；web 后端可被容器化。
> 区域：ap-northeast-1（东京，距青岛用户最近的海外区）。账户 153705321444，profile oversea1。

## 文档目的

定义把项目改造为「**对外服务 + 每日自动刷新**」生产系统所需的基础设施、调度与运维能力。核心新增：**每日定时主动预算浪报并落缓存**（与在线请求读写解耦），把 Open-Meteo 调用量从"每次查询"压到"每日 N 次"。

## 用户故事

- 作为**运营者**，我希望系统每天自动拉取最新预报与昨日回算并刷新，无需人工触发。
- 作为**会员**，我希望任何时刻打开站点都能秒开当日最新浪报（命中预算缓存）。
- 作为**维护者**，我希望基础设施可由代码复现部署、有监控告警、密钥不落明文。

## 1. 基础设施即代码（IaC）

**1.1** THE SYSTEM SHALL 用 IaC（Terraform 或 CDK）声明式定义全部生产资源（计算/存储/网络/调度/监控），可 `plan`/`apply` 复现。
**1.2** THE SYSTEM SHALL 把环境差异（dev/staging/prod）参数化，不硬编码账号/区域/域名。
**1.3** THE SYSTEM SHALL 将容器镜像发布到 **ECR**，镜像 tag 含版本/commit。

## 2. 计算托管（在线请求）

**2.1** THE SYSTEM SHALL 将 FastAPI 后端容器化并托管于 **ECS Fargate**（或等价无服务器方案），由 **ALB** 暴露。
**2.2** THE SYSTEM SHALL 配置 ALB 健康检查与目标组；任务异常自动替换。
**2.3** WHERE 低流量，THE SYSTEM SHALL 允许最小规格（如 1 task / 0.25 vCPU）以控成本，支持后续水平扩展。

## 3. 网络与 TLS

**3.1** THE SYSTEM SHALL 全程 HTTPS：**ACM 证书** + **Route53** 域名解析。
**3.2** THE SYSTEM SHALL 仅经 CloudFront/ALB 暴露公网入口；后端任务置于私有子网，经 NAT 或 VPC Endpoint 出网。

## 4. 持久化与缓存存储

**4.1** THE SYSTEM SHALL 用托管数据库（**RDS Postgres** 或 **DynamoDB**）存 users/members/saved_spots/accuracy_votes，**不得用 SQLite 文件**（Fargate 无状态/多实例不可用）。
**4.2** THE SYSTEM SHALL 把每日预算的浪报 JSON 落**缓存存储**（**S3 预算 JSON + CloudFront** 优先，或 DynamoDB / Redis），键含浪点+日期。
**4.3** THE SYSTEM SHALL 用 **Secrets Manager** 存 DB 凭据与（若有）Open-Meteo 付费 key，以 `valueFrom` 注入容器，**禁止明文 env**。

## 5. 每日自动更新（本 spec 核心）

**5.1** THE SYSTEM SHALL 用 **EventBridge Scheduler** 按 cron 每日触发刷新（建议 1–2 次/日，对齐 ECMWF 模型更新）。
**5.2** WHEN 触发，THE SYSTEM SHALL 运行引擎对所有上架浪点预算：今天起的预报 + `past_days=1` 的昨日历史，处理口径与在线一致。
**5.3** THE SYSTEM SHALL 按 GMT+8 计算 today/yesterday，写入缓存前经引擎 `validate`（含历史/预报日期互斥、离岸判定、口径一致），**校验不通过不覆盖上一版**。
**5.4** IF Open-Meteo 不可用或刷新失败，THEN THE SYSTEM SHALL 保留上一日预算结果并记录告警，**不得清空/白屏**。
**5.5** WHEN 刷新成功，THE SYSTEM SHALL 使 CloudFront 对应缓存生效（失效或短 TTL），令在线请求命中最新预算结果。
**5.6** THE SYSTEM SHALL 使每日刷新与在线请求**读写解耦**：在线路径只读缓存，不直接打 Open-Meteo。

## 6. 前端托管与 CDN

**6.1** THE SYSTEM SHALL 将前端静态资源托管于 **S3** 并经 **CloudFront** 分发（OAC、HTTPS、合理缓存策略）。
**6.2** THE SYSTEM SHALL 把 `/api/*` 经 CloudFront/ALB 路由到后端，`/` 路由到静态站点。

## 7. 可观测性

**7.1** THE SYSTEM SHALL 将后端与刷新任务日志汇聚到 **CloudWatch Logs**。
**7.2** THE SYSTEM SHALL 配置 **CloudWatch Alarms**：刷新失败、5xx 率、任务不健康、DB 连接异常。
**7.3** THE SYSTEM SHALL 提供 **CloudWatch Dashboard** 概览（请求量/延迟/错误率/刷新状态/缓存命中）。

## 8. 安全

**8.1** THE SYSTEM SHALL 对查询接口限流（应用层或 WAF），防滥用。
**8.2** THE SYSTEM SHALL 最小化安全组/IAM 权限（最小权限原则）；任务角色仅授予所需资源。
**8.3** WHERE 需要，THE SYSTEM SHALL 在 CloudFront/ALB 前置 **WAF**（速率限制、常见攻击规则）。
**8.4** THE SYSTEM SHALL 不在镜像/IaC state/日志中暴露密钥明文。

## 9. CI/CD

**9.1** THE SYSTEM SHALL 提供从源码到镜像到部署的可重复流水线（本地脚本或 CodeBuild/CodePipeline）。
**9.2** THE SYSTEM SHALL 在部署前运行单元测试（含引擎 validate 相关），失败阻断发布。

## 验收标准

| # | 标准 |
|---|------|
| D1 | 全栈资源由 IaC 复现，`plan` 无漂移；镜像在 ECR |
| D2 | 后端经 ALB/Fargate 提供 HTTPS 服务，健康检查生效 |
| D3 | 自定义域名 + ACM TLS 可访问 |
| D4 | 用户/会员/自评存托管 DB；预算 JSON 落 S3/Dynamo；密钥走 Secrets Manager |
| D5 | EventBridge 每日按 GMT+8 触发刷新，预算今天起预报 + 昨日历史，经 validate，失败不覆盖 |
| D6 | 前端经 S3+CloudFront 分发，`/api/*` 正确路由，在线请求命中预算缓存 <500ms |
| D7 | CloudWatch 日志/告警/Dashboard 就绪，刷新失败可告警 |
| D8 | 限流 + 最小权限 + 无密钥明文 |
| D9 | CI/CD 可重复部署，部署前跑测试 |

## 范围外
多区域容灾、蓝绿/金丝雀发布、自动伸缩策略调优、成本异常自动治理（列入路线图）。
