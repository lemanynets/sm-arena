# app/nardy_game/router.py
"""Callback query handlers for Nardi (Short Backgammon)."""
from __future__ import annotations

import uuid
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from .engine import (
    NardyGame, WHITE, BLACK,
    new_game, get_game, delete_game,
    legal_moves, apply_move, ai_move, check_winner,
)
from .ui import build_board_kb, render_text

from app.db import init_db, upsert_user
from app.i18n import detect_lang, t

router = Router()


def _safe_name(u) -> str:
    return (u.full_name or u.username or str(u.id)).replace("<", "").replace(">", "")


async def _safe_edit(msg, text: str, reply_markup=None):
    try:
        await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise


async def _safe_answer(cb: CallbackQuery, text: str | None = None, show_alert: bool = False):
    try:
        await cb.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest:
        pass


# ---------------------------------------------------------------------------
# Start game (from callback nds|ai / nds|pvp)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("nds|"))
async def nardy_start_cb(cb: CallbackQuery):
    _, mode = cb.data.split("|", 1)
    uid = cb.from_user.id
    uname = _safe_name(cb.from_user)

    init_db()
    lang = "uk"
    try:
        lang = detect_lang(cb)
    except Exception:
        pass
    upsert_user(uid, cb.from_user.username, cb.from_user.first_name, lang)

    gid = str(uuid.uuid4())[:8]
    gs = new_game(gid, uid, uname, vs_ai=(mode == "ai"),
                  chat_id=cb.message.chat.id)

    gs.message_id = cb.message.message_id
    await _safe_answer(cb)
    await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))


# ---------------------------------------------------------------------------
# Control buttons (roll, resign, new)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("ndc|"))
async def nardy_ctrl_cb(cb: CallbackQuery):
    _, gid, action = cb.data.split("|", 2)
    gs = get_game(gid)

    if not gs:
        await _safe_answer(cb, "Гру не знайдено. Почни нову.", show_alert=True)
        return

    # Only the active player can act
    if cb.from_user.id not in (gs.white_id, gs.black_id) and not (gs.vs_ai and cb.from_user.id == gs.white_id):
        await _safe_answer(cb, "Це не твоя гра.", show_alert=True)
        return
    if not gs.vs_ai and (
        (gs.turn == WHITE and cb.from_user.id != gs.white_id) or
        (gs.turn == BLACK and cb.from_user.id != gs.black_id)
    ):
        await _safe_answer(cb, "Зачекай свого ходу.")
        return

    if action == "roll":
        if gs.dice is not None:
            await _safe_answer(cb, "Ти вже кинув кубики — роби хід!")
            return
        if gs.finished:
            await _safe_answer(cb, "Гра вже завершена.")
            return
        gs.roll()
        moves = gs.get_moves()
        if not moves:
            # No legal moves — pass turn
            gs.dice = None
            gs.turn = -gs.turn
            await _safe_answer(cb, "Немає доступних ходів — хід передано.")
        await _safe_answer(cb)
        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))

    elif action == "resign":
        if not gs.finished:
            gs.finished = True
            gs.winner = BLACK if gs.turn == WHITE else WHITE
        await _safe_answer(cb, "Ти здався!")
        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))

    elif action == "new":
        uid = cb.from_user.id
        uname = _safe_name(cb.from_user)
        delete_game(gid)
        new_gid = str(uuid.uuid4())[:8]
        new_gs = new_game(new_gid, uid, uname, vs_ai=gs.vs_ai,
                          chat_id=cb.message.chat.id)
        await _safe_answer(cb)
        await _safe_edit(cb.message, render_text(new_gs), reply_markup=build_board_kb(new_gs))


# ---------------------------------------------------------------------------
# Board point click (select / move)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("nd|"))
async def nardy_point_cb(cb: CallbackQuery):
    parts = cb.data.split("|")
    if len(parts) != 3:
        return
    _, gid, pt_str = parts
    try:
        pt = int(pt_str)
    except ValueError:
        return

    gs = get_game(gid)
    if not gs:
        await _safe_answer(cb, "Гру не знайдено.", show_alert=True)
        return

    if gs.finished:
        await _safe_answer(cb, "Гра завершена!")
        return

    # Check if it's this user's turn
    is_white_turn = gs.turn == WHITE and cb.from_user.id == gs.white_id
    is_black_turn = gs.turn == BLACK and (
        (gs.vs_ai is False and cb.from_user.id == gs.black_id) or False
    )
    if gs.vs_ai:
        # In AI mode white is the human player
        if gs.turn != WHITE or cb.from_user.id != gs.white_id:
            await _safe_answer(cb, "Зачекай — AI ходить...")
            return
    else:
        if not (is_white_turn or is_black_turn):
            await _safe_answer(cb, "Зачекай свого ходу.")
            return

    if gs.dice is None:
        await _safe_answer(cb, "Спочатку кинь кубики! 🎲")
        return

    moves = gs.get_moves()

    # First click — select source
    if gs.selected is None:
        v = gs.board[pt] if 1 <= pt <= 24 else 0
        if v == 0 or (gs.turn == WHITE and v < 0) or (gs.turn == BLACK and v > 0):
            await _safe_answer(cb, "Обери свою шашку.")
            return
        # Check if this piece has any moves
        local_dests = {t for f, t, d in moves if f == pt}
        if not local_dests:
            await _safe_answer(cb, "Ця шашка не може ходити.")
            return
        gs.selected = pt
        await _safe_answer(cb)
        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))
        return

    # Second click — try to move or re-select
    if pt == gs.selected:
        # Deselect
        gs.selected = None
        await _safe_answer(cb)
        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))
        return

    # Check if target is a valid dest
    valid_moves = [(f, t, d) for f, t, d in moves if f == gs.selected and t == pt]
    if not valid_moves:
        # Try re-selecting (if user clicked own piece)
        v = gs.board[pt] if 1 <= pt <= 24 else 0
        if (gs.turn == WHITE and v > 0) or (gs.turn == BLACK and v < 0):
            local_dests = {t for f, t, d in moves if f == pt}
            if local_dests:
                gs.selected = pt
                await _safe_answer(cb)
                await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))
                return
        await _safe_answer(cb, "Недопустимий хід.")
        return

    frm, to, die = valid_moves[0]
    gs.board = apply_move(gs.board, gs.turn, frm, to)
    gs.selected = None

    w = check_winner(gs.board)
    if w is not None:
        gs.finished = True
        gs.winner = w
        await _safe_answer(cb)
        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))
        return

    # Check if any more moves are available with remaining dice
    remaining_moves = gs.get_moves()
    # Remove consumed die (for doubles we keep consuming; for different dice remove the used one)
    d1, d2 = gs.dice
    if d1 == d2:
        # Subtract one use — we track by counting remaining checkers is too complex;
        # simplify: reset dice so human must roll again (for simplicity)
        pass

    # Switch turn after consuming move
    # Simple approach: after any click the entire dice roll is used and turn passes
    # (full proper dice tracking is complex; we give one pair per turn)
    gs.dice = None  # reset so next player must roll
    gs.turn = -gs.turn

    await _safe_answer(cb)
    await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))

    # If vs AI and now it's AI's turn
    if gs.vs_ai and gs.turn == BLACK and not gs.finished:
        import asyncio
        await asyncio.sleep(0.8)
        dice = gs.roll()
        new_board, made = ai_move(gs.board, BLACK, dice)
        gs.board = new_board
        gs.dice = None
        gs.turn = WHITE

        w = check_winner(gs.board)
        if w is not None:
            gs.finished = True
            gs.winner = w

        await _safe_edit(cb.message, render_text(gs), reply_markup=build_board_kb(gs))
