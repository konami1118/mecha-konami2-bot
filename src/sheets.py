# -*- coding: utf-8 -*-
"""
Google Sheets への参加者データ書き込み
- スレッド名をタブ名としてスレッドごとに分けて保存
- ユーザーIDをキーとしてupsert
"""

import json
from datetime import datetime, timezone, timedelta
import gspread
from google.cloud import secretmanager
from google.oauth2.service_account import Credentials
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_PROJECT_ID = "ow-discord-event-support-bot"
_cached_creds: Credentials = None


def _get_sheets_credentials() -> Credentials:
    global _cached_creds
    if _cached_creds is not None:
        return _cached_creds
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{_PROJECT_ID}/secrets/SHEETS_SERVICE_ACCOUNT_KEY/versions/latest"
    response = client.access_secret_version(request={"name": name})
    key_info = json.loads(response.payload.data.decode("UTF-8"))
    _cached_creds = Credentials.from_service_account_info(key_info, scopes=SCOPES)
    return _cached_creds

# ヘッダー行
HEADERS = [
    "初回応募日時",   # A
    "ユーザーname",   # B
    "DiscordID",      # C
    "ユーザーID",     # D
    "バトルタグ",     # E
    "プラットフォーム", # F
    "タンクランク",   # G
    "ダメージランク", # H
    "サポートランク", # I
    "メインロール",   # J
    "希望ゲスト",     # K
    "コメント",       # L
    "ステータス",     # M
    "最終更新日時",   # N
]

# ステータス定数
STATUS_NEW    = "回答済み"
STATUS_EDITED = "編集済み"
STATUS_CANCELLED = "取り消し済み"


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

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

    col_d = sheet.col_values(4)
    user_id_str = str(user_id)
    is_existing = user_id_str in col_d
    status = STATUS_EDITED if is_existing else STATUS_NEW

    if is_existing:
        row_index = col_d.index(user_id_str) + 1
        # 初回応募日時（A列）を保持する
        first_submitted_at = sheet.cell(row_index, 1).value or now
        row_data = [
            first_submitted_at,
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
            status,
            now,
        ]
        sheet.update([row_data], f"A{row_index}:N{row_index}")
        print(f"[Sheets] 既存行を更新: row={row_index}, status={status}")
    else:
        row_data = [
            now,
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
            status,
            now,
        ]
        sheet.append_row(row_data)
        print(f"[Sheets] 新規行を追加, status={status}")


def cancel_participant(user_id: int, thread_name: str):
    """スプシの該当ユーザー行のステータスを「取り消し済み」に更新する"""
    print(f"[Sheets] cancel_participant 開始: user_id={user_id}, thread={thread_name}")
    try:
        sheet = _get_sheet(thread_name)

        col_d = sheet.col_values(4)
        user_id_str = str(user_id)

        if user_id_str not in col_d:
            print(f"[Sheets] cancel_participant: ユーザーが見つからない (user_id={user_id})")
            return

        row_index = col_d.index(user_id_str) + 1
        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")
        # ステータス(M列=13)と最終更新日時(N列=14)を更新
        sheet.update_cell(row_index, 13, STATUS_CANCELLED)
        sheet.update_cell(row_index, 14, now)
        print(f"[Sheets] ステータスを「取り消し済み」に更新: row={row_index}")
    except Exception as e:
        import traceback
        print(f"[Sheets] cancel_participant エラー: {e}")
        traceback.print_exc()
