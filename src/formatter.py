# -*- coding: utf-8 -*-
"""
応募結果のDiscord Embed整形
"""

import discord


EMOJI_OW2    = "<:I_OW2:968673447712522280>"
EMOJI_TANK   = "<:tank:1428669383944830976>"
EMOJI_DAMAGE = "<:damage:1428669635150086214>"
EMOJI_SUPPORT = "<:support:1428669965611044927>"
EMOJI_PLATFORM = "<a:or_ar:1430108348279164959>"

PLATFORM_VALUE_EMOJIS = {
    "PC": "<:p_pc:962736429333643334>",
    "CS": "<:p_playstation:962735784073502730>",
}
EMOJI_GUEST  = "<:e_sportsmanship:962725420887859301>"

RANK_EMOJIS = {
    "ブロンズ":       "<:r1_Bronze:1274396477787078666>",
    "シルバー":       "<:r2_Silver:1274397237853683773>",
    "ゴールド":       "<:r3_Gold:1274397269793443870>",
    "プラチナ":       "<:r4_Platinum:1274397326760476753>",
    "ダイヤ":         "<:r5_Diamond:1274397378081984532>",
    "マスター":       "<:r6_Master:1274397457035563192>",
    "グランドマスター": "<:r7_Grandmaster:1274397509267099649>",
    "チャンピオン":    "<:r8_Champions:1209154735614201866>",
}


def _rank_with_emoji(rank: str) -> str:
    if not rank or rank == "未プレイ":
        return rank or "未入力"
    for tier, emoji in RANK_EMOJIS.items():
        if tier in rank:
            return f"{emoji} {rank}"
    return rank


def build_submission_embed(user: discord.Member, answers: dict, event_type: str = "custom") -> discord.Embed:
    embed = discord.Embed(
        title=f"{EMOJI_OW2} 応募内容",
        color=discord.Color.blurple()
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    embed.add_field(name=f"{EMOJI_PLATFORM} バトルタグ", value=answers.get("battletag", "未入力"), inline=False)
    platform = answers.get("platform", "")
    platform_emoji = PLATFORM_VALUE_EMOJIS.get(platform, "")
    platform_value = f"{platform_emoji} {platform}".strip() if platform else "未入力"
    embed.add_field(name=f"{EMOJI_PLATFORM} プラットフォーム", value=platform_value, inline=False)
    embed.add_field(name=f"{EMOJI_TANK} タンク最高ランク", value=_rank_with_emoji(answers.get("tank_rank", "")), inline=True)
    embed.add_field(name=f"{EMOJI_DAMAGE} ダメージ最高ランク", value=_rank_with_emoji(answers.get("dps_rank", "")), inline=True)
    embed.add_field(name=f"{EMOJI_SUPPORT} サポート最高ランク", value=_rank_with_emoji(answers.get("support_rank", "")), inline=True)
    embed.add_field(name="メインロール", value=answers.get("main_role", "未入力"), inline=True)
    guest_label = f"{EMOJI_GUEST} コーチングしてもらいたいゲスト" if event_type == "coaching" else f"{EMOJI_GUEST} 一緒に戦いたいゲスト"
    embed.add_field(name=guest_label, value=answers.get("preferred_guest", "未入力"), inline=True)

    comment = answers.get("comment", "")
    if comment:
        embed.add_field(name="💬 コメント", value=comment, inline=False)

    return embed
