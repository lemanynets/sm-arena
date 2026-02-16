from __future__ import annotations

import asyncio
from typing import Optional

import chess
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .ai import choose_move
from .storage import (
    GameSession,
    STORE,
    cancel_waiting,
    create_lobby,
    enqueue_or_match,
    end_private_game,
    get_game,
    get_lobby,
    join_lobby,
    user_active_game,
)
from .ui import build_board_kb, render_text, unpack_sq

from app.db import get_chat, get_news, get_skin, init_db, upsert_user
from app.i18n import detect_lang, t
from app.keyboards import arena_menu_kb

router = Router()


def _safe_name(u) -> str:
    return (u.full_name or u.username or str(u.id)).replace("<", "").replace(">", "")


def _lang_or_default(event) -> str:
    try:
        return detect_lang(event)
    except Exception:
        return "uk"


async def _safe_edit(msg, text: str, reply_markup=None):
    try:
        await msg.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise


async def _safe_answer(cb: CallbackQuery, text: str | None = None, show_alert: bool = False):
    try:
        await cb.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        s = str(e).lower()
        if "query is too old" in s or "query id is invalid" in s or "response timeout expired" in s:
            return
        raise


def _join_kb(gid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Join as black", callback_data=f"chj|{gid}")]]
    )


def _chess_menu(lang: str) -> InlineKeyboardMarkup:
    chat = get_chat()
    news = get_news()
    return arena_menu_kb(lang, "chess", chat_url=chat.get("url", ""), news_url=news.get("url", ""))


def _ai_levels_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "ai_level_easy"), callback_data="sm:ch:ai:easy"),
                InlineKeyboardButton(text=t(lang, "ai_level_normal"), callback_data="sm:ch:ai:normal"),
                InlineKeyboardButton(text=t(lang, "ai_level_hard"), callback_data="sm:ch:ai:hard"),
            ],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:game:chess")],
        ]
    )


def _searching_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "ch_cancel_search"), callback_data="sm:ch:pvp:cancel")],
            [InlineKeyboardButton(text=t(lang, "back_to_games"), callback_data="sm:game:select")],
        ]
    )


def _select_move(candidates: list[chess.Move]) -> Optional[chess.Move]:
    if not candidates:
        return None
    # Auto-promotion preference.
    for pref in (chess.QUEEN, chess.KNIGHT, chess.ROOK, chess.BISHOP):
        for mv in candidates:
            if mv.promotion == pref:
                return mv
    return candidates[0]


def _update_game_over(gs: GameSession) -> bool:
    if not gs.board.is_game_over(claim_draw=True):
        return False
    out = gs.board.outcome(claim_draw=True)
    gs.finished = True
    gs.winner = out.winner if out else None
    if out:
        gs.outcome_reason = (
            str(out.termination).replace("Termination.", "").replace("_", " ").title()
        )
    if gs.is_private:
        end_private_game(gs)
    return True


async def _edit_game_messages(cb: CallbackQuery, gs: GameSession):
    text = render_text(gs.white_name, gs.black_name, gs.board, gs.selected, gs.winner, gs.outcome_reason)

    if not gs.is_private:
        skin = get_skin(cb.from_user.id)
        kb = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin)
        await _safe_edit(cb.message, text, reply_markup=kb)
        return

    bot = cb.bot
    skin_white = get_skin(gs.white_id) if gs.white_id else "default"
    skin_black = get_skin(gs.black_id) if gs.black_id else "default"
    kb_white = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin_white)
    kb_black = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin_black)

    for chat_id, message_id in (
        (gs.white_chat_id, gs.white_message_id),
        (gs.black_chat_id, gs.black_message_id),
    ):
        if not chat_id or not message_id:
            continue
        kb = kb_white if chat_id == gs.white_chat_id else kb_black
        try:
            await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                continue
        except Exception:
            continue


@router.message(Command("chess"))
async def cmd_chess(msg: Message):
    if msg.chat.type == "private":
        lang = _lang_or_default(msg)
        await msg.answer(f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}", reply_markup=_chess_menu(lang))
        return
    await start_chess_from_message(msg)


@router.callback_query(F.data == "sm:menu:chess")
async def cb_menu_chess(cb: CallbackQuery):
    await _safe_answer(cb)
    if not cb.message:
        return
    if cb.message.chat.type == "private":
        lang = _lang_or_default(cb)
        await cb.message.edit_text(f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}", reply_markup=_chess_menu(lang))
    else:
        await start_chess_from_message(cb.message)


@router.callback_query(F.data == "sm:ch:play_ai")
async def ch_play_ai(cb: CallbackQuery):
    lang = _lang_or_default(cb)
    await cb.message.edit_text(t(lang, "ch_ai_choose"), reply_markup=_ai_levels_kb(lang))
    await _safe_answer(cb)


@router.callback_query(F.data.startswith("sm:ch:ai:"))
async def ch_ai_start(cb: CallbackQuery):
    level = (cb.data or "").split(":")[-1]
    lang = _lang_or_default(cb)

    init_db()
    upsert_user(cb.from_user.id, cb.from_user.username, cb.from_user.first_name, lang)

    active = user_active_game(cb.from_user.id)
    if active:
        if getattr(active, "finished", False):
            end_private_game(active)
        elif getattr(active, "vs_ai", False) and int(getattr(active, "white_id", 0)) == int(cb.from_user.id):
            text = render_text(
                active.white_name,
                active.black_name,
                active.board,
                active.selected,
                active.winner,
                active.outcome_reason,
            )
            skin = get_skin(cb.from_user.id)
            kb = build_board_kb(active.gid, active.board, active.selected, skin=skin)
            m = await cb.message.answer(text, reply_markup=kb)
            active.white_chat_id = m.chat.id
            active.white_message_id = m.message_id
            await cb.message.edit_text(
                f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}",
                reply_markup=_chess_menu(lang),
            )
            await _safe_answer(cb, "Game restored ✅")
            return
        else:
            await _safe_answer(cb, "You already have an active game.", show_alert=True)
            return

    gid = STORE.new_gid()
    gs = GameSession(
        gid=gid,
        white_id=cb.from_user.id,
        black_id=0,
        white_name=_safe_name(cb.from_user),
        black_name="AI",
        board=chess.Board(),
        vs_ai=True,
        ai_level=level,
    )
    text = render_text(gs.white_name, gs.black_name, gs.board, gs.selected, gs.winner, gs.outcome_reason)
    skin = get_skin(cb.from_user.id)
    kb = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin)
    await cb.message.edit_text(text, reply_markup=kb)

    gs.white_chat_id = cb.message.chat.id
    gs.white_message_id = cb.message.message_id
    STORE.games[gid] = gs
    STORE.active_by_user[gs.white_id] = gid

    await _safe_answer(cb)


@router.callback_query(F.data == "sm:ch:play_pvp")
async def ch_play_pvp(cb: CallbackQuery):
    lang = _lang_or_default(cb)

    if cb.message.chat.type != "private":
        await _safe_answer(cb)
        await start_chess_from_message(cb.message)
        return

    active = user_active_game(cb.from_user.id)
    if active:
        if getattr(active, "finished", False):
            end_private_game(active)
        else:
            await _safe_answer(cb, "You already have an active game.", show_alert=True)
            return

    await cb.message.edit_text(
        f"{t(lang,'brand_title')}\n{t(lang,'ch_menu_pvp')}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Find opponent", callback_data="sm:ch:pvp:search")],
                [InlineKeyboardButton(text=t(lang, "back_to_games"), callback_data="sm:game:select")],
            ]
        ),
    )
    await _safe_answer(cb)


@router.callback_query(F.data == "sm:ch:pvp:search")
async def ch_pvp_search(cb: CallbackQuery):
    lang = _lang_or_default(cb)

    active = user_active_game(cb.from_user.id)
    if active:
        if getattr(active, "finished", False):
            end_private_game(active)
        else:
            await _safe_answer(cb, "You already have an active game.", show_alert=True)
            return

    status, gs = enqueue_or_match(cb.from_user.id, _safe_name(cb.from_user))
    if status == "waiting":
        await cb.message.edit_text(t(lang, "ch_searching"), reply_markup=_searching_kb(lang))
        await _safe_answer(cb)
        return

    assert gs is not None
    init_db()
    upsert_user(gs.white_id, None, gs.white_name, lang)
    upsert_user(gs.black_id, None, gs.black_name, lang)

    text = render_text(gs.white_name, gs.black_name, gs.board, gs.selected, gs.winner, gs.outcome_reason)
    skin_white = get_skin(gs.white_id)
    skin_black = get_skin(gs.black_id)
    kb_white = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin_white)
    kb_black = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin_black)

    bot = cb.bot
    m_white = await bot.send_message(gs.white_id, text, reply_markup=kb_white)
    m_black = await bot.send_message(gs.black_id, text, reply_markup=kb_black)

    gs.white_chat_id, gs.white_message_id = m_white.chat.id, m_white.message_id
    gs.black_chat_id, gs.black_message_id = m_black.chat.id, m_black.message_id

    await cb.message.edit_text("Opponent found. Game sent to your private chat.", reply_markup=_chess_menu(lang))
    await _safe_answer(cb)


@router.callback_query(F.data == "sm:ch:pvp:cancel")
async def ch_pvp_cancel(cb: CallbackQuery):
    lang = _lang_or_default(cb)
    cancel_waiting(cb.from_user.id)
    await cb.message.edit_text(
        f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}",
        reply_markup=_chess_menu(lang),
    )
    await _safe_answer(cb, "Search cancelled")


async def start_chess_from_message(msg: Message):
    if msg.chat.type == "private":
        return

    existing = get_lobby(msg.chat.id)
    if existing and not existing.black_id:
        await msg.answer("Chess lobby already exists here. Join it from the button.")
        return

    init_db()
    upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name, None)

    lobby_msg = await msg.answer("Creating chess lobby...")
    gs = create_lobby(
        chat_id=msg.chat.id,
        message_id=lobby_msg.message_id,
        creator_id=msg.from_user.id,
        creator_name=_safe_name(msg.from_user),
    )

    text = (
        "♞ <b>Chess</b>\n"
        f"White: <b>{gs.white_name}</b>\n"
        "Black: <i>waiting</i>\n\n"
        "Tap the button below to join:"
    )
    await _safe_edit(lobby_msg, text, reply_markup=_join_kb(gs.gid))


@router.callback_query(F.data.startswith("chj|"))
async def join_cb(cb: CallbackQuery):
    gid = cb.data.split("|", 1)[1]
    gs = get_game(gid)
    if not gs:
        lang = _lang_or_default(cb)
        if cb.message and cb.message.chat.type == "private":
            await _safe_edit(
                cb.message,
                f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}\n\nPrevious game is no longer available. Start a new one.",
                reply_markup=_chess_menu(lang),
            )
        await _safe_answer(cb, "Game not found. Start a new one.", show_alert=True)
        return

    if cb.message.chat.id != gs.chat_id:
        await _safe_answer(cb, "This game is in another chat.", show_alert=True)
        return
    if cb.from_user.id == gs.white_id:
        await _safe_answer(cb, "You are already white.", show_alert=True)
        return
    if gs.black_id and gs.black_id != cb.from_user.id:
        await _safe_answer(cb, "Black player is already taken.", show_alert=True)
        return

    joined = join_lobby(gs.chat_id, cb.from_user.id, _safe_name(cb.from_user))
    if not joined:
        await _safe_answer(cb, "Could not join this game.", show_alert=True)
        return

    gs = joined
    text = render_text(gs.white_name, gs.black_name, gs.board, gs.selected, gs.winner, gs.outcome_reason)
    skin = get_skin(cb.from_user.id)
    kb = build_board_kb(gs.gid, gs.board, gs.selected, skin=skin)
    await _safe_answer(cb, "Game started")
    await _safe_edit(cb.message, text, reply_markup=kb)


@router.callback_query(F.data.startswith("ch|"))
async def board_click(cb: CallbackQuery):
    try:
        _, gid, sq_token = cb.data.split("|")
    except ValueError:
        await _safe_answer(cb, "Bad data", show_alert=True)
        return

    gs = get_game(gid)
    if not gs:
        lang = _lang_or_default(cb)
        if cb.message and cb.message.chat.type == "private":
            await _safe_edit(
                cb.message,
                f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}\n\nPrevious game was closed after restart. Start a new game.",
                reply_markup=_chess_menu(lang),
            )
        await _safe_answer(cb, "Game not found. Start a new game.", show_alert=True)
        return

    if gs.vs_ai:
        if cb.from_user.id != gs.white_id:
            await _safe_answer(cb, "This is not your game.", show_alert=True)
            return
    else:
        if gs.black_id == 0 and not gs.is_private:
            await _safe_answer(cb, "Waiting for second player.", show_alert=True)
            return
        if cb.from_user.id not in (gs.white_id, gs.black_id):
            await _safe_answer(cb, "This is not your game.", show_alert=True)
            return

    if gs.finished:
        await _safe_answer(cb, "Game is already finished.", show_alert=True)
        return

    if cb.from_user.id == gs.white_id:
        side = chess.WHITE
    elif cb.from_user.id == gs.black_id:
        side = chess.BLACK
    else:
        side = chess.WHITE

    if side != gs.board.turn:
        await _safe_answer(cb, "Not your move.", show_alert=True)
        return

    try:
        sq = unpack_sq(sq_token)
    except Exception:
        await _safe_answer(cb, "Bad square", show_alert=True)
        return

    gs.touch()
    legal = list(gs.board.legal_moves)

    if gs.selected is None:
        piece = gs.board.piece_at(sq)
        if not piece or piece.color != gs.board.turn:
            await _safe_answer(cb, "Select your piece.")
            return
        if not any(mv.from_square == sq for mv in legal):
            await _safe_answer(cb, "This piece has no legal moves.")
            return
        gs.selected = sq
        await _safe_answer(cb)
        await _edit_game_messages(cb, gs)
        return

    piece = gs.board.piece_at(sq)
    if piece and piece.color == gs.board.turn and any(mv.from_square == sq for mv in legal):
        gs.selected = sq
        await _safe_answer(cb)
        await _edit_game_messages(cb, gs)
        return

    candidates = [
        mv
        for mv in legal
        if mv.from_square == gs.selected and mv.to_square == sq
    ]
    mv = _select_move(candidates)
    if mv is None:
        await _safe_answer(cb, "Illegal move.")
        return

    gs.board.push(mv)
    gs.selected = None
    _update_game_over(gs)
    await _safe_answer(cb)
    await _edit_game_messages(cb, gs)

    if gs.vs_ai and not gs.finished and gs.board.turn == chess.BLACK:
        await asyncio.sleep(0.25)
        ai_mv = choose_move(gs.board, gs.ai_level)
        if ai_mv is not None:
            gs.board.push(ai_mv)
        _update_game_over(gs)
        await _edit_game_messages(cb, gs)


@router.callback_query(F.data.startswith("chc|"))
async def control_cb(cb: CallbackQuery):
    try:
        _, gid, action = cb.data.split("|")
    except ValueError:
        await _safe_answer(cb, "Bad data", show_alert=True)
        return

    gs = get_game(gid)
    if not gs:
        lang = _lang_or_default(cb)
        if cb.message and cb.message.chat.type == "private":
            await _safe_edit(
                cb.message,
                f"{t(lang,'brand_title')}\n{t(lang,'ch_choose')}\n\nPrevious game is no longer available. Start a new one.",
                reply_markup=_chess_menu(lang),
            )
        await _safe_answer(cb, "Game not found. Start a new game.", show_alert=True)
        return

    uid = cb.from_user.id
    if gs.vs_ai:
        if uid != gs.white_id:
            await _safe_answer(cb, "This is not your game.", show_alert=True)
            return
    else:
        if uid not in (gs.white_id, gs.black_id):
            await _safe_answer(cb, "This is not your game.", show_alert=True)
            return

    if action == "reset":
        gs.selected = None
        await _safe_answer(cb, "Selection cleared.")
    elif action == "resign":
        gs.finished = True
        gs.selected = None
        gs.winner = chess.BLACK if uid == gs.white_id else chess.WHITE
        gs.outcome_reason = "Resignation"
        if gs.is_private:
            end_private_game(gs)
        await _safe_answer(cb, "Resigned.")
    elif action == "new":
        gs.board.reset()
        gs.selected = None
        gs.finished = False
        gs.winner = None
        gs.outcome_reason = ""
        if gs.is_private:
            STORE.active_by_user[gs.white_id] = gs.gid
            if gs.black_id:
                STORE.active_by_user[gs.black_id] = gs.gid
        await _safe_answer(cb, "New game started.")
    else:
        await _safe_answer(cb, "Unknown action.", show_alert=True)
        return

    await _edit_game_messages(cb, gs)
