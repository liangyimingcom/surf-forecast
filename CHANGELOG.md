# CHANGELOG — surf-forecast

> 审计链：版本tag ↔ commit ↔ 部署时间 ↔ 变更摘要 ↔ 结果。全程 GMT+8。
> 每次 `deploy.sh frontend` 成功发布后自动追加一行（Phase 0 地基）。
> 格式：`YYYY-MM-DD HH:MM GMT+8 · vX.Y.Z · <commit> · <摘要> · <结果>`

## Releases
- 2026-07-26 · v0.1.0 · (genesis) · 引入版本化发布地基(不可变镜像tag/CHANGELOG/rollback/金丝雀) · 建立基线
- 2026-07-26 13:25 GMT+8 · v0.1.0 · e86f264 · G.1 首个版本化镜像发布(v0.1.0 双tag) + 滚动部署 · 已滚动
- 2026-07-26 13:30 GMT+8 · v0.1.0 · e86f264 · canary@https://d2hmhl7n8yga53.cloudfront.net · 通过
- 2026-07-26 13:31 GMT+8 · v0.1.0 · e86f264 · G.2 回滚演练：ECS 钉到不可变 :v0.1.0(task def:7) · 已切换
- 2026-07-26 16:52 GMT+8 · v0.1.1 · 609196c · 需求seed-0001: 直播免责文案补充 + 自迭代闭环 E/B/D 上线(feedback落库/澄清UI/更新日志/pipeline/审计链) · 已滚动部署(taskdef:8)
- 2026-07-26 16:52 GMT+8 · v0.1.1 · 609196c · canary@https://d2hmhl7n8yga53.cloudfront.net 冻结E2E 64/0 · 通过
- 2026-07-26 17:00 GMT+8 · v0.1.1 · 2906f5a · G.B1: 生产建 surf-forecast-dev-feedback 表(TTL expiresAt)+任务角色补授+/api/feedback 上线 · 端到端通过
- 2026-07-26 19:43 GMT+8 · v0.1.2 · 8ed5617 · surf-report-web 韧性与契约(report.schema/故障降级不白屏/cache TTL) + accuracy-feedback(rateYesterday上报) · 已滚动部署(taskdef:9)
- 2026-07-26 19:43 GMT+8 · v0.1.2 · 8ed5617 · canary@https://d2hmhl7n8yga53.cloudfront.net 冻结E2E 64/0 · 通过
- 2026-07-26 22:15 GMT+8 · v0.1.3 · 48dd878 · 前端提速(report+history并行/客户端会话缓存秒开) + 后端TTL memo(SF_REPORT_TTL=900/SF_HISTORY_TTL=21600) · 已滚动部署(taskdef:10)
- 2026-07-26 22:15 GMT+8 · v0.1.3 · 48dd878 · canary@生产 冻结E2E 64/0 + TTL重复请求0.82→0.69s · 通过
- 2026-07-26 23:42 GMT+8 · v0.1.4 · 68f65c8 · 在线LLM澄清真接入(Secrets注入SF_LLM_KEY+ECS执行角色授权;/api/clarify source=llm)+LLM coder · 已滚动部署(taskdef:11) · **开始LLM计费**
- 2026-07-26 23:42 GMT+8 · v0.1.4 · 68f65c8 · canary@生产 冻结E2E 64/0 + /api/clarify 真调LLM返回页面感知选项 · 通过
- 2026-07-27 01:17 GMT+8 · v0.1.5 · c790858 · 提建议第3步 LLM 页面感知多选(与手动并存) · 已部署(taskdef:12,补tag)
- 2026-07-27 01:17 GMT+8 · v0.1.6 · 0098166 · 修缓存显示(澄清增强接受source=cache,每次都显chips) · 已滚动部署(taskdef:13)+金丝雀64/0
- 2026-07-27 12:10 GMT+8 · v0.2.0 · 340ee97 · 甲·Vite+Vue3决策助手整体重建(3路由页+后端契约重塑+诚实分层鉴权+会员锁占位+图表组件化);SF_SPA_DIST默认服Vue;REFRESH_BUDGET 50→80 · 已滚动部署(taskdef:14)·金丝雀vue_spa 19/0·刷新scheduler→:14
