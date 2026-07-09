# Requirements — Custom Spots（浪点 / 位置自定义与管理，v2 新增）

> EARS 格式。本 spec 把"浪点"从 `refresh.py` 硬编码的 `DEFAULT_SPOTS` 升级为**用户可自定义、可管理、可被定时刷新链路动态消费**的一等实体。
> 边界：本 spec 拥有「浪点注册表 + 自定义经纬度 + 多点管理 + 动态刷新编排」；复用 surf-report-web 的鉴权/视图、deployment-and-ops 的缓存与调度、surf-forecast-analyzer 的引擎与区域阈值。
> UI 基准：[reference/reports/ui-golden-sample-浪报MVP.html](../../../reference/reports/ui-golden-sample-浪报MVP.html)（位置查询栏 `#spotSel` / `#coordInput` 为占位起点）。

## 文档目的

当前位置是**硬编码**的（`src/web/refresh.py::DEFAULT_SPOTS` 仅含青岛山东头；`find_spot` 按坐标 2 位小数匹配；在线请求自定义坐标会回退实时计算、不进缓存、不被每日刷新覆盖）。`saved_spots` DynamoDB 表已建但 `/api/spots` CRUD 未实现，前端 `#coordInput` 点查询走占位提示。

本 spec 让会员能：**用地图/经纬度自定义浪点 → 命名 → 保存多点 → 一键切换 → 该浪点自动纳入每日定时抓取与缓存刷新**，从而获得与默认浪点同等的"读缓存 <500ms + 昨日回看"体验。

## 1. 自定义经纬度与浪点创建

**1.1** WHEN 会员输入合法经纬度（lat∈[-90,90], lon∈[-180,180]）或在地图上点选，THE SYSTEM SHALL 解析为候选浪点坐标（保留 ≥4 位小数精度）。
**1.2** THE SYSTEM SHALL 允许会员为浪点命名（1-32 字符，可含中文；同一用户内名称唯一）。
**1.3** WHEN 创建浪点，THE SYSTEM SHALL 自动按坐标推断**朝向 spot_facing_deg**（默认继承区域缺省，允许用户覆盖；离岸判定依赖此值）。
**1.4** THE SYSTEM SHALL 为每个浪点生成稳定 `slug`（用于缓存键 `{slug}/latest.json`），slug 在系统内全局唯一且不可变。
**1.5** IF 坐标位于内陆/无海浪数据，THEN SHALL 在保存前给出明确警告（可仍保存，但标注"无海浪数据"）。
**1.6** WHERE 坐标落在已标定海域（黄海等），THE SYSTEM SHALL 绑定该海域 thresholds 配置；WHERE 未标定海域，SHALL 标注"阈值未标定（按黄海近似）"。

## 2. 多浪点管理（CRUD）

**2.1** THE SYSTEM SHALL 提供会员浪点的增/查/改/删（`/api/spots`），数据隔离到该用户（PK=email）。
**2.2** THE SYSTEM SHALL 限制单用户浪点数量上限（free=3，paid=20），超限给升级引导。
**2.3** WHEN 会员重命名/调整朝向，THE SYSTEM SHALL 更新记录但**保持 slug 不变**（避免缓存键漂移）。
**2.4** WHEN 会员删除浪点，THE SYSTEM SHALL 软删除（标记 inactive），保留缓存与历史回看至 TTL 到期；不立即清缓存。
**2.5** THE SYSTEM SHALL 记录每个浪点 `created_at_gmt8` / `last_viewed_at_gmt8`，供"常用浪点"排序与冷浪点回收。

## 3. 浪点切换与查询

**3.1** WHEN 会员选择已保存浪点，THE SYSTEM SHALL 切换查询目标并加载该浪点浪报（优先读缓存，未命中回退实时计算）。
**3.2** THE SYSTEM SHALL 在前端提供：预设/已保存浪点下拉 + "新增自定义" 入口 + 地图点选 + 当前浪点高亮。
**3.3** WHEN 切换浪点，THE SYSTEM SHALL 同步刷新 Hero/日期条/逐日卡/图表/昨日回看，无整页刷新（复用现有 render/loadLive）。
**3.4** THE SYSTEM SHALL 记住会员"上次选中浪点"，下次进入默认展示之。

## 4. 动态定时抓取与刷新（后端核心）

**4.1** THE SYSTEM SHALL 把每日刷新的"上架浪点列表"从硬编码 `DEFAULT_SPOTS` 升级为**动态浪点注册表**（默认浪点 + 所有 active 用户浪点去重）。
**4.2** WHEN EventBridge 触发 refresh（GMT+8 02:00/14:00），THE SYSTEM SHALL 遍历动态注册表，对每个 active 浪点预算预报+昨日历史并写缓存（复用 `refresh_spots`）。
**4.3** THE SYSTEM SHALL 按坐标 + 朝向**去重**：同坐标（4 位小数）多用户共享同一 slug 与缓存，避免重复抓取 Open-Meteo。
**4.4** WHERE 浪点数量增长，THE SYSTEM SHALL 控制 Open-Meteo 调用频率（批次 + 间隔 + 每次预算上限 N 点），规避免费档限频；超出预算的冷浪点降级为"按需实时计算 + 短 TTL 缓存"。
**4.5** IF 某浪点 validate 失败或取数异常，THEN SHALL 跳过该点、保留上一版、不影响其他浪点（继承 R5.4 红线）。
**4.6** THE SYSTEM SHALL 对"近 N 天无人查看"的冷浪点暂停定时刷新（仅按需计算），节省调用与存储。
**4.7** WHEN 新浪点首次创建，THE SYSTEM SHALL 触发一次即时预算（不必等下个调度窗口），使新浪点立即可用。

## 5. 数据正确性与诚实（继承红线）

**5.1** THE SYSTEM SHALL 对自定义浪点复用引擎全部事实校验（星期 GMT+8 / 历史预报互斥 / 周期口径 / 虚构叙事拦截 / 离岸判定按该点 spot_facing_deg）。
**5.2** THE SYSTEM SHALL 对未标定海域显式标注阈值来源（"按黄海近似"），不伪装为已标定精度。
**5.3** 自定义浪点的缓存与历史 SHALL 与默认浪点同口径（同一 render_json，含 wdeg/tp2/tideEvents）。

## 6. 安全与配额

**6.1** THE SYSTEM SHALL 对 `/api/spots` 全部操作要求有效会话（401 保护，前端零信任）。
**6.2** THE SYSTEM SHALL 校验/转义浪点名称（防注入/XSS），坐标做范围与精度校验。
**6.3** WHERE free 等级，THE SYSTEM SHALL 同时受浪点数（2.2）与查询频次（web R1.5）双重约束。
**6.4** THE SYSTEM SHALL 防止用户通过坐标枚举滥用 Open-Meteo（每用户每日新建浪点数上限 + 全局去重）。

## 验收标准

| # | 标准 |
|---|------|
| C1 | 会员可用经纬度/地图点选创建命名浪点，slug 稳定唯一 |
| C2 | 单用户浪点 CRUD 生效，数据隔离，free=3/paid=20 上限 |
| C3 | 切换浪点即时加载（缓存命中 <500ms），记住上次选中 |
| C4 | 新建浪点触发即时预算，立即可查；下一调度窗口起纳入定时刷新 |
| C5 | 动态注册表 = 默认 + active 用户浪点，按坐标去重，无重复抓取 |
| C6 | 内陆/无数据坐标保存前警告；未标定海域标注阈值来源 |
| C7 | 某浪点失败不影响其他浪点；保留上一版不白屏 |
| C8 | 冷浪点暂停定时刷新；删除软删除保留历史至 TTL |
| C9 | 全部接口 401 保护；名称/坐标校验转义；离岸判定按该点朝向 |
| C10 | 自定义浪点缓存/历史与默认同口径含 wdeg；全程 GMT+8 |

## 范围外
- 多浪点**横向对比**视图（属未来；本 spec 只做单点切换）。
- 第三方地图商业授权细节（用开源底图/坐标输入起步）。
- 浪点社区分享/公开浪点库（未来）。
- 反向地理编码出"地名"（可选增强，非 MVP）。
