# Tasks — self-iterate-ops spec（可审物，零代码）

> 单一驱动器(auto-nudge,禁 task_run)。纯文档;不改运行时(.py/.mjs/HTML)/不碰生产。
> L0 只作 ADR 附推荐待人批,不自行定案。全程 GMT+8;据实勾选,禁记未落地。
> 基线：pytest 188 · master 9905996 · v5 治理模型+实施计划已在 docs/。

## S1 requirements
- [x] S1.1 摸底既有 spec requirements 写法(EARS/编号)——对齐 custom-spots 风格(WHEN/THE SYSTEM SHALL/WHERE/IF-THEN + 编号 X.Y)
- [x] S1.2 `.kiro/specs/self-iterate-ops/requirements.md`：6 组(建议提交澄清/每日triage/按风险分流/draft PR/人主导发布/红线约束) + EARS 验收 + v5 红线作约束性需求 + 明标"工具/流程spec非产品功能" + 范围外

## S2 design
- [x] S2.1 design.md 架构总览(收编 v5 G1-G5 + 数据流图 + 与产品5-spec边界)
- [x] S2.2 ADR §7：L0 决策 D-a~D-d 各附**推荐值+备选+倾向**(待评审拍板,未定案)
- [x] S2.3 数据模型(feedback +lane/spec_ref/decided_gmt8;非回滚;旧行容错) + 状态机 + 接口(mark/promote/--from-queue) + 硬规则兜底 + 复用组件清单 + 测试策略(红线随层)

## S3 tasks
- [x] S3.1 tasks.md 实施任务：排序 L0决策→L1数据模型→L2接口→L3用户可见→L4内部逻辑→L5机械/集成;红线逻辑(状态机/lane/契约扫描/兜底)测试随层编织;每条映射 requirements(R…) + 可回滚性 + G门

## S4 结构注册
- [x] S4.1 structure.md：spec 边界表 +self-iterate-ops(标🔧"工具·流程spec,非产品功能") + 标题"六个 Spec(5产品+1工具)" + tree + 依赖说明(解耦产品线)
- [x] S4.2 README「快速导航」+条目 + "五个产品spec+self-iterate-ops🔧" + "6 spec三件套(5产品+1工具)"

## S5 校验收尾
- [x] S5.1 一致性自查：三件套齐全 · requirements 1.1–6.5 完整 · tasks 13 个 R 引用全命中 · ADR-1~4(D-a~D-d)完整 · EARS 27 处
- [x] S5.2 pytest **188** 无倒退(零代码) + 提交 PR + 创建 STOP

## [生产写操作门 G]
- 无(纯文档)。实现代码留后续独立 goal。
