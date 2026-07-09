# Design — Custom Spots（浪点自定义与管理，v2 新增）

> 回应 requirements.md。复用：surf-report-web 鉴权/视图、deployment-and-ops 缓存/调度、surf-forecast-analyzer 引擎/区域阈值。
> 核心改造：把 `refresh.py::DEFAULT_SPOTS`（硬编码）升级为 **DynamoDB 动态浪点注册表**，让用户浪点与默认浪点同等纳入"读写解耦"的每日刷新链路。

## 1. 架构定位

```
会员浏览器
  │  地图点选 / 经纬度输入 / 浪点下拉切换
  ▼
前端 SPA（浪报MVP.html 扩展：spotManager 组件）
  │  /api/spots(CRUD)        /api/report?lat&lon&spot&days
  ▼
FastAPI（src/web/）
  ├─ spots.py(新)   浪点 CRUD + slug 生成 + 去重 + 配额        ← 本 spec 新增
  ├─ deps.get_report  上架/已保存浪点命中缓存，否则回退引擎
  └─ db.py          saved_spots 表读写（已有表，补访问方法）
        │
        ▼
  DynamoDB saved_spots（用户浪点）  +  spot_registry（去重后的全局活跃浪点，新）
        │                                   ▲
        │ 创建即时预算                       │ 每日刷新读注册表
        ▼                                   │
  refresh.py（写侧）：注册表替代 DEFAULT_SPOTS → refresh_spots → S3 缓存
        ▲
  EventBridge Scheduler（GMT+8 02:00/14:00，已有）+ 新建即时预算（按需触发）
```

不变量：**计算仍在引擎、缓存仍读写解耦、鉴权仍全后端**。本 spec 只新增"浪点是谁、谁要被刷"的注册与编排。

## 2. 数据模型

### 2.1 用户浪点 `saved_spots`（DynamoDB，表已存在）

```
PK = email (S)              # 用户隔离
SK = slug  (S)              # 该用户下浪点
attrs:
  name            (S)       # 用户命名，1-32 字符，用户内唯一
  lat, lon        (N)       # ≥4 位小数
  spot_facing_deg (N)       # 朝向，默认继承区域，可覆盖
  region          (S)       # 标定海域键（如 "huanghai"）或 "uncalibrated"
  status          (S)       # active | inactive(软删)
  created_at_gmt8 (S)
  last_viewed_at_gmt8 (S)
```

### 2.2 全局浪点注册表 `spot_registry`（DynamoDB，新表）

去重后的"需要被定时刷新"的浪点集合。多用户同坐标共享一行（一个 slug 一份缓存）。

```
PK = slug (S)                       # 全局唯一，= 缓存键前缀
attrs:
  spot            (S)               # 展示名（取首个创建者命名或规范名）
  lat, lon        (N)
  spot_facing_deg (N)
  region          (S)
  days            (N)  default 6
  ref_count       (N)               # 引用它的用户数（删到 0 → 可回收）
  refresh_enabled (BOOL)            # 冷浪点暂停定时刷新
  last_viewed_at_gmt8 (S)           # 任一用户查看即更新
  last_refresh_at_gmt8 (S)
  source          (S)               # "default" | "user"
```

> `slug` 生成：`slugify(name)` 冲突时退化为 `geo-{lat4}-{lon4}`（坐标编码），保证全局唯一 + 稳定（R1.4/2.3）。去重键 = round(lat,4)+round(lon,4)+facing。

### 2.3 与现有 `DEFAULT_SPOTS` 的关系

- 默认浪点（青岛山东头）作为 `source=default` 的固定注册表行（迁移时写入，或代码兜底合并）。
- `refresh.py` 的 `DEFAULT_SPOTS` 常量保留为**回退兜底**（注册表不可用时仍能刷默认点），但刷新主路径改读注册表。

## 3. 存储方案权衡（ADR 见 §8）

| 方案 | 注册表存储 | 选择 |
|------|-----------|------|
| A 复用 saved_spots 扫描去重 | 每次刷新 Scan 全表去重 | ❌ Scan 成本随用户涨 |
| **B 独立 spot_registry 表（选）** | 创建/删除时维护 ref_count，刷新只读 active 行 | ✅ 刷新 O(活跃浪点) 不 Scan 用户表 |

## 4. API 变更（src/web/spots.py 新增）

```
GET    /api/spots                 [鉴权] → 该用户浪点列表(含 status/last_viewed)
POST   /api/spots                 [鉴权] {name,lat,lon,facing?} → 创建(校验+去重+配额+即时预算) → spot(含 slug)
PATCH  /api/spots/{slug}          [鉴权] {name?,facing?} → 重命名/改朝向(slug 不变)
DELETE /api/spots/{slug}          [鉴权] → 软删(status=inactive, ref_count--)
POST   /api/spots/{slug}/select   [鉴权] → 记为"上次选中" + 更新 last_viewed
```

`POST /api/spots` 流程：
```
校验坐标范围/精度 → 配额检查(free=3/paid=20) → 名称唯一性 →
推断 region/facing → 去重(查 registry 同坐标) →
  命中: registry.ref_count++ ; 复用 slug
  未命中: 生成 slug + 写 registry(refresh_enabled=true) + 触发即时预算
写 saved_spots(PK=email,SK=slug) → 返回 spot
```

`GET /api/report` 不变签名；`deps.get_report` 扩展：先查 registry（按坐标）命中 → 读 `{slug}/latest.json`；未命中 → 回退引擎实时计算（自定义/冷浪点）。

## 5. 动态刷新编排（refresh.py 改造，仅文档设计）

```python
# 现状: refresh_spots(DEFAULT_SPOTS, writer)
# 改造: 注册表驱动
def active_registry_spots(store) -> list[dict]:
    # 读 spot_registry 中 status=active 且 refresh_enabled=true 的行
    # 合并 DEFAULT_SPOTS 兜底；按预算上限 N 截断(冷点靠后)
    ...

def scheduled_refresh(store, writer):
    spots = active_registry_spots(store)
    summary = refresh_spots(spots, writer)   # 复用既有，逐点 validate 守门
    update_last_refresh(store, summary)      # 回写 last_refresh_at
    return summary
```

- **即时预算**（新建浪点 C4）：`POST /api/spots` 未命中去重时，同步/异步调 `refresh_spots([new_spot], writer)` 写一次缓存，使新点立即可读。
- **频率控制 R4.4**：每次调度预算上限 N（如 50）点；超出按 `last_viewed` 排序，冷点降级"按需 + 短 TTL"。
- **冷浪点回收 R4.6**：`last_viewed_at` 超 K 天 → `refresh_enabled=false`（仅按需计算）。

## 6. 前端交互（浪报MVP.html 扩展，附加式不破坏）

现有 `#spotSel`(下拉) + `#coordInput`(经纬度) 为起点，新增 `spotManager`：

- **浪点下拉**：预设 + 已保存浪点（名称 + 坐标小字）+ "➕ 新增自定义"。
- **新增面板**：经纬度输入 **或** 嵌入轻量地图（开源底图，点选回填坐标）+ 名称 + 朝向(可选) → POST /api/spots → 成功后切换并 loadLive。
- **切换**：选中 → `SPOT={lat,lon,name,days}` 重赋值 → `loadLive()`（复用现有实时数据层）→ POST `/select` 记忆。
- **管理**：浪点旁 ✏️重命名 / 🗑删除（软删）。
- **降级**：未登录或接口不可用 → 回退当前内嵌示例（不白屏）。

> 地图为渐进增强：MVP 可先"经纬度输入 + checkip 风格坐标提示"，地图点选作为阶段 B。

## 7. 测试

| 测试 | C |
|------|---|
| test_spot_create（坐标校验/命名唯一/slug 稳定） | C1 |
| test_spot_crud（CRUD + 用户隔离 + 配额上限） | C2 |
| test_spot_dedup（同坐标多用户共享 slug，ref_count） | C5 |
| test_select_persist（记住上次选中 + last_viewed） | C3 |
| test_instant_budget（新建触发即时预算，立即可读） | C4 |
| test_registry_refresh（注册表驱动 refresh，逐点 validate） | C5,C7 |
| test_cold_recycle（冷浪点暂停刷新；软删保留历史） | C8 |
| test_inland_warn / test_uncalibrated_label | C6 |
| test_spots_auth（401 保护 + 名称转义） | C9 |
| test_custom_contract（自定义点缓存含 wdeg，GMT+8） | C10 |

## 8. ADR

- **ADR-CS1** 独立 `spot_registry` 表（非扫 saved_spots 去重）：刷新成本 O(活跃浪点) 而非 O(用户)。
- **ADR-CS2** slug 全局唯一且不可变，作为缓存键前缀：重命名不漂移缓存（R2.3）。
- **ADR-CS3** 同坐标全局去重共享缓存：控 Open-Meteo 调用量（继承 ADR-D1 读写解耦初衷）。
- **ADR-CS4** 新建浪点即时预算 + 调度兜底：兼顾"立即可用"与"批量经济"。
- **ADR-CS5** 删除软删 + 冷点暂停刷新：成本随活跃度而非历史累计增长。
- **ADR-CS6** 未标定海域显式标注"按黄海近似"：数据诚实优先（不伪装精度）。
- **ADR-CS7** 前端附加式扩展现有 MVP（const→可切换 SPOT），地图为阶段 B 增强，不破坏既有视图。
