# Tasks — Forecast Accuracy Feedback（v2）

> 前置：引擎历史模式(past_days)可用；web spec 鉴权与 DB 就绪（持久化部分）。
> MVP 前端已实现，本 spec 把它正式化并接后端。

## 阶段 0：MVP（已实现）
- [x] 0.1 renderVerify() 昨日卡 + 系统预报判断 predict 对照
- [x] 0.2 rateYesterday() 四档自评 + 即时针对性反馈
- [x] 0.3 复用预报图表函数渲染昨日（口径一致）
- [x] 0.4 昨日回看置于预报内容之后（非首屏）

## 阶段 1：历史数据正式化
- [x] 1.1 引擎/后端 history.py：past_days=1 取昨日，按 GMT+8 算 date=today−1 _(R1.1,1.4;F1)_ ✅ build_context include_history + deps.get_history
- [x] 1.2 HISTORY 含 predict{}（系统对昨日的预报判断） _(R1.3;F3)_ ✅ render._predict_from
- [x] 1.3 校验昨日口径与预报一致（同评分/图表/离岸编码） _(R1.2;F2)_ ✅ 同 analyze_day/render_json 管线 + validate 互斥
- [x] 1.4 test_history_date + test_history_parity + test_predict_present _(F1,F2,F3)_ ✅ test_golden 历史口径/互斥 + test_render predict

## 阶段 2：自评持久化
- [x] 2.1 GET /api/report/history 接口 _(R1)_ ✅ app.py（缓存优先+回退）
- [x] 2.2 POST /api/accuracy/vote → accuracy_votes 表（含 GMT+8 时间） _(R2.3;F5)_ ✅ feedback.record_vote
- [ ] 2.3 前端 rateYesterday 登录态下调用 vote 接口 _(R2.3)_ 🔸 P5 前端动态化时接
- [x] 2.4 test_vote_feedback + test_vote_persist _(F4,F5)_ ✅ test_feedback 7 项

## 阶段 3：偏差校准
- [x] 3.1 GET /api/accuracy/bias?spot：统计近 N 条→偏差倾向+建议 _(R3.1,3.2;F6)_ ✅ feedback.compute_bias（min_votes=3，排除 noidea）
- [x] 3.2 预报旁呈现校准提示，**不修改原评分** _(R3.3;F6)_ ✅ 仅提示，note 声明不改原分
- [x] 3.3 test_bias（≥N 出建议、原分不变） _(F6)_ ✅

## 阶段 4：位置与时区核验
- [ ] 4.1 test_placement（verify DOM 在 cards 之后） _(F7)_ 🔸 P5 前端
- [x] 4.2 全程 GMT+8 标注核验 _(R4.2)_ ✅ vote created_at_gmt8 + 历史 GMT+8 日界

## 依赖
```
引擎 past_days → 1.x → 2.x → 3.x ; 0.x 已完成(MVP前端)
web 鉴权/DB → 2.2/3.1
```

## 完成定义
昨日日期 GMT+8 正确且不与预报重叠 + 昨日口径与预报一致 + 四档反馈正确 + 登录持久化 + 偏差提示不篡改原分 + 位于预报之后。
