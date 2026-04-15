# -*- coding: utf-8 -*-
"""
応募完了時の処理
- 既存投稿があれば編集、なければ新規投稿
- data/submissions/ にJSONで保存
- interaction への応答は呼び出し元が行う
"""

import asyncio
import json
import os
import discord
from src.forms.session import Session
from src.formatter import build_submission_embed
from src.sheets import upsert_participant
import src.bot_state as bot_state

SUBMISSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "submissions")


def _submission_path(thread_id: int) -> str:
    return os.path.join(SUBMISSIONS_DIR, f"{thread_id}.json")


def _load_submissions(thread_id: int) -> dict:
    path = _submission_path(thread_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_submissions(thread_id: int, data: dict):
    os.makedirs(SUBMISSIONS_DIR, exist_ok=True)
    path = _submission_path(thread_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def handle_submit(interaction: discord.Interaction, session: Session, event_type: str = "custom"):
    user = interaction.user
    thread = interaction.channel
    thread_id = thread.id
    user_id_str = str(user.id)

    submissions = _load_submissions(thread_id)
    embed = build_submission_embed(user, session.answers, event_type=event_type)

    existing = submissions.get(user_id_str)

    if existing and existing.get("message_id"):
        try:
            msg = await thread.fetch_message(existing["message_id"])
            await msg.edit(embed=embed)
        except discord.NotFound:
            msg = await thread.send(embed=embed)
    else:
        msg = await thread.send(embed=embed)

    submissions[user_id_str] = {"message_id": msg.id, "answers": session.answers}
    _save_submissions(thread_id, submissions)
    print(f"[SUBMIT] {user} ({user.id}) が応募完了 / スレッド: {thread.name} / 回答: {session.answers}")
    print(f"[DEBUG] 応募embed message_id={msg.id}")
    await asyncio.to_thread(upsert_participant, user.id, user.display_name, str(user), session.answers, thread_name=thread.name)

    # 応募ボタンメッセージを一番下に移動
    if thread_id in bot_state.active_views:
        from src.views.start_view import StartView
        view_info = bot_state.active_views[thread_id]
        old_msg_id = bot_state.apply_messages.get(thread_id)
        print(f"[DEBUG] old apply_message_id={old_msg_id}, 応募embed message_id={msg.id}, 一致={old_msg_id == msg.id}")
        if old_msg_id:
            try:
                old_msg = await thread.fetch_message(old_msg_id)
                print(f"[DELETE] 旧apply_message削除: message_id={old_msg_id}")
                await old_msg.delete()
            except discord.NotFound:
                print(f"[DEBUG] 旧apply_message見つからず (message_id={old_msg_id})")
        new_view = StartView(guests=view_info.guests, event_type=view_info.event_type, is_open=True)
        bot_state.active_views[thread_id] = new_view
        event_label = "コーチングイベント" if view_info.event_type == "coaching" else "対抗カスタム"
        embed = discord.Embed(
            title="📢 応募受付中！",
            color=discord.Color.blurple()
        )
        embed.add_field(name="イベント", value=event_label, inline=True)
        embed.add_field(name="ゲスト", value=" / ".join(view_info.guests), inline=True)
        embed.set_footer(text="下のボタンから応募してください。")
        new_apply_msg = await thread.send(embed=embed, view=new_view)
        bot_state.apply_messages[thread_id] = new_apply_msg.id
        bot_state.save_apply_state()

    return msg
