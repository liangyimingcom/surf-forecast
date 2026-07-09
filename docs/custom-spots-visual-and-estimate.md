# Custom Spots — 架构/流程图 + 工作量与排期评估

> 配套 [.kiro/specs/custom-spots/](../.kiro/specs/custom-spots/) 三件套。仅文档，不改源码。
> 区域 ap-northeast-1 ｜ 把 `refresh.py::DEFAULT_SPOTS` 硬编码升级为 DynamoDB 动态浪点注册表。

## 1. 架构图（组件与数据流）

```mermaid
flowchart TB
  U["会员浏览器"] -->|HTTPS| CF["CloudFront"]
  CF --> ALB["ALB(SG 仅 CloudFront)"]
  ALB --> FE["前端 SPA<br/>spotManager: 下拉/地图/切换"]

  subgraph API["FastAPI (src/web/)"]
    SP["spots.py(新)<br/>CRUD + slug + 去重 + 配额"]
    DP["deps.get_report<br/>按坐标命中缓存/回退引擎"]
    DB["db.py<br/>saved_spots + spot_registry"]
  end
  FE -->|/api/spots CRUD| SP
  FE -->|/api/report| DP
  SP --> DB
  DP --> DB

  subgraph DDB["DynamoDB"]
    T1[("saved_spots<br/>PK=email,SK=slug")]
    T2[("spot_registry(新)<br/>PK=slug,ref_count")]
  end
  DB --> T1
  DB --> T2

  SP -->|未命中去重→即时预算| RJ
  EB["EventBridge GMT+8<br/>02:00/14:00"] --> RJ["refresh<br/>active_registry_spots"]
  RJ -->|读 active 浪点| T2
  RJ -->|build_context+validate| ENG["引擎(确定性)"]
  ENG -->|REST| OM["Open-Meteo ECMWF"]
  RJ -->|写缓存| S3[("S3 cache<br/>{slug}/latest.json")]
  DP -->|读缓存| S3
```

## 2. 流程图：新建自定义浪点（即时预算）

```mermaid
sequenceDiagram
  participant U as 会员
  participant FE as 前端
  participant SP as spots.py
  participant REG as spot_registry
  participant SAV as saved_spots
  participant RJ as refresh
  participant S3 as S3 cache
  U->>FE: 地图点选/输入经纬度 + 命名
  FE->>SP: POST /api/spots {name,lat,lon,facing?}
  SP->>SP: 校验坐标/精度 + 配额(free=3/paid=20) + 名称唯一
  SP->>REG: 查同坐标(round4)是否已存在
  alt 已存在(去重命中)
    REG-->>SP: 复用 slug；ref_count++
  else 新坐标
    SP->>SP: 生成稳定 slug(slugify/geo-编码)
    SP->>REG: 写注册表行(refresh_enabled=true)
    SP->>RJ: 即时预算 refresh_spots([new])
    RJ->>S3: 写 {slug}/latest.json (validate 守门)
  end
  SP->>SAV: 写 saved_spots(PK=email,SK=slug)
  SP-->>FE: 返回 spot(含 slug)
  FE->>FE: 切换并 loadLive() → 立即可读
```

## 3. 流程图：浪点切换查询（读侧）

```mermaid
sequenceDiagram
  participant U as 会员
  participant FE as 前端
  participant DP as deps.get_report
  participant REG as spot_registry
  participant S3 as S3 cache
  participant ENG as 引擎
  U->>FE: 选择已保存浪点
  FE->>DP: GET /api/report?lat&lon&spot&days
  DP->>REG: 按坐标查注册表
  alt 上架浪点命中
    DP->>S3: 读 {slug}/latest.json
    S3-->>DP: REPORT(含 wdeg) <500ms
  else 未命中/冷浪点/自定义
    DP->>ENG: build_context → render_json
    ENG-->>DP: REPORT(实时计算)
  end
  DP-->>FE: REPORT
  FE->>DP: POST /api/spots/{slug}/select (记 last_viewed)
```

## 4. 流程图：每日动态刷新（写侧，注册表驱动）

```mermaid
flowchart LR
  EB["EventBridge GMT+8"] --> AR["active_registry_spots<br/>(active + refresh_enabled)"]
  AR --> BUD{"预算上限 N?"}
  BUD -->|N 内| LOOP["逐浪点 build_context+validate"]
  BUD -->|超出冷点| DEG["降级:按需+短TTL"]
  LOOP --> VAL{"validate?"}
  VAL -->|通过| WR["写 {slug} latest/today/history"]
  VAL -->|失败| SKIP["跳过+保留上一版+告警"]
  WR --> RC["回写 last_refresh"]
  COLD["last_viewed 超 K 天"] --> OFF["refresh_enabled=false"]
```

## 5. 实现工作量评估

> 颗粒度：人日（1 人日 ≈ 熟悉本仓的工程师专注 1 天）。含编码 + 单测，不含跨团队评审等待。

| 阶段 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| **1 数据层** | db 访问方法 + spot_registry 模型 + slug/去重/区域推断 + moto 测试 | **2.0** | 🟢 纯代码，moto 离线 |
| **2 CRUD API** | spots.py 5 路由 + 校验转义 + 配额 + 软删 + 测试 | **2.5** | 🟡 边界多(唯一性/配额/转义) |
| **3 查询切换** | deps.get_report 扩展按坐标命中 + select 记忆 + 契约测试 | **1.0** | 🟢 复用现有缓存读 |
| **4 动态刷新** | active_registry_spots + 即时预算 + 频率控制 + 冷点回收 + 测试 | **2.5** | 🟡 去重/预算上限/竞态 |
| **5 前端** | spotManager 下拉/新增面板/切换/管理(附加式) + JS 校验 + 浏览器走查 | **2.5** | 🟡 不破坏现有 MVP；地图(5.5)阶段B另计 |
| **5.5 地图(阶段B)** | 开源底图点选回填(可选增强) | **1.5** | 🟢 可延后 |
| **6 IaC** | storage 加 spot_registry 表 + IAM + validate/plan | **1.0** | 🟡 apply 需审批；表 replace 竞态教训 |
| **联调+E2E+修复** | 端到端(创建→刷新→切换→缓存命中) + 部署冒烟 | **1.5** | 🟡 |
| | **MVP 合计（不含地图）** | **≈ 13 人日** | |
| | **含地图阶段B** | **≈ 14.5 人日** | |

## 6. 排期（建议，单人推进）

```mermaid
gantt
  title custom-spots 实现排期(单人,人日)
  dateFormat X
  axisFormat %s
  section 后端
  阶段1 数据层+注册表      :a1, 0, 2d
  阶段2 CRUD API          :a2, after a1, 3d
  阶段3 查询切换          :a3, after a2, 1d
  阶段4 动态刷新编排      :a4, after a3, 3d
  section 前端
  阶段5 spotManager       :b1, after a3, 3d
  section 上线
  阶段6 IaC(apply审批)    :c1, after a4, 1d
  联调E2E+修复            :c2, after c1, 2d
  section 可选
  阶段5.5 地图(阶段B)     :d1, after c2, 2d
```

**关键路径**：1 → 2 → 4 → 6 → E2E（后端约 11.5 人日）；前端 5 可与 4 并行。**MVP 可上线约 2.5-3 周**（单人，含审批等待缓冲）。

## 7. 风险与前置

| 风险 | 缓解 |
|------|------|
| DynamoDB 同名表 replace 竞态（历史教训） | 新表 create_before_destroy 或确认删除完成再 apply |
| 坐标枚举滥用 Open-Meteo | 全局去重 + 每用户每日新建上限 + 预算上限 N |
| 前端改动破坏现有 MVP | 附加式扩展(const→可切换 SPOT)，失败回退内嵌不白屏 |
| apply 审批门 | 阶段 6 plan 摘要后人工授权(遵守 apply 红线) |

## 8. 不变量（继承红线）
slug 不可变作缓存键；validate 守门；读写解耦；GMT+8 日界；离岸判定按该点 spot_facing_deg；未标定海域标注"按黄海近似"；鉴权全后端 401 保护。
