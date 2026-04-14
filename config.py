# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from google.cloud import secretmanager

load_dotenv()

_PROJECT_ID = "ow-discord-event-support-bot"


def _secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{_PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


BOT_TOKEN = _secret("DISCORD_BOT_TOKEN")
SERVER_ID = int(_secret("DISCORD_SERVER_ID"))
SPREADSHEET_ID = _secret("SPREADSHEET_ID")

ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "900"))

if not BOT_TOKEN:
    raise ValueError("Secret Manager から DISCORD_BOT_TOKEN を取得できませんでした")
if not SERVER_ID:
    raise ValueError("Secret Manager から DISCORD_SERVER_ID を取得できませんでした")
