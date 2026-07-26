# North Star — 产出第 6 个 Kiro spec：self-iterate-ops（可审物，零代码）

## 目标
把「自迭代闭环 v5 人主导治理模型」升格为**正式的第 6 个 Kiro spec** `self-iterate-ops`，
产出完整三件套（requirements / design / tasks）并注册进项目结构。
**纯文档 / 零代码 / 零 live 触碰**——本 goal 只产可审规格，不改 review_queue/req_pipeline/feedback 运行时、不碰生产。

## 产物
1. `.kiro/specs/self-iterate-ops/requirements.md`：EARS 风格用户故事 + 验收标准；把 v5 红线作为约束性需求。
2. `.kiro/specs/self-iterate-ops/design.md`：架构（收编 v5 G1-G5）+ **L0 决策作 ADR 附推荐值（待 spec 评审拍板，loop 不自行定案）** + 数据模型 + 接口 + 复用既有组件（review_queue/req_pipeline/audit_trace/每日 cron）。
3. `.kiro/specs/self-iterate-ops/tasks.md`：实施任务，**排序=决策→数据模型→新接口→用户可见→内部逻辑→机械/测试（红线逻辑测试随层例外）**，每条映射 requirements。
4. 注册：`structure.md` spec 边界表 +1、README 导航、根 roadmap 提及；**明标"工具/流程 spec，与产品功能 spec 区分"**（不侵蚀产品范围认知）。

## DoD
- 三件套齐全、交叉引用一致、EARS 验收可测；L0 以 ADR 形式列出**推荐值 + 备选**待人批（未擅自定案）。
- 结构注册完成（structure.md/README/roadmap 提及 self-iterate-ops 且标注工具属性）。
- **零代码改动** → pytest 仍 **188** 不倒退（仅验证无回归，不新增测试）。
- 全程 GMT+8；据实勾选。

## 红线
- **单一驱动器**：auto-nudge 唯一驱动，**禁 task_run**；与每日 triage cron(8e721bb9)/任何产品 goal 不并发写同一文件。
- **纯文档**：不改任何 `.py`/`.mjs`/`web/浪报MVP.html` 运行时；不碰生产 DynamoDB/ECS。
- **L0 不自行拍板**：D-a~D-d 只作 ADR 附推荐，最终由人在 spec 评审时定。
- 沿用既有红线（GMT+8 / DATA CONTRACT / float→Decimal / 全401 / SG禁0.0.0.0/0 / terraform禁-auto-approve）——作为 spec 的约束性需求写入，不在本 goal 实现。

## 范围外
写任何实现代码；改 review_queue/req_pipeline/feedback；碰生产；替人定 L0 决策；产品 5-spec 主线工作。

## 停止
三件套 + 注册完成、pytest 188 无倒退后创建 STOP：
`/Users/yiming/.meshclaw/workspace-surf-forecast/.stop-chat-3-1783779532`
