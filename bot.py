# -*- coding: utf-8 -*-
"""
応募受付Bot エントリーポイント

スラッシュコマンド:
  /apply_open   - 応募受付を開始（管理者ロール限定）
  /apply_close  - 応募受付を締め切る（管理者ロール限定）
"""

import discord
from discord import app_commands
import config
from src.views.start_view import StartView
from src.utils import extract_guests_from_title

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# スレッドID → StartView のマッピング（締切操作用）
active_views: dict[int, StartView] = {}
# スレッドID → 応募メッセージID のマッピング
apply_messages: dict[int, int] = {}


def _is_admin(interaction: discord.Interaction) -> bool:
    if interaction.permissions.administrator:
        return True
    member = interaction.user
    if isinstance(member, discord.Member):
        return any(r.id == config.ADMIN_ROLE_ID for r in member.roles)
    return False


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    import traceback
    print(f"[ERROR] コマンドエラー: {error}")
    traceback.print_exc()
    if not interaction.response.is_done():
        await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)


@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=config.SERVER_ID))
    print(f"Bot起動: {bot.user}")


@tree.command(
    name="apply_open",
    description="このスレッドで応募受付を開始します（管理者専用）",
    guild=discord.Object(id=config.SERVER_ID)
)
async def apply_open(interaction: discord.Interaction):
    if not _is_admin(interaction):
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("このコマンドはスレッド内でのみ使用できます。", ephemeral=True)
        return

    guests, event_type = extract_guests_from_title(thread.name)
    if not guests:
        await interaction.response.send_message(
            "スレッドタイトルからゲスト名を取得できませんでした。\n"
            "タイトルに `ゲスト1 vs ゲスト2` の形式が含まれているか確認してください。",
            ephemeral=True
        )
        return

    view = StartView(guests=guests, event_type=event_type, is_open=True)
    active_views[thread.id] = view

    event_label = "コーチングイベント" if event_type == "coaching" else "対抗カスタム"
    await interaction.response.defer()
    msg = await interaction.followup.send(
        f"**📢 応募受付を開始しました！**\n"
        f"イベント: **{event_label}** ／ ゲスト: **{' / '.join(guests)}**\n\n"
        f"下のボタンから応募してください。",
        view=view,
        wait=True
    )
    apply_messages[thread.id] = msg.id


@tree.command(
    name="apply_close",
    description="このスレッドの応募受付を締め切ります（管理者専用）",
    guild=discord.Object(id=config.SERVER_ID)
)
async def apply_close(interaction: discord.Interaction):
    if not _is_admin(interaction):
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("このコマンドはスレッド内でのみ使用できます。", ephemeral=True)
        return

    view = active_views.get(thread.id)
    msg_id = apply_messages.get(thread.id)
    if not view or not msg_id:
        await interaction.response.send_message("このスレッドに有効な受付メッセージが見つかりません。", ephemeral=True)
        return

    # ボタンを非活性に更新
    closed_view = StartView(guests=view.guests, event_type=view.event_type, is_open=False)
    try:
        msg = await thread.fetch_message(msg_id)
        await msg.edit(view=closed_view)
    except discord.NotFound:
        pass

    active_views.pop(thread.id, None)
    await interaction.response.defer()
    await interaction.followup.send("**📪 応募受付を締め切りました。**")


bot.run(config.BOT_TOKEN)
