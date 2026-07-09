# Tasks — Deployment & Ops（生产部署与每日自动更新，v2）

> Kiro 约定：一次一个任务，完成勾 [x]。标注满足的需求/验收标准(D)。
> 前置：analyzer 能 render(JSON 含 wdeg) 且支持 --past-days；web 后端可容器化。

## 阶段 0：决策与准备
- [ ] 0.1 决策部署方案 A(Serverless) / B(Fargate)，记录于 design ADR-D3 _(D1)_
- [ ] 0.2 决策 Open-Meteo 商用许可（免费降频 vs 付费 key），影响缓存策略与成本 _(R5.6)_
- [ ] 0.3 确认区域 ap-northeast-1、域名（新 Route53 zone 或复用子域）_(D3)_

## 阶段 1：IaC 骨架与镜像（D1）
- [x] 1.1 Terraform 工程骨架 + 环境 tfvars(dev/staging/prod) 参数化 _(R1.1,1.2)_ ✅ root+versions+vars+outputs，dev.tfvars.example，`terraform validate` 通过（未 apply）
- [x] 1.2 ECR 仓库 `surf-forecast`；后端 Dockerfile；构建推镜像（偏好云端 ARM64 t4g 构建）_(R1.3;D1)_ ✅ ECR 模块 + Dockerfile(ARM64/uvicorn/非root/healthcheck)；构建推镜像待 apply 后
- [x] 1.3 VPC 网络模块：公私子网 + NAT/VPC Endpoint + 安全组最小化 _(R3.2,8.2)_ ✅ network 模块（2AZ 公私子网/NAT/ALB·App SG 最小化）

## 阶段 2：存储与密钥（D4）
- [x] 2.1 数据库：RDS Postgres(B) 或 DynamoDB(A)，建 users/members/saved_spots/accuracy_votes _(R4.1)_ ✅ DynamoDB on-demand 4 表(users PK=email/sessions+TTL/votes+spots复合键) **已上线持久化验证**（注册→DynamoDB users 表；vote→accuracy_votes 3 条）
- [x] 2.2 缓存存储：S3 cache 桶（预算 JSON）键规约 `spot/date`、`spot/history/date` _(R4.2)_ ✅ S3 cache + web 桶（全私有 + OAC 待 CDN）
- [ ] 2.3 Secrets Manager：DB 凭据 +（若有）Open-Meteo key，容器 valueFrom 注入 _(R4.3,8.4)_

## 阶段 3：在线计算与网络（D2,D3）
- [x] 3.1 计算托管：Fargate+ALB(B) 或 Lambda+API Gateway(A)，健康检查/目标组 _(R2.1,2.2,2.3)_ ✅ **已 apply 42 资源**；ECR 镜像经临时 t4g EC2 构建推送；ECS 服务 running
- [~] 3.2 ACM 证书 + Route53 记录，全程 HTTPS _(R3.1;D3)_ ✅ HTTPS 已经 CloudFront 默认证书(*.cloudfront.net)达成（唯一公网入口 https://d37u8s32zy0h38.cloudfront.net）；⛔ 自定义域名 ACM/Route53 仍待定（people.aws.dev 内部域不可对外）
- [x] 3.3 部署后冒烟：/api/health 200、ALB 健康 _(D2)_ ✅ 公网 ALB 端到端：注册→登录(httponly cookie)→/api/report 200 返真实含 wdeg 浪报；未登录 401；free 钳 3 天
> ✅ 现状：后端已接 DynamoDB 持久化（SF_STORE=dynamo，重启不丢用户/投票）。公网唯一入口 = CloudFront https://d37u8s32zy0h38.cloudfront.net（ALB 仅 CloudFront 前缀列表可达，HTTP:80 内部回源）。

## 阶段 4：每日自动更新（D5，本 spec 核心）
- [x] 4.1 refresh_job：遍历上架浪点，build_context 预报 + past_days=1 历史 → render JSON _(R5.2)_ ✅ src/web/refresh.py（build_context include_history）
- [x] 4.2 作业内按 GMT+8 算 today/yesterday；写缓存前过引擎 validate；不通过不覆盖 _(R5.3;D5)_ ✅ ZoneInfo Asia/Shanghai + validate 守门
- [x] 4.3 失败降级：Open-Meteo 故障/校验失败 → 保留上一版 + 告警，不白屏 _(R5.4)_ ✅ skipped 不覆盖 + log.error
- [x] 4.4 EventBridge Scheduler cron(Asia/Shanghai, 02:00&14:00) 触发 refresh_job _(R5.1)_ ✅ scheduler 模块（2 时段→ECS RunTask 覆盖命令 python -m web.refresh_cli）+ refresh_cli 入口；validate 通过，待 apply
- [x] 4.5 刷新成功后 CloudFront 失效/短 TTL，在线命中最新预算 _(R5.5)_ ✅ CloudFront E2ZQMKCAN0V79D 已部署；/api/* 行为 TTL=0 不缓存（动态实时）；deploy.sh frontend 含 create-invalidation `/*`
- [x] 4.6 后端 query/history 改为先读缓存（读写解耦），未命中回退计算并写缓存 _(R5.6;D6)_ ✅ deps.get_report 上架浪点命中 S3 缓存，自定义坐标/未命中回退引擎；SF_CACHE_BUCKET 启用
- [x] 4.7 test_refresh：手动触发 → 缓存出现今天/昨天键、validate 通过、失败不覆盖 _(D5)_ ✅ 3 项通过

## 阶段 5：前端托管与 CDN（D6）
- [x] 5.1 CloudFront 单一 ALB 源(HTTPS)；`/` 与 `/api/*` 同源经 ALB 回源 _(R6.1,6.2)_ ✅ **架构改为 ALB 单源**（前端已内置 FastAPI 镜像，去 S3/OAC）；CloudFront 默认行为转发 ALB 透传 cookie/query；**ALB SG 锁 CloudFront 托管前缀列表 pl-58a04531、移除 0.0.0.0/0 → ALB 不再公网直暴露，DyePack/Epoxy 风险根治**
- [x] 5.2 前端发布：浪报MVP.html 内置镜像由 FastAPI `/` 直供，经 CloudFront 暴露 _(R6.1)_ ✅ Dockerfile COPY web + app.py `/` FileResponse；deploy.sh build(临时 EC2)→redeploy→CloudFront 失效
- [x] 5.3 端到端：CDN 加载前端、API 路由正确、命中缓存 <500ms _(D6)_ ✅ headless Chromium 终验：CloudFront HTTPS 加载前端 0 SVG/JS 报错（仅 favicon 404）、Hero/日期条/逐日卡/剧情实时(当日 GMT+8)、/api/* 路由正确、读缓存命中

## 阶段 6：可观测性（D7）
- [x] 6.1 CloudWatch Logs：后端 + 刷新任务日志组 _(R7.1)_ ✅ /ecs/surf-forecast-dev（compute 模块）
- [x] 6.2 Alarms：刷新失败、5xx 率、UnhealthyHost、RDS 连接/CPU _(R7.2)_ ✅ observability 模块（refresh-skipped 日志过滤 + alb-5xx + unhealthy-hosts，SNS 通知）
- [x] 6.3 Dashboard `surf-forecast-overview`：请求/延迟/错误/刷新状态/缓存命中 _(R7.3)_ ✅ 4 widget（请求/5xx、p50/p99、ECS CPU/Mem、刷新跳过）
- [ ] 6.4 test_alarm：制造刷新失败 → 告警触发可见 _(D7)_ 🔸 待 apply 后人工验证

## 阶段 7：安全（D8）
- [ ] 7.1 限流：HTTP API throttling 或 WAF rate-based(per-IP) _(R8.1)_ 🔸 待 WAF 模块
- [x] 7.2 IAM 最小权限：刷新任务角色 / 后端角色按需授权 _(R8.2)_ ✅ task role 仅 DynamoDB rw + cache S3 rw；scheduler role 仅 RunTask+PassRole
- [ ] 7.3 （可选）WAF 套 CloudFront：rate limit + 托管规则集 _(R8.3)_
- [x] 7.4 扫描确认镜像/state/日志无明文密钥 _(R8.4;D8)_ ✅ 无密钥（DynamoDB 走 IAM、Open-Meteo 免 key）；.gitignore 排除 tfstate/tfvars

## 阶段 8：CI/CD（D9）
- [x] 8.1 deploy.sh：test→build→push ECR→tf apply，可重复 _(R9.1)_ ✅ deploy.sh 子命令 test/validate/apply/build(EC2)/redeploy/frontend/smoke/all
- [x] 8.2 部署前跑 pytest（含 validate 测试），失败阻断 _(R9.2;D9)_ ✅ cmd_test 失败 die 阻断
- [x] 8.3 部署文档（操作手册 + 回滚步骤）_(D1)_ ✅ docs/deployment-runbook.md（一键/分步/回滚/HTTPS收尾/踩坑/成本）

## 依赖
```
0.x ──> 1.x ──> 2.x ──┬─> 3.x ──┬─> 4.x ──> 5.x ──> 6.x ──> 7.x ──> 8.x
                      └─> (引擎 render+past_days, web 后端容器化 为外部前置)
4.x 依赖 2.2(缓存桶) + 引擎 build_context/validate ; 5.x 依赖 3.x(路由) + 4.x(有缓存可命中)
```

## 完成定义
全栈 IaC 可复现 + HTTPS 服务可达 + 托管 DB/缓存/密钥就位 + EventBridge 每日按 GMT+8 刷新且 validate 守门（失败不覆盖）+ 前端经 CDN 命中缓存 <500ms + 监控告警就绪 + 限流与最小权限 + 无明文密钥 + 一键部署且测试阻断。
> 数据诚实红线（GMT+8 日界 / 预报历史互斥 / 口径一致 / 离岸判定）在刷新链路中继续由引擎 validate 强制，不得绕过。
