# Design — Surf Forecast Analyzer（v2 引擎）

> 回应 requirements.md。当前 `src/surf_forecast/physics.py` 已实现（含风向判定），余为脚手架。

## 1. 管线

```
fetch(+past_days) → models(校验) → analyze(评分+风向+短板) → validate(事实自检) → render(JSON/MD)
                                         ↓                ↓
                                   scoring/physics   thresholds.yaml
```

计算/叙事分离；评分、物理、风向是纯函数。

## 2. 数据模型（models.py，pydantic v2）

```python
class WindKind(str,Enum): OFFSHORE="off"; CROSS="cross"; ONSHORE="on"

class ForecastPoint(BaseModel):
    time: datetime              # GMT+8
    wave_height_m, wave_direction_deg
    wave_period_mean_s          # Tm
    wave_period_peak_s | None   # Tp
    swell_height_m, swell_direction_deg
    wind_wave_height_m
    wind_speed_kn, wind_direction_deg, wind_gust_kn
    sea_level_m, sst_c
    source: str; confidence: Confidence
    @property swell_purity, gust_ratio
    def wind_kind(self, spot_facing_deg) -> WindKind   # 离岸/侧岸/向岸

class DailyForecast: date, weekday(GMT+8派生只读), points[], tide_extremes[],
                     sunrise, sunset, moon_phase, is_midrange
class ParamScore: name, score(0-10), grade, note
class DailyAnalysis: forecast, scores{}, composite, weakest_param,
                     best_window, board, recommendation, dawn_wind_kind, confidence_notes[]
class ReportContext: spot, coord, calibrated_at(GMT+8), days[], history|None, ranking[], lifecycle
```

## 3. fetch.py（需求 1.x）

三路调用按 time 对齐；`past_days` 支持历史；WAM 缺分区回退 best_match；失败抛 DataSourceError 标注字段。

## 4. physics.py（已实现）

`wavelength / group_velocity / energy_index / nearshore_height / swell_purity / direction_16 / is_onshore / is_dispersion_rising`。
v2 风向判定 `wind_kind(deg, facing)` 返回 off/cross/on（diff<60 on, >120 off）。

## 5. scoring.py（需求 3.x）

每项 `score_x(value, thresholds, ctx) -> ParamScore`。`score_wind` 接收风向，offshore 放宽一档。`composite_score` 加权；`weakest`；`rank_days`（并列质量优先）。

## 6. validate.py（需求 2.x，红线自动化）

`verify_weekday_gmt8 / moon_age / verify_tide_vs_moon / verify_period_citation / verify_narrative_support / flag_gust_anomaly / tag_midrange_confidence / verify_history_forecast_disjoint`。ERROR 阻断，WARNING 入声明。

## 7. render.py（需求 4/5）

从 DailyAnalysis 套模板出 JSON（Web）或 Markdown（CLI）。叙事段先过 `verify_narrative_support`。JSON 形状 = 前端 DAYS/HISTORY/REPORT 契约。

## 8. DATA CONTRACT（与前端对齐）

```
DailyAnalysis(JSON) ≈ 前端 DAYS[i]:
{ id,date,week,today,score,stars,tag,phase,dawnWind,window,windows[],board,level,
  novice, times[],hs[],swell[],tp[],tp2[],wind[],gust[],wdeg[],   # wdeg 供风向编码
  tideEvents[],tideText, dims{}, pa[], lesson[], plan[], safety[] }
HISTORY = 同形状 + predict{} （昨日预报判断，供校验对照）
```
> 关键：前端图表已消费 `wdeg`（风向度）做离岸编码；引擎 JSON 必须输出 wdeg。

## 9. CLI（cli.py）

`--lat --lon --days --spot --out --style --config [--past-days]`。

## 10. 测试

| 测试 | AC |
|------|----|
| test_physics（含 wind_kind 157°判定） | A6 |
| test_scoring（阈值/权重/排序/短板/离岸放宽） | A7 |
| test_validate（星期GMT+8/月相/周期/历史互斥） | A2,3,4,9 |
| test_narrative（虚构拦截） | A5 |
| test_config | A8 |
| test_golden（复现 6/24 王者、离岸判定、6/19历史） | A1,A6 |

## ADR

- ADR-1 Open-Meteo 非爬 Windy。
- ADR-2 计算/叙事分离。
- ADR-3 校验独立成关、可阻断。
- ADR-4 双周期口径强制标注。
- ADR-5 阈值全配置（含 spot_facing_deg）。
- **ADR-6（v2）风向 wind_kind 作为评分输入与 JSON 输出字段（wdeg），离岸风一等公民。**
- **ADR-7（v2）历史回算复用同一管线，仅 past_days 不同，保证口径一致以支撑校验。**
