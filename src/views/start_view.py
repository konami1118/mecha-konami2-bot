# -*- coding: utf-8 -*-
"""
スレッドに投稿される「応募する」ボタン
"""

import asyncio
import json
import os
import discord
from src.forms.session import store
from src.sheets import cancel_participant
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
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"エラーが発生しました: {error}", ephemeral=True)
        except discord.HTTPException:
            pass

    async def _on_reset(self, interaction: discord.Interaction):
        print(f"[RESET] {interaction.user} が応募取り消しボタンを押した（ダイアログ表示のみ、削除なし）")
        try:
            confirm_view = _CancelConfirmView(interaction.user.id, interaction.channel)
            await interaction.response.send_message(
                "本当に応募を取り消しますか？",
                view=confirm_view,
                ephemeral=True,
            )
        except discord.NotFound:
            print("[WARN] _on_reset: インタラクションが期限切れ")

    async def _on_click(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            print(f"[WARN] _on_click: インタラクションが期限切れ（defer失敗） (user_id={interaction.user.id})")
            return

        from src.utils import extract_guests_from_title
        thread = interaction.channel
        guests, event_type = extract_guests_from_title(thread.name)
        if not guests:
            await interaction.followup.send("スレッド情報を取得できませんでした。管理者にお知らせください。", ephemeral=True)
            return

        user_id = interaction.user.id
        thread_id = interaction.channel_id

        existing = store.get(user_id)
        if existing:
            # 5秒以内に作られたセッションはダブルクリックとみなして無視
            import time
            if time.time() - existing.created_at < 5:
                print(f"[WARN] _on_click: ダブルクリックを無視 (user_id={user_id})")
                try:
                    await interaction.delete_original_response()
                except discord.HTTPException:
                    pass
                return
            store.delete(user_id)

        store.create(user_id, thread_id)
        print(f"[START] {interaction.user} ({interaction.user.id}) が応募を開始 / スレッド: {thread.name} / イベント: {event_type}")

        view = FormView(user_id, guests, event_type=event_type, start_interaction=interaction)
        await interaction.followup.send(
            view.current_prompt(),
            view=view,
            ephemeral=True
        )


class _CancelConfirmView(discord.ui.View):
    def __init__(self, user_id: int, thread):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.thread = thread

        # インスタンスごとにユニークなcustom_idを生成（デコレータはクラス共通IDになるためNG）
        confirm_btn = discord.ui.Button(label="はい、取り消す", style=discord.ButtonStyle.danger)
        confirm_btn.callback = self._on_confirm
        cancel_btn = discord.ui.Button(label="キャンセル", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self._on_cancel
        self.add_item(confirm_btn)
        self.add_item(cancel_btn)

    async def _on_confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの操作ではありません。", ephemeral=True)
            return
        await self._do_cancel(interaction)

    async def _on_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの操作ではありません。", ephemeral=True)
            return
        await interaction.response.edit_message(content="取り消しをキャンセルしました。", view=None)

    async def _do_cancel(self, interaction: discord.Interaction):
        thread_id = self.thread.id
        store.delete(self.user_id)

        path = os.path.join(SUBMISSIONS_DIR, f"{thread_id}.json")
        entry_found = False
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                submissions = json.load(f)
            entry = submissions.pop(str(self.user_id), None)
            if entry:
                entry_found = True
                if entry.get("message_id"):
                    try:
                        print(f"[DELETE] 応募embed削除: message_id={entry['message_id']}, user={interaction.user}")
                        msg = await self.thread.fetch_message(entry["message_id"])
                        await msg.delete()
                    except discord.NotFound:
                        pass
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(submissions, f, ensure_ascii=False, indent=2)

        print(f"[CANCEL] {interaction.user} ({self.user_id}) が応募を取り消し / スレッド: {self.thread.name} / エントリ存在: {entry_found}")
        if entry_found:
            await asyncio.to_thread(cancel_participant, self.user_id, self.thread.name)
            await interaction.response.edit_message(content="応募を取り消しました。", view=None)
        else:
            await interaction.response.edit_message(content="応募データが見つかりませんでした（未応募または取り消し済み）。", view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print(f"[ERROR] _CancelConfirmView エラー: {error}")
        traceback.print_exc()
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(content="⚠️ エラーが発生しました。もう一度お試しください。", view=None)
            else:
                await interaction.edit_original_response(content="⚠️ エラーが発生しました。もう一度お試しください。", view=None)
        except discord.HTTPException:
            pass
