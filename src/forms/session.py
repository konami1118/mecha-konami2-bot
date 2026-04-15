# -*- coding: utf-8 -*-
"""
ユーザーごとの回答途中セッション管理

- メモリ上で保持（Bot再起動時は消失、許容）
- SESSION_TIMEOUT_SECONDS 経過後に自動破棄
- 同一ユーザーの多重セッションを防止
"""

import time
from typing import Optional
from config import SESSION_TIMEOUT_SECONDS


class Session:
    def __init__(self, user_id: int, thread_id: int):
        self.user_id = user_id
        self.thread_id = thread_id
        self.answers: dict = {}          # ステップ名 → 回答値
        self.current_step: int = 0       # 現在のステップインデックス
        self.created_at: float = time.time()

    def is_expired(self) -> bool:
        return time.time() - self.created_at > SESSION_TIMEOUT_SECONDS

    def answer(self, step_key: str, value: str):
        self.answers[step_key] = value

    def advance(self):
        self.current_step += 1


class SessionStore:
    """スレッドごと・ユーザーごとのセッション管理"""

    def __init__(self):
        # { user_id: Session }
        self._sessions: dict[int, Session] = {}

    def create(self, user_id: int, thread_id: int) -> Session:
        session = Session(user_id, thread_id)
        self._sessions[user_id] = session
        return session

    def get(self, user_id: int) -> Optional[Session]:
        session = self._sessions.get(user_id)
        if session and session.is_expired():
            self.delete(user_id)
            return None
        return session

    def delete(self, user_id: int):
        self._sessions.pop(user_id, None)

    def has_active(self, user_id: int) -> bool:
        return self.get(user_id) is not None

    def cleanup_expired(self):
        """期限切れセッションを一括削除する"""
        expired = [uid for uid, s in self._sessions.items() if s.is_expired()]
        for uid in expired:
            del self._sessions[uid]
        if expired:
            print(f"[Session] 期限切れセッションを削除: {len(expired)} 件")


# グローバルインスタンス
store = SessionStore()
