# -*- coding: utf-8 -*-
"""
応募受付Bot エントリーポイント

スラッシュコマンド:
  /apply_open   - 応募受付を開始（管理者ロール限定）
  /apply_close  - 応募受付を締め切る（管理者ロール限定）
"""

import json
import os
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

APPLY_STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "apply_state.json")


def _load_apply_state():
    if os.path.exists(APPLY_STATE_FILE):
        with open(APPLY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_apply_state():
    os.makedirs(os.path.dirname(APPLY_STATE_FILE), exist_ok=True)
    state = {
        str(tid): {
            "msg_id": apply_messages[tid],
            "guests": active_views[tid].guests,
            "event_type": active_views[tid].event_type,
        }
        for tid in active_views if tid in apply_messages
    }
    with open(APPLY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


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
    # 永続ビューを登録（再起動後も応募ボタンが動くように）
    bot.add_view(StartView(guests=[], event_type="custom", is_open=True))

    # apply状態を復元
    state = _load_apply_state()
    for tid_str, info in state.items():
        tid = int(tid_str)
        view = StartView(guests=info["guests"], event_type=info["event_type"], is_open=True)
        active_views[tid] = view
        apply_messages[tid] = info["msg_id"]

    await tree.sync(guild=discord.Object(id=config.SERVER_ID))
    print(f"Bot起動: {bot.user}")


@tree.command(
    name="apply_open",
    description="このスレッドで応募受付を開始します（管理者専用）",
    guild=discord.Object(id=config.SERVER_ID)
)
async def apply_open(interaction: discord.Interaction):
    await interaction.response.defer()

    if not _is_admin(interaction):
        await interaction.followup.send("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await interaction.followup.send("このコマンドはスレッド内でのみ使用できます。", ephemeral=True)
        return

    guests, event_type = extract_guests_from_title(thread.name)
    if not guests:
        await interaction.followup.send(
            "スレッドタイトルからゲスト名を取得できませんでした。\n"
            "タイトルに `ゲスト1 vs ゲスト2` の形式が含まれているか確認してください。",
            ephemeral=True
        )
        return

    view = StartView(guests=guests, event_type=event_type, is_open=True)
    active_views[thread.id] = view

    event_label = "コーチングイベント" if event_type == "coaching" else "対抗カスタム"
    embed = discord.Embed(
        title="📢 応募受付を開始しました！",
        color=discord.Color.blurple()
    )
    embed.add_field(name="イベント", value=event_label, inline=True)
    embed.add_field(name="ゲスト", value=" / ".join(guests), inline=True)
    embed.set_footer(text="下のボタンから応募してください。")
    msg = await interaction.followup.send(
        embed=embed,
        view=view,
        wait=True
    )
    apply_messages[thread.id] = msg.id
    _save_apply_state()


@tree.command(
    name="apply_close",
    description="このスレッドの応募受付を締め切ります（管理者専用）",
    guild=discord.Object(id=config.SERVER_ID)
)
async def apply_close(interaction: discord.Interaction):
    await interaction.response.defer()

    if not _is_admin(interaction):
        await interaction.followup.send("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await interaction.followup.send("このコマンドはスレッド内でのみ使用できます。", ephemeral=True)
        return

    view = active_views.get(thread.id)
    msg_id = apply_messages.get(thread.id)
    if not view or not msg_id:
        await interaction.followup.send("このスレッドに有効な受付メッセージが見つかりません。", ephemeral=True)
        return

    # ボタンを非活性に更新
    closed_view = StartView(guests=view.guests, event_type=view.event_type, is_open=False)
    try:
        msg = await thread.fetch_message(msg_id)
        await msg.edit(view=closed_view)
    except discord.NotFound:
        pass

    active_views.pop(thread.id, None)
    apply_messages.pop(thread.id, None)
    _save_apply_state()
    await interaction.followup.send("**📪 応募受付を締め切りました。**")


bot.run(config.BOT_TOKEN)
