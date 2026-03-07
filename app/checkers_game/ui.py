from __future__ import annotations

from typing import Optional, Tuple, Set

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .engine import SIZE, RED, BLUE, legal_moves, is_dark, piece_color, is_king

# Skin packs for checkers. Keys are compatible with app/config.py SKINS.
# Telegram inline keyboards look best when each cell is a single emoji/char.
SKIN_PACKS = {
    # default / classic
    "default": {
        "r_man": "🔴",
        "r_king": "🟥",
        "b_man": "🔵",
        "b_king": "🟦",
        "dark": "⠀",
        "light": "⠀",
        "move": "🟢",
        "sel": "🟡",
    },
    "classic": {
        "r_man": "🔴",
        "r_king": "🟥",
        "b_man": "🔵",
        "b_king": "🟦",
        "dark": "⠀",
        "light": "⠀",
        "move": "🟢",
        "sel": "🟡",
    },

    # 3d
    "3d": {
        "r_man": "🍒",
        "r_king": "🍒👑",
        "b_man": "🫐",
        "b_king": "🫐👑",
        "dark": "⬛️",
        "light": "⠀",
        "move": "✅",
        "sel": "⭐️",
    },
    "three_d": {
        "r_man": "🍒",
        "r_king": "🍒👑",
        "b_man": "🫐",
        "b_king": "🫐👑",
        "dark": "⬛️",
        "light": "⠀",
        "move": "✅",
        "sel": "⭐️",
    },

    # neon
    "neon": {
        "r_man": "❤️",
        "r_king": "💖",
        "b_man": "💙",
        "b_king": "🩵",
        "dark": "⬛️",
        "light": "⠀",
        "move": "🟦",
        "sel": "🟧",
    },

    # mono / minimal
    "mono": {
        "r_man": "R",
        "r_king": "R",
        "b_man": "B",
        "b_king": "B",
        "dark": "·",
        "light": "⠀",
        "move": "■",
        "sel": "□",
    },
    "minimal": {
        "r_man": "R",
        "r_king": "R",
        "b_man": "B",
        "b_king": "B",
        "dark": "·",
        "light": "⠀",
        "move": "■",
        "sel": "□",
    },
}


def _pack(skin: str) -> dict:
    key = (skin or "default").lower()
    return SKIN_PACKS.get(key) or SKIN_PACKS["default"]


def unpack_sq(s: str) -> Tuple[int, int]:
    return int(s[0]), int(s[1])


def cb_cell(gid: str, r: int, c: int) -> str:
    return f"ck|{gid}|{r}{c}"


def _cell(board, r: int, c: int, pack: dict) -> str:
    if not is_dark(r, c):
        return pack["light"]

    v = board[r][c]
    if v == 0:
        return pack["dark"]

    col = piece_color(v)
    king = is_king(v)

    if col == RED:
        return pack["r_king"] if king else pack["r_man"]
    return pack["b_king"] if king else pack["b_man"]


def build_board_kb(
    gid: str,
    board,
    turn: int,
    selected: Optional[Tuple[int, int]],
    forced_from: Optional[Tuple[int, int]],
    skin: str = "default",
) -> InlineKeyboardMarkup:
    pack = _pack(skin)
    kb = InlineKeyboardBuilder()

    moves_map = legal_moves(board, turn, forced_from=forced_from)
    dests: Set[Tuple[int, int]] = set()
    if selected and selected in moves_map:
        for mv in moves_map[selected]:
            dests.add(mv.to)

    for r in range(SIZE):
        row = []
        for c in range(SIZE):
            txt = _cell(board, r, c, pack)

            if (r, c) == selected:
                txt = pack["sel"]
            elif (r, c) in dests and board[r][c] == 0:
                txt = pack["move"]

            row.append(InlineKeyboardButton(text=txt, callback_data=cb_cell(gid, r, c)))
        kb.row(*row)

    kb.row(
        InlineKeyboardButton(text="🔄 Скинути", callback_data=f"ckc|{gid}|reset"),
        InlineKeyboardButton(text="🏁 Здатися", callback_data=f"ckc|{gid}|resign"),
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Меню", callback_data="sm:game:checkers"),
    )
    kb.row(
        InlineKeyboardButton(text="♻️ Нова гра", callback_data=f"ckc|{gid}|new"),
    )
    return kb.as_markup()


def coord_human(r: int, c: int) -> str:
    # a1..h8 (bottom is 1). Our board row 7 is bottom.
    file = "abcdefgh"[c]
    rank = str(8 - r)
    return f"{file}{rank}"





def render_text(
    red_name: str,
    blue_name: str,
    turn: int,
    selected: Optional[Tuple[int, int]],
    must_continue: bool,
    winner: Optional[int],
) -> str:
    if winner == RED:
        return f"♟️ <b>Шашки</b>\n🏆 Переміг: <b>{red_name}</b> 🔴"
    if winner == BLUE:
        return f"♟️ <b>Шашки</b>\n🏆 Переміг: <b>{blue_name}</b> 🔵"

    who = red_name if turn == RED else blue_name
    side = "🔴" if turn == RED else "🔵"
    sel = f" | Вибрано: <code>{coord_human(*selected)}</code>" if selected else ""
    extra = " | <i>продовжуй взяття тією ж шашкою</i>" if must_continue else ""
    return f"♟️ <b>Шашки</b>\nХід: <b>{who}</b> {side}{sel}{extra}"
