# Kiro 后续开发指南（v2）

> 给在 Kiro 上接手本项目的人/AI。读完即可上手。

## 1. Kiro 资产怎么组织

| 资产 | 位置 | 何时加载 |
|------|------|---------|
| Steering | `.kiro/steering/*.md` | 每次对话**始终**加载（`inclusion: always`） |
| Specs | `.kiro/specs/<feature>/` | 处理该功能时引用 |
| Hooks | `.kiro/hooks/*.kiro.hook` | 事件触发 |

心智：**Steering=始终为真；Spec=当前要做；Hook=自动要做。**

## 2. 三个 Spec 的关系（v2 关键）

```
surf-forecast-analyzer   ← 共享后端引擎（取数/评分/物理/校验/渲染）
        ↑                         ↑
surf-report-web          forecast-accuracy-feedback
（鉴权/查询/会员视图）      （昨日回看/自评/偏差校准）
```

- 都依赖 analyzer；feedback 的昨日回看嵌在 web 视图里。
- **先把 analyzer 跑通**（含历史模式 + JSON 输出 wdeg），web 和 feedback 才有数据。

## 3. 上手三步

1. 读 steering：product → domain-knowledge → tech → structure。
2. 读你要做的那个 spec 的 requirements→design→tasks。
3. 从该 spec 的 tasks 第一个未勾项开始，一次一个。

样板：`src/surf_forecast/physics.py` 已实现并通过校验（含 `wind_kind` 离岸判定），是代码风格基准。`web/浪报MVP.html` 是会员视图的完整实现基准。

## 4. 实现优先级

```
analyzer: physics(✅) → scoring → models → validate → fetch(+past_days) → analyze → render(JSON含wdeg) → cli
web:      app/auth/db → query(接引擎) → cache → 前端改fetch
feedback: history(past_days=1) → vote持久化 → 偏差校准
```

先纯函数、用 reference 历史数据做 fixture 钉死判断正确性，再接 I/O 与前端。

## 5. 三条 v2 必须延续的设计

1. **离岸风一等公民**：评分要吃风向、JSON 要输出 `wdeg`、图示要按 offshore/cross/onshore 着色。浪点朝向在 `thresholds.yaml: spot_facing_deg`。
2. **昨日回看用真实历史、口径一致**：`past_days=1` 复用同一管线；历史区与预报区日期**不重叠**；校准只提示不篡改原评分。
3. **GMT+8 全程**：星期/今天/昨天按北京时间日历算；页面带校准时间戳。

## 6. 五条事实红线（validate 必须硬拦截）

见 domain-knowledge 第九节。重点：GMT+8 星期、月相↔潮型、周期口径、**禁止虚构物理**、中期降级、历史/预报日期互斥、离岸判定正确。

## 7. 前端动态化最小路径（web spec 阶段 A）

当前 HTML 内嵌 `DAYS`/`HISTORY` 常量。把它们换成 `fetch('/api/report')` 和 `fetch('/api/report/history')`，门禁换真鉴权——信息架构/图表/样式不动，W5（对齐基准）天然满足。**`DAYS`/`HISTORY` 的形状就是 API 契约**（含 wdeg/tp2/tideEvents）。

## 8. 质量基准（reference/，只读）

- `ui-golden-sample-浪报MVP.html` — UI 验收基准快照。
- `v2-report-golden-sample.md` — 分析叙事质量基准。
- `v1-report-baseline.md` / `fact-check-comparison.md` — 反面教材 + validate 来源。

## 9. 数据刷新（每日 GMT+8）

拉今天起的预报 + 昨天的历史回算；更新 DAYS/HISTORY，保证日期不重叠、星期正确、更新校准时间戳。可用 `refresh-data.kiro.hook` 或外部 cron。

## 10. 路线图（各项开工前先建 spec）

| 优先级 | 功能 |
|--------|------|
| P0 | 跑通 analyzer JSON 输出 → web 动态化 → feedback 持久化 |
| P1 | 数据缓存层、多浪点对比、保存浪点 |
| P2 | 偏差校准可视化、与官方浮标实测对比、通俗版叙事 |
| P3 | 支付/订阅、推送、社区聚合评分、长期历史趋势 |

## 11. 运行

```bash
pip install -e ".[dev]"
pytest tests/test_physics.py          # 已通过样板
python -m surf_forecast.cli --lat 36.092 --lon 120.468 --days 6 --spot "青岛山东头" --out report.md
uvicorn web.app:app --reload          # 后端实现后
# 前端：浏览器打开 web/浪报MVP.html（口令 surf2026），切高手模式看完整图表
```
