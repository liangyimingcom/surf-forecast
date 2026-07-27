# North Star — 在线 LLM 澄清 + LLM coder 实现（L1-L5，按 v6 设计）

## 目标
按 `docs/自迭代-在线LLM澄清与coder-设计v6.md`（ADR-5~8）实现两块 AI 环节：
- **在线匿名 LLM 澄清**（ECS 调 <llm-gateway>；每步自动；仅应用层护栏）。
- **LLM coder**（写实现但一律人工审 draft PR，守 v5 G1）。
本地全程 **mock LLM 测试**（不真烧钱/不触网）；真调网关 + Secrets 注入 + 部署 = **生产写操作门 G**。

## 范围（决策优先排序；红线逻辑测试随层）
- **L1 数据模型**：per-IP 限流 + 全局日预算计数（DynamoDB，float→Decimal）；选项缓存键(page-schema+步骤+已选)；LLM 输出结构化需求 schema + 校验器。
- **L2 接口**：后端 `POST /api/clarify`（匿名+限流→缓存→调网关(key from Secrets)→schema校验→写缓存；超限/不通/报错降级模板）；`req_pipeline --llm-coder`（生成锚点 patch→硬门→draft PR，永远人工审）。
- **L3 用户可见**：前端澄清 UI 每步调 /api/clarify（loading 态；≤4 轮收敛；跳过逃生；降级无缝切模板）。
- **L4 内部逻辑**：per-IP 限流 + 日预算硬闸 + 反注入(系统/数据分隔) + coder 锚点patch/禁碰web-e2e/diff扫描/需求当数据。
- **L5 机械/测试**：限流/预算/缓存/schema校验/降级 单测(边界双侧+mutation) + /api/clarify 降级集成 + coder patch+门 集成（全 mock LLM）。

## DoD
- pytest 全绿（LLM 全 mock，不触网/不烧钱）+ 冻结 E2E 64/0 + 0 JS 报错。
- 降级链可证：网关不通/超限 → 无缝退预置模板、不报错、不白屏。
- 数据诚实/反注入/缓存不碰可见性 红线守住；全程 GMT+8。

## 红线
- **单一驱动器**（禁 task_run）；与每日 triage cron/其他 goal 不并发写同文件。
- **人主导**：LLM coder 产出一律停 draft PR 等人工审，**无自动合并/部署**（守 v5 G1）。
- 匿名 LLM 仅**应用层**护栏（per-IP + 全局日预算硬闸 + 选项缓存 + 降级模板），**不引 WAF**。
- 反注入（用户/需求文本作 data 段）；CodeLens/源码/key 不外露；LLM 输出 schema 校验。
- 沿用：GMT+8 / DATA CONTRACT / float→Decimal(_to_decimal) / 全401 / SG禁0.0.0.0/0 / terraform禁-auto-approve。
- 每轮 codelens-dev 摸底+爆炸半径；pytest/E2E 零倒退；**真调网关/Secrets/部署留 G 门**。

## 范围外
无人值守自动合并/部署；WAF/CloudFront；LLM 略过人眼上线；pytest 里真调网关(必须 mock)。

## 停止
L1-L5 本地完成+全绿、仅剩 G 门（Secrets+部署）时创建 STOP：
`/Users/yiming/.meshclaw/workspace-surf-forecast/.stop-chat-3-1783779532`
