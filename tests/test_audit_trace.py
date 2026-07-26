# -*- coding: utf-8 -*-
"""D4 审计链解析器 单测——确定性（防回归）。"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_spec = importlib.util.spec_from_file_location(
    "audit_trace", os.path.join(_ROOT, "tools", "audit_trace.py"))
at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

_SAMPLE = [
    "- 2026-07-26 13:25 GMT+8 · v0.1.0 · e86f264 · G.1 首个版本化镜像发布 · 已滚动",
    "- 2026-07-26 14:00 GMT+8 · v0.1.1 · abc1234 · 需求seed-0001: 直播免责文案补充 · 已滚动",
    "  普通说明行(非条目,应被忽略)",
]


def _parse(lines, monkeypatch, tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr(at, "CHANGELOG", str(p))
    return at.parse_changelog()


def test_parse_changelog_matches_entries(monkeypatch, tmp_path):
    entries = _parse(_SAMPLE, monkeypatch, tmp_path)
    assert len(entries) == 2  # 忽略非条目行
    assert entries[0]["ver"] == "v0.1.0"
    assert entries[1]["commit"] == "abc1234"
    assert entries[1]["result"] == "已滚动"


def test_changelog_for_requirement_hit(monkeypatch, tmp_path):
    entries = _parse(_SAMPLE, monkeypatch, tmp_path)
    hit = at.changelog_for_requirement("seed-0001", entries)
    assert len(hit) == 1 and hit[0]["ver"] == "v0.1.1"


def test_changelog_for_requirement_miss(monkeypatch, tmp_path):
    entries = _parse(_SAMPLE, monkeypatch, tmp_path)
    assert at.changelog_for_requirement("seed-9999", entries) == []


def test_changelog_for_version(monkeypatch, tmp_path):
    entries = _parse(_SAMPLE, monkeypatch, tmp_path)
    assert len(at.changelog_for_version("v0.1.0", entries)) == 1


def test_parse_ignores_malformed_lines(monkeypatch, tmp_path):
    # 坏行不应崩解析器(逐条隔离)
    entries = _parse(["- 残缺行没有分隔", "# 标题", ""], monkeypatch, tmp_path)
    assert entries == []
