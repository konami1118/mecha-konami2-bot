# -*- coding: utf-8 -*-
"""
テキスト入力モーダル（バトルタグ）
"""

import re
import discord
from src.forms.session import store
from src.forms.steps import STEPS

BATTLETAG_PATTERN = re.compile(r'^.+#\d+$')


class BattletagModal(discord.ui.Modal, title="バトルタグを入力してください"):
    battletag = discord.ui.TextInput(
        label="バトルタグ",
        placeholder="例: PlayerName#1234",
        min_length=3,
        max_length=30,
    )

    def __init__(self, user_id: int, guests: list[str], event_type: str = "custom", start_interaction=None):
        super().__init__()
        self.user_id = user_id
        self.guests = guests
        self.event_type = event_type
        self.start_interaction = start_interaction

    async def on_submit(self, interaction: discord.Interaction):
        value = self.battletag.value.strip()

        # バリデーション: Name#数字 形式チェック
        if not BATTLETAG_PATTERN.match(value):
            await interaction.response.send_message(
                "バトルタグの形式が正しくありません。`PlayerName#1234` の形式で入力してください。",
                ephemeral=True
            )
            return

        session = store.get(self.user_id)
        if not session:
            await interaction.response.send_message("セッションが切れました。最初からやり直してください。", ephemeral=True)
            return

        step_key = STEPS[session.current_step]
        session.answer(step_key, value)
        session.advance()

        from src.views.form_view import FormView
        view = FormView(self.user_id, self.guests, event_type=self.event_type, start_interaction=self.start_interaction)
        await interaction.response.edit_message(
            content=view.current_prompt(),
            view=view,
        )


class CommentModal(discord.ui.Modal, title="コメントを入力してください"):
    comment = discord.ui.TextInput(
        label="コメント",
        placeholder="自由にどうぞ（例: よろしくお願いします！）",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True,
    )

    def __init__(self, user_id: int, start_interaction: discord.Interaction = None, event_type: str = "custom"):
        super().__init__()
        self.user_id = user_id
        self.start_interaction = start_interaction
        self.event_type = event_type

    async def on_submit(self, interaction: discord.Interaction):
        session = store.get(self.user_id)
        if not session:
            await interaction.response.edit_message(content="セッションが切れました。最初からやり直してください。", view=None)
            return

        step_key = STEPS[session.current_step]
        session.answer(step_key, self.comment.value.strip())
        session.advance()

        await interaction.response.edit_message(content="⏳ 処理中...", view=None)
        try:
            from src.handlers.submit import handle_submit
            msg = await handle_submit(interaction, session, event_type=self.event_type)
            if msg:
                jump_url = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}/{msg.id}"
                jump_view = discord.ui.View()
                jump_view.add_item(discord.ui.Button(label="📋 応募内容を確認する", url=jump_url))
                await interaction.edit_original_response(content="✅ 応募が完了しました！", view=jump_view)
            else:
                await interaction.edit_original_response(content="✅ 応募が完了しました！")
        except Exception as e:
            import traceback
            print(f"[ERROR] handle_submit エラー: {e}")
            traceback.print_exc()
        finally:
            store.delete(self.user_id)
