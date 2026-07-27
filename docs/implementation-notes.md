# Implementation Notes — 页面重规划（Fable5 计划）

计划文档：`docs/Fable5实施计划.html`（决策依据：`docs/Fable5迭代建议.md`）

**执行约定**：遇到边缘情况迫使偏离计划时，选**保守选项**（改动面最小、可逆性最高），
记录在下方 Deviations，然后继续推进，不停下等确认。每阶段完成在 Progress 记一行验收结果。

## Progress

| 日期 | 阶段 | 结果 |
|------|------|------|
| 2026-07-27 | 计划制定 | 八项决策确认，实施计划与本文件建立。未开工。 |
| 2026-07-27 | R0 摸底 | 结构注入点定位：#gate(462)/demoAuth(1003)/surf2026/SAMPLE_NEWS(1257)·CARPOOL(1308)·ADS(1333)/ANNOUNCEMENTS(2232) 待删；后端 catalog_scores(app.py:206) 需登录=伪门禁；recommend 数据源=评分缓存。 |
| 2026-07-27 | R0.2 降级态根因 | **每日刷新未覆盖全部浪点**：S3 latest.json 分布 07-27仅3点/07-25共47点(两天前)/6点无缓存(52<58)。首屏 recommend 现只能拿两天前分→冲浪预报失效。结论：刷新覆盖修复属 deployment-and-ops/EventBridge(真基建·G门)，与前端重建解耦；recommend 必须只排当日新鲜点+显式降级(degraded:bool 设计已预埋)。缓存管线本身健康(02:00 GMT+8 跑过)，问题在覆盖预算而非管线死。 |
| 2026-07-27 | P1 后端契约 | recommend/regions公开(只排新鲜点·诚实降级) + render_json动态checklist/disclaimer(清青岛硬编码) + flags会员锁+member_gate + 微信占位501 + User可空字段 + report.schema同步。pytest→264。 |
| 2026-07-27 | P2 脚手架+build | Vite+Vue3+Router+Pinia(web/frontend) + 后端SF_SPA_DIST门控服build/+SPA回退 + Dockerfile Node stage + charts.js忠实移植+ChartBox.vue(零依赖SVG)。 |
| 2026-07-27 | P3 目录页 | SpotsPage(区域/搜索/评分徽标/收藏/仅直播) + catalog/scores改公开(Fable5§2.2)。Leaflet地图待补。 |
| 2026-07-27 | P4 详情页 | report/history改member_gate分层 + SpotPage(日期条/日卡五维/ChartBox三图/物理/行动/小白高手模式/回看自评/偏差校准) + 直播占位(守cams合规红线,不暴露逆向流)。 |
| 2026-07-27 | P5 首页 | HomePage决策助手(首访引导+一屏答案+亚军≤2+三渐进入口+降级态显式)。 |
| 2026-07-27 | P6 会员锁占位 | App loadFlags + LockBadge(就位开关控,一期隐藏) + 微信占位弹层。真拦截在后端member_gate。 |
| 2026-07-27 | P7/P8 | Vue站干净(旧HTML P9兜底/归档) + 新E2E vue_spa.mjs 19/19(抓修P5 computed未import bug)=切/前置门。 |
| 2026-07-27 | P9 切换+冻结 | Dockerfile默认服Vue(SF_SPA_DIST,单HTML兜底) + self-iterate冻结ADR-9/稳定后重定义ADR-10。 |
| 2026-07-27 | P10 收尾 | pytest 267 · Vue E2E 19/0 · 冻结单HTML E2E 50/0(双前端并存) · 文档回写。剩 G门真部署 v0.2.0。 |

## Deviations

> 格式：日期 / 触发情况 / 计划原文 / 实际做法（保守选项）/ 理由

（暂无）

## Open Questions（不阻塞开工）

- Vue 3 vs React：计划采用 Vue 3，可逆，P2 开工前最终确认。
- 匿名态 `/api/accuracy/vote` 去重策略（设备指纹 vs 放任）：P1 实现时定，默认放任（保守）。
- 更新日志入口最终位置（页脚 vs 详情页底）：视觉稿阶段定，默认页脚（保守）。
