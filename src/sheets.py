# -*- coding: utf-8 -*-
"""
Google Sheets への参加者データ書き込み
- スレッド名をタブ名としてスレッドごとに分けて保存
- ユーザーIDをキーとしてupsert
"""

import json
import gspread
from google.cloud import secretmanager
from google.oauth2.service_account import Credentials
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_PROJECT_ID = "ow-discord-event-support-bot"


def _get_sheets_credentials() -> Credentials:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{_PROJECT_ID}/secrets/SHEETS_SERVICE_ACCOUNT_KEY/versions/latest"
    response = client.access_secret_version(request={"name": name})
    key_info = json.loads(response.payload.data.decode("UTF-8"))
    return Credentials.from_service_account_info(key_info, scopes=SCOPES)

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
    print(f"[Sheets] 認証中...")
    creds = _get_sheets_credentials()
    gc = gspread.authorize(creds)
    print(f"[Sheets] スプレッドシートを開く: {config.SPREADSHEET_ID}")
    spreadsheet = gc.open_by_key(config.SPREADSHEET_ID)

    # Googleスプシのタブ名上限は100文字
    tab_name = thread_name[:100]
    print(f"[Sheets] タブ名: {tab_name}")

    try:
        sheet = spreadsheet.worksheet(tab_name)
        print(f"[Sheets] 既存タブを使用")
    except gspread.WorksheetNotFound:
        print(f"[Sheets] タブが存在しないため新規作成")
        sheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(HEADERS))
        sheet.append_row(HEADERS)

    return sheet


def upsert_participant(user_id: int, display_name: str, discord_name: str, answers: dict, thread_name: str = "参加者"):
    """参加者データをスプシに書き込む（既存行は上書き）"""
    print(f"[Sheets] upsert_participant 開始: user_id={user_id}, thread={thread_name}")
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
        print(f"[Sheets] 既存行を更新: row={row_index}")
    else:
        sheet.append_row(row_data)
        print(f"[Sheets] 新規行を追加")
