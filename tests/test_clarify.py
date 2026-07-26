# -*- coding: utf-8 -*-
"""L2.3 /api/clarify 单测（LLM 全 mock，不触网）：降级/LLM/畸形/缓存 分支。"""
import pytest
from fastapi.testclient import TestClient

import web.app as A
import web.llm_client as L


@pytest.fixture
def client():
    return TestClient(A.app)


def test_clarify_degrades_when_llm_unconfigured(client, monkeypatch):
    monkeypatch.setattr(L, "is_configured", lambda: False)
    r = client.post("/api/clarify", json={"page": "report", "step": 2, "chosen": []})
    j = r.json()
    assert r.status_code == 200 and j["degraded"] is True and j["source"] == "template"
    assert len(j["options"]) >= 3


def test_clarify_uses_llm_when_valid(client, monkeypatch):
    monkeypatch.setattr(L, "is_configured", lambda: True)
    monkeypatch.setattr(A, "_llm_chat", lambda msgs: '{"options":["评分偏乐观","图表不显","离岸判定错"]}')
    A._clarify_cache.clear()
    r = client.post("/api/clarify", json={"page": "live", "step": 5, "chosen": ["a"]})
    j = r.json()
    assert j["degraded"] is False and j["source"] == "llm" and j["options"][0] == "评分偏乐观"


def test_clarify_degrades_on_malformed_llm(client, monkeypatch):
    monkeypatch.setattr(L, "is_configured", lambda: True)
    monkeypatch.setattr(A, "_llm_chat", lambda msgs: "这不是 JSON")
    A._clarify_cache.clear()
    r = client.post("/api/clarify", json={"page": "live", "step": 6, "chosen": ["b"]})
    assert r.json()["source"] == "template" and r.json()["degraded"] is True


def test_clarify_degrades_on_gateway_error(client, monkeypatch):
    monkeypatch.setattr(L, "is_configured", lambda: True)
    def _boom(msgs):
        raise L.LLMError("网关不通")
    monkeypatch.setattr(A, "_llm_chat", _boom)
    A._clarify_cache.clear()
    r = client.post("/api/clarify", json={"page": "other", "step": 7, "chosen": ["c"]})
    assert r.json()["source"] == "template"


def test_clarify_cache_hit_second_call(client, monkeypatch):
    monkeypatch.setattr(L, "is_configured", lambda: True)
    calls = {"n": 0}
    def _once(msgs):
        calls["n"] += 1
        return '{"options":["缓存项1","缓存项2"]}'
    monkeypatch.setattr(A, "_llm_chat", _once)
    A._clarify_cache.clear()
    body = {"page": "live", "step": 3, "chosen": ["dup"]}
    r1 = client.post("/api/clarify", json=body)
    r2 = client.post("/api/clarify", json=body)          # 同键 → 缓存命中,不再调 LLM
    assert r1.json()["source"] == "llm" and r2.json()["source"] == "cache"
    assert calls["n"] == 1
