"""R3 坐标解析歧义防护 —— 同 4dp 坐标命中多行时必须确定性选取，且两个 store 语义一致。

背景（真实数据）：注册表里存在同 4dp 坐标的多个浪点（2026-08-05 生产实测 3 组，
其中 `sl54 虹海湾山海里` / `sl84 Kirra` 跨滩跨区 = 真数据损坏）。
旧实现两个 store 都「取迭代顺序里的第一个」，而 **DynamoDB scan 顺序不保证稳定**
→ 同一坐标可能今天解析成 A、明天解析成 B → S3 缓存键跟着翻
→ 详情页可能显示另一个浪点的报告。与 v0.3.2「坐标精度错位致缓存永不命中」同族。
"""
from __future__ import annotations

import logging

import boto3
import pytest
from moto import mock_aws

from web import db

PREFIX = "surf-forecast-r3"


def _row(slug, lat, lon, **kw):
    return {"slug": slug, "spot": slug.upper(), "lat": lat, "lon": lon,
            "status": "active", **kw}


# —— 共享判定函数（两个 store 都委托它，语义一致由构造保证）——

def test_pick_none_when_no_match():
    assert db.pick_registry_match([], 1.0, 2.0) is None


def test_pick_single_match_returned_asis():
    r = _row("only", 1.0, 2.0)
    assert db.pick_registry_match([r], 1.0, 2.0) is r


def test_pick_multi_is_deterministic_by_slug():
    rows = [_row("sl84", 3.0, 4.0), _row("sl54", 3.0, 4.0)]
    assert db.pick_registry_match(rows, 3.0, 4.0)["slug"] == "sl54"
    # 反序输入同样结果（确定性，不依赖入参顺序）
    assert db.pick_registry_match(rows[::-1], 3.0, 4.0)["slug"] == "sl54"


def test_pick_multi_warns_with_all_slugs(caplog):
    """告警必须列出全部候选 + 实际选中者，否则站长无从核对。"""
    with caplog.at_level(logging.WARNING, logger="web.db"):
        db.pick_registry_match([_row("sl84", 3.0, 4.0), _row("sl54", 3.0, 4.0)], 3.0, 4.0)
    msg = caplog.text
    assert "解析歧义" in msg and "sl54" in msg and "sl84" in msg


# —— InMemoryStore ——

def test_inmemory_multi_match_deterministic():
    s = db.InMemoryStore()
    for r in (_row("sl84", 22.6017, 114.9073), _row("sl54", 22.6017, 114.9073)):
        s.upsert_registry(r)
    assert s.find_registry_by_coord(22.6017, 114.9073)["slug"] == "sl54"


def test_inmemory_insert_order_does_not_change_result():
    """插入顺序反过来也必须选中同一行（旧实现会翻）。"""
    a, b = _row("sl54", 1.0, 2.0), _row("sl84", 1.0, 2.0)
    s1, s2 = db.InMemoryStore(), db.InMemoryStore()
    for r in (a, b):
        s1.upsert_registry(r)
    for r in (b, a):
        s2.upsert_registry(r)
    assert s1.find_registry_by_coord(1.0, 2.0)["slug"] == \
        s2.find_registry_by_coord(1.0, 2.0)["slug"] == "sl54"


def test_inmemory_inactive_rows_ignored():
    s = db.InMemoryStore()
    s.upsert_registry(_row("gone", 1.0, 2.0, status="inactive"))
    assert s.find_registry_by_coord(1.0, 2.0) is None


def test_inmemory_precision_is_4dp():
    """匹配精度必须与 dedup_key 一致：6 位小数入库、4 位查询也要命中
    （v0.3.2 就是这个精度错位导致 S3 缓存从未命中）。"""
    s = db.InMemoryStore()
    s.upsert_registry(_row("p", 18.66726619819232, 110.28828471517565))
    assert s.find_registry_by_coord(18.6673, 110.2883)["slug"] == "p"


# —— DynamoDBStore（moto 真跑）与 InMemoryStore 等价 ——

@pytest.fixture
def ddb():
    with mock_aws():
        res = boto3.resource("dynamodb", region_name="ap-northeast-1")
        res.create_table(
            TableName=f"{PREFIX}-spot_registry",
            KeySchema=[{"AttributeName": "slug", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "slug", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        yield db.DynamoDBStore(PREFIX, resource=res)


def test_two_stores_pick_the_same_row(ddb):
    rows = [_row("sl84", 22.6017, 114.9073), _row("sl54", 22.6017, 114.9073)]
    mem = db.InMemoryStore()
    for r in rows:
        mem.upsert_registry(dict(r))
        ddb.upsert_registry(dict(r))
    got_mem = mem.find_registry_by_coord(22.6017, 114.9073)["slug"]
    got_ddb = ddb.find_registry_by_coord(22.6017, 114.9073)["slug"]
    assert got_mem == got_ddb == "sl54"      # 两 store 语义一致（R3 验收）


def test_ddb_no_match_returns_none(ddb):
    ddb.upsert_registry(_row("x", 1.0, 2.0))
    assert ddb.find_registry_by_coord(50.0, 60.0) is None
