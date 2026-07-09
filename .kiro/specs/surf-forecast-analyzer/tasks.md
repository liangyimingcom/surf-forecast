# Tasks — Surf Forecast Analyzer（v2 引擎）

> Kiro 约定：一次一个任务，完成勾 [x]。标注满足的需求/AC。

## 阶段 0：脚手架（v1 已建，v2 沿用）
- [x] 0.1 目录结构、pyproject、physics.py（含 wind_kind 风向判定）
- [ ] 0.2 thresholds.yaml 增补 `spot_facing_deg`、离岸放宽档位

## 阶段 1：模型与配置
- [x] 1.1 models.py：WindKind 枚举、ForecastPoint(含 wind_kind 方法)、DailyForecast(weekday GMT+8 只读)、DailyAnalysis(含 dawn_wind_kind)、ReportContext(含 calibrated_at, history) _(R1.1,3.1)_ ✅ test_models 7 项通过
- [x] 1.2 load_thresholds 解析含 spot_facing_deg _(R6.1)_ ✅ 含 weights 合计校验

## 阶段 2：物理与评分
- [x] 2.1 physics.py 核心函数 + wind_kind/is_onshore _(R3.5;A6)_
- [x] 2.2 scoring.py：五项评分，score_wind 接收风向、离岸放宽一档；composite/weakest/rank _(R3.x;A7)_ ✅
- [x] 2.3 test_physics(风向157°判定) + test_scoring _(A6,A7)_ ✅ test_scoring 9 项通过

## 阶段 3：数据获取（含历史）
- [x] 3.1 fetch.py：三路 Open-Meteo + GMT+8 + 对齐合并 _(R1.1-1.3)_ ✅ build_daily_forecasts 纯函数
- [x] 3.2 past_days 历史模式，口径与预报一致 _(R1.4;A9)_ ✅ 同解析/合并路径
- [x] 3.3 字段回退、失败处理、潮汐极值提取 _(R1.5)_ ✅ WAM→best_match 回退 + DataSourceError + extract_tide_extremes ｜ test_fetch 9 项通过

## 阶段 4：校验关
- [x] 4.1 validate.py：verify_weekday_gmt8、月相↔潮型、周期口径、阵风异常、中期降级 _(R2.1-2.5;A2,3,4)_ ✅
- [x] 4.2 verify_narrative_support + verify_history_forecast_disjoint + validate_report 编排 _(R2.4,2.6;A5,A9)_ ✅
- [x] 4.3 test_validate + test_narrative _(A2-A5,A9)_ ✅ 12 项通过（含频散/先行波拦截、历史互斥阻断）

## 阶段 5：编排
- [x] 5.1 analyze.py：fetch→DailyForecast→评分+风向+短板+窗口+板型→DailyAnalysis→排名→生命周期 _(R3,R4.5)_ ✅ build_context 含 validate 守门
- [x] 5.2 白天时段过滤、dawn_wind_kind 计算 _(R3.3,3.5)_ ✅ test_analyze 6 项通过

## 阶段 6：渲染（JSON 契约 + MD）
- [x] 6.1 render.py：输出 JSON（形状=前端 DAYS/HISTORY，**含 wdeg**）+ Markdown _(R5.1;DATA CONTRACT)_ ✅ render_json 含 wdeg/tp/tp2/tideEvents/dims；**前端契约对齐修复（2026-06-25）**：times/windows([[起,止]])/tideEvents 全数字形（消除前端 SVG NaN/负宽）、dims 中文键、pa 三元组、lesson/plan [标题,正文]、best 标记王者日、story 数据驱动剧情 _(test_render 含契约守卫，91 passed)_
- [x] 6.2 叙事段过 verify_narrative_support；生命周期 ASCII/数据 _(R2.4,5.2)_ ✅ render_report 套 j2 + render_lifecycle_ascii
- [x] 6.3 可信度声明含 GMT+8 校准时间戳 _(R5.3)_ ✅ calibratedAt "YYYY-MM-DD HH:MM GMT+8" ｜ test_render 6 项通过

## 阶段 7：CLI 与端到端
- [x] 7.1 cli.py（含 --past-days） _(R1.4)_ ✅ 含 --format md|json，校验阻断返回码 2
- [x] 7.2 test_golden：复现 6/24 王者排名、各日离岸判定、6/19 历史口径一致 _(A1,A6,A9)_ ✅ 含 CLI JSON 端到端 wdeg
- [x] 7.3 test_config _(A8)_ ✅ 阈值驱动结果验证 ｜ 真实 Open-Meteo 端到端跑通(6日/含wdeg/过validate)

## 依赖
```
0.2→1.x→2.x─┐
        3.x─┼→5.x→6.x→7.x
        4.x─┘
```

## 完成定义
代码+单测通过+满足标注需求+对照 v2 黄金样本无质量倒退+不重现事实红线+JSON 含 wdeg 且与前端契约一致。
