"""H1.1 坐标护栏 — 导入路径不得静默放非法坐标进刷新池。

背景（真实事故）：石老人源快照里 sl75(石梅湾九里)/sl76(富力湾全景) 的 lat=110.363232
（>90，实为经度值）。导入路径 build_registry_rows 过去绕过了用户 CRUD 必过的
spots_model.validate_coord，两点因此带着非法坐标进了注册表并 refresh_enabled=True
→ Open-Meteo 每日返回 "Latitude must be in range of -90 to 90°"
→ 刷新固定 58/60、failed=[sl75,sl76]，持续一周无人察觉。

护栏语义（不是丢弃，是隔离）：
  - 仍写入注册表且 status=active  → 公开目录/直播照常可见（守"可见性不耦合刷新开关"红线）
  - refresh_enabled=False        → 退出刷新池，manifest expected 不再包含它 → 不再每日失败
  - op_status="pending" + coord_invalid=<原因>  → 状态可见，可被人工修坐标后解封
"""
from __future__ import annotations
import json
import pathlib
import pytest

from web import seed as _seed
from web import spots_model as sm

SNAPSHOT = pathlib.Path(__file__).resolve().parents[1] / "reference" / "data" / "shilaoren_spots.json"
BAD_SLUGS = {"sl75", "sl76"}


def _rows():
    return _seed.build_registry_rows(json.loads(SNAPSHOT.read_text(encoding="utf-8")))


def test_snapshot_still_has_the_two_bad_coords():
    """源数据事实钉死：快照里恰好这两点 lat 越界（若上游修了，此测试会提醒我们解封）。"""
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    bad = {s["slug"] for s in snap["spots"]
           if isinstance(s.get("lat"), (int, float)) and not (-90 <= s["lat"] <= 90)}
    assert bad == BAD_SLUGS, f"快照越界点变了: {bad}"


def test_bad_coord_rows_are_quarantined_not_dropped():
    rows = {r["slug"]: r for r in _rows()}
    # 不丢弃：仍在注册表、仍 active（公开目录可见）
    for slug in BAD_SLUGS:
        assert slug in rows, f"{slug} 被丢弃了——应隔离而非丢弃（目录可见性红线）"
        assert rows[slug]["status"] == "active"
        # 隔离：退出刷新池 + 状态可见
        assert rows[slug]["refresh_enabled"] is False
        assert rows[slug]["op_status"] == "pending"
        assert "lat 超范围" in rows[slug]["coord_invalid"]


def test_good_coord_rows_unaffected():
    rows = [r for r in _rows() if r["slug"] not in BAD_SLUGS]
    assert len(rows) >= 55, "正常点数量异常，护栏疑似误伤"
    assert all(r["refresh_enabled"] is True for r in rows)
    assert all("coord_invalid" not in r for r in rows)


def test_total_registry_count_unchanged():
    """隔离不减少目录条数（58 全在），只把 2 点移出刷新池。"""
    rows = _rows()
    assert len(rows) == 58
    assert sum(1 for r in rows if r["refresh_enabled"]) == 56


def test_crud_path_still_fails_loud():
    """用户 CRUD 路径语义不变：非法坐标直接抛错（不隔离、不静默）。"""
    with pytest.raises(ValueError, match="lat 超范围"):
        sm.validate_coord(110.363232, 114.842491)
    with pytest.raises(ValueError, match="lon 超范围"):
        sm.validate_coord(18.6, 200.0)
