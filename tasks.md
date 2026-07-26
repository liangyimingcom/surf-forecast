# Tasks — surf-report-web 韧性与契约

> 单一驱动器(auto-nudge,禁 task_run)。改前 codelens-dev 摸底+爆炸半径+守红线;改后 pytest/E2E/bash -n。
> 排序:契约→用户可见→内部→测试(红线逻辑测试随层)。真部署留 G 门。全程 GMT+8;据实勾选。
> 基线：pytest 188 · 冻结E2E 64/0 · master f450e13 · 生产 v0.1.1。

## R0 摸底
- [x] R0.1 codelens 摸底完成：render_json 形状(顶层 spot/coord/spotFacingDeg/calibratedAt/ranking/days[]/story/history/lifecycle/confidenceNotes;days 经 _day_to_dict) · 上游 cli/app.report/deps.get_report/get_history/refresh · **已有契约测试**(test_render contract_keys/chart_numeric/wdeg_redline/dual_period + test_cache_read/test_spots_cache 缓存命中未命中) · 缓存=deps._cache_reader/_writer(S3 latest.json,SF_CACHE_BUCKET,无进程TTL)→3.1 为新增 TTL 层 · loadLive 已有回退内嵌(但不提示,W2 补友好态)

## W1 · 0.2 数据契约（最先，最可能调整）
- [x] W1.1 `web/report.schema.json`：REPORT 契约(days非空/wdeg+times/hs/wind/gust/tp 数字数组/tp2 num-null/tideEvents [时,位]/calibratedAt GMT+8/date YYYY-MM-DD/history 互斥) JSON Schema draft-07 单一真相源 _(R2.4)_
- [x] W1.2 `tools/validate_report.py`(stdlib,无jsonschema依赖) enforce 红线子集 + `tests/test_report_schema.py` 10 用例(真实 render_json 过校验 + 缺wdeg/字符串/长度/GMT+8/空days/tideEvents/best计数/历史重叠 双侧钉死)。pytest 188→**198**

## W2 · 3.2 故障降级不白屏（用户可见）
- [x] W2.1 后端确认 cache-first + 失败干净 502（cache命中即服务/未命中才失败）;补 502 降级单测(DataSourceError→502可读detail;history 同) _(R4.3)_
- [x] W2.2 前端 loadLive 失败→**可见降级 banner** #sfDegraded(示例数据非实时+重试) + metaCalib 诚实标注「⚠️示例数据」;成功隐藏;retryLive();非白屏(不再静默展示旧样本) _(W8)_
- [x] W2.3 [随层测试] 后端 502 单测×2 + 前端 degraded_probe.mjs 3/3(拦 /api/report→非白屏+banner可见+诚实标注) + 冻结 E2E 64/0 无倒退。pytest 198→**200**

## W3 · 3.1 cache.py TTL（内部）
- [x] W3.1 `src/web/cache.py` TTLCache(进程内 TTL+LRU,注入时钟,ttl<=0停用) + 接线 deps.get_report/get_history memo(默认 SF_REPORT_TTL/SF_HISTORY_TTL=0 停用,env开启);**纯性能层键=查询参数不碰可见性**(冷点炸弹红线) _(R4.1,4.2)_
- [x] W3.2 `tests/test_cache.py` 9 用例:TTL命中/age==ttl过期(双侧钉死+mutation)/LRU淘汰刷新/停用/get_report memo(TTL内只算一次·过期重算·默认停用)。pytest 200→**209** 无倒退

## W4 · 收尾
- [x] W4.1 全量 pytest **209** + 冻结 E2E **64/0** + schema 校验器 CLI「✅合乎契约」+ bash -n OK；提交 PR + STOP

## [生产写操作门 G]
- [x] G.1 真部署 v0.1.2:td:9滚动COMPLETED+生产金丝雀64/0+git tag v0.1.2+CHANGELOG(2026-07-26)
