---
inclusion: always
---

# Tech Steering — 技术栈与工程约定（v2）

## 架构总览

```
┌──────────────────────────┐
│ 前端 SPA（会员视图）        │  类 reference UI 黄金样本：门禁→查询→排名→逐日图表→昨日回看
│  单 HTML(MVP) → Vite 演进  │
└────────────┬─────────────┘
             │ HTTPS / JSON（DATA CONTRACT = 前端 DAYS/HISTORY 形状）
┌────────────▼─────────────┐
│ Web 后端 FastAPI          │  鉴权 / 会员 / 缓存 / 校验反馈存储 / 编排
└────────────┬─────────────┘
             │ import
┌────────────▼─────────────┐
│ surf_forecast 分析引擎     │  fetch → 评分 → validate → render(JSON)
└────────────┬─────────────┘
             │ REST（含 past_days 历史回算）
        Open-Meteo ECMWF WAM / IFS
```

## 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 分析引擎 | Python 3.11 + pydantic v2 | 强类型预报数据；纯函数评分易测 |
| Web 后端 | FastAPI | 同语言直接 import 引擎；自带 OpenAPI |
| 鉴权 | argon2 哈希 + httponly cookie / JWT | 防 XSS；前端零信任 |
| 数据库 | SQLite(MVP)→Postgres | 用户/会员/保存浪点/**校验反馈** |
| 缓存 | LRU(MVP)→Redis | 浪报 TTL；历史回算可长缓存 |
| 前端 | 单 HTML(当前MVP) → Vite+轻框架 | UI 已验证，渐进迁移 |
| 数据渲染 | 内联 SVG（无图表库） | 浪高柱/双周期线/风潮/生命周期全自绘，零依赖、可单测 |

## 数据源（关键决策）

**Open-Meteo**（同源 ECMWF，免 key，REST），不爬 Windy（JS 渲染不稳）。

三路 + 历史：
- 浪：`marine` `ecmwf_wam025` → `wave_height/direction/period/peak_period`
- 分区+海面+SST：`marine` best_match → `swell_*/wind_wave_height/sea_level_height_msl/sea_surface_temperature`
- 风：`forecast` `ecmwf_ifs025`（`wind_speed_unit=kn`）→ `wind_speed/direction/gusts_10m`
- **历史回算**：同接口加 `past_days=N`，用于昨日回看（见 forecast-accuracy-feedback spec）

## 时区与时间（v2 强化）

- **全程 Asia/Shanghai (GMT+8)**，所有 API 调用带 `timezone=Asia/Shanghai`。
- 报告/页面须显式标注**校准时间戳**（如 `校准 2026-06-20 北京时间 GMT+8`）。
- "今天/昨天/D+N" 一律按 GMT+8 日界计算，禁止用 UTC 推算星期（v1 星期错一天的教训）。

## 风向编码（v2 新增，一等公民）

```
浪点朝向 spot_facing（浪从该方向来，山东头≈157° SSE）
windKind(deg): diff = |((deg - facing + 180) mod 360) - 180|
  diff < 60  → onshore  向岸（吹乱，差）
  diff > 120 → offshore 离岸（梳面，最佳）
  else       → cross    侧岸（尚可）
风羽箭头指向风的“去向”=(来向+180)；离岸风箭头指向海面。
```

## 双周期口径

同时取 `wave_period`(Tm) 与 `wave_peak_period`(Tp)。报告/图表必须标注口径：橙实线=Tm，红虚线=Tp。二者物理意义不同，混用会误导。

## 物理公式（实现务必正确）

```
波长     L = 1.56 × T²          3.3s→17m, 6s→56m, 7s→76m
群速     Cg = g·T / (4π)        频散判据
能量     E ∝ H² × T
纯度     purity = swell_H / total_H
近岸     H_near ≈ H_off × 0.7~0.8
```

## 工程约定

1. **计算/叙事分离**：评分、物理、风向判定是纯函数；叙事在模板/前端，绝不进计算层。
2. **阈值全配置**：`config/thresholds.yaml`，不硬编码；跨海域换配置（含 `spot_facing_deg`）。
3. **可信度一等公民**：每数据点带 source/confidence；D+5+ 自动降级 ±30%。
4. **前端零信任**：鉴权只在后端，前端不含可绕过逻辑（当前 MVP 口令门禁仅占位）。
5. **DATA CONTRACT 锚点**：当前 HTML 的 `DAYS`/`HISTORY` 对象形状 = 后端 `/api/report` 与 `/api/report/history` 的返回形状。

## 验证纪律（自动化，来自历次教训）

- 星期/今天/昨天：GMT+8 日历计算，禁手填。
- 月相↔潮型自洽；潮差量级符合海域。
- 周期引用值=实际 Tm 或 Tp 且标注口径。
- 物理叙事须有当日数据支撑（禁止虚构"先行波"等）。
- 历史回看用真实回算数据；预报区与历史区不得日期重叠（同一天不能既预报又历史）。

## 运行（目标）

```bash
# 引擎
python -m surf_forecast.cli --lat 36.092 --lon 120.468 --days 6 --spot "青岛山东头" --out report.md
# Web
uvicorn web.app:app --reload
```
