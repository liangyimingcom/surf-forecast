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

## Deviations

> 格式：日期 / 触发情况 / 计划原文 / 实际做法（保守选项）/ 理由

（暂无）

## Open Questions（不阻塞开工）

- Vue 3 vs React：计划采用 Vue 3，可逆，P2 开工前最终确认。
- 匿名态 `/api/accuracy/vote` 去重策略（设备指纹 vs 放任）：P1 实现时定，默认放任（保守）。
- 更新日志入口最终位置（页脚 vs 详情页底）：视觉稿阶段定，默认页脚（保守）。
