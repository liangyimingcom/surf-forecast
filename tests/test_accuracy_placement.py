# -*- coding: utf-8 -*-
"""4.1 test_placement (F7)：昨日回看区块须在日卡(#cards)之后（源序/DOM 顺序）。"""
import os

_HTML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "浪报MVP.html")


def _html():
    with open(_HTML, encoding="utf-8") as f:
        return f.read()


def test_review_after_cards():
    s = _html()
    i_cards = s.find('id="cards"')
    i_verify = s.find('id="verify"')
    assert i_cards != -1, "缺 #cards 日卡容器"
    assert i_verify != -1, "缺 #verify 昨日回看区块"
    assert i_verify > i_cards, "昨日回看须在日卡之后(F7)"


def test_rate_posts_vote_api():
    # 2.3：rateYesterday 应上报 /api/accuracy/vote（登录态）
    s = _html()
    seg = s[s.find("function rateYesterday"): s.find("function rateYesterday") + 900]
    assert "/api/accuracy/vote" in seg and "credentials" in seg
