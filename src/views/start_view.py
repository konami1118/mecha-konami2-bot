# -*- coding: utf-8 -*-
"""
スレッドに投稿される「応募する」ボタン
"""

import json
import os
import discord
from src.forms.session import store
from src.views.form_view import FormView

SUBMISSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "submissions")


class StartView(discord.ui.View):
    def __init__(self, guests: list[str], event_type: str = "custom", is_open: bool = True):
        super().__init__(timeout=None)  # 永続ボタン
        self.guests = guests
        self.event_type = event_type
        self._update_button(is_open)

    def _update_button(self, is_open: bool):
        self.clear_items()
        btn = discord.ui.Button(
            label="応募する" if is_open else "受付終了",
            style=discord.ButtonStyle.primary if is_open else discord.ButtonStyle.secondary,
            custom_id="apply_start",
            disabled=not is_open,
        )
        btn.callback = self._on_click
        self.add_item(btn)

        if is_open:
            cancel_btn = discord.ui.Button(
                label="応募取り消し",
                style=discord.ButtonStyle.danger,
                custom_id="apply_reset",
            )
            cancel_btn.callback = self._on_reset
            self.add_item(cancel_btn)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print(f"[ERROR] StartView エラー: {error}")
        traceback.print_exc()
        if not interaction.response.is_done():
            await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)

    async def _on_reset(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        thread = interaction.channel
        thread_id = thread.id

        # セッション削除
        store.delete(user_id)

        # submissions.json から該当ユーザーの応募を削除
        path = os.path.join(SUBMISSIONS_DIR, f"{thread_id}.json")
        msg_deleted = False
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                submissions = json.load(f)
            entry = submissions.pop(str(user_id), None)
            if entry and entry.get("message_id"):
                try:
                    msg = await thread.fetch_message(entry["message_id"])
                    await msg.delete()
                    msg_deleted = True
                except discord.NotFound:
                    pass
            with open(path, "w", encoding="utf-8") as f:
                json.dump(submissions, f, ensure_ascii=False, indent=2)

        print(f"[CANCEL] {interaction.user} ({user_id}) が応募を取り消し / スレッド: {thread.name} / メッセージ削除: {msg_deleted}")
        if msg_deleted:
            await interaction.response.send_message("応募を取り消しました。", ephemeral=True)
        else:
            await interaction.response.send_message("応募データが見つかりませんでした（未応募または取り消し済み）。", ephemeral=True)

    async def _on_click(self, interaction: discord.Interaction):
        from src.utils import extract_guests_from_title
        thread = interaction.channel
        guests, event_type = extract_guests_from_title(thread.name)
        if not guests:
            await interaction.response.send_message("スレッド情報を取得できませんでした。管理者にお知らせください。", ephemeral=True)
            return

        user_id = interaction.user.id
        thread_id = interaction.channel_id

        existing = store.get(user_id)
        if existing:
            # 古いセッションは破棄して再スタート
            store.delete(user_id)

        store.create(user_id, thread_id)
        print(f"[START] {interaction.user} ({interaction.user.id}) が応募を開始 / スレッド: {thread.name} / イベント: {event_type}")

        view = FormView(user_id, guests, event_type=event_type, start_interaction=interaction)
        await interaction.response.send_message(
            view.current_prompt(),
            view=view,
            ephemeral=True
        )
