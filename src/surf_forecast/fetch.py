"""Open-Meteo 数据获取 —— 见 design.md 第 3 节、requirements 1.x、Task 3.x.

三路调用并按 time 对齐合并：
  marine(ecmwf_wam025): wave_height, wave_direction, wave_period, wave_peak_period
  marine(best_match):   swell_wave_*, wind_wave_height, sea_level_height_msl, sea_surface_temperature
  forecast(ecmwf_ifs025): wind_speed_10m, wind_direction_10m, wind_gusts_10m  (wind_speed_unit=kn)
分辨率 3h，时区 Asia/Shanghai。WAM 缺分区字段回退 best_match 并记录 source（需求 1.5）。
失败抛 DataSourceError，标注受影响字段（需求 1.4）。
历史模式：past_days=N，口径与预报一致（需求 1.4）。
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime

from .models import Confidence, DailyForecast, ForecastPoint, TideExtreme

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Shanghai"

# 与 thresholds.yaml confidence.midrange_day_threshold 默认一致（D+5+ 降级）
MIDRANGE_DAY_THRESHOLD = 5


class DataSourceError(RuntimeError):
    """数据源失败，附带受影响字段列表。"""

    def __init__(self, message: str, fields: list[str] | None = None):
        super().__init__(message)
        self.fields = fields or []


def _hourly(payload: dict) -> dict:
    return (payload or {}).get("hourly", {}) or {}


def _index_by_time(payload: dict) -> dict[str, int]:
    """把 hourly.time 列表映射为 {time_str: index}，便于跨源按时间对齐。"""
    times = _hourly(payload).get("time", []) or []
    return {t: i for i, t in enumerate(times)}


def _at(series: dict, key: str, idx: int | None):
    if idx is None:
        return None
    arr = series.get(key)
    if not arr or idx >= len(arr):
        return None
    return arr[idx]


def build_daily_forecasts(
    wam: dict,
    best: dict,
    wind: dict,
    *,
    sun: dict | None = None,
    midrange_threshold: int = MIDRANGE_DAY_THRESHOLD,
) -> list[DailyForecast]:
    """纯函数：把三路 hourly JSON 按 time 对齐合并为 DailyForecast 列表（按日期分组）。

    以 WAM 时间轴为主；best/wind 缺失字段回退或置默认；记录 source（需求 1.5）。
    """
    wam_h = _hourly(wam)
    best_h = _hourly(best)
    wind_h = _hourly(wind)
    times = wam_h.get("time", []) or []
    best_idx = _index_by_time(best)
    wind_idx = _index_by_time(wind)

    # 按日期分组累积时段
    by_date: dict[_date, list[ForecastPoint]] = {}
    order: list[_date] = []
    for i, tstr in enumerate(times):
        dt = datetime.fromisoformat(tstr)
        d = dt.date()
        bi = best_idx.get(tstr)
        wi = wind_idx.get(tstr)

        # 总浪高/向/周期：优先 WAM，缺则回退 best_match（需求 1.5）
        wh = _at(wam_h, "wave_height", i)
        source = "ecmwf_wam025"
        if wh is None:
            wh = _at(best_h, "wave_height", bi)
            source = "best_match(fallback)"
        if wh is None:
            continue  # 该时段无浪高数据，跳过

        point = ForecastPoint(
            time=dt,
            wave_height_m=float(wh),
            wave_direction_deg=float(_at(wam_h, "wave_direction", i)
                                     or _at(best_h, "wave_direction", bi) or 0.0),
            wave_period_mean_s=float(_at(wam_h, "wave_period", i)
                                     or _at(best_h, "wave_period", bi) or 0.0),
            wave_period_peak_s=_opt_float(_at(wam_h, "wave_peak_period", i)),
            swell_height_m=float(_at(best_h, "swell_wave_height", bi) or 0.0),
            swell_direction_deg=float(_at(best_h, "swell_wave_direction", bi) or 0.0),
            wind_wave_height_m=float(_at(best_h, "wind_wave_height", bi) or 0.0),
            wind_speed_kn=float(_at(wind_h, "wind_speed_10m", wi) or 0.0),
            wind_direction_deg=float(_at(wind_h, "wind_direction_10m", wi) or 0.0),
            wind_gust_kn=float(_at(wind_h, "wind_gusts_10m", wi) or 0.0),
            sea_level_m=float(_at(best_h, "sea_level_height_msl", bi) or 0.0),
            sst_c=float(_at(best_h, "sea_surface_temperature", bi) or 0.0),
            source=source,
        )
        if d not in by_date:
            by_date[d] = []
            order.append(d)
        by_date[d].append(point)

    # 日出日落映射（forecast daily）；未单独提供时回退到 wind 载荷自带的 daily
    sun_map = _sun_map(sun if sun is not None else wind)

    daily: list[DailyForecast] = []
    for offset, d in enumerate(order):
        is_mid = offset >= midrange_threshold
        pts = by_date[d]
        if is_mid:
            for p in pts:
                p.confidence = Confidence.LOW  # D+5+ 降级（需求 2.5）
        sr, ss = sun_map.get(d.isoformat(), (None, None))
        levels = [p.sea_level_m for p in pts]
        ptimes = [p.time for p in pts]
        daily.append(
            DailyForecast(
                date=d,
                points=pts,
                tide_extremes=extract_tide_extremes(levels, ptimes),
                sunrise=sr,
                sunset=ss,
                is_midrange=is_mid,
            )
        )
    return daily


def _opt_float(v):
    return float(v) if v is not None else None


def _sun_map(sun: dict | None) -> dict[str, tuple]:
    if not sun:
        return {}
    daily = (sun or {}).get("daily", {}) or {}
    days = daily.get("time", []) or []
    sunrise = daily.get("sunrise", []) or []
    sunset = daily.get("sunset", []) or []
    out = {}
    for i, d in enumerate(days):
        sr = datetime.fromisoformat(sunrise[i]) if i < len(sunrise) else None
        ss = datetime.fromisoformat(sunset[i]) if i < len(sunset) else None
        out[d] = (sr, ss)
    return out


def extract_tide_extremes(sea_level_series, times) -> list[TideExtreme]:
    """从海面高度序列提取局部高低潮极值（Task 3.3，需求 4.1）。

    局部极大→high，局部极小→low；端点与相邻相等忽略。
    """
    out: list[TideExtreme] = []
    n = len(sea_level_series)
    for i in range(1, n - 1):
        prev, cur, nxt = sea_level_series[i - 1], sea_level_series[i], sea_level_series[i + 1]
        if cur > prev and cur > nxt:
            out.append(TideExtreme(time=times[i], level_m=float(cur), kind="high"))
        elif cur < prev and cur < nxt:
            out.append(TideExtreme(time=times[i], level_m=float(cur), kind="low"))
    return out


def _build_marine_params(lat, lon, days, past_days, hourly_vars, model=None) -> dict:
    p = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(hourly_vars),
        "timezone": TIMEZONE,
        "forecast_days": days,
    }
    if past_days:
        p["past_days"] = past_days
    if model:
        p["models"] = model
    return p


def fetch_forecast(lat: float, lon: float, days: int, *, past_days: int = 0,
                   client=None, timeout: float = 20.0) -> list[DailyForecast]:
    """拉取并合并三路数据，返回 DailyForecast 列表（Task 3.1-3.3）。

    past_days>0 时进入历史模式（需求 1.4），口径与预报完全一致（同解析/合并路径）。
    失败抛 DataSourceError，标注受影响字段（需求 1.5）。
    """
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise DataSourceError("httpx 未安装", ["*"]) from e

    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        wam = _get(client, MARINE_URL, _build_marine_params(
            lat, lon, days, past_days,
            ["wave_height", "wave_direction", "wave_period", "wave_peak_period"],
            model="ecmwf_wam025"), ["wave_height", "wave_period"])
        best = _get(client, MARINE_URL, _build_marine_params(
            lat, lon, days, past_days,
            ["swell_wave_height", "swell_wave_direction", "wind_wave_height",
             "sea_level_height_msl", "sea_surface_temperature"]),
            ["swell_wave_height", "sea_level_height_msl"])
        wind_params = {
            "latitude": lat, "longitude": lon,
            "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "wind_speed_unit": "kn", "timezone": TIMEZONE, "forecast_days": days,
            "models": "ecmwf_ifs025", "daily": "sunrise,sunset",
        }
        if past_days:
            wind_params["past_days"] = past_days
        wind = _get(client, FORECAST_URL, wind_params, ["wind_speed_10m"])
    finally:
        if own_client:
            client.close()

    return build_daily_forecasts(wam, best, wind, sun=wind)


def _get(client, url, params, required_fields):
    """单次请求 + 基本校验；失败抛 DataSourceError 标注受影响字段。"""
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise DataSourceError(f"请求失败 {url}: {e}", required_fields) from e
    hourly = _hourly(data)
    empty = [f for f in required_fields if not hourly.get(f)]
    if empty:
        raise DataSourceError(f"字段为空 {url}: {empty}", empty)
    return data
