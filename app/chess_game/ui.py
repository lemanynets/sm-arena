from __future__ import annotations

from typing import Optional, Set

import chess
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------------------------------------------------------------------
# Piece Style Variants
# ---------------------------------------------------------------------------
_PIECES_CLASSIC = {  # Unicode outline pieces (default)
    "P": "♙", "p": "♟",
    "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

_PIECES_EMOJI = {  # Fun emoji characters
    "P": "💂", "p": "👾",
    "N": "🦄", "B": "🧙", "R": "🏰", "Q": "👸", "K": "🤴",
    "n": "🐴", "b": "🧛", "r": "🗼", "q": "🧟", "k": "💀",
}

_PIECES_LETTERS = {  # Text letters — fastest to read
    "P": "P", "p": "p",
    "N": "N", "B": "B", "R": "R", "Q": "Q", "K": "K",
    "n": "n", "b": "b", "r": "r", "q": "q", "k": "k",
}

_PIECES_FILLED = {  # Filled / solid block style
    "P": "♟", "p": "♟",
    "N": "♞", "B": "♝", "R": "♜", "Q": "♛", "K": "♚",
    "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

PIECE_STYLES: dict[str, dict] = {
    "classic": _PIECES_CLASSIC,
    "emoji":   _PIECES_EMOJI,
    "letters": _PIECES_LETTERS,
    "filled":  _PIECES_FILLED,
}

# ---------------------------------------------------------------------------
# Board / Cell Style Variants  (light_square, dark_square)
# ---------------------------------------------------------------------------
BOARD_STYLES: dict[str, tuple[str, str]] = {
    "classic": ("⠀", "⠀"),
    "neon":    ("🟢", "🟤"),
    "ocean":   ("🌊", "🌑"),
    "fire":    ("🔥", "🌑"),
    "ice":     ("❄️", "🌑"),
    "royal":   ("⠀", "⠀"),      # Invisible background (clean look)
    "clear":   ("⠀", "⠀"),      # Added explicitly for those wanting a completely empty board
}

# Highlight overlays (selected / legal move target)
_HL_SELECTED = "🟡"
_HL_MOVE     = "🟢"
_HL_CAPTURE  = "❌"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_skin(skin: str) -> tuple[dict, tuple[str, str]]:
    """Return (piece_map, (light_cell, dark_cell)) from a composite skin string.
    Skin format: "<pieces_style>:<board_style>"  e.g. "emoji:fire"
    Falls back gracefully on unknown tokens.
    """
    parts = (skin or "classic:classic").split(":", 1)
    pieces_key = parts[0] if parts[0] in PIECE_STYLES else "classic"
    board_key  = parts[1] if len(parts) > 1 and parts[1] in BOARD_STYLES else "classic"
    return PIECE_STYLES[pieces_key], BOARD_STYLES[board_key]


def unpack_sq(token: str) -> int:
    return chess.parse_square(token)


def cb_cell(gid: str, square: int) -> str:
    return f"ch|{gid}|{chess.square_name(square)}"


def _piece_text(
    board: chess.Board,
    square: int,
    pieces: dict,
    light: str,
    dark: str,
) -> str:
    piece = board.piece_at(square)
    if piece:
        return pieces.get(piece.symbol(), piece.symbol())
    is_dark = (chess.square_file(square) + chess.square_rank(square)) % 2 == 1
    return dark if is_dark else light


def _targets(board: chess.Board, selected: Optional[int]) -> Set[int]:
    if selected is None:
        return set()
    out: Set[int] = set()
    for mv in board.legal_moves:
        if mv.from_square == selected:
            out.add(mv.to_square)
    return out


# ---------------------------------------------------------------------------
# Board Keyboard Builder
# ---------------------------------------------------------------------------

def build_board_kb(
    gid: str,
    board: chess.Board,
    selected: Optional[int],
    skin: str = "classic:classic",
) -> InlineKeyboardMarkup:
    pieces, (light, dark) = _parse_skin(skin)
    kb = InlineKeyboardBuilder()
    targets = _targets(board, selected)

    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            sq = chess.square(file, rank)
            if sq == selected:
                txt = _HL_SELECTED
            elif sq in targets:
                txt = _HL_CAPTURE if board.piece_at(sq) else _HL_MOVE
            else:
                txt = _piece_text(board, sq, pieces, light, dark)
            row.append(InlineKeyboardButton(text=txt, callback_data=cb_cell(gid, sq)))
        kb.row(*row)

    kb.row(
        InlineKeyboardButton(text="🔄 Скинути", callback_data=f"chc|{gid}|reset"),
        InlineKeyboardButton(text="🏳 Здатися", callback_data=f"chc|{gid}|resign"),
    )
    kb.row(InlineKeyboardButton(text="⬅️ Меню", callback_data="sm:game:chess"))
    kb.row(InlineKeyboardButton(text="♻️ Нова гра", callback_data=f"chc|{gid}|new"))
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Text Rendering
# ---------------------------------------------------------------------------

def _termination_label(raw: str) -> str:
    return raw.replace("Termination.", "").replace("_", " ").strip().title()


def render_text(
    white_name: str,
    black_name: str,
    board: chess.Board,
    selected: Optional[int],
    winner: Optional[bool],
    outcome_reason: str,
) -> str:
    """Render the board state as human-readable HTML text."""
    if winner is chess.WHITE:
        return (
            f"♛ <b>Шахи</b>\n"
            f"🏆 Переможець: <b>{white_name}</b> (білі)\n"
            f"<i>{outcome_reason or 'Гра завершена'}</i>"
        )
    if winner is chess.BLACK:
        return (
            f"♛ <b>Шахи</b>\n"
            f"🏆 Переможець: <b>{black_name}</b> (чорні)\n"
            f"<i>{outcome_reason or 'Гра завершена'}</i>"
        )

    if board.is_game_over(claim_draw=True):
        reason = outcome_reason
        if not reason:
            out = board.outcome(claim_draw=True)
            reason = _termination_label(str(out.termination)) if out else "Нічия"
        return f"♛ <b>Шахи</b>\n🤝 Нічия\n<i>{reason}</i>"

    who  = white_name if board.turn == chess.WHITE else black_name
    side = "⬜ білі"  if board.turn == chess.WHITE else "⬛ чорні"
    sel  = f" | вибрано: <code>{chess.square_name(selected)}</code>" if selected is not None else ""
    check = " | ⚠️ шах!" if board.is_check() else ""
    return f"♛ <b>Шахи</b>\nХід: <b>{who}</b> ({side}){sel}{check}"
