"""P2.2 单测：SF_SPA_DIST 门控的 SPA 服务 + history 回退 + /api 不被遮蔽 + 默认行为不变。"""
from fastapi.testclient import TestClient

import web.app as A


def test_spa_served_and_history_fallback(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<div id='app'>VUE_SPA</div>", encoding="utf-8")
    monkeypatch.setattr(A, "_SPA_DIST", str(tmp_path))
    c = TestClient(A.app)
    assert "VUE_SPA" in c.get("/").text                      # / 服 SPA
    r = c.get("/spot/shandongtou")                            # 未知非 api 路径 → history 回退
    assert r.status_code == 200 and "VUE_SPA" in r.text
    assert c.get("/api/health").json() == {"status": "ok"}    # /api 未被 catch-all 遮蔽
    assert c.get("/api/nope").status_code == 404              # /api 未知 → 404，不返回 SPA


def test_no_spa_default_unknown_404(monkeypatch):
    monkeypatch.setattr(A, "_SPA_DIST", "")
    c = TestClient(A.app)
    assert c.get("/some/unknown/path").status_code == 404     # 无 SPA → 404，行为同前（并行安全）
