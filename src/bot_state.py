# -*- coding: utf-8 -*-
"""
bot.py と handlers で共有する状態
"""

import json
import os

# スレッドID → StartView のマッピング
active_views: dict = {}
# スレッドID → 応募メッセージID のマッピング
apply_messages: dict = {}

APPLY_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "apply_state.json")


def save_apply_state():
    os.makedirs(os.path.dirname(APPLY_STATE_FILE), exist_ok=True)
    state = {
        str(tid): {
            "msg_id": apply_messages[tid],
            "guests": active_views[tid].guests,
            "event_type": active_views[tid].event_type,
        }
        for tid in active_views if tid in apply_messages
    }
    with open(APPLY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def load_apply_state() -> dict:
    if os.path.exists(APPLY_STATE_FILE):
        with open(APPLY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
