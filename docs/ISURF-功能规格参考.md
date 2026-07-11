# 功能规格说明（石老人-实时浪报）

> 面向导入其他业务系统的结构化说明：每个功能含 **需求 / 实现 / 接口 / 数据字段 / 复刻状态**。
> 需求编号规则：`F-<模块>-<序号>`。状态：✅已复刻 / 🟡已逆向未复刻 / ⛔需登录态。

---

## 一、系统概述

| 项 | 说明 |
|---|---|
| 产品定位 | 面向冲浪爱好者的实时浪况平台：直播摄像头、多日浪况预报、浪点地图、社区（拼车/活动/二手）、排水量工具 |
| 客户端 | 微信小程序（`navigationStyle: custom`，webview 混合渲染） |
| 后端 Base | `https://isurf.c-pan.cn` |
| 视频 | HLS（`.m3u8`），腾讯云 `https://isurfvideo.c-pan.cn/live/{spot}.m3u8` |
| 鉴权 | 只读内容接口无需登录；用户/社区接口用 `token`（`/user/*`） |
| 上游校验 | 校验 `Referer=servicewechat.com/...`、`User-Agent` 含 MiniProgramEnv；API 限定 CORS 来源 |

页面清单（`app-config.json`）：首页、冲浪搭子(拼车)、个人中心（三 Tab）；webview、浪点地图、预报(forcast)、活动墙(news)、二手发布、意见反馈、关于我们、商务合作、我发布的、维护页、广告详情、公告详情。

---

## 二、功能需求与实现明细

### 模块 A：在线视频直播

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-A-01 | 展示浪点直播列表 | 首页 `getCamera()` 拉 `/default/v2/getCamera/{ctid}`，渲染卡片 | ✅ |
| F-A-02 | 播放浪点实时直播 | 每个浪点 `live_src` 为 HLS；小程序用原生 `<live-player>`，复刻版用 `hls.js`（Safari 原生），点击卡片起播 | ✅ |
| F-A-03 | 直播状态监听 | 小程序 `statechange` 监听 `live-player` code；复刻版监听 `<video>` playing/error | ✅ |
| F-A-04 | 直播封面/占位 | `post_url` 作为封面图 | ✅ |

**关键实现点**
- 视频流 CORS 反射任意 Origin → 前端可直连播放，无需代理。
- 复刻 `playStream()`：Safari 用 `video.src` 原生 HLS；其他浏览器用 `Hls.js`（`liveDurationInfinity + lowLatencyMode`）。

### 模块 B：首页浪点列表与地区筛选

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-B-01 | 地区分类 Tab | `/default/getCategories`，按 `ct_sort` 倒序 | ✅ |
| F-B-02 | 按地区筛选浪点 | 切 Tab 传 `ctid` 调 `getCamera/{ctid}`，`all`=全部 | ✅ |
| F-B-03 | 卡片展示实时指标 | 浪高 `wave_height_now` / 周期 `wave_spacing` / 风力 `wind_power` + LIVE 标记 | ✅ |

地区枚举：广东(1) 海南(2) 福建(3) 广西(4) 浙江(5) 山东(6) 其他(7) 国外(8)。

### 模块 C：浪点详情 · 浪况预报

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-C-01 | 今日概览 | `Sat 07/11`（本地日期）+ **Air/Sea 水温**（`tableData[0][0].temperatureEl` / `[0][1]`） | ✅ |
| F-C-02 | Overview | 当日浪高范围(min-max)、周期、风力 + 浪向/风向箭头(SVG) | ✅ |
| F-C-03 | 日出/日落 | `sun`="04:53 - 19:13" 拆分 | ✅ |
| F-C-04 | 多日浪况预报表 | `getNewForecast/{cId}` 的 `tableData`(JSON字符串, 16天)；列：时间/浪涌/间隔/浪向/风力/风向/评价/天气 | ✅ |
| F-C-05 | 评价星级 | `starClass` 含 `star1/2/3` → 1~3★ | ✅ |
| F-C-06 | 潮汐曲线 | `tidesLineChartArr`(SVG 分段)；有内容才展示（石老人当前为空） | ✅（数据驱动） |
| F-C-07 | 导航到浪点 | `latitude/longitude` 打开地图 marker | ✅ |

**预报单元格字段契约（`tableData[day][slot]`）**

| 字段 | 含义 | 示例 |
|---|---|---|
| `timeSlotTit` | [周, 日, 时段] | `["Sa","11","04h"]` |
| `currentMonth` | 月份 | `7` |
| `WaveEl` | 浪涌(m) | `"0.9"` |
| `WavePeriodEl` | 间隔/周期(s) | `"6"` |
| `WaveDirectionEl` | 浪向(SVG 箭头) | `<svg…rotate(334)…>` |
| `WaveDirectionTitle` | 浪向文字 | `"SSE (154°)"` |
| `windSpEl` | 风力(kph) | `"9"` |
| `windGustsEl` | 阵风(kph) | `"20"` |
| `windDirectionEl` | 风向(SVG) | `<svg…>` |
| `windDirectionTitle` | 风向文字 | `"SSE (168°)"` |
| `temperatureEl` | 气温(°C) | `"25"` |
| `starClass` | 评价 | `"…star2…"` |

### 模块 D：周边推荐

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-D-01 | 推荐分类 | `/default/getAdType` → surfClub(冲浪店) / restaurant(餐厅酒吧) / hotel(酒店) | ✅ |
| F-D-02 | 推荐详情 | `POST /default/getAdsInfo` body `{"adId_list":"[..]"}`；按 `type_id` 分组渲染 title/description/post_url | ✅ |

### 模块 E：轮播 Banner 与公告

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-E-01 | 首页轮播图 | `/default/getBanner`，`type`=img/web/min_app，自动轮播 | ✅ |
| F-E-02 | 滚动公告 | `/default/getNoticeShowList`（顶层 `list[]`），跑马灯 | ✅ |
| F-E-03 | 公告详情 | `/default/getNoticeInfo/{id}`（富文本 `rich_text_content`） | 🟡 |

### 模块 F：冲浪板排水量计算器

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-F-01 | 选项加载 | `/default/getVolumeField` → `weight[]`(kg) + `type[]`(水平名) | ✅ |
| F-F-02 | 计算排水量 | `POST /default/getVolume` 表单 `weight=<kg>&type=<水平名称>` → `data[0].volume`(L) | ✅ |

> 注意：`type` 传**水平名称**（如"中级"）而非索引。样例：70kg 中级→31L，初学者→49L。

### 模块 G：浪点地图

| 编号 | 需求 | 实现 | 状态 |
|---|---|---|---|
| F-G-01 | 浪点地图 | 小程序 `pages/map`；`getNewForecast` 提供 `latitude/longitude` | 🟡（复刻版以"导航"跳转地图代替） |

### 模块 H：社区（冲浪搭子/拼车）⛔ 需登录

| 编号 | 需求 | 接口 | 状态 |
|---|---|---|---|
| F-H-01 | 拼车枚举 | `POST /default/getCarpoolingEnum` | 🟡⛔ |
| F-H-02 | 拼车列表 | `POST /default/queryCarpoolList` | 🟡⛔ |
| F-H-03 | 拼车详情 | `GET /default/getCarpoolInfo/{id}` | 🟡⛔ |
| F-H-04 | 发布/更新/删除拼车 | `POST createCarpool / updateCarpool / deleteCarpooling` | 🟡⛔ |

### 模块 I：活动墙 / 二手 ⛔ 需登录

| 编号 | 需求 | 接口 | 状态 |
|---|---|---|---|
| F-I-01 | 活动/二手列表 | `POST /default/getNewsList` | 🟡⛔ |
| F-I-02 | 详情 | `GET /default/getNewsInfo/{id}` | 🟡⛔ |
| F-I-03 | 类型/Banner | `GET getNewsType / getNewsBanerList` | 🟡 |
| F-I-04 | 发布/更新/传图 | `POST createNews / updateNews / updateNewsImg` | 🟡⛔ |

### 模块 J：用户 / 个人中心 ⛔ 需登录

| 编号 | 需求 | 接口 | 状态 |
|---|---|---|---|
| F-J-01 | 登录 | `POST /user/login` | 🟡⛔ |
| F-J-02 | 校验 token | `POST /user/verifyToken` | 🟡⛔ |
| F-J-03 | 用户信息 | `POST /user/getUserInfo / updateUserInfo` | 🟡⛔ |
| F-J-04 | 头像上传 | `POST /user/updateUserImg` | 🟡⛔ |

### 模块 K：其他

| 编号 | 需求 | 接口 | 状态 |
|---|---|---|---|
| F-K-01 | 意见反馈 | `POST /default/createFeedback`（类型含"直播视频异常"等） | 🟡 |
| F-K-02 | 小程序信息 | `GET /default/miniProgramInfo`（版本、客服邮箱） | ✅ |
| F-K-03 | 微信支付/会员 | `POST /default/v1/wxpay / viptaocan` | ⛔ |
| F-K-04 | 商务合作/关于我们 | 静态页 | 🟡 |

---

## 三、完整 API 索引

| 方法 | 路径 | 功能 | 复刻 |
|---|---|---|---|
| GET | `/default/getCategories` | 地区分类 | ✅ |
| GET | `/default/v2/getCamera/{ctid}` | 浪点直播列表 | ✅ |
| GET | `/default/getBanner` | 轮播图 | ✅ |
| GET | `/default/getNoticeShowList` | 公告列表 | ✅ |
| GET | `/default/getNoticeInfo/{id}` | 公告详情 | 🟡 |
| GET | `/default/getNewForecast/{cId}` | 多日浪况预报+潮汐+日出日落+坐标 | ✅ |
| GET | `/default/getForecast/{cId}` | 旧版预报（现返回空） | — |
| GET | `/default/getAdType` | 周边推荐分类 | ✅ |
| POST | `/default/getAdsInfo` | 周边推荐详情 | ✅ |
| GET | `/default/getAdInfo/{id}` | 广告详情 | 🟡 |
| GET | `/default/getVolumeField` | 排水量选项 | ✅ |
| POST | `/default/getVolume` | 排水量计算 | ✅ |
| GET | `/default/miniProgramInfo` | 小程序信息 | ✅ |
| POST | `/default/createFeedback` | 意见反馈 | 🟡 |
| POST | `/default/*carpool*` | 拼车系列 | 🟡⛔ |
| POST | `/default/*News*` | 活动/二手系列 | 🟡⛔ |
| POST | `/default/v1/wxpay`,`viptaocan` | 支付/会员 | ⛔ |
| POST | `/user/login`,`verifyToken`,`getUserInfo`,`updateUserInfo`,`updateUserImg` | 用户 | 🟡⛔ |

---

## 四、非功能需求

| 项 | 要求 |
|---|---|
| 兼容性 | 移动端优先；HLS 播放兼容 Safari(原生) 与 Chrome/Firefox(hls.js) |
| CORS | 内容 API 限来源 → 需服务端代理；视频流允许任意源 → 前端直连 |
| 性能 | 直播低延迟(lowLatencyMode)；列表图片懒加载 |
| 合规 | 仅公开只读接口；不复刻登录态/支付；伪装请求头仅用于研究 |
| 可维护 | 接口取值路径集中在 `app.js`；域名/请求头集中在 `server.js` |
