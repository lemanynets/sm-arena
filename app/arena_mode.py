"""
app/arena_mode.py — Hearthstone-style Arena Mode

Entry: player pays ARENA_ENTRY_FEE coins.
Play:  matched against random opponents (XO or Checkers).
End:   after 3 losses OR 10 wins, reward is issued based on win count.

This module holds in-memory sessions. Sessions survive until completed or bot restarts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ARENA_ENTRY_FEE = 100          # coins to enter
ARENA_MAX_WINS = 10
ARENA_MAX_LOSSES = 3

# Reward tiers (wins >= threshold → (lootbox_id or coin amount, label))
ARENA_REWARDS: list[tuple[int, str, str]] = [
    (0,  "coins:20",           "20 Монет 🪙"),
    (2,  "coins:60",           "60 Монет 🪙"),
    (4,  "coins:150",          "150 Монет 🪙"),
    (6,  "lootbox:bronze",     "Бронзова скриня 📦"),
    (8,  "lootbox:gold",       "Золота скриня 🥇"),
    (10, "lootbox:gold",       "Золота скриня 🥇 + 200 Монет"),
]


def _get_reward(wins: int) -> tuple[str, str]:
    """Return (reward_id, label) for the given win count."""
    chosen = ARENA_REWARDS[0]
    for threshold, rid, label in ARENA_REWARDS:
        if wins >= threshold:
            chosen = (rid, label)
    return chosen


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------
@dataclass
class ArenaSession:
    session_id: str
    user_id: int
    game: str               # "xo" or "checkers"
    wins: int = 0
    losses: int = 0
    started_at: float = field(default_factory=time.time)
    finished: bool = False
    reward_id: Optional[str] = None
    reward_label: Optional[str] = None

    @property
    def is_done(self) -> bool:
        return self.wins >= ARENA_MAX_WINS or self.losses >= ARENA_MAX_LOSSES

    def record_win(self) -> None:
        self.wins += 1
        if self.is_done:
            self._finish()

    def record_loss(self) -> None:
        self.losses += 1
        if self.is_done:
            self._finish()

    def _finish(self) -> None:
        self.finished = True
        rid, rlabel = _get_reward(self.wins)
        if self.wins == ARENA_MAX_WINS:
            rid = "lootbox:gold"
            rlabel = "Золота скриня 🥇 + 200 Монет"
        self.reward_id = rid
        self.reward_label = rlabel


# ---------------------------------------------------------------------------
# In-memory registry (reset on bot restart, acceptable for persistence-lite)
# ---------------------------------------------------------------------------
_SESSIONS: dict[int, ArenaSession] = {}   # user_id → active session


def get_session(user_id: int) -> Optional[ArenaSession]:
    s = _SESSIONS.get(user_id)
    if s and s.finished:
        return s          # caller should claim reward and then remove
    return s


def start_session(user_id: int, game: str = "xo") -> ArenaSession:
    sid = str(uuid.uuid4())[:8]
    s = ArenaSession(session_id=sid, user_id=user_id, game=game)
    _SESSIONS[user_id] = s
    return s


def end_session(user_id: int) -> None:
    _SESSIONS.pop(user_id, None)


def report_win(user_id: int) -> Optional[ArenaSession]:
    s = _SESSIONS.get(user_id)
    if s and not s.finished:
        s.record_win()
    return s


def report_loss(user_id: int) -> Optional[ArenaSession]:
    s = _SESSIONS.get(user_id)
    if s and not s.finished:
        s.record_loss()
    return s
