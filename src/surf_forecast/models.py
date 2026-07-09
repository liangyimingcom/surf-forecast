"""pydantic 数据模型 —— 见 design.md 第 2 节、requirements 1.x/3.x、Task 1.1.

实现要点：
- ForecastPoint 含所有参数，字段名带单位；swell_purity / gust_ratio 为计算属性；
  wind_kind(spot_facing_deg) 委托 physics.wind_kind 映射为 WindKind 枚举（离岸风一等公民）。
- DailyForecast.weekday 由 date 派生且只读（需求 2.1，GMT+8 日历，禁止外部赋值）。
- Confidence 枚举 HIGH/MEDIUM/LOW；中期预报(D+5+)由 analyze 层置 LOW。
- ReportContext.calibrated_at 为 GMT+8 校准时间戳（需求 5.3）。
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from . import physics

# GMT+8 中文星期（date.weekday(): 周一=0 … 周日=6）
_WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class Confidence(str, Enum):
    """数据点可信度。中期预报(D+5+)自动降级 LOW（需求 2.5）。"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WindKind(str, Enum):
    """风向相对浪点朝向的三分类（离岸风一等公民，ADR-D6/ADR-6）。"""

    OFFSHORE = "off"   # 离岸：梳直浪面，最佳
    CROSS = "cross"    # 侧岸：尚可
    ONSHORE = "on"     # 向岸：吹乱浪面，差


class ForecastPoint(BaseModel):
    """单个 3 小时预报时段（时间为 GMT+8）。"""

    time: datetime                       # GMT+8
    wave_height_m: float                 # 总浪高 Hs
    wave_direction_deg: float
    wave_period_mean_s: float            # 平均周期 Tm
    wave_period_peak_s: Optional[float] = None  # 谱峰周期 Tp（比 Tm 大 0.8-2s）
    swell_height_m: float = 0.0
    swell_direction_deg: float = 0.0
    wind_wave_height_m: float = 0.0
    wind_speed_kn: float = 0.0
    wind_direction_deg: float = 0.0      # 风的来向
    wind_gust_kn: float = 0.0
    sea_level_m: float = 0.0             # 相对 MSL
    sst_c: float = 0.0
    source: str = "ecmwf_wam025"
    confidence: Confidence = Confidence.HIGH

    @computed_field  # type: ignore[prop-decorator]
    @property
    def swell_purity(self) -> float:
        """涌浪纯度 (%) = 涌浪高 / 总浪高 * 100。"""
        return physics.swell_purity(self.swell_height_m, self.wave_height_m)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gust_ratio(self) -> float:
        """阵风比 = 阵风 / 平均风速（>阈值标记数据异常）。"""
        if self.wind_speed_kn <= 0:
            return 0.0
        return self.wind_gust_kn / self.wind_speed_kn

    def wind_kind(self, spot_facing_deg: float) -> WindKind:
        """按浪点朝向判定本时段风为 offshore/cross/onshore。"""
        return WindKind(physics.wind_kind(self.wind_direction_deg, spot_facing_deg))


class TideExtreme(BaseModel):
    """潮汐局部极值（高潮/低潮）。"""

    time: datetime                       # GMT+8
    level_m: float
    kind: Literal["high", "low"]


class DailyForecast(BaseModel):
    """单日预报：白天时段集合 + 潮汐极值 + 天文信息。"""

    # 禁止外部传入未知字段（尤其 weekday 须由 date 派生，需求 2.1）
    model_config = ConfigDict(extra="forbid")

    date: date                           # GMT+8 日历日期
    points: list[ForecastPoint] = Field(default_factory=list)
    tide_extremes: list[TideExtreme] = Field(default_factory=list)
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    moon_phase: Optional[str] = None     # 朔/上弦/望/下弦 等
    is_midrange: bool = False            # D+5+ 中期预报标记

    @computed_field  # type: ignore[prop-decorator]
    @property
    def weekday(self) -> str:
        """由 date 派生的 GMT+8 中文星期（只读，禁止手填，需求 2.1）。"""
        return _WEEKDAY_CN[self.date.weekday()]


class ParamScore(BaseModel):
    """单参数评分结果。"""

    name: str                            # wave_height/period/wind/purity/tide
    score: float                         # 0-10
    grade: str                           # 阈值档位文案（如 "🟢 适中"）
    note: str = ""                       # 当日数据 + 对冲浪的影响


class DailyAnalysis(BaseModel):
    """单日深度分析（评分 + 短板 + 最佳窗口 + 板型 + 风向）。"""

    forecast: DailyForecast
    scores: dict[str, ParamScore] = Field(default_factory=dict)
    composite: float = 0.0               # 综合分 0-10
    weakest_param: str = ""              # 短板参数（最低分项，需求 3.4）
    best_window: str = ""               # 最佳窗口（如 "05:00-07:30"）
    board: str = ""                     # 推荐板型
    recommendation: str = ""            # 一句话行动建议
    dawn_wind_kind: Optional[WindKind] = None  # 晨风风质（morning glass 判断）
    confidence_notes: list[str] = Field(default_factory=list)


class ReportContext(BaseModel):
    """完整报告上下文 —— render 层的输入，对齐 DATA CONTRACT。"""

    spot: str
    lat: float
    lon: float
    spot_facing_deg: float = 157.0
    calibrated_at: datetime              # GMT+8 校准时间戳（需求 5.3）
    days: list[DailyAnalysis] = Field(default_factory=list)
    history: Optional[DailyAnalysis] = None   # 昨日回看（feedback spec）
    ranking: list[int] = Field(default_factory=list)  # days 索引按综合分降序
    lifecycle: list[dict] = Field(default_factory=list)  # 涌浪事件生命周期数据
    warnings: list[str] = Field(default_factory=list)    # validate 收集的可信度声明项
