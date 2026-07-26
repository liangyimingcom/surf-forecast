# Roadmap — surf-report-web 韧性与契约

单一驱动器(auto-nudge,禁 task_run)。每轮先 codelens-dev 摸底+爆炸半径+守红线,改后 pytest/E2E/bash -n。
排序:契约(最可能调整)→用户可见降级→内部cache→测试随层。真部署留 G 门。

## R0 摸底（codelens-dev SOP）
- explain_code/find_symbol：render_json 输出形状 / get_report(deps) 数据流 / 前端 loadLive 降级现状 / cache 现状(SF_CACHE_BUCKET flag)。
- get_impact/find_affected_tests：改 render/缓存的爆炸半径 + 受影响测试。find_route：/api/report、/api/report/history 契约。

## W1 · 0.2 数据契约（最先，最可能调整）
- 抽 DAYS/HISTORY/REPORT 形状 → `web/report.schema.json`（JSON Schema，含 wdeg/tp2/tideEvents/times/windows/hs/wind/gust 数字字段、GMT+8 日期约束）。
- 校验脚本(纯node或python stdlib)：对一份真实 render_json 校验合乎 schema，防契约漂移。

## W2 · 3.2 故障降级不白屏（用户可见）
- 后端：Open-Meteo 取数异常时的降级策略（现状 502）——保留可读错误 + 若有缓存回退缓存。
- 前端：loadLive 失败已回退内嵌；强化为**友好态提示 + 不 NaN 图表 + 校准时间戳诚实标注**（数据来源/降级说明）。
- [随层测试] 模拟取数失败 → 前端有内容非白屏；后端降级路径单测。

## W3 · 3.1 cache.py TTL（内部）
- cache.py：预报短 TTL / 历史长缓存；`SF_CACHE_BUCKET` 特性开关；**可见性不耦合成本**（冷点炸弹红线）。
- [随层测试] test_cache：TTL 命中/过期**边界双侧钉死** + mutation(改 TTL±1 或比较符须变红)。

## W4 · 收尾
- 全量 pytest + 冻结 E2E 64/0 + schema 校验 + bash -n；据实勾选;创建 STOP。

## [生产写操作门 G]（停下发 blocker 等人工确认）
- G.1 真部署(build+redeploy+canary 64/0 + git tag + CHANGELOG)——含数据/缓存改动上线。
