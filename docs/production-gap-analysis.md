# 生产化 Gap 分析 —— 「生产上线 + 每日自动更新」

> 目标：把当前以 spec 文档 + 引擎脚手架 + 前端 MVP 为主的项目，改造为可对外服务、每日自动刷新的生产系统。
> 核查时间：2026-06-20 GMT+8 ｜ AWS account=153705321444 ｜ 目标区域：ap-northeast-1（东京，距青岛用户最近的海外区）
> 配套：[deployment-and-ops spec](../.kiro/specs/deployment-and-ops/) ｜ [AWS 架构图](#五每日自动更新-aws-架构) ｜ [月度成本估算](#六月度-aws-成本估算)

---

## 一、AWS 环境核查结论

用 `AWS_PROFILE=oversea1 AWS_REGION=ap-northeast-1` 扫描，结论：**本项目在 AWS 上零部署**。

| 资源类型 | 扫描结果 | 与本项目相关 |
|----------|----------|--------------|
| ECS 集群 | 仅 `CentralizedLogging-*`（日志方案） | ❌ 无关 |
| Lambda | 全是 amplify-* / CentralizedLogging-* / SSM / video-on-demand 等 | ❌ 无关 |
| S3 | 大量 workshop/demo/kiro-gateway(us-east-1) 桶 | ❌ 无 surf 站点桶 |
| EventBridge 规则 | 仅 Inspector/GatedGarden/SageMaker 托管规则 | ❌ 无 surf 调度 |

→ 账户是个人沙箱，与多项目共用。**生产基建需从零搭建**（ECR / 计算托管 / DB / 缓存 / CDN / 调度 / 监控 / DNS-TLS 全缺）。

---

## 二、当前已实现范围（代码事实）

| spec | ✅ 已实现 | ⬜ 未实现 |
|------|-----------|-----------|
| **analyzer 引擎** | `physics.py`（波长/群速/能量/风向判定）+ `test_physics`；`thresholds.yaml`（**已含 `spot_facing_deg:157`、`offshore_bonus_band:1`**，0.2 基本完成）；`pyproject` 完整 | `fetch/analyze/scoring/validate/render/models/cli` **全部 `NotImplementedError`** |
| **web 网站** | `web/浪报MVP.html` 纯前端 MVP（双模式 / 三类 SVG 图 / 离岸风质条 / 昨日回看 / 口令占位 / **数据写死内嵌**） | FastAPI 后端**完全不存在**（auth/query/cache/history/db 零）；前端仍静态内嵌 |
| **feedback 校验** | 前端 `renderVerify` / `rateYesterday`（四档自评 + 即时反馈） | 历史正式化、`/api/accuracy/vote` 持久化、偏差校准**全无** |
| **运维** | `.kiro/hooks/refresh-data.kiro.hook`（manual/disabled，预埋每日刷新概念） | 无 IaC / 无调度 / 无监控 / 无部署脚本 |

**核心判断**：引擎当前跑不出任何真实数据（取数/评分/校验/渲染全是占位异常），前端展示的是写死样例。距"生产 + 每日自动更新"四层全空 —— ① 引擎未接通 → ② 无后端 → ③ 无调度刷新 → ④ 无基建。

**Spec 覆盖盲区**：三个 spec 设计的是**惰性按需查询 + TTL 缓存**（web 4.1），并未覆盖"**每日定时主动预算并刷新**"这一生产诉求，也未覆盖 **IaC / 部署 / 可观测性**。本次新增 `deployment-and-ops` spec 填补该盲区。

---

## 三、Gap 清单

每项：当前状态 vs 生产要求 → 需新增 AWS 组件 → 落到 spec/task。

### 🔴 Gap 1 — 引擎未接通真实数据（最底层阻塞）
- **现状 vs 生产**：取数/评分/校验/渲染为 `NotImplementedError` → 生产要求产出符合契约（含 `wdeg`）的真实 JSON。
- **AWS 组件**：无（纯代码）。但需决策 **Open-Meteo 商用许可**：免费档为非商用 / <1 万次/日，会员收费产品须评估付费 key 或"每日预算 + 缓存降频"以压低调用量。
- **落到**：`analyzer 1.x / 2.2 / 3.x / 4.x / 5.x / 6.1 / 7.x`。

### 🔴 Gap 2 — 无 Web 后端（鉴权 / 查询 / 缓存）
- **现状 vs 生产**：FastAPI 不存在、前端写死、口令占位 → 生产要求真鉴权(argon2)、401 保护、会员配额、查询接引擎、缓存。
- **AWS 组件**：计算托管 **ECS Fargate + ALB**（沿用 kiro-gateway 成熟模式）；**ACM 证书 + Route53**（TLS/DNS）。
- **落到**：`web 1.x / 2.x` + `deployment-and-ops`（D2/D3）。

### 🔴 Gap 3 — 每日自动更新机制（spec 盲区，本次新增）
- **现状 vs 生产**：仅惰性查询 + TTL；有概念 hook 但无落地 → 生产要求每日（对齐 ECMWF 模型更新，建议 1–2 次/日，按 GMT+8）主动重算所有上架浪点的预报 + 昨日历史，写入存储，前端/API 命中即返回。
- **AWS 组件**：**EventBridge Scheduler**（cron，GMT+8 触发）；刷新计算 **ECS Scheduled Task / Lambda**（跑引擎 `build_context` + `--past-days=1`）；预算结果存储见 Gap 4。
- **落到**：`deployment-and-ops`（D5 调度刷新）+ 复用 `analyzer --past-days`。

### 🟠 Gap 4 — 持久化存储（用户 / 会员 / 自评 / 缓存）
- **现状 vs 生产**：spec 写 SQLite→Postgres；SQLite 在 Fargate 多实例无状态下不可用 → 生产要求托管 DB + 缓存。
- **AWS 组件**：
  - 关系数据(users/members/saved_spots/accuracy_votes)：**RDS Postgres（db.t4g.micro）** 或 **Aurora Serverless v2**；轻量可选 **DynamoDB on-demand**。
  - 预算浪报缓存：**S3 预算 JSON + CloudFront**（每日刷新场景最省）或 **DynamoDB** 或 **ElastiCache Redis**。
  - 密钥/DB 凭据：**Secrets Manager**（教训：避免明文 env，用 `valueFrom`）。
- **落到**：`web 1.1(db) / 3.1(cache)`、`feedback 2.2(votes)` + `deployment-and-ops`（D4 存储）。

### 🟠 Gap 5 — 前端托管 + 动态化 + CDN
- **现状 vs 生产**：单 HTML 内嵌数据 → 生产要求静态资源 CDN 分发 + fetch 真 API。
- **AWS 组件**：**S3 静态站点桶 + CloudFront**（OAC、HTTPS、缓存策略）。
- **落到**：`web 5.1 / 5.2 / 5.4` + `deployment-and-ops`（D6 前端托管）。

### 🟡 Gap 6 — 校验闭环持久化
- **现状 vs 生产**：自评仅前端即时反馈 → 生产要求登录持久化 + 偏差校准。
- **AWS 组件**：复用 Gap 4 的 DB（accuracy_votes 表）。
- **落到**：`feedback 1.x / 2.x / 3.x / 4.x`。

### 🟡 Gap 7 — 可观测性 / 安全 / 上线护栏
- **现状 vs 生产**：无监控/告警/限流/WAF → 生产要求日志、告警、限流、HTTPS、输入校验。
- **AWS 组件**：**CloudWatch Logs + Alarms + Dashboard**；**WAF**（可选，套 CloudFront/ALB）；ALB 健康检查；限流（应用层或 WAF）。
- **落到**：`web 7.1 / 7.2` + `deployment-and-ops`（D7 可观测性、D8 安全）。

### ⚙️ Gap 8 — IaC 与 CI/CD
- **现状 vs 生产**：无部署脚本/IaC → 生产要求可复现部署。
- **AWS 组件**：**ECR**（镜像）；Terraform/CDK 定义全栈；本地或 CodeBuild 构建（偏好云端 ARM64 t4g 构建）。
- **落到**：`deployment-and-ops`（D1 IaC 骨架、D9 CI/CD）。

---

## 四、优先级任务清单（含阻塞依赖）

```
P0 引擎接通 ──┬─> P1 Web后端 ──┬─> P2 每日调度刷新 ─┐
(JSON含wdeg)  │   (鉴权+查询)   │   (EventBridge)    ├─> P2 前端动态化+CDN ─> P3 校验闭环 ─> P3 上线护栏
              └─> P1 托管DB ────┴─> P1 缓存存储 ─────┘
              └─[并行]─> P0 基建脚手架(ECR/IaC/Secrets/DNS-TLS)
```

| 优先级 | 任务 | 阻塞依赖 | spec / task |
|--------|------|----------|-------------|
| **P0-1** | 完成引擎：models→scoring→fetch→validate→analyze→render(JSON 含 wdeg)→cli | 无（地基） | analyzer 1.x/2.2/3.x/4.x/5.x/6.1/7.x |
| **P0-2** | 基建脚手架：ECR、Secrets Manager、ACM、Route53 子域、IaC 骨架 | 无（与 P0-1 并行） | deploy D1 |
| **P0-3** | 决策 Open-Meteo 商用许可与降频策略 | 无 | analyzer 设计补注 |
| **P1-1** | Web 后端骨架 + 托管 DB + argon2 鉴权 + 401 | P0-1, P0-2 | web 1.x；deploy D4 |
| **P1-2** | 查询接口接引擎 + 缓存存储 | P1-1 | web 2.x/3.x；deploy D4 |
| **P1-3** | 计算托管上线：ECS Fargate + ALB（HTTPS） | P1-1, P0-2 | deploy D2/D3 |
| **P2-1** | **每日自动更新**：EventBridge Scheduler + Scheduled Task/Lambda 刷新→写缓存 | P1-2 | deploy D5 |
| **P2-2** | 前端动态化（去内嵌→fetch）+ 接真鉴权 + S3+CloudFront | P1-2 | web 5.x；deploy D6 |
| **P3-1** | 校验闭环：历史正式化 + vote 持久化 + 偏差校准 | P1-1, P2-1 | feedback 1.x/2.x/3.x/4.x |
| **P3-2** | 上线护栏：CloudWatch 告警/Dashboard、WAF/限流、test_security | P1-3, P2-2 | web 7.x；deploy D7/D8 |
| **P3-3** | CI/CD 流水线 | P1-3 | deploy D9 |

**两条硬依赖链**：
1. **P0-1 引擎是全局阻塞** —— 产出 JSON 才能解锁 web 查询、调度刷新、校验。先做收益最大。
2. **每日自动更新（P2-1）依赖缓存存储（P1-2）就位** —— 无可写预算存储则定时刷新无处落地。

---

## 五、每日自动更新 AWS 架构

详见独立架构图（draw.io）。文字描述：

```
                         ┌──────────────── 用户（浏览器，青岛/国内） ────────────────┐
                         ▼                                                          │
                  Route53 + ACM(TLS)                                                │
                         ▼                                                          │
                   CloudFront (CDN)                                                 │
                    ├── /            → S3 静态站点桶（前端 SPA）                       │
                    └── /api/*       → ALB → ECS Fargate(FastAPI 后端)               │
                                              │  鉴权/查询/会员/缓存读                  │
                                              ├── RDS Postgres(users/members/votes)  │
                                              ├── 缓存读 ← S3 预算 JSON / DynamoDB     │
                                              └── Secrets Manager(DB/API key)        │
                                                                                     │
   ┌──── 每日自动更新链路（与在线请求解耦）────────────────────────────┐               │
   │  EventBridge Scheduler (cron, GMT+8, 1-2次/日)                  │               │
   │        ▼                                                        │               │
   │  ECS Scheduled Task / Lambda (跑引擎 build_context + past_days=1)│               │
   │        │  → Open-Meteo ECMWF WAM/IFS 取数 → 评分 → validate      │               │
   │        ▼                                                        │               │
   │  写预算 JSON → S3 / DynamoDB（今天起预报 + 昨日历史，键含日期）─────┘               │
   │        ▼  CloudFront 失效/短 TTL → 在线请求命中预算结果（<500ms）                  ─┘
   └────────────────────────────────────────────────────────────────┘
                    ▲
                CloudWatch Logs + Alarms + Dashboard（贯穿全栈）
```

**设计要点**：
- **读写解耦**：每日调度链路负责"写"（预算并落 S3/Dynamo），在线请求只"读"缓存 → 把 Open-Meteo 调用量从"每次查询"压到"每日 N 次"，既省钱又规避商用许可风险。
- **GMT+8 边界**：Scheduler 用 `cron(... Asia/Tokyo)` 或以 UTC 换算，刷新逻辑内部按 GMT+8 计算 today/yesterday，保证预报区与历史区不重叠（沿用引擎 validate）。
- **降级**：Open-Meteo 故障时刷新失败 → 保留上一日预算结果 + CloudFront 继续服务旧数据并标注时效（不白屏，web R4.3）。
- **轻量优先**：低流量会员站，缓存层用 **S3 预算 JSON + CloudFront** 即可，无需 ElastiCache；DB 低流量用 **db.t4g.micro** 或 **DynamoDB on-demand**。

---

## 六、月度 AWS 成本估算

> 假设：低流量会员站（数百日活内），刷新 1–5 个浪点、每日 1–2 次。区域 ap-northeast-1（东京）。
> ⚠️ 估算值，实际以 [AWS Pricing Calculator](https://calculator.aws/) 为准；不含数据传出突增与税费。

### 方案 A —— 精益 Serverless（推荐起步，低流量最省）
计算用最小 Fargate 或 Lambda，缓存走 S3+CloudFront，DB 用 DynamoDB on-demand，**无 RDS、无 Redis、无常驻 ALB**（API 用 API Gateway + Lambda）。

| 组件 | 规格/用量 | 月成本(USD) |
|------|-----------|-------------|
| Lambda（API + 每日刷新） | 低调用量，多在免费额度内 | ~$0–2 |
| API Gateway (HTTP API) | 数十万请求/月 | ~$1–3 |
| DynamoDB (on-demand) | 用户/会员/votes + 缓存，小规模 | ~$1–3 |
| S3（静态 + 预算 JSON） | <1GB + 少量请求 | ~$1 |
| CloudFront | 低流量 <10GB 出 | ~$1–5 |
| EventBridge Scheduler | 每日几次 | ~$0 |
| Secrets Manager | 2 个密钥 | ~$0.8 |
| Route53 | 1 个 hosted zone | ~$0.5 |
| CloudWatch | 日志 + 少量告警 | ~$2–4 |
| ECR | 镜像存储（若用容器刷新） | ~$0.1 |
| **合计** | | **≈ $10–25 / 月** |

### 方案 B —— 标准容器栈（沿用 kiro-gateway 模式，弹性/可演进强）
常驻 Fargate + ALB + RDS，缓存仍可用 S3 省去 Redis。

| 组件 | 规格/用量 | 月成本(USD) |
|------|-----------|-------------|
| ECS Fargate | 1 task，0.25 vCPU / 0.5 GB，24×7 | ~$9 |
| ALB | 基础 + 低 LCU | ~$18–22 |
| RDS Postgres | db.t4g.micro，单 AZ，20GB | ~$13–16 |
| S3 + CloudFront | 静态 + 预算 JSON + CDN | ~$3–6 |
| EventBridge Scheduler | 每日几次 | ~$0 |
| 每日刷新 Lambda | 低调用 | ~$0–1 |
| Secrets Manager | 2 个密钥 | ~$0.8 |
| Route53 | 1 个 hosted zone | ~$0.5 |
| CloudWatch | 日志 + 告警 + Dashboard | ~$4–6 |
| ECR | 镜像存储 | ~$0.1 |
| **合计** | | **≈ $50–75 / 月** |

### 方案 C —— 高可用（多 AZ / 加 Redis / WAF，规模上量后）
方案 B 基础上：RDS 多 AZ(×2 ≈ +$15)、ElastiCache t4g.micro(~$12)、WAF(~$8+按请求)、Fargate 2 task(~+$9)。
**≈ $95–140 / 月**。

### 成本建议
- **起步用方案 A**：低流量阶段最省，且"每日预算 + S3 缓存"天然契合每日自动更新模型，把 Open-Meteo 调用降到最低。
- **用户增长后迁移方案 B**：需要会话/复杂查询/关系型报表时上 RDS + Fargate（与你 kiro-gateway 运维经验一致，复用 build-on-ec2 ARM64 构建）。
- **方案 C 仅在付费用户规模化、需 SLA 时启用**。
- 最大变量是 **CloudFront 数据传出** 与 **Open-Meteo 商用 API**（若选付费档）——这两项需按真实流量重估。

---

## 七、需先改 spec 再开工的三处

1. **每日定时刷新链路** —— 三个原 spec 未覆盖 → 由本次 `deployment-and-ops` D5 承接。
2. **AWS IaC / 部署** —— 未覆盖 → `deployment-and-ops` D1/D2/D3/D9。
3. **生产可观测性** —— 未覆盖 → `deployment-and-ops` D7/D8。

> 数据诚实红线（GMT+8 日界、预报/历史日期互斥、口径一致、离岸判定）在生产链路中**继续由引擎 validate 强制**，调度刷新不得绕过校验。
