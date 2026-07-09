# Design — Forecast Accuracy Feedback（v2）

> 回应 requirements.md。MVP 已在 web/浪报MVP.html 落地（renderVerify/rateYesterday/HISTORY）；本设计正式化 + 后端持久化 + 校准。

## 1. 数据流

```
引擎(past_days=1) → HISTORY(JSON, 同预报口径) → 前端 renderVerify 展示昨日预报+图表
用户点四档 → rateYesterday 即时反馈 → [登录] POST /api/accuracy/vote → DB
累积 votes → 偏差分析 → 后续预报附"体感校准提示"
```

## 2. 昨日数据（HISTORY）

引擎历史模式产出，形状 = 前端 DAYS[i] + `predict{}`：

```js
HISTORY = {
  id,date,week,score,scoreWord,tag, windows[], times[],
  hs[],swell[],tp[],tp2[],wind[],gust[],wdeg[],   // 与预报同口径，含风向
  tideEvents[],tideText, dims{}, pa[],
  predict:{ height,period,wind,best,board,verdict } // 系统当时对昨日的判断，供对照
}
```

`date` 由后端按 GMT+8 计算 = today−1（需求 1.4 / F1）。

## 3. 前端（已实现，待接后端）

- `renderVerify()`：渲染昨日卡（综合分徽章 + 系统预报判断 `predict` + 自评按钮 + 高手模式下的五维/双周期图/离岸风况图/分参数解读）。
- `rateYesterday(kind)`：四档→即时彩色反馈文案（accurate/optimistic/conservative/noidea）。
- 位置：在 `<main id="cards">`（预报）**之后**渲染（需求 4.1 / F7）。
- 复用预报的 `waveChart/windTideChart/windQualityStrip/waveLegend`，保证 F2 口径一致。

待接后端：`rateYesterday` 在登录态下额外 `POST /api/accuracy/vote`。

## 4. 后端（src/web/，与 web spec 共库）

```
history.py   GET /api/report/history → 引擎 past_days=1 → HISTORY(含 predict)
feedback.py  POST /api/accuracy/vote {spot,date,kind} → accuracy_votes 表
             GET  /api/accuracy/bias?spot → 偏差倾向 + 校准建议
```

DB 表 `accuracy_votes(user_id, spot, date, kind, created_at_gmt8)`。

## 5. 偏差校准（需求 3）

```
votes(spot, last N) → 统计 optimistic/conservative/accurate 占比
  若 optimistic 占多 → bias="偏乐观" → 建议"预期下调半档"
  若 conservative 占多 → bias="偏保守" → 建议"可上调半档"
  否则 → "标定可信"
```
仅作**提示**附加在预报旁，**不修改 DailyAnalysis.composite**（需求 3.3 / F6，保持数据诚实）。

## 6. 测试

| 测试 | F |
|------|---|
| test_history_date（today−1, 不与预报重叠, GMT+8） | F1 |
| test_history_parity（与预报同评分/图表函数） | F2 |
| test_predict_present | F3 |
| test_vote_feedback（四档文案） | F4 |
| test_vote_persist（含 GMT+8 时间） | F5 |
| test_bias（≥N 条出建议、不改原分） | F6 |
| test_placement（verify 在 cards 之后 DOM 序） | F7 |

## ADR
- ADR-F1 历史回算复用引擎同一管线（仅 past_days），口径一致是校验有效的前提。
- ADR-F2 校准只提示不篡改原评分——数据诚实优先于"显得更准"。
- ADR-F3 昨日回看置于预报之后——信任工具不抢主信息首屏。
- ADR-F4 自评先做前端即时反馈（无需登录即有价值），登录才持久化与校准。
