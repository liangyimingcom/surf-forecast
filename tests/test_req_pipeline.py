# -*- coding: utf-8 -*-
"""D2 pipeline 安全门 单测——确定性、双侧钉死边界（防 AI 自测自过 + 防回归）。"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_PIPE = os.path.join(_ROOT, "tools", "req_pipeline.py")
_spec = importlib.util.spec_from_file_location("req_pipeline", _PIPE)
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


# ---- 资格门 ----
def test_eligibility_accepted_frontend_ok():
    req = {"status": "accepted", "kind": "improve", "auto_eligible": True, "rollbackable": True}
    assert rp.gate_eligibility(req).ok is True

def test_eligibility_remove_never_auto():
    req = {"status": "accepted", "kind": "remove", "auto_eligible": True, "rollbackable": True}
    assert rp.gate_eligibility(req).ok is False

def test_eligibility_not_accepted_blocked():
    for st in ("new", "triaged", "in_progress", "rejected", "expired"):
        req = {"status": st, "kind": "improve", "auto_eligible": True, "rollbackable": True}
        assert rp.gate_eligibility(req).ok is False

def test_eligibility_not_rollbackable_blocked():
    req = {"status": "accepted", "kind": "improve", "auto_eligible": True, "rollbackable": False}
    assert rp.gate_eligibility(req).ok is False


# ---- 路径白名单门（禁碰 web/e2e/，⊆ 白名单）----
def test_whitelist_only_html_ok():
    assert rp.gate_path_whitelist({"web/浪报MVP.html"}).ok is True

def test_whitelist_touch_e2e_blocked():
    assert rp.gate_path_whitelist({"web/浪报MVP.html", "web/e2e/new_features.mjs"}).ok is False

def test_whitelist_backend_change_blocked():
    assert rp.gate_path_whitelist({"src/web/app.py"}).ok is False

def test_whitelist_empty_blocked():
    assert rp.gate_path_whitelist(set()).ok is False


# ---- 非删除门（附加式）----
def test_non_delete_pure_add_ok():
    assert rp.gate_non_delete(["<p>新增文案</p>"], []).ok is True

def test_non_delete_text_replace_ok():
    # 单行文案替换：removed=1, added=1（净删除不超）
    assert rp.gate_non_delete(["新文案。"], ["旧文案。"]).ok is True

def test_non_delete_remove_element_blocked():
    assert rp.gate_non_delete([], ['<div id="cam">x</div>']).ok is False

def test_non_delete_remove_function_blocked():
    assert rp.gate_non_delete([], ["function openCam(){}"]).ok is False

def test_non_delete_net_removal_blocked():
    # 净删除行数 > 新增（边界：2 removed > 1 added）
    assert rp.gate_non_delete(["a"], ["x", "y"]).ok is False
def test_non_delete_equal_counts_ok():
    # 边界另一侧：1 == 1，不触发净删除
    assert rp.gate_non_delete(["a"], ["b"]).ok is True


# ---- secret / 后门 / 新出网 扫描门 ----
def test_secret_apikey_blocked():
    assert rp.gate_secret_scan(["const k='sk-ABCDEF0123456789xyz'"]).ok is False

def test_secret_awskey_blocked():
    assert rp.gate_secret_scan(["AKIAIOSFODNN7EXAMPLE"]).ok is False

def test_secret_eval_blocked():
    assert rp.gate_secret_scan(["eval(userInput)"]).ok is False

def test_secret_innerhtml_blocked():
    assert rp.gate_secret_scan(["el.innerHTML = data"]).ok is False

def test_secret_new_outbound_blocked():
    assert rp.gate_secret_scan(["fetch('https://evil.example.com/x')"]).ok is False

def test_secret_known_host_ok():
    # 已知上游域不算新增出网
    assert rp.gate_secret_scan(["fetch('https://api.open-meteo.com/v1/marine')"]).ok is True

def test_secret_clean_text_ok():
    assert rp.gate_secret_scan(["直播流来自公开来源，仅供研究用途；信号可能随时段变化。"]).ok is True
