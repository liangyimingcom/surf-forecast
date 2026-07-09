# Requirements — Surf Report Web（v2 会员网站）

> EARS 格式。在引擎之上的动态会员站。
> UI 验收基准：[reference/reports/ui-golden-sample-浪报MVP.html](../../../reference/reports/ui-golden-sample-浪报MVP.html)（= web/浪报MVP.html 快照）。

## 文档目的

会员登录后查询指定位置浪报，得到富交互的逐日深度分析视图。当前 `web/浪报MVP.html` 是会员视图的完整 MVP 实现（纯前端、内嵌数据、口令占位）；本 spec 用真实后端替换占位部分，并把现有 UApp 行为正式化为需求。

## 1. 会员与鉴权

**1.1** WHEN 访客注册，THE SYSTEM SHALL 以 argon2 加盐哈希存密码，绝不明文。
**1.2** WHEN 凭据正确，THE SYSTEM SHALL 签发有时效令牌（httponly+secure cookie / JWT）。
**1.3** IF 无有效令牌访问浪报接口，THEN SHALL 返回 401，不返回任何浪报数据。
**1.4** THE SYSTEM SHALL 维护会员等级（free/paid）。
**1.5** WHERE free 等级，THE SYSTEM SHALL 限制查询频次/可查天数，超限给升级引导。
**1.6** THE SYSTEM SHALL 提供登出。
> 当前 MVP 的 `surf2026` 口令门禁是占位，由 1.1-1.6 取代；前端不得含可绕过逻辑。

## 2. 位置查询

**2.1** WHEN 提交 (lat, lon, days)，THE SYSTEM SHALL 校验经纬度合法、days 受等级约束。
**2.2** THE SYSTEM SHALL 支持预设浪点下拉 + 自定义经纬度（当前 MVP 已有此 UI，点查询走占位提示）。
**2.3** THE SYSTEM SHALL 允许会员保存/管理常用浪点。
**2.4** WHEN 合法查询，THE SYSTEM SHALL 调引擎生成浪报，返回 DATA CONTRACT JSON（含 wdeg）。
**2.5** IF 位置无海浪数据（内陆），THEN 返回明确错误。

## 3. 会员视图（对齐 UI 黄金样本）

**3.1** THE SYSTEM SHALL 呈现：可信度声明（含 GMT+8 校准时间戳）、Hero 必冲卡、一句话剧情、N 日排名日期条、逐日卡片、7 日总结、昨日回看（见 feedback spec）、下水清单、免责页脚。
**3.2** THE SYSTEM SHALL 提供 **🐣小白 / 🏄高手 双模式**：小白只看一句话+窗口+板型+人群；高手展开五维评分、SVG 图表、分参数解读、物理小课堂、行动方案、安全备忘。
**3.3** THE SYSTEM SHALL 用内联 SVG 渲染：①浪高柱(涌浪/总浪分层)+周期双口径线(Tm实线/Tp虚线) ②风况(按 offshore/cross/onshore 着色的风向点+箭头)+潮位 ③7 日生命周期柱。
**3.4** THE SYSTEM SHALL 在风况图前呈现**离岸风质条**（每时段：风质色块+风向箭头+风速）及风质图例。
**3.5** 图表 SHALL 用自适应 HTML 图例（非拥挤 SVG 内嵌文字）。
**3.6** WHILE 展示，THE SYSTEM SHALL 支持日期条点选跳转、"为什么N分"展开、模式切换，无整页刷新。
**3.7** 时间显示 SHALL 全程 GMT+8。

## 4. 性能与缓存

**4.1** THE SYSTEM SHALL 缓存同位置/天数浪报（TTL 3-6h，对齐模型更新）。
**4.2** 命中 SHALL <500ms；未命中 <5s 并写缓存。
**4.3** IF Open-Meteo 不可用，THEN 返回最近缓存并标注时效，不白屏。

## 5. 数据正确性

**5.1** THE SYSTEM SHALL 复用引擎事实校验（星期GMT+8/月相/周期/虚构叙事/中期/离岸判定）。
**5.2** WHERE 非黄海，THE SYSTEM SHALL 用该海域阈值（含 spot_facing_deg）。

## 6. 安全

**6.1** 全程 HTTPS；密钥/DB 凭据走环境变量。
**6.2** 查询接口限流；输入校验/转义。
**6.3** 前端零信任：鉴权只在后端，无凭据泄露。

## 验收标准

| # | 标准 |
|---|------|
| W1 | 未登录无法获取浪报数据(401) |
| W2 | 注册/登录/登出全流程，密码哈希 |
| W3 | free/paid 限制生效 |
| W4 | 任意合法经纬度可查、返回含 wdeg 的 JSON |
| W5 | 会员视图信息架构/交互对齐 UI 黄金样本 |
| W6 | 双模式、三类 SVG 图表、离岸风质条、HTML 图例齐全 |
| W7 | 报告不违反事实红线；离岸判定正确 |
| W8 | 缓存命中<500ms、故障降级不白屏 |
| W9 | 无前端可绕过鉴权、无凭据暴露 |
| W10 | 全程 GMT+8 |

## 范围外
支付扣费、社交登录、推送、多语言、多浪点横向对比。
