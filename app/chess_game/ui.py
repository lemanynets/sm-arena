from __future__ import annotations

from typing import Optional, Set

import chess
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


_ASCII_PIECES = {
    "P": "P",
    "N": "N",
    "B": "B",
    "R": "R",
    "Q": "Q",
    "K": "K",
    "p": "p",
    "n": "n",
    "b": "b",
    "r": "r",
    "q": "q",
    "k": "k",
}


def _theme(skin: str) -> dict:
    # Keep board symbols text-only to avoid black-square glyph artifacts in Telegram clients.
    s = (skin or "default").lower()
    if s in ("mono", "minimal", "neon"):
        return {
            "pieces": _ASCII_PIECES,
            "dark": ".",
            "light": " ",
            "selected": "*",
            "move": "+",
            "capture": "x",
        }
    return {
        "pieces": _ASCII_PIECES,
        "dark": ".",
        "light": " ",
        "selected": "*",
        "move": "+",
        "capture": "x",
    }


def unpack_sq(token: str) -> int:
    return chess.parse_square(token)


def cb_cell(gid: str, square: int) -> str:
    return f"ch|{gid}|{chess.square_name(square)}"


def _piece_text(board: chess.Board, square: int, theme: dict) -> str:
    piece = board.piece_at(square)
    if piece:
        return theme["pieces"][piece.symbol()]
    is_dark = (chess.square_file(square) + chess.square_rank(square)) % 2 == 1
    return theme["dark"] if is_dark else theme["light"]


def _targets(board: chess.Board, selected: Optional[int]) -> Set[int]:
    if selected is None:
        return set()
    out: Set[int] = set()
    for mv in board.legal_moves:
        if mv.from_square == selected:
            out.add(mv.to_square)
    return out


def build_board_kb(
    gid: str,
    board: chess.Board,
    selected: Optional[int],
    skin: str = "default",
) -> InlineKeyboardMarkup:
    theme = _theme(skin)
    kb = InlineKeyboardBuilder()

    targets = _targets(board, selected)
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            sq = chess.square(file, rank)
            txt = _piece_text(board, sq, theme)
            if sq == selected:
                txt = theme["selected"]
            elif sq in targets:
                txt = theme["capture"] if board.piece_at(sq) else theme["move"]
            row.append(InlineKeyboardButton(text=txt, callback_data=cb_cell(gid, sq)))
        kb.row(*row)

    kb.row(
        InlineKeyboardButton(text="Reset", callback_data=f"chc|{gid}|reset"),
        InlineKeyboardButton(text="Resign", callback_data=f"chc|{gid}|resign"),
    )
    kb.row(InlineKeyboardButton(text="Menu", callback_data="sm:game:chess"))
    kb.row(InlineKeyboardButton(text="New game", callback_data=f"chc|{gid}|new"))
    return kb.as_markup()


def _termination_label(raw: str) -> str:
    return (
        raw.replace("Termination.", "")
        .replace("_", " ")
        .strip()
        .title()
    )


def render_text(
    white_name: str,
    black_name: str,
    board: chess.Board,
    selected: Optional[int],
    winner: Optional[bool],
    outcome_reason: str,
) -> str:
    if winner is chess.WHITE:
        return f"Chess\nWinner: <b>{white_name}</b> (white)\n<i>{outcome_reason or 'Game over'}</i>"
    if winner is chess.BLACK:
        return f"Chess\nWinner: <b>{black_name}</b> (black)\n<i>{outcome_reason or 'Game over'}</i>"

    if board.is_game_over(claim_draw=True):
        reason = outcome_reason
        if not reason:
            out = board.outcome(claim_draw=True)
            reason = _termination_label(str(out.termination)) if out else "Draw"
        return f"Chess\nDraw\n<i>{reason}</i>"

    who = white_name if board.turn == chess.WHITE else black_name
    side = "white" if board.turn == chess.WHITE else "black"
    sel = f" | selected: <code>{chess.square_name(selected)}</code>" if selected is not None else ""
    check = " | check" if board.is_check() else ""
    return f"Chess\nTurn: <b>{who}</b> ({side}){sel}{check}"

