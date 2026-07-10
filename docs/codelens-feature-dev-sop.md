# 新功能开发 × CodeLens 生命周期 SOP（浪报 surf-forecast）

> 面向"新增功能/需求"的实操手册：把 CodeLens 21 工具嵌进 Kiro spec 驱动开发的每个阶段。
> **定位**：CodeLens 不写代码，它是你的**代码事实层**——需求前摸底、设计找接入点、改前算爆炸半径、改后守红线、收尾刷新 spec。
> 本文以 backlog 项「**多浪点横向对比**」为靶子，**①②③ 阶段附本机实跑的真实输出**（package `liangyimingcom/surf-forecast`，revision `527125044f30462a938e`）。
> 用法：新会话里自然语言直调（`用 codelens <工具> ...`），或 curl 直连（见 `codelens-meshclaw-integration.md` 附录 A）。

---

## 全生命周期总览

```mermaid
flowchart LR
  p0["①需求前<br/>摸清现状/约束"] --> p1["②设计<br/>找接入点/复用"]
  p1 --> p2["③拆任务<br/>评估爆炸半径+红线触点"]
  p2 --> p3["④实现中<br/>随时问代码"]
  p3 --> p4["⑤验证<br/>红线自动核对"]
  p4 --> p5["⑥收尾<br/>刷新spec闭环"]
  p5 -.下一个需求.-> p0
```

| 阶段 | 主用工具 | 产出 | 防止的坑 |
|------|----------|------|----------|
| ①需求前 | explain_code / search_spec_artifacts / get_specification_doc | 有据的 requirements.md | 重复造轮子、漏约束 |
| ②设计 | find_symbol / build_context / find_callers | 接入点明确的 design.md | 加错地方、动了不该动的 |
| ③拆任务 | get_impact / find_route / find_affected_tests | 带红线标记的 tasks.md | 低估爆炸半径 |
| ④实现 | explain_code / build_context | 顺畅实现 | 卡壳翻代码耗时 |
| ⑤验证 | find_route / search_spec_artifacts / get_impact | 红线核对表 | 线上 500 / SVG NaN / 401 漏保护 |
| ⑥收尾 | generate_spec / get_revision_metadata | 最新 spec 快照 | 后续查旧快照 |

---

## ① 需求前 —— 摸清现状与约束（实跑：explain_code）

**调用**
```
用 codelens explain_code 问：现在的浪报查询是单浪点还是支持多浪点？
后端 get_report 与 spot_registry 如何协作取数？DATA CONTRACT 里 days 是否含 wdeg？
```

**本机实跑真实返回（节选）**
> **支持多浪点**，"每用户多浪点 + 全局去重注册表"两级模型：
> - 完整 CRUD/切换：`GET/POST/PATCH/DELETE /api/spots` + `POST /api/spots/{slug}/select` [`src/web/app.py:139‑175`]，实现在 [`src/web/spots.py:31,91,102,120,131`]
> - 用户浪点按 email 隔离（`saved_spots` PK=email/SK=slug），free=3/paid=20 配额
> - 全局去重注册表 `spot_registry`：按 `round(lat,4)+round(lon,4)+facing` 去重，同坐标共享 slug+缓存，引用计数管理生命周期
> - **单次 `/api/report` 仍是针对一个浪点** [`src/web/app.py:83`]，但系统整体管理并刷新多点

**对"多浪点对比"需求的启示**：数据/存储层已支持多点，**缺口在**：① 一个能一次取多点的接口（或前端并发多次 `/api/report`）；② 前端对比视图。→ requirements.md 聚焦这两点，不必碰引擎/注册表。

---

## ② 设计 —— 找接入点、最大化复用（实跑：find_symbol + build_context）

**调用**
```
用 codelens find_symbol get_report
用 codelens build_context get_report
```

**本机实跑真实返回（节选）**
- `find_symbol` → `get_report` 定义在 [`src/web/deps.py:74`]，签名 `def get_report(lat, lon, days, spot) -> dict`
- `build_context` → **caller** 是 `report` [`src/web/app.py:84`]；关键 **callee**：`_resolve_slug`（先查注册表）[`deps.py:64`]、`find_spot` [`refresh.py:74`]、`get_store` [`db.py:287`]

**设计决策**：对比视图**复用 `get_report` 循环取多点**（每点走既有"注册表命中→读缓存→未命中回退引擎"路径），新增只做：
- 后端 `GET /api/report/compare?slugs=a,b,c`（内部对已选浪点循环调 `get_report`）
- 前端对比组件（复用现有 SVG 渲染，保证每点数组含 wdeg）
- **不动**引擎内核（physics/scoring/validate/analyze）

---

## ③ 拆任务 —— 算爆炸半径 + 标红线触点（实跑：get_impact）

**调用**
```
用 codelens get_impact get_report
用 codelens get_impact _to_decimal
```

**本机实跑真实返回（节选）**
- `get_impact get_report` → **radius 5，downstreamCount 66，upstreamCount 6**。下游深达引擎 `analyze.py`/`fetch.py`（`analyze_day`/`_score_point`/`build_lifecycle`…）。
  → **含义**：`get_report` 是高杠杆枢纽，**改它签名/行为会波及 66 个下游符号**。多浪点对比应**在其外层包一层**（新 compare 接口循环调用），**不改 `get_report` 本身**，把爆炸半径降到最小。
- `get_impact _to_decimal` → **upstream 4 个调用方**：`add_vote`[`db.py:189`]、`put_spot`[`db.py:201`]、`put_user`[`db.py:171`]、`upsert_registry`[`db.py:226`]。
  → **红线含义**：这 4 个就是当前**全部 DynamoDB 写路径**，都已过 `_to_decimal`。**若对比功能要落任何新表/新字段写入，必须新增经过 `_to_decimal` 的写函数**，否则线上 500（moto 不暴露）。

**tasks.md 红线标记**（据实跑得出）：
- [ ] compare 接口**只读**、循环复用 `get_report` — 不改其签名（避开 66 下游）
- [ ] 若写入新数据 → 必过 `_to_decimal`（对齐现有 4 个写路径）
- [ ] compare 接口带 `current_user` 依赖（401）
- [ ] compare 返回每点仍含 `wdeg` 数组（DATA CONTRACT）

---

## ④ 实现中 —— 卡壳随时问
```
用 codelens explain_code 问：新 compare 接口应复用哪个缓存读路径？未命中怎么回退？
用 codelens build_context render.py 里生成 SVG 数组字段的函数（保证对比数据无 NaN）
```

## ⑤ 验证 —— 红线变自动检查
```
用 codelens find_route              → 核对 /api/report/compare 有 current_user 依赖（401）
用 codelens search_spec_artifacts "wdeg"  → 确认对比数据每点含 wdeg
用 codelens get_impact _to_decimal  → 确认新写入（若有）已进 4 写路径之列
用 codelens find_affected_tests <改动符号>  → 只跑受影响的 pytest 子集
```
配合本地 `pytest`（子集）+ 线上 CloudFront 端到端。

## ⑥ 收尾 —— 刷新 spec 闭环
```
push 后 → nightly cron (2b5e1f8c) 自动 generate_spec 增量重生成
或手动 generate_spec(name="liangyimingcom/surf-forecast", branch="master")
→ get_revision_metadata 轮询至 SUCCESS
```
让下轮 `explain_code`/`get_impact` 基于最新代码事实。

---

## 心法（两条铁律）
1. **逆向 spec 是"现状"不是"意图"**：CodeLens 告诉你代码现在长什么样；红线意图仍以 `.kiro/steering` + `.kiro/specs` 为准，二者做 gap 核对而非互相覆盖。
2. **代码一改就刷新 spec**：spec 反映某个 commit；不刷新则 `explain_code`/`find_route` 查的是旧快照。

## 五条红线的 CodeLens 守护映射（速查）
| 红线 | 守护工具 |
|------|----------|
| GMT+8 日界 / 预报历史互斥 | `explain_code` + `search_spec_artifacts "GMT+8"` |
| DATA CONTRACT 含 wdeg | `search_spec_artifacts "wdeg"` |
| DynamoDB float→Decimal | `get_impact _to_decimal`（核对写路径全覆盖） |
| /api/spots 全 401 | `find_route` |
| slug 不可变 | `get_impact make_slug` / `find_callers` |

_本文 ①②③ 输出为 2026-07-10 本机对 revision 527125…的真实实跑结果。_
