# -*- coding: utf-8 -*-
"""
応募フォームのステップ定義
"""

# ランクティア（ランク名, ブロンズ最上段）
RANK_TIERS = [
    "未プレイ",
    "ブロンズ", "シルバー", "ゴールド", "プラチナ",
    "ダイヤ", "マスター", "グランドマスター", "チャンピオン",
]

# ランクディビジョン（数字, 1最上段）
RANK_DIVISIONS = ["1", "2", "3", "4", "5"]

MAIN_ROLES = ["タンク", "ダメージ", "サポート"]

PLATFORMS = ["PC", "CS"]

STEPS = [
    "battletag",
    "platform",
    "tank_rank",
    "dps_rank",
    "support_rank",
    "main_role",
    "preferred_guest",
    "comment",
]

STEP_LABELS = {
    "battletag":       "バトルタグ",
    "platform":        "プラットフォーム",
    "tank_rank":       "タンク最高ランク",
    "dps_rank":        "ダメージ最高ランク",
    "support_rank":    "サポート最高ランク",
    "main_role":       "メインロール",
    "preferred_guest": "一緒に戦いたいゲスト",
    "comment":         "コメント（任意）",
}

RANK_STEPS = {"tank_rank", "dps_rank", "support_rank"}
