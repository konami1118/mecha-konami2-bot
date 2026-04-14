# -*- coding: utf-8 -*-
"""
スレッドに投稿される「応募する」ボタン
"""

import discord
from src.forms.session import store
from src.views.form_view import FormView


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
            reset_btn = discord.ui.Button(
                label="リセット",
                style=discord.ButtonStyle.secondary,
                custom_id="apply_reset",
            )
            reset_btn.callback = self._on_reset
            self.add_item(reset_btn)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print(f"[ERROR] StartView エラー: {error}")
        traceback.print_exc()
        if not interaction.response.is_done():
            await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)

    async def _on_reset(self, interaction: discord.Interaction):
        store.delete(interaction.user.id)
        await interaction.response.send_message("応募状態をリセットしました。再度「応募する」を押してください。", ephemeral=True)

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
            if existing.thread_id != thread_id:
                # 別スレッドのセッションが残っていたらリセット
                store.delete(user_id)
            else:
                # 同じスレッドで既に応募中
                await interaction.response.send_message(
                    "すでに応募フォームが開いています。既存のフォームを完了するかキャンセルしてください。",
                    ephemeral=True
                )
                return

        store.create(user_id, thread_id)

        view = FormView(user_id, guests, event_type=event_type, start_interaction=interaction)
        await interaction.response.send_message(
            view.current_prompt(),
            view=view,
            ephemeral=True
        )
