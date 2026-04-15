# -*- coding: utf-8 -*-
"""
回答フォームのステップ制御View
各ステップに応じてセレクトメニュー / モーダル起動ボタンを切り替える
"""

import discord
from src.forms.steps import (
    STEPS, STEP_LABELS, RANK_TIERS, RANK_DIVISIONS, MAIN_ROLES, RANK_STEPS, PLATFORMS,
)
from src.forms.session import store
from src.views.modals import BattletagModal, CommentModal

PLATFORM_EMOJIS = {
    "PC": "<:p_pc:962736429333643334>",
    "CS": "<:p_playstation:962735784073502730>",
}

RANK_EMOJIS = {
    "未プレイ":        "",
    "ブロンズ":        "<:r1_Bronze:1274396477787078666>",
    "シルバー":        "<:r2_Silver:1274397237853683773>",
    "ゴールド":        "<:r3_Gold:1274397269793443870>",
    "プラチナ":        "<:r4_Platinum:1274397326760476753>",
    "ダイヤ":          "<:r5_Diamond:1274397378081984532>",
    "マスター":        "<:r6_Master:1274397457035563192>",
    "グランドマスター": "<:r7_Grandmaster:1274397509267099649>",
    "チャンピオン":    "<:r8_Champions:1209154735614201866>",
}

ROLE_EMOJIS = {
    "タンク":   "<:tank:1428669383944830976>",
    "ダメージ": "<:damage:1428669635150086214>",
    "サポート": "<:support:1428669965611044927>",
}


class FormView(discord.ui.View):
    def __init__(self, user_id: int, guests: list[str], event_type: str = "custom", start_interaction: discord.Interaction = None):
        super().__init__(timeout=900)
        self.user_id = user_id
        self.guests = guests
        self.event_type = event_type
        self.start_interaction = start_interaction
        # ランクステップの途中選択状態 { step_key: {"tier": str, "div": str} }
        self._pending: dict[str, dict] = {}
        self._build()

    def current_prompt(self) -> str:
        session = store.get(self.user_id)
        if not session:
            return "セッションが切れました。最初からやり直してください。"
        step_key = STEPS[session.current_step]
        label = STEP_LABELS[step_key]
        if step_key == "preferred_guest" and self.event_type == "coaching":
            label = "コーチングしてもらいたいゲスト"
        return f"**【{session.current_step + 1}/{len(STEPS)}】{label}** を選択してください。"

    def _build(self):
        self.clear_items()
        session = store.get(self.user_id)
        if not session:
            return

        step_key = STEPS[session.current_step]

        if step_key == "battletag":
            btn = discord.ui.Button(label="バトルタグを入力する", style=discord.ButtonStyle.primary, row=0)
            btn.callback = self._open_battletag_modal
            self.add_item(btn)

        elif step_key == "platform":
            select = discord.ui.Select(
                placeholder="プラットフォームを選択してください",
                options=[
                    discord.SelectOption(
                        label=p,
                        value=p,
                        emoji=PLATFORM_EMOJIS.get(p)
                    ) for p in PLATFORMS
                ],
                custom_id="platform_select",
                row=0,
            )
            select.callback = self._on_select
            self.add_item(select)

        elif step_key in RANK_STEPS:
            pending = self._pending.get(step_key, {})
            selected_tier = pending.get("tier")
            selected_div = pending.get("div")

            tier_options = [
                discord.SelectOption(
                    label=r,
                    value=r,
                    default=(r == selected_tier),
                    emoji=RANK_EMOJIS.get(r) or None
                )
                for r in RANK_TIERS
            ]
            tier_select = discord.ui.Select(
                placeholder="ランクを選択（未プレイ / ブロンズ〜チャンピオン）",
                options=tier_options,
                custom_id=f"tier_{step_key}",
                row=0,
            )
            tier_select.callback = self._on_rank_partial
            self.add_item(tier_select)

            div_options = [
                discord.SelectOption(label=d, value=d, default=(d == selected_div))
                for d in RANK_DIVISIONS
            ]
            div_select = discord.ui.Select(
                placeholder="ティアを選択（1〜5）",
                options=div_options,
                custom_id=f"div_{step_key}",
                row=1,
            )
            div_select.callback = self._on_rank_partial
            self.add_item(div_select)

        elif step_key == "main_role":
            pending_roles = self._pending.get("main_role", {}).get("values", [])
            select = discord.ui.Select(
                placeholder="メインロールを選択してください（複数選択可）",
                options=[
                    discord.SelectOption(
                        label=r,
                        value=r,
                        emoji=ROLE_EMOJIS.get(r),
                        default=(r in pending_roles),
                    ) for r in MAIN_ROLES
                ],
                custom_id="main_role_select",
                min_values=1,
                max_values=len(MAIN_ROLES),
                row=0,
            )
            select.callback = self._on_role_select
            self.add_item(select)

        elif step_key == "preferred_guest":
            options = [discord.SelectOption(label=g, value=g) for g in self.guests]
            options.append(discord.SelectOption(label="どちらでもOK", value="どちらでもOK"))
            if self.event_type == "coaching":
                placeholder = "コーチングしてもらいたいゲストを選択してください"
            else:
                placeholder = "一緒に戦いたいゲストを選択してください"
            select = discord.ui.Select(
                placeholder=placeholder,
                options=options,
                custom_id="guest_select",
                row=0,
            )
            select.callback = self._on_select
            self.add_item(select)

        elif step_key == "comment":
            btn_input = discord.ui.Button(label="コメントを入力する", style=discord.ButtonStyle.primary, row=0)
            btn_input.callback = self._open_comment_modal
            self.add_item(btn_input)
            btn_skip = discord.ui.Button(label="スキップ", style=discord.ButtonStyle.secondary, row=0)
            btn_skip.callback = self._skip_comment
            self.add_item(btn_skip)

        # キャンセルボタン（常に表示）
        cancel_btn = discord.ui.Button(label="キャンセル", style=discord.ButtonStyle.danger, row=4)
        cancel_btn.callback = self._on_cancel
        self.add_item(cancel_btn)

    async def _open_comment_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        await interaction.response.send_modal(CommentModal(self.user_id, self.start_interaction, self.event_type))

    async def _skip_comment(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        await self._advance(interaction, "")

    async def _open_battletag_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        await interaction.response.send_modal(BattletagModal(self.user_id, self.guests, event_type=self.event_type, start_interaction=self.start_interaction))

    async def _on_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        store.delete(self.user_id)
        print(f"[CANCEL] {interaction.user} ({interaction.user.id}) が応募をキャンセル")
        await interaction.response.edit_message(content="応募をキャンセルしました。", view=None)

    async def _on_rank_partial(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return

        session = store.get(self.user_id)
        if not session:
            await interaction.response.send_message("セッションが切れました。最初からやり直してください。", ephemeral=True)
            return

        step_key = STEPS[session.current_step]
        if step_key not in self._pending:
            self._pending[step_key] = {}

        custom_id = interaction.data["custom_id"]
        value = interaction.data["values"][0]

        if custom_id.startswith("tier_"):
            self._pending[step_key]["tier"] = value
            if value == "未プレイ":
                # 未プレイはディビジョン不要 → そのまま確定
                await self._advance(interaction, "未プレイ")
                return
        elif custom_id.startswith("div_"):
            self._pending[step_key]["div"] = value

        pending = self._pending[step_key]

        # ランク・ティア両方揃ったら確定
        if "tier" in pending and "div" in pending:
            combined = pending["tier"] + pending["div"]
            await self._advance(interaction, combined)
        else:
            # 片方だけ → 再描画せず静かに受け取る
            await interaction.response.defer()

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        await self._advance(interaction, interaction.data["values"][0])

    async def _on_role_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの応募フォームではありません。", ephemeral=True)
            return
        roles = interaction.data["values"]
        value = "/".join(roles)
        await self._advance(interaction, value)

    async def _advance(self, interaction: discord.Interaction, value: str):
        session = store.get(self.user_id)
        if not session:
            await interaction.response.send_message("セッションが切れました。最初からやり直してください。", ephemeral=True)
            return

        step_key = STEPS[session.current_step]
        session.answer(step_key, value)
        session.advance()

        if session.current_step >= len(STEPS):
            from src.handlers.submit import handle_submit
            await interaction.response.edit_message(content="⏳ 処理中...", view=None)
            try:
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
                await interaction.edit_original_response(content="⚠️ 応募処理中にエラーが発生しました。もう一度お試しください。", view=None)
            finally:
                store.delete(self.user_id)
        else:
            self._build()
            await interaction.response.edit_message(
                content=self.current_prompt(),
                view=self,
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print(f"[ERROR] FormView エラー: {error}")
        traceback.print_exc()
        if not interaction.response.is_done():
            await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)

    async def on_timeout(self):
        pass  # セッションは SESSION_TIMEOUT_SECONDS で自動失効するため削除不要
