from __future__ import annotations

import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import chess


@dataclass
class GameSession:
    gid: str

    # group mode location
    chat_id: int = 0
    message_id: int = 0

    # players
    white_id: int = 0
    black_id: int = 0
    white_name: str = ""
    black_name: str = ""

    # private mode messages (chat_id == user_id in private)
    white_chat_id: int = 0
    white_message_id: int = 0
    black_chat_id: int = 0
    black_message_id: int = 0

    # game state
    board: chess.Board = field(default_factory=chess.Board)
    selected: Optional[int] = None

    # meta
    finished: bool = False
    winner: Optional[bool] = None  # chess.WHITE / chess.BLACK / None(draw)
    outcome_reason: str = ""

    vs_ai: bool = False
    ai_level: str = "easy"

    last_activity: float = field(default_factory=lambda: time.time())
    tournament_id: int = 0
    tmatch_id: int = 0

    def touch(self):
        self.last_activity = time.time()

    @property
    def is_private(self) -> bool:
        return self.white_chat_id != 0 or self.black_chat_id != 0


@dataclass
class Waiting:
    user_id: int
    name: str
    ts: float = field(default_factory=lambda: time.time())


class MemoryStore:
    def __init__(self):
        self.games: Dict[str, GameSession] = {}
        self.lobby_by_chat: Dict[int, str] = {}
        self.active_by_user: Dict[int, str] = {}
        self.waiting: Optional[Waiting] = None

    def new_gid(self) -> str:
        return secrets.token_hex(3)


STORE = MemoryStore()


def create_lobby(chat_id: int, message_id: int, creator_id: int, creator_name: str) -> GameSession:
    gid = STORE.new_gid()
    gs = GameSession(
        gid=gid,
        chat_id=chat_id,
        message_id=message_id,
        white_id=creator_id,
        white_name=creator_name,
        board=chess.Board(),
    )
    STORE.games[gid] = gs
    STORE.lobby_by_chat[chat_id] = gid
    return gs


def get_lobby(chat_id: int) -> Optional[GameSession]:
    gid = STORE.lobby_by_chat.get(chat_id)
    if not gid:
        return None
    return STORE.games.get(gid)


def join_lobby(chat_id: int, joiner_id: int, joiner_name: str) -> Optional[GameSession]:
    gid = STORE.lobby_by_chat.get(chat_id)
    if not gid:
        return None
    gs = STORE.games.get(gid)
    if not gs or gs.finished:
        STORE.lobby_by_chat.pop(chat_id, None)
        return None
    if gs.black_id and gs.black_id != joiner_id:
        return None
    gs.black_id = int(joiner_id)
    gs.black_name = str(joiner_name)
    STORE.lobby_by_chat.pop(chat_id, None)
    gs.touch()
    return gs


def user_active_game(user_id: int) -> Optional[GameSession]:
    gid = STORE.active_by_user.get(int(user_id))
    if not gid:
        return None
    return STORE.games.get(gid)


def cancel_waiting(user_id: int) -> bool:
    w = STORE.waiting
    if w and w.user_id == int(user_id):
        STORE.waiting = None
        return True
    return False


def enqueue_or_match(user_id: int, name: str) -> tuple[str, Optional[GameSession]]:
    uid = int(user_id)
    if STORE.waiting is None:
        STORE.waiting = Waiting(uid, name)
        return "waiting", None
    if STORE.waiting.user_id == uid:
        return "waiting", None

    other = STORE.waiting
    STORE.waiting = None

    gid = STORE.new_gid()
    if random.random() < 0.5:
        white_id, white_name = other.user_id, other.name
        black_id, black_name = uid, name
    else:
        white_id, white_name = uid, name
        black_id, black_name = other.user_id, other.name

    gs = GameSession(
        gid=gid,
        white_id=white_id,
        black_id=black_id,
        white_name=white_name,
        black_name=black_name,
        board=chess.Board(),
    )
    STORE.games[gid] = gs
    STORE.active_by_user[white_id] = gid
    STORE.active_by_user[black_id] = gid
    return "matched", gs


def create_private_match(
    a_id: int,
    a_name: str,
    b_id: int,
    b_name: str,
    tournament_id: int = 0,
    tmatch_id: int = 0,
) -> GameSession:
    gid = STORE.new_gid()
    if random.random() < 0.5:
        white_id, white_name = int(a_id), str(a_name)
        black_id, black_name = int(b_id), str(b_name)
    else:
        white_id, white_name = int(b_id), str(b_name)
        black_id, black_name = int(a_id), str(a_name)

    gs = GameSession(
        gid=gid,
        white_id=white_id,
        black_id=black_id,
        white_name=white_name,
        black_name=black_name,
        board=chess.Board(),
        tournament_id=int(tournament_id),
        tmatch_id=int(tmatch_id),
    )
    STORE.games[gid] = gs
    STORE.active_by_user[white_id] = gid
    STORE.active_by_user[black_id] = gid
    return gs


def end_private_game(gs: GameSession):
    for uid in (gs.white_id, gs.black_id):
        if int(uid) > 0:
            STORE.active_by_user.pop(int(uid), None)


def get_game(gid: str) -> Optional[GameSession]:
    return STORE.games.get(gid)
