# -*- coding: utf-8 -*-
"""
スレッドタイトルからゲスト名とイベント種別を抽出
"""

import re


def extract_guests_from_title(title: str) -> tuple[list[str], str]:
    """
    スレッドタイトルからゲスト名とイベント種別を返す。

    戻り値:
        (guests, event_type)
        event_type: "coaching" (＆区切り) or "custom" (それ以外)

    対応パターン例:
    - "なるる vs 雪のれんこん"  → custom
    - "末っ子かわい × もふもふゆ" → custom
    - "なるる ＆ 雪のれんこん"   → coaching
    """
    # ＆（全角）のみコーチング、それ以外はカスタム
    m_coaching = re.search(r'(\S+)\s*＆\s*(\S+)', title)
    if m_coaching:
        g1, g2 = _clean(m_coaching.group(1)), _clean(m_coaching.group(2))
        return [g for g in [g1, g2] if g], "coaching"

    m_custom = re.search(
        r'(\S+)\s*(?:vs\.?|VS\.?|&|×|対)\s*(\S+)',
        title
    )
    if m_custom:
        g1, g2 = _clean(m_custom.group(1)), _clean(m_custom.group(2))
        return [g for g in [g1, g2] if g], "custom"

    return [], "custom"


def _clean(s: str) -> str:
    return re.sub(r'[！!、。　＼\/].*$', '', s).strip()
