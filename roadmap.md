# Roadmap — 在线 LLM 澄清 + coder 实现

单一驱动器(auto-nudge,禁 task_run)。改前 codelens-dev 摸底+爆炸半径;改后 pytest/E2E/bash -n。
LLM 全程 mock 测试(不触网);真调网关/Secrets/部署留 G 门。红线逻辑测试随层编织。

## R0 摸底
- codelens/grep：feedback 落库链、模板澄清 UI(降级兜底基点)、req_pipeline edit 入口、deps 环境读取(Secrets 注入点)。

## L1 数据模型
- llm_usage 计数(per-IP 滑窗 + 全局日累计;float→Decimal;DynamoDB 新表 or 复用) + 选项缓存(内存 LRU/TTL) + 澄清需求 schema + 校验器。
- [随层] 限流窗口/日预算边界 + schema 校验拒畸形 单测(双侧钉死+mutation)。

## L2 接口
- `POST /api/clarify`(匿名+限流)：缓存→调网关(可注入 client,测试 mock)→schema 校验→写缓存;超限/不通/报错→降级模板。
- `req_pipeline --llm-coder`：调网关生成锚点 patch(mock 可测)→既有硬门→draft PR(永远人工审)。
- [随层] /api/clarify 各分支 + coder patch 生成/应用 单测(mock LLM)。

## L3 用户可见
- 前端澄清 UI 每步调 /api/clarify(loading 态;≤4 轮;跳过逃生);超限/降级无缝切模板+提示不报错。
- [随层] 冻结 E2E 64/0 不倒退 + 澄清降级探针(mock 网关不通→模板)。

## L4 内部逻辑(护栏)
- per-IP 限流 + 全局日预算硬闸(超限→降级,不再调网关);反注入(系统/数据分隔);coder 锚点patch/禁碰web-e2e/diff扫描/需求当数据。
- [随层] 硬闸/反注入/coder 退回 单测。

## L5 收尾
- 全量 pytest(LLM全mock) + 冻结 E2E 64/0 + bash -n;据实勾选;STOP。

## [生产写操作门 G]（停下发 blocker 等人工确认）
- G.1 Secrets Manager 存网关 key + ECS 任务角色 valueFrom 注入 + (若新表)建表+IAM。
- G.2 部署(build+redeploy+canary+tag+CHANGELOG) + 生产真调网关冒烟(带预算/限流)。
