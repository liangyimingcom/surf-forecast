# Requirements — Surf Forecast Analyzer（v2 引擎）

> EARS 格式。分析引擎是 Web 站与校验机制的共享后端模块。
> 质量基准：reference/reports/v2-report-golden-sample.md；事实红线：fact-check-comparison.md。

## 文档目的

定义引擎能力：输入坐标+天数，输出逐日深度分析（评分、物理、风向、行动方案）的结构化数据/Markdown。v2 相对 v1 新增：双周期口径、离岸风编码、GMT+8 强制、历史回算模式。

## 1. 数据获取

**1.1** WHEN 给定 (lat, lon, days)，THE SYSTEM SHALL 从 Open-Meteo marine(`ecmwf_wam025`) 取浪高、浪向、平均周期 Tm、谱峰周期 Tp。

**1.2** THE SYSTEM SHALL 从 best_match 取涌浪/风浪分区、海面高度、SST，从 `ecmwf_ifs025` 取风速/风向/阵风（单位节）。

**1.3** THE SYSTEM SHALL 全部请求带 `timezone=Asia/Shanghai`，3 小时分辨率。

**1.4** WHEN 需要历史浪报，THE SYSTEM SHALL 用 `past_days=N` 取历史回算数据，字段口径与预报完全一致。

**1.5** IF 请求失败或字段空，THEN THE SYSTEM SHALL 报告失败并标注受影响字段，WAM 缺分区时回退 best_match 并记录来源。

## 2. 数据校验（事实红线自动化）

**2.1** THE SYSTEM SHALL 用 GMT+8 日历计算星期/今天/昨天，禁止人工输入。

**2.2** THE SYSTEM SHALL 校验潮型与月相自洽（朔望=大潮），潮差量级符合海域，偏差超 2 倍发警告。

**2.3** WHEN 报告引用周期值，THE SYSTEM SHALL 确保等于实际 Tm 或 Tp 并标注口径。

**2.4** WHILE 生成物理叙事（先行波/频散等），THE SYSTEM SHALL 校验依赖的数据条件当日成立，否则不生成。

**2.5** THE SYSTEM SHALL 对 D+5+ 标注可信度降级 ±30%。

**2.6** THE SYSTEM SHALL 校验历史区与预报区日期不重叠。

## 3. 评分与风向

**3.1** THE SYSTEM SHALL 对每个白天时段计算浪高、周期、风况、纯度、潮汐五项分项评分（0-10）。

**3.2** THE SYSTEM SHALL 按 thresholds.yaml 权重计算综合分，权重可配置。

**3.3** THE SYSTEM SHALL 仅评估白天（日出-日落）时段。

**3.4** THE SYSTEM SHALL 标注短板参数（最低分项）。

**3.5** THE SYSTEM SHALL 按浪点朝向 `spot_facing_deg` 把每个时段风分类为 offshore/cross/onshore，并据此调整风况评分（离岸放宽一档）。

**3.6** WHEN 综合分接近，THE SYSTEM SHALL 质量参数（纯度/风）优先于数量参数（浪高）排序，并在叙事中解释。

## 4. 逐日分析输出

**4.1** 每天 SHALL 产出：原始数据表、潮汐、浪高/纯度/周期/风况/潮汐五段分析、实战行动方案。

**4.2** 每参数分析 SHALL 含阈值标准、当日数据、对冲浪的具体影响。

**4.3** 周期分析 SHALL 含波长/能量换算、跨日对比、对起乘/骑乘影响、Tm/Tp 双口径。

**4.4** 风况分析 SHALL 含风速时间线 + 离岸/向岸判定 + 对浪面影响。

**4.5** 行动方案 SHALL 落到时间表、板型、装备、时长。

## 5. 渲染输出

**5.1** THE SYSTEM SHALL 输出结构化 JSON（供 Web 前端，形状对齐 DATA CONTRACT）与/或 Markdown（CLI）。

**5.2** THE SYSTEM SHALL 输出排名（综合分降序，星期正确）、逐日分析、7 日总结（生命周期、公式、排名解释）。

**5.3** THE SYSTEM SHALL 在头部输出可信度声明（来源、星期/月相核验、GMT+8 校准时间戳、中期预报降级）。

## 6. 配置可移植

**6.1** THE SYSTEM SHALL 从 thresholds.yaml 读全部阈值/权重/`spot_facing_deg`，不硬编码。

**6.2** WHERE 非黄海海域，THE SYSTEM SHALL 应用对应阈值配置。

## 验收标准

| # | 标准 |
|---|------|
| A1 | 每天六段分析+行动方案齐全 |
| A2 | 星期/今天/昨天 GMT+8 计算正确 |
| A3 | 潮型↔月相自洽 |
| A4 | 周期口径标注且与数据一致 |
| A5 | 无虚构物理叙事 |
| A6 | 每时段 offshore/onshore 判定正确（山东头 157°） |
| A7 | 评分排序与权重一致、可复算 |
| A8 | 改 yaml 改结果，代码不变 |
| A9 | 历史模式与预报口径一致、日期不重叠 |
