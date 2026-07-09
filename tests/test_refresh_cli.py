"""refresh_cli 入口单测 —— 退出码语义（缺env=2 / 有ok=0 / 全跳过=1）。"""

from web import refresh_cli


def test_missing_bucket_returns_2(monkeypatch):
    monkeypatch.delenv("SF_CACHE_BUCKET", raising=False)
    assert refresh_cli.main() == 2


def test_success_returns_0(monkeypatch):
    monkeypatch.setenv("SF_CACHE_BUCKET", "b")
    monkeypatch.setattr(refresh_cli, "S3CacheWriter", lambda bucket: object())
    monkeypatch.setattr(refresh_cli, "recycle_cold_spots", lambda store: [])
    monkeypatch.setattr(refresh_cli, "scheduled_refresh", lambda store, w: {"shandongtou": "ok"})
    assert refresh_cli.main() == 0


def test_all_skipped_returns_1(monkeypatch):
    monkeypatch.setenv("SF_CACHE_BUCKET", "b")
    monkeypatch.setattr(refresh_cli, "S3CacheWriter", lambda bucket: object())
    monkeypatch.setattr(refresh_cli, "recycle_cold_spots", lambda store: [])
    monkeypatch.setattr(refresh_cli, "scheduled_refresh",
                        lambda store, w: {"shandongtou": "skipped: error(X)"})
    assert refresh_cli.main() == 1
