# -*- coding: utf-8 -*-
"""
Google Sheets への参加者データ書き込み
- スレッド名をタブ名としてスレッドごとに分けて保存
- ユーザーIDをキーとしてupsert
"""

import gspread
import google.auth
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ヘッダー行
HEADERS = [
    "ユーザーname",
    "DiscordID",
    "ユーザーID",
    "バトルタグ",
    "プラットフォーム",
    "タンクランク",
    "ダメージランク",
    "サポートランク",
    "メインロール",
    "希望ゲスト",
    "コメント",
]


def _get_sheet(thread_name: str) -> gspread.Worksheet:
    creds, _ = google.auth.default(scopes=SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(config.SPREADSHEET_ID)

    # Googleスプシのタブ名上限は100文字
    tab_name = thread_name[:100]

    try:
        sheet = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(HEADERS))
        sheet.append_row(HEADERS)

    return sheet


def upsert_participant(user_id: int, display_name: str, discord_name: str, answers: dict, thread_name: str = "参加者"):
    """参加者データをスプシに書き込む（既存行は上書き）"""
    sheet = _get_sheet(thread_name)

    row_data = [
        display_name,
        discord_name,
        str(user_id),
        answers.get("battletag", ""),
        answers.get("platform", ""),
        answers.get("tank_rank", ""),
        answers.get("dps_rank", ""),
        answers.get("support_rank", ""),
        answers.get("main_role", ""),
        answers.get("preferred_guest", ""),
        answers.get("comment", ""),
    ]

    col_c = sheet.col_values(3)
    user_id_str = str(user_id)

    if user_id_str in col_c:
        row_index = col_c.index(user_id_str) + 1
        sheet.update(f"A{row_index}:K{row_index}", [row_data])
    else:
        sheet.append_row(row_data)
