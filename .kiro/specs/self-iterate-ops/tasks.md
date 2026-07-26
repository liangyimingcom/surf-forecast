# Tasks — Self-Iterate Ops（实施任务，人主导）

> 对应 requirements.md / design.md。排序原则：**最可能调整的决策在前**（L0决策 → L1数据模型 → L2接口 → L3用户可见 → L4内部逻辑），**机械/纯集成测试垫底（L5）**；但**红线逻辑（lane判定/契约扫描/兜底）测试随层编织**（执行注意 2）。
> 每条标映射 requirements 编号 + 可回滚性。真发布留生产写操作门 G。单一驱动器。
> 状态：本 spec 为**规格**，以下 tasks 为后续实现 goal 的蓝图，当前均未实现。

## L0 · 决策（动手前经评审拍板；对应 design §7 ADR）
- [x] L0.1 ADR-1 契约关键字黑名单=§4.3列表（D-a，已定案）_(R4.3, R6.4)_
- [x] L0.2 ADR-2 升格=promote→目标产品spec tasks一条新task引用feedback id（D-b，已定案）_(R3.2)_
- [x] L0.3 ADR-3 lane 落 feedback 字段（D-c，已定案）_(R3.1)_
- [x] L0.4 ADR-4 triage 渠道=dashboard-only（D-d，已定案）_(R2.1)_

## L1 · 数据模型 / 契约（非回滚；旧行容错）
- [ ] L1.1 feedback 需求对象扩展 `lane`/`spec_ref`/`decided_gmt8`；写入 `_to_decimal`，读路径缺字段默认值 _(R6.3, R3.1)_ · 可回滚性=否(动数据契约)
- [ ] L1.2 requirement-schema.md 同步字段 + 状态机补 `in_progress`/`promoted`（promoted 永不 TTL）_(R2.4, R3.2)_
- [ ] L1.3 [随层测试] status 状态机 + TTL(仅new/rejected) + promoted 免删 单测(双侧钉死) _(R2.4)_

## L2 · 新接口（向后兼容）
- [ ] L2.1 review_queue `mark <id> --lane direct` + `promote <id> --spec <name>`(写 lane/spec_ref/decided_gmt8;promote→status=promoted) _(R3.1, R3.2)_
- [ ] L2.2 req_pipeline `--from-queue <id>`(读生产 accepted+lane=direct;取代 seed json 入口;lane-aware) _(R4.1)_
- [ ] L2.3 [随层测试] mark/promote 状态流转 + --from-queue 读取(内存 store) 单测 _(R3.1)_

## L3 · 用户可见（低优先）
- [ ] L3.1 认领码 track 状态文案扩展(已受理/已升格排期/已上线;复用 GET /api/feedback/track) _(R5.5, R1.4)_

## L4 · 内部逻辑（硬规则兜底）
- [ ] L4.1 req_pipeline 新增契约关键字扫描门(ADR-1 清单);direct diff 命中/超白名单/碰 web-e2e → 强制退回 promote + 通知 _(R3.4, R4.3, R4.4)_ · 可回滚性=是(纯逻辑)
- [ ] L4.2 [随层测试] 契约扫描/超白名单/删除/碰e2e → 退回 promote 单测(边界双侧钉死 + mutation：改比较符/清单±1 须变红) _(R3.4)_

## L5 · 机械 / 纯集成测试 / 收口
- [ ] L5.1 review_queue↔req_pipeline↔audit_trace 串联集成测试(内存 store,不碰生产) _(R5.3)_
- [ ] L5.2 文档收口(README/tools 说明) + tools/crons 镜像同步校验 + pytest 全绿不倒退

## [生产写操作门 G]（停下发 blocker 等人工确认）
- [ ] G.1 首条 direct 需求真出 draft PR(--create-pr) → 人审合
- [ ] G.2 人主导发布(build+redeploy+canary+git tag+CHANGELOG) + 需求 status=shipped
- [ ] G.3 L1.1 若上生产：feedback 新字段读写在生产验证(旧行容错)
