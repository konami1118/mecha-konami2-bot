# -*- coding: utf-8 -*-
"""
応募結果のDiscord Embed整形
"""

import discord


EMOJI_OW2    = "<:I_OW2:968673447712522280>"
EMOJI_TANK   = "<:tank:1428669383944830976>"
EMOJI_DAMAGE = "<:damage:1428669635150086214>"
EMOJI_SUPPORT = "<:support:1428669965611044927>"
EMOJI_PLATFORM = "<:p_pc:962736429333643334>"
EMOJI_GUEST  = "<:e_sportsmanship:962725420887859301>"


def build_submission_embed(user: discord.Member, answers: dict, event_type: str = "custom") -> discord.Embed:
    embed = discord.Embed(
        title=f"{EMOJI_OW2} 応募内容",
        color=discord.Color.blurple()
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    embed.add_field(name="バトルタグ", value=answers.get("battletag", "未入力"), inline=False)
    embed.add_field(name=f"{EMOJI_PLATFORM} プラットフォーム", value=answers.get("platform", "未入力"), inline=False)
    embed.add_field(name=f"{EMOJI_TANK} タンク最高ランク", value=answers.get("tank_rank", "未入力"), inline=True)
    embed.add_field(name=f"{EMOJI_DAMAGE} ダメージ最高ランク", value=answers.get("dps_rank", "未入力"), inline=True)
    embed.add_field(name=f"{EMOJI_SUPPORT} サポート最高ランク", value=answers.get("support_rank", "未入力"), inline=True)
    embed.add_field(name="メインロール", value=answers.get("main_role", "未入力"), inline=True)
    guest_label = f"{EMOJI_GUEST} コーチングしてもらいたいゲスト" if event_type == "coaching" else f"{EMOJI_GUEST} 一緒に戦いたいゲスト"
    embed.add_field(name=guest_label, value=answers.get("preferred_guest", "未入力"), inline=True)

    comment = answers.get("comment", "")
    if comment:
        embed.add_field(name="💬 コメント", value=comment, inline=False)

    return embed
