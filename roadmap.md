# Roadmap — surf-forecast 发布地基 (Phase 0)

单一驱动器（dashboard auto-nudge）。每轮挑最高杠杆一步，改前先 grep/codelens 摸底，改后 dry-run 验证，
勾选须与文件一致。触碰生产的步骤停下发 blocker 等人工确认。

- **P0.0 前提探测（先做）**
  确认三项待验证前提（见 v4 文档第六节）：① 当前 frontend 构建是否覆盖 `:latest`（→无回滚物）
  ② ECR 现有镜像 tag 情况 ③ master 分支保护/自动合并策略。产出结论，据此定版本 tag 方案。
- **P0.1 版本号 + 不可变镜像 tag 方案**
  定 semver 来源（`VERSION` 文件或 git tag，patch 自增）；`deploy.sh frontend` 构建时**同时打 `:vX.Y.Z` 与 `:latest`**；
  保留最近 10 版清理策略。先实现 + dry-run，不推真镜像。
- **P0.2 CHANGELOG + 审计链**
  `CHANGELOG.md` 结构；`deploy.sh` 发布成功后自动追加「时间·版本·commit·摘要·结果」；版本↔commit↔时间可回溯。
- **P0.3 `deploy.sh rollback`**
  新增子命令：列可用版本 tag → 切 ECS 到上一个 `:vX.Y.Z`（不重建）→ 记 CHANGELOG。bash -n + 逻辑走查。
- **P0.4 真浏览器金丝雀 + 自动回滚**
  部署后对生产跑 `web/e2e/new_features.mjs` + 0 JS 报错；失败→自动 `rollback`。先对 localhost 验证脚本，再定生产接线。
- **P0.5 关键端点计数告警**
  catalog/cams/report 计数跌 0 告警（最简可落地：脚本 + send_message 或 CloudWatch，二选一）。
- **P0.6 验证 + 收尾**
  pytest/E2E 全绿零倒退；deploy.sh bash -n；本地金丝雀脚本跑通；README/文档更新；据实勾选。
- **[生产写操作门]** P0.1–P0.5 的"真打 tag / 真部署 / 真回滚演练 / 真建告警"统一在此停下，发一次 blocker 等人工确认后执行。
