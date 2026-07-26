# North Star — surf-forecast 发布地基 (Phase 0：版本化 / 回滚 / 可观测)

## 目标（唯一）
把 surf-forecast 的发布从"覆盖式 :latest + 无回滚 + 弱冒烟"升级为
**可版本化、可回滚、可观测**的发布地基——它是「用户建议自迭代闭环 v4」的一切前提。
详细设计见 `docs/自迭代闭环-设计与提示词-v4.md`（Phase 0 节 + 第六节待验证前提）。

## 为什么先做这个
- 现状 `deploy.sh` 只有 test/frontend/redeploy，构建**覆盖 :latest** → 旧镜像被覆盖 → **根本没有可回滚的产物**。
- 无 semver / 无 CHANGELOG / 无审计链 / 无真金丝雀（curl-200 抓不到"200 但白屏"）。
- 不修这层，后面的"无人值守自动上线 + 自动回滚"都是空中楼阁。

## 起点（已有，勿重复造）
- `deploy.sh`：test(pytest门) / frontend(t4g构建推:latest) / redeploy(ECS force-new)。
- 生产：ECS `surf-forecast-dev-cluster`/`surf-forecast-dev-svc`，ECR `surf-forecast-dev-backend`，
  CloudFront `d2hmhl7n8yga53`，profile `oversea1` 账号 153705321444 ap-northeast-1。
- 已有冻结基线 E2E：`web/e2e/new_features.mjs`（64 断言）+ pytest 147。

## 完成定义 (DoD)
1. **不可变版本 tag**：每次发布给 ECR 镜像打 `vX.Y.Z`（semver，patch 自增），`:latest` 仅指针；保留最近 10 版。
2. **审计链 + CHANGELOG**：`CHANGELOG.md` 每次发布追加「YYYY-MM-DD HH:MM GMT+8 · vX.Y.Z · commit · 变更摘要 · 结果」；版本tag↔commit↔CHANGELOG↔部署时间可回溯。
3. **`deploy.sh rollback`**：切回上一个版本镜像 tag + 记录 CHANGELOG（不重建）。
4. **真浏览器金丝雀**：部署后对**生产**跑冻结基线 E2E（`new_features.mjs`）+ 0 JS 报错；失败 → 自动 rollback 上一版本 + 告警。
5. **计数告警**：catalog/cams/report 关键端点计数跌 0 时告警（先做最简：脚本探测 + send_message/CloudWatch 二选一，能落地即可）。
6. pytest/E2E 零倒退；全程 GMT+8。

## 红线（不可违反）
- **单一驱动器**：只靠 dashboard auto-nudge 推进，**绝不调 task_run**。
- **生产写操作(打真 tag / 真部署 / 真回滚演练 / 建 CloudWatch 告警) 属高风险**：先本地实现 + dry-run 验证，
  **到真正触碰生产这一步发一次 blocker 停下等人工确认**，不在 loop 内自动推生产。
- 不跑 `terraform apply`（本 Phase 纯脚本/发布层，不动 IaC；如必须动基建则停下发 blocker）。
- 沿用既有红线：GMT+8 / DATA CONTRACT wdeg / float→Decimal / `/api/*` 全 401 /
  ALB SG 禁 0.0.0.0/0(仅 pl-58a04531) / terraform 禁 -auto-approve。
- 每轮改前用 skill `surf-forecast-codelens-dev` 摸底 + grep 实际文件确认现状；勾选须与文件一致，禁记未落地完成项。
- 改 `deploy.sh` 后必须能在**不触碰生产**前提下 dry-run 通过（bash -n + 逻辑走查 + 本地金丝雀脚本对 localhost 验证）。

## 停止条件
创建 `STOP_LOOP` 文件即停。到"生产写操作门"也停下等确认。
