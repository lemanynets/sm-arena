from __future__ import annotations

import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .engine import RED, BLUE, initial_board

@dataclass
class GameSession:
    gid: str

    # group mode
    chat_id: int = 0
    message_id: int = 0

    # players
    red_id: int = 0
    blue_id: int = 0
    red_name: str = ""
    blue_name: str = ""

    # private mode message locations (chat_id == user_id for private chats)
    red_chat_id: int = 0
    red_message_id: int = 0
    blue_chat_id: int = 0
    blue_message_id: int = 0

    # game state
    board: list = field(default_factory=initial_board)
    turn: int = RED
    selected: Optional[Tuple[int, int]] = None
    forced_from: Optional[Tuple[int, int]] = None

    # meta
    finished: bool = False
    winner: Optional[int] = None  # RED / BLUE / None

    vs_ai: bool = False
    ai_level: str = "easy"

    last_activity: float = field(default_factory=lambda: time.time())
    # tournament context
    tournament_id: int = 0
    tmatch_id: int = 0


    def touch(self):
        self.last_activity = time.time()

    @property
    def is_private(self) -> bool:
        return self.red_chat_id != 0 or self.blue_chat_id != 0


@dataclass
class Waiting:
    user_id: int
    name: str
    ts: float = field(default_factory=lambda: time.time())

class MemoryStore:
    def __init__(self):
        self.games: Dict[str, GameSession] = {}
        self.lobby_by_chat: Dict[int, str] = {}     # group chat_id -> gid
        self.active_by_user: Dict[int, str] = {}    # private user_id -> gid
        self.waiting: Optional[Waiting] = None      # 1-slot matchmaking queue

    def new_gid(self) -> str:
        return secrets.token_hex(3)  # 6 chars

STORE = MemoryStore()

# ----- Group lobby helpers -----
def create_lobby(chat_id: int, message_id: int, creator_id: int, creator_name: str) -> GameSession:
    gid = STORE.new_gid()
    gs = GameSession(
        gid=gid,
        chat_id=chat_id,
        message_id=message_id,
        red_id=creator_id,
        blue_id=0,
        red_name=creator_name,
        blue_name="",
        board=initial_board(),
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
    if gs.blue_id and gs.blue_id != joiner_id:
        return None
    gs.blue_id = joiner_id
    gs.blue_name = joiner_name
    STORE.lobby_by_chat.pop(chat_id, None)
    gs.touch()
    return gs

# ----- Private matchmaking -----
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

def enqueue_or_match(user_id: int, name: str) -> Tuple[str, Optional[GameSession]]:
    """
    Returns ("waiting", None) if queued, or ("matched", session) if matched.
    """
    uid = int(user_id)
    if STORE.waiting is None:
        STORE.waiting = Waiting(uid, name)
        return "waiting", None
    if STORE.waiting.user_id == uid:
        return "waiting", None

    # match with waiting user
    other = STORE.waiting
    STORE.waiting = None

    gid = STORE.new_gid()
    # random colors
    import random
    if random.random() < 0.5:
        red_id, red_name = other.user_id, other.name
        blue_id, blue_name = uid, name
    else:
        red_id, red_name = uid, name
        blue_id, blue_name = other.user_id, other.name

    gs = GameSession(
        gid=gid,
        red_id=red_id,
        blue_id=blue_id,
        red_name=red_name,
        blue_name=blue_name,
        board=initial_board(),
    )
    STORE.games[gid] = gs
    STORE.active_by_user[red_id] = gid
    STORE.active_by_user[blue_id] = gid
    return "matched", gs


def create_private_match(a_id: int, a_name: str, b_id: int, b_name: str, tournament_id: int = 0, tmatch_id: int = 0) -> GameSession:
    """Force-create a private checkers match between two users (used for tournaments)."""
    import random
    gid = STORE.new_gid()
    # random colors
    if random.random() < 0.5:
        red_id, red_name = int(a_id), str(a_name)
        blue_id, blue_name = int(b_id), str(b_name)
    else:
        red_id, red_name = int(b_id), str(b_name)
        blue_id, blue_name = int(a_id), str(a_name)

    gs = GameSession(
        gid=gid,
        red_id=red_id,
        blue_id=blue_id,
        red_name=red_name,
        blue_name=blue_name,
        board=initial_board(),
        tournament_id=int(tournament_id),
        tmatch_id=int(tmatch_id),
    )
    STORE.games[gid] = gs
    STORE.active_by_user[red_id] = gid
    STORE.active_by_user[blue_id] = gid
    return gs

def end_private_game(gs: GameSession):
    for uid in (gs.red_id, gs.blue_id):
        STORE.active_by_user.pop(int(uid), None)

def get_game(gid: str) -> Optional[GameSession]:
    return STORE.games.get(gid)