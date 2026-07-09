# Goal — 浪报 Surf Forecast 生产上线

> 自治循环 Goal description。基于现有方案（**方案 A Serverless 起步**，可迁 B Fargate；统一 **Terraform IaC**）。
> 区域 ap-northeast-1 ｜ profile oversea1 ｜ account 153705321444。
> 配套：[production-gap-analysis.md](production-gap-analysis.md) ｜ [deployment-and-ops spec](../.kiro/specs/deployment-and-ops/)。

## 目标陈述
将项目从"文档 + 引擎脚手架 + 前端 MVP"推进到 **可对外服务 + 每日自动更新** 的生产系统。落地形态：Lambda+API Gateway / DynamoDB / S3+CloudFront，统一 Terraform IaC。代码与后端在 A/B 形态间通用，上量后可迁 Fargate。

## 执行约定与审批门（自治循环必须遵守）
- **P1（引擎）纯代码、无 AWS 副作用 → 可全自治执行**（取数、评分、校验、渲染、CLI、单测）。
- **P2–P7 涉及真实 AWS 资源（Terraform apply、Lambda/DynamoDB/CloudFront/Route53/ACM/EventBridge 等，产生费用且有 blast radius）→ 每个 Terraform `apply` 前必须暂停并请求人工审批**（先 `tf plan` 给出变更摘要，批准后再 apply）。
- 任何破坏性 AWS 操作（删除/替换有状态资源）一律先确认。
- 失败两次以上不做增量补丁，先诊断根因再换思路。
- 每阶段完成后回灌结论到对应 spec 的 tasks.md（勾选 [x]）。

## 全局红线（贯穿所有阶段，任何任务不得违反）
1. **数据诚实**：GMT+8 日界算 today/yesterday；预报区与历史区日期互斥；周期 Tm/Tp 双口径标注；离岸/向岸判定按 `spot_facing_deg=157`；严禁用正确物理套不存在数据。
2. **validate 守门**：取数/渲染/每日刷新写缓存前必过引擎 `validate`，不通过不覆盖上一版。
3. **计算/叙事/鉴权三分离**：评分物理纯函数、叙事在模板/前端、鉴权全后端（前端零信任）。
4. **阈值全配置**：只改 `config/thresholds.yaml`，不硬编码。
5. **无明文密钥**：DB/API key 一律 Secrets Manager `valueFrom`。
6. **DATA CONTRACT**：引擎 JSON 形状=前端 DAYS/HISTORY，**必须含 `wdeg`**。
7. 每个改动遵循对应 spec；需求变更先改 requirements。

## 依赖顺序（关键路径）
```
P0 决策 ─┬─> P1 引擎(全局阻塞) ─┐
         └─[并行]─> P2 基建脚手架 ┴─> P3 Web后端 ─> P4 每日刷新 ─> P5 前端动态化+CDN ─> P6 校验闭环 ─> P7 上线护栏
```

---

## P0 — 决策与准备（无阻塞，先行）
- **deploy 0.1** 确认部署方案 A（Serverless 起步），记入 ADR-D3
- **deploy 0.2** 决策 Open-Meteo 商用许可（免费降频 vs 付费 key）→ 影响缓存策略与成本
- **deploy 0.3** 确认 ap-northeast-1 + 域名（新 Route53 zone 或复用子域）
- **退出条件**：三项决策落定，写入 design ADR。

## P1 — 分析引擎接通（🔴 全局阻塞，纯代码可全自治，先做）
- **analyzer 0.2** 核验 `thresholds.yaml` 的 `spot_facing_deg`/`offshore_bonus_band`（已基本就位，补测试确认）
- **analyzer 1.1 / 1.2** `models.py`（WindKind/ForecastPoint.wind_kind/DailyForecast GMT+8 weekday/ReportContext）+ `load_thresholds`
- **analyzer 2.2 / 2.3** `scoring.py` 五项评分（score_wind 离岸放宽一档）+ composite/weakest/rank + `test_scoring`
- **analyzer 3.1 / 3.2 / 3.3** `fetch.py` 三路 Open-Meteo + GMT+8 对齐 + `past_days` 历史 + 潮汐极值 + 字段回退
- **analyzer 4.1 / 4.2 / 4.3** `validate.py` 红线自动化（星期GMT+8/月相↔潮型/周期口径/虚构叙事拦截/历史预报互斥）+ `test_validate`+`test_narrative`
- **analyzer 5.1 / 5.2** `analyze.py` 编排（白天过滤、dawn_wind_kind、生命周期）
- **analyzer 6.1 / 6.2 / 6.3** ⭐ `render.py` 输出 **JSON（含 wdeg/tp2/tideEvents）** + Markdown + 可信度声明（GMT+8 时间戳）
- **analyzer 7.1 / 7.2 / 7.3** `cli.py`（含 `--past-days`）+ `test_golden`（复现 6/24 王者排名、离岸判定、6/19 历史口径一致）+ `test_config`
- **web 0.2**（并行）抽 `web/report.schema.json` 作前后端契约单一来源（含 wdeg/tp2/tideEvents）
- **退出条件**：`surf-forecast --lat 36.092 --lon 120.468 --days 6 --spot 青岛山东头` 跑出真实报告；JSON 含 wdeg 且过 validate；golden 测试通过。

## P2 — 基建脚手架（🔴 与 P1 并行；apply 需审批门）
- **deploy 1.1** Terraform 工程骨架 + dev/staging/prod tfvars 参数化
- **deploy 1.2** ECR `surf-forecast` + 后端 Dockerfile（云端 ARM64 t4g 构建）
- **deploy 1.3** VPC 网络模块：公私子网 + NAT/VPC Endpoint + 安全组最小化
- **deploy 2.1** DynamoDB on-demand 建 users/members/saved_spots/accuracy_votes
- **deploy 2.2** S3 cache 桶 + 键规约 `spot/date`、`spot/history/date`
- **deploy 2.3** Secrets Manager（DB/API key），运行时 `valueFrom` 注入
- **deploy 3.2** ACM 证书 + Route53 记录
- **退出条件**：`tf plan` 无漂移、资源齐全；ECR 有镜像；证书签发。

## P3 — Web 后端（依赖 P1 引擎 + P2 存储）
- **web 1.1–1.5** FastAPI app + DB 接入 + argon2 鉴权/登录登出 + `current_user`/401 保护 + 会员等级配额 + `test_auth`/`test_members`
- **web 2.1–2.5** `query.py` 校验+region阈值 → 接引擎返回 REPORT(含 wdeg) → `history.py` 昨日回算 → 内陆/无数据报错 + `test_query`/`test_contract`
- **web 3.1–3.3** `cache.py` 读缓存优先 + Open-Meteo 故障降级不白屏 + `test_cache`
- **web 4.1** 保存浪点 CRUD（可并行）
- **deploy 3.1 / 3.3** 计算托管上线（Lambda+API Gateway）+ 冒烟 `/api/health` 200
- **退出条件**：HTTPS 下登录→查询→返回含 wdeg 的 REPORT；401 保护生效；缓存读路径通。

## P4 — 每日自动更新（🔴 依赖 P2 缓存 + P1 引擎 + P3 缓存读）
- **deploy 4.1** `refresh_job`：遍历上架浪点，build_context 预报 + `past_days=1` 历史 → render JSON
- **deploy 4.2** 作业内按 GMT+8 算 today/yesterday；写缓存前过 validate；不通过不覆盖
- **deploy 4.3** 失败降级：Open-Meteo/校验失败 → 保留上一版 + 告警，不白屏
- **deploy 4.4** EventBridge Scheduler cron(Asia/Shanghai, 02:00 & 14:00) 触发
- **deploy 4.5** 刷新成功 → CloudFront 失效/短 TTL → 在线命中
- **deploy 4.6** 后端 query/history 读写解耦（只读缓存，未命中回退计算并写）
- **deploy 4.7** `test_refresh`：手动触发→缓存出现今天/昨天键、validate 通过、失败不覆盖
- **退出条件**：定时触发后缓存按 GMT+8 正确滚动；在线请求命中预算结果 <500ms；失败不覆盖验证通过。

## P5 — 前端动态化 + CDN（依赖 P3 API + P4 缓存有数据）
- **web 5.1** 移除内嵌 DAYS/HISTORY，改 fetch `/api/report` 与 `/history`
- **web 5.2** 门禁占位 → 真 `/api/auth` + 会话态
- **web 5.3** 自定义经纬度 + 保存浪点接 `/api/spots`
- **web 5.4** 走查对齐 UI 黄金样本（双模式/三图表/离岸风质条/HTML图例/GMT+8）
- **deploy 5.1 / 5.2 / 5.3** S3 web 桶 + CloudFront(OAC/HTTPS)，`/` 静态、`/api/*` 路由后端；发布+失效流程；端到端 <500ms
- **退出条件**：经 CDN 加载的动态站点功能/交互不逊于 MVP 黄金样本；命中缓存 <500ms。

## P6 — 校验闭环（依赖 P1 past_days + P3 后端/DB + P4 历史刷新）
- **feedback 1.1–1.4** 历史正式化：past_days=1 取昨日(GMT+8 today−1)；HISTORY 含 predict{}；口径一致；`test_history_date`/`parity`/`predict_present`
- **feedback 2.1–2.4** `GET /api/report/history` + `POST /api/accuracy/vote`→votes 表(含 GMT+8 时间) + 前端登录态调用 + `test_vote_*`
- **feedback 3.1–3.3** 偏差校准：近 N 条统计→提示建议，**不改原评分** + `test_bias`
- **feedback 4.1 / 4.2** `test_placement`(verify 在 cards 之后) + 全程 GMT+8 核验
- **退出条件**：昨日回看口径与预报一致、日期不重叠；登录自评持久化；偏差提示不篡改原分；位于预报之后。

## P7 — 上线护栏（依赖 P3/P5 在线，发布前最后一关）
- **deploy 6.1–6.4** CloudWatch Logs + Alarms(刷新失败/5xx/不健康/DB) + Dashboard `surf-forecast-overview` + `test_alarm`
- **deploy 7.1–7.4** 限流(API throttling/WAF rate-based) + IAM 最小权限 + (可选)WAF + 扫描无明文密钥
- **web 7.1 / 7.2** `test_security`(无泄露/限流/注入) + 密钥环境变量、部署文档
- **deploy 8.1–8.3** `deploy.sh`(test→build→push→tf apply) + 部署前跑 pytest 阻断 + 部署文档+回滚步骤
- **退出条件**：告警可触发、Dashboard 反映；限流+最小权限+无明文密钥；一键部署且测试阻断生效。

## 范围外（不阻塞上线，列后续）
- **web 6.1 / 6.2** Vite 组件化、会员中心、配额 UI、响应式打磨（阶段 B，上线后迭代）
- 多区域容灾、蓝绿/金丝雀、支付扣费、社交登录、多浪点横向对比。

## 生产上线 Definition of Done
P0–P7 全部退出条件满足：引擎产真实 JSON(含 wdeg) + HTTPS 服务可达 + argon2 鉴权无前端绕过 + 每日按 GMT+8 自动刷新且 validate 守门(失败不覆盖) + 前端经 CDN 命中缓存 <500ms + 昨日回看校验闭环 + 监控告警/限流/最小权限/无明文密钥 + 一键部署且测试阻断；全程数据诚实红线零违反。
