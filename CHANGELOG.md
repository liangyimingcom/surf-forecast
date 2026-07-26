# CHANGELOG — surf-forecast

> 审计链：版本tag ↔ commit ↔ 部署时间 ↔ 变更摘要 ↔ 结果。全程 GMT+8。
> 每次 `deploy.sh frontend` 成功发布后自动追加一行（Phase 0 地基）。
> 格式：`YYYY-MM-DD HH:MM GMT+8 · vX.Y.Z · <commit> · <摘要> · <结果>`

## Releases
- 2026-07-26 · v0.1.0 · (genesis) · 引入版本化发布地基(不可变镜像tag/CHANGELOG/rollback/金丝雀) · 建立基线
- 2026-07-26 13:25 GMT+8 · v0.1.0 · e86f264 · G.1 首个版本化镜像发布(v0.1.0 双tag) + 滚动部署 · 已滚动
- 2026-07-26 13:30 GMT+8 · v0.1.0 · e86f264 · canary@https://d2hmhl7n8yga53.cloudfront.net · 通过
- 2026-07-26 13:31 GMT+8 · v0.1.0 · e86f264 · G.2 回滚演练：ECS 钉到不可变 :v0.1.0(task def:7) · 已切换
