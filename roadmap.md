# Roadmap — self-iterate-ops spec（可审物，零代码）

单一驱动器(auto-nudge,禁 task_run)。纯文档产出;不改运行时/不碰生产。每轮据实勾选。

## S1 requirements.md
- 摸底既有 spec 的 requirements 写法(EARS/编号/验收)对齐风格。
- 用户故事：终端用户提建议 / 人工每日 triage 审阅 / accepted 按风险分流 / AI 出 draft PR / 人主导发布 / 审计追溯。
- 验收标准(EARS)；把 v5 红线(人主导·去无人值守·硬规则兜底·非回滚·单驱动)写成**约束性需求**。

## S2 design.md
- 架构总览：收编 v5 G1-G5;数据流(建议→审阅→分流→PR→发布→审计);与产品 5-spec 的边界(工具≠产品功能)。
- **ADR（L0 决策，附推荐值+备选，待人批）**：D-a 分流硬规则清单 / D-b 升格 spec 映射 / D-c lane 记录方式 / D-d triage 渠道。
- 数据模型：feedback 需求对象(+lane/spec_ref/decided_gmt8;非回滚;读路径容忍旧行缺字段)。
- 接口：review_queue(promote/mark) / req_pipeline(--from-queue,lane-aware) / 每日 cron。
- 复用清单：review_queue.py/req_pipeline.py/audit_trace.py/tools/crons/surf_triage.py(已建)。

## S3 tasks.md
- 实施任务排序(决策优先):L0决策 → L1数据模型/契约 → L2新接口 → L3用户可见 → L4内部逻辑(硬规则兜底) → L5机械/测试。
- **红线逻辑(lane判定/兜底)测试随层编织,不推迟 L5**(执行注意 2)。
- 每条任务映射 requirements 编号 + 标可回滚性。

## S4 结构注册
- `structure.md` spec 边界表 +self-iterate-ops(标"工具/流程 spec");README「快速导航」+条目;根 roadmap/README 提及。

## S5 一致性校验 + 收尾
- 三件套交叉引用/EARS 格式/ADR 完整性自查;pytest 188 无倒退(零代码);创建 STOP。

## [生产写操作门 G]
- 无。本 goal 纯文档。实现 self-iterate-ops 的代码 = 后续独立 goal，且真发布仍留 G 门。
