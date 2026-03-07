# app/nardy_game/ui.py
"""
Renders the Nardi (Short Backgammon) board as a Telegram Inline Keyboard.

Board visual:  2 rows of 12 points each + action row.
  Top row (left→right):  points 13-24  (black travels this way)
  Bottom row (right→left): points 12-1 (white travels this way)

Each button shows:
  ⬛  - empty point
  ♙N  - N white checkers
  ♟N  - N black checkers
  🟡  - selected source point
  🟢  - legal destination
  🔴  - selected (opponent's piece on target, blocked)
"""
from __future__ import annotations

from typing import Optional, Set

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .engine import NardyGame, WHITE, BLACK, legal_moves_for_die


# Emoji representations
_EMPTY = "⬛"
_WHITE = "♙"
_BLACK = "♟"
_HL_SEL = "🟡"   # selected source
_HL_DEST = "🟢"   # legal destination
_HL_BLOCK = "🔴"  # blocked (can't land)

# Bear-off columns
_WHITE_TRAY = "🏁"
_BLACK_TRAY = "🏁"


def _pt_label(board: list, pt: int, color: int, selected: Optional[int],
              dests: Set[int]) -> str:
    """Return button text for a given point (1-24)."""
    if pt == selected:
        return _HL_SEL
    if pt in dests:
        return _HL_DEST
    v = board[pt]
    if v == 0:
        return _EMPTY
    n = abs(v)
    label = str(n) if n > 1 else ""
    return (_WHITE if v > 0 else _BLACK) + label


def _bear_off_label(board: list, color: int) -> str:
    """Button for the bear-off tray."""
    if color == WHITE:
        n = board[0]
        return f"🏁{n}" if n > 0 else "🏁"
    else:
        n = board[25]
        return f"🏁{n}" if n > 0 else "🏁"


def cb_pt(gid: str, pt: int) -> str:
    return f"nd|{gid}|{pt}"


def cb_ctrl(gid: str, action: str) -> str:
    return f"ndc|{gid}|{action}"


def build_board_kb(gs: NardyGame) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    # Compute legal destinations from selected source
    dests: Set[int] = set()
    if gs.selected is not None and gs.dice:
        d1, d2 = gs.dice
        dice_list = [d1, d1, d1, d1] if d1 == d2 else [d1, d2]
        for die in set(dice_list):
            for frm, to in legal_moves_for_die(gs.board, gs.turn, die):
                if frm == gs.selected:
                    dests.add(to)

    color = gs.turn

    # ── Top row: points 13 → 24 (left to right) ──
    top_row = []
    for pt in range(13, 25):
        txt = _pt_label(gs.board, pt, color, gs.selected, dests)
        top_row.append(InlineKeyboardButton(text=txt, callback_data=cb_pt(gs.gid, pt)))
    kb.row(*top_row)

    # ── Dice / info row ──
    dice_txt = f"🎲 {gs.dice[0]}  {gs.dice[1]}" if gs.dice else "🎲 ?"
    turn_txt = "⚪ Хід" if gs.turn == WHITE else "⚫ Хід"
    kb.row(
        InlineKeyboardButton(text=f"🏁 {gs.board[0]}", callback_data=cb_pt(gs.gid, 25)),
        InlineKeyboardButton(text=dice_txt, callback_data=cb_ctrl(gs.gid, "roll")),
        InlineKeyboardButton(text=f"🏁 {gs.board[25]}", callback_data=cb_pt(gs.gid, 0)),
    )

    # ── Bottom row: points 12 → 1 (left to right, visually reversed) ──
    bot_row = []
    for pt in range(12, 0, -1):
        txt = _pt_label(gs.board, pt, color, gs.selected, dests)
        bot_row.append(InlineKeyboardButton(text=txt, callback_data=cb_pt(gs.gid, pt)))
    kb.row(*bot_row)

    # ── Action buttons ──
    roll_label = "🎲 Кинути" if not gs.dice else f"🎲 {gs.dice[0]}·{gs.dice[1]}"
    kb.row(
        InlineKeyboardButton(text=roll_label, callback_data=cb_ctrl(gs.gid, "roll")),
        InlineKeyboardButton(text="🏳 Здатися", callback_data=cb_ctrl(gs.gid, "resign")),
    )
    kb.row(InlineKeyboardButton(text="⬅️ Меню", callback_data="sm:game:nardy"))
    kb.row(InlineKeyboardButton(text="♻️ Нова гра", callback_data=cb_ctrl(gs.gid, "new")))
    return kb.as_markup()


def render_text(gs: NardyGame) -> str:
    """Build the status text shown above the board."""
    if gs.finished:
        if gs.winner == WHITE:
            wname = gs.white_name
            return f"🎲 <b>Нарди</b>\n🏆 Переможець: <b>{wname}</b> (⚪ білі)!"
        else:
            bname = gs.black_name
            return f"🎲 <b>Нарди</b>\n🏆 Переможець: <b>{bname}</b> (⚫ чорні)!"

    side = "⚪ Білі" if gs.turn == WHITE else "⚫ Чорні"
    name = gs.white_name if gs.turn == WHITE else gs.black_name
    dice_str = f"🎲 {gs.dice[0]}·{gs.dice[1]}" if gs.dice else "🎲 (кидай!)"
    off_w = gs.board[0]
    off_b = gs.board[25]
    sel = f" | обрано: <code>{gs.selected}</code>" if gs.selected else ""
    return (
        f"🎲 <b>Нарди</b>\n"
        f"Хід: <b>{name}</b> ({side}){sel}\n"
        f"{dice_str}   ⚪зн:{off_w}  ⚫зн:{off_b}"
    )
