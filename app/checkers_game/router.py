from __future__ import annotations

import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from .engine import (
    RED, BLUE,
    piece_color, legal_moves, apply_step, maybe_promote,
    count_pieces, has_any_moves, initial_board
)
from .storage import (
    create_lobby, join_lobby, get_lobby, get_game,
    user_active_game, enqueue_or_match, cancel_waiting, end_private_game
)
from .ui import build_board_kb, unpack_sq, render_text
from .ai import choose_turn

from app.i18n import t
from app.keyboards import arena_menu_kb
from app.db import init_db, upsert_user, bump_total, bump_weekly, get_rating, set_rating, get_skin_ck, get_chat, get_news

# update_elo is optional (exists in твоєму проекті для XO)
try:
    from app.rating import update_elo  # type: ignore
except Exception:
    update_elo = None

router = Router()

def _safe_name(u) -> str:
    return (u.full_name or u.username or str(u.id)).replace("<", "").replace(">", "")

async def _safe_edit(msg, text: str, reply_markup=None):
    try:
        await msg.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

def _join_kb(gid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Приєднатись (стати 🔵)", callback_data=f"ckj|{gid}")]]
    )

# ---------------- Entry points ----------------
@router.message(Command("checkers"))
async def cmd_checkers(msg: Message):
    # In private we show checkers menu; in group we create lobby
    if msg.chat.type == "private":
        lang = "uk"
        try:
            from app.i18n import detect_lang
            lang = detect_lang(msg)
        except Exception:
            pass
        await msg.answer(
            f"{t(lang,'brand_title')}\n{t(lang,'ck_choose')}",
            reply_markup=_checkers_menu(lang)
        )
        return
    await start_checkers_from_message(msg)

@router.callback_query(F.data == "sm:menu:checkers")
async def cb_menu_checkers(cb: CallbackQuery):
    await cb.answer()
    if cb.message:
        # If private => show checkers submenu; if group => create lobby
        if cb.message.chat.type == "private":
            lang = "uk"
            try:
                from app.i18n import detect_lang
                lang = detect_lang(cb)
            except Exception:
                pass
            await cb.message.edit_text(
                f"{t(lang,'brand_title')}\n{t(lang,'ck_choose')}",
                reply_markup=_checkers_menu(lang)
            )
        else:
            await start_checkers_from_message(cb.message)

def _checkers_menu(lang: str) -> InlineKeyboardMarkup:
    chat = get_chat()
    news = get_news()
    return arena_menu_kb(lang, "checkers", chat_url=chat.get('url',''), news_url=news.get('url',''))

def _ai_levels_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "ai_level_easy"), callback_data="sm:ck:ai:easy"),
            InlineKeyboardButton(text=t(lang, "ai_level_normal"), callback_data="sm:ck:ai:normal"),
            InlineKeyboardButton(text=t(lang, "ai_level_hard"), callback_data="sm:ck:ai:hard"),
        ],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:game:checkers")],
    ])

def _searching_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "ck_cancel_search"), callback_data="sm:ck:pvp:cancel")],
        [InlineKeyboardButton(text=t(lang, "back_to_games"), callback_data="sm:game:select")],
    ])

# ---------------- Checkers menu actions (private) ----------------
@router.callback_query(F.data == "sm:ck:play_ai")
async def ck_play_ai(cb: CallbackQuery):
    lang = "uk"
    try:
        from app.i18n import detect_lang
        lang = detect_lang(cb)
    except Exception:
        pass
    await cb.message.edit_text(t(lang, "ck_ai_choose"), reply_markup=_ai_levels_kb(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:ck:ai:"))
async def ck_ai_start(cb: CallbackQuery):
    level = cb.data.split(":")[-1]
    lang = "uk"
    try:
        from app.i18n import detect_lang
        lang = detect_lang(cb)
    except Exception:
        pass

    init_db()
    upsert_user(cb.from_user.id, cb.from_user.username, cb.from_user.first_name, lang)

    # prevent starting multiple games
    if user_active_game(cb.from_user.id):
        await cb.answer("Ти вже в грі.", show_alert=True)
        return

    # create session vs AI (user is RED, bot is BLUE)
    from .storage import STORE, GameSession
    gid = STORE.new_gid()
    gs = GameSession(
        gid=gid,
        red_id=cb.from_user.id,
        blue_id=0,
        red_name=_safe_name(cb.from_user),
        blue_name="AI",
        board=initial_board(),
        vs_ai=True,
        ai_level=level,
    )
    # send message in private chat
    text = render_text(gs.red_name, gs.blue_name, gs.turn, gs.selected, False, None)
    skin = get_skin_ck(cb.from_user.id)
    kb = build_board_kb(gs.gid, gs.board, gs.turn, gs.selected, gs.forced_from, skin=skin)
    await cb.message.edit_text(text, reply_markup=kb)

    gs.red_chat_id = cb.message.chat.id
    gs.red_message_id = cb.message.message_id
    STORE.games[gid] = gs
    STORE.active_by_user[gs.red_id] = gid

    await cb.answer()

@router.callback_query(F.data == "sm:ck:play_pvp")
async def ck_play_pvp(cb: CallbackQuery):
    lang = "uk"
    try:
        from app.i18n import detect_lang
        lang = detect_lang(cb)
    except Exception:
        pass

    if cb.message.chat.type != "private":
        # in group -> lobby
        await cb.answer()
        await start_checkers_from_message(cb.message)
        return

    if user_active_game(cb.from_user.id):
        await cb.answer("Ти вже в грі.", show_alert=True)
        return

    await cb.message.edit_text(
        f"{t(lang,'brand_title')}\n{t(lang,'ck_menu_pvp')}\n\nНатисни «Пошук», щоб знайти суперника.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Пошук", callback_data="sm:ck:pvp:search")],
            [InlineKeyboardButton(text=t(lang, "back_to_games"), callback_data="sm:game:select")],
        ])
    )
    await cb.answer()

@router.callback_query(F.data == "sm:ck:pvp:search")
async def ck_pvp_search(cb: CallbackQuery):
    lang = "uk"
    try:
        from app.i18n import detect_lang
        lang = detect_lang(cb)
    except Exception:
        pass

    if user_active_game(cb.from_user.id):
        await cb.answer("Ти вже в грі.", show_alert=True)
        return

    status, gs = enqueue_or_match(cb.from_user.id, _safe_name(cb.from_user))
    if status == "waiting":
        await cb.message.edit_text(t(lang, "ck_searching"), reply_markup=_searching_kb(lang))
        await cb.answer()
        return

    # matched -> create two messages
    assert gs is not None
    init_db()
    # ensure both users exist in DB
    upsert_user(gs.red_id, None, gs.red_name, lang)
    upsert_user(gs.blue_id, None, gs.blue_name, lang)
    # send game board to both users (each sees their own skin)
    text = render_text(gs.red_name, gs.blue_name, gs.turn, None, False, None)
    skin_red = get_skin_ck(gs.red_id)
    skin_blue = get_skin_ck(gs.blue_id)
    kb_red = build_board_kb(gs.gid, gs.board, gs.turn, None, None, skin=skin_red)
    kb_blue = build_board_kb(gs.gid, gs.board, gs.turn, None, None, skin=skin_blue)

    # IMPORTANT: in private, chat_id == user_id
    bot = cb.bot
    m_red = await bot.send_message(gs.red_id, text, reply_markup=kb_red)
    m_blue = await bot.send_message(gs.blue_id, text, reply_markup=kb_blue)

    gs.red_chat_id, gs.red_message_id = m_red.chat.id, m_red.message_id
    gs.blue_chat_id, gs.blue_message_id = m_blue.chat.id, m_blue.message_id

    await cb.message.edit_text("✅ Знайшов суперника! Дивись гру в чаті з ботом.", reply_markup=_checkers_menu(lang))
    await cb.answer()

@router.callback_query(F.data == "sm:ck:pvp:cancel")
async def ck_pvp_cancel(cb: CallbackQuery):
    lang = "uk"
    try:
        from app.i18n import detect_lang
        lang = detect_lang(cb)
    except Exception:
        pass

    cancel_waiting(cb.from_user.id)
    await cb.message.edit_text(
        f"{t(lang,'brand_title')}\n{t(lang,'ck_choose')}",
        reply_markup=_checkers_menu(lang)
    )
    await cb.answer("Пошук зупинено.")

# ---------------- Group lobby (as before) ----------------
async def start_checkers_from_message(msg: Message):
    # PvP найпростіше в групі
    if msg.chat.type == "private":
        # already handled via menu in private
        return

    existing = get_lobby(msg.chat.id)
    if existing and not existing.blue_id:
        await msg.answer("♟️ Лобі вже є. Хтось хай натисне «Приєднатись».")
        return

    init_db()
    upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name, None)

    lobby_msg = await msg.answer("♟️ Створюю лобі...")
    gs = create_lobby(
        chat_id=msg.chat.id,
        message_id=lobby_msg.message_id,
        creator_id=msg.from_user.id,
        creator_name=_safe_name(msg.from_user),
    )

    text = (
        "♟️ <b>Шашки</b>\n"
        f"Гравець 🔴: <b>{gs.red_name}</b>\n"
        "Гравець 🔵: <i>очікується</i>\n\n"
        "Натисни кнопку нижче, щоб приєднатись:"
    )

    await _safe_edit(
        lobby_msg,
        text,
        reply_markup=_join_kb(gs.gid),
    )

@router.callback_query(F.data.startswith("ckj|"))
async def join_cb(cb: CallbackQuery):
    gid = cb.data.split("|", 1)[1]
    gs = get_game(gid)
    if not gs:
        await cb.answer("Гру не знайдено.", show_alert=True)
        return

    if cb.message.chat.id != gs.chat_id:
        await cb.answer("Ця гра в іншому чаті.", show_alert=True)
        return

    if cb.from_user.id == gs.red_id:
        await cb.answer("Ти вже 🔴. Потрібен інший гравець 😄", show_alert=True)
        return

    if gs.blue_id and gs.blue_id != cb.from_user.id:
        await cb.answer("Вже є гравець 🔵.", show_alert=True)
        return

    joined = join_lobby(gs.chat_id, cb.from_user.id, _safe_name(cb.from_user))
    if not joined:
        await cb.answer("Не вдалось приєднатись.", show_alert=True)
        return

    gs = joined
    text = render_text(gs.red_name, gs.blue_name, gs.turn, gs.selected, gs.forced_from is not None, gs.winner)
    skin = get_skin_ck(cb.from_user.id)
    kb = build_board_kb(gs.gid, gs.board, gs.turn, gs.selected, gs.forced_from, skin=skin)

    await cb.answer("Починаємо!")
    await _safe_edit(cb.message, text, reply_markup=kb)

# ---------------- Core gameplay (group + private + AI) ----------------
async def _edit_game_messages(cb: CallbackQuery, gs):
    text = render_text(gs.red_name, gs.blue_name, gs.turn, gs.selected, gs.forced_from is not None, gs.winner)
    skin = get_skin_ck(cb.from_user.id)
    kb = build_board_kb(gs.gid, gs.board, gs.turn, gs.selected, gs.forced_from, skin=skin)

    # group game uses cb.message
    if not gs.is_private:
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        return

    bot = cb.bot

    skin_red = get_skin_ck(gs.red_id) if gs.red_id else 'default'
    skin_blue = get_skin_ck(gs.blue_id) if getattr(gs, 'blue_id', 0) else 'default'
    kb_red = build_board_kb(gs.gid, gs.board, gs.turn, gs.selected, gs.forced_from, skin=skin_red)
    kb_blue = build_board_kb(gs.gid, gs.board, gs.turn, gs.selected, gs.forced_from, skin=skin_blue)

    # edit both players (best effort)
    for chat_id, message_id in [(gs.red_chat_id, gs.red_message_id), (gs.blue_chat_id, gs.blue_message_id)]:
        if not chat_id or not message_id:
            continue
        kb = kb_red if chat_id == gs.red_chat_id else kb_blue
        try:
            await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                continue
        except Exception:
            continue


async def _tournament_hook(bot: Bot, gs):
    if getattr(gs, "tmatch_id", 0) and getattr(gs, "tournament_id", 0) and gs.winner in (RED, BLUE):
        winner_uid = int(gs.red_id) if gs.winner == RED else int(gs.blue_id)
        try:
            from app import db as _db
            _db.set_match_result(int(gs.tmatch_id), int(winner_uid))
            _db.advance_round_if_ready(int(gs.tournament_id))
        except Exception:
            pass
        try:
            from app.tournament_service import run_pending_for_tournament
            await run_pending_for_tournament(bot, int(gs.tournament_id))
        except Exception:
            pass

def _finish_and_score(gs):
    """Apply статистику/рейтинги тільки для ігор з реальним суперником (PvP).

    ВАЖЛИВО: vs AI — не чіпаємо ні статистику, ні Elo, ні weekly.
    """
    try:
        init_db()
    except Exception:
        return

    # vs AI: не рахуємо статистику/elo, але звільняємо сесію, щоб гравець міг стартувати нову гру
    if getattr(gs, "vs_ai", False):
        if gs.is_private:
            end_private_game(gs)
        return

    if gs.red_id and gs.blue_id:
        red_win = (gs.winner == RED)
        blue_win = (gs.winner == BLUE)

        # counters
        bump_total(gs.red_id, win=red_win, game="checkers")
        bump_total(gs.blue_id, win=blue_win, game="checkers")
        bump_weekly(gs.red_id, win=red_win, game="checkers")
        bump_weekly(gs.blue_id, win=blue_win, game="checkers")

        # Elo
        try:
            rx = get_rating(gs.red_id, game="checkers")
            rb = get_rating(gs.blue_id, game="checkers")
            score_red = 1.0 if red_win else 0.0
            if update_elo:
                nr, nb = update_elo(rx, rb, score_red)
            else:
                # fallback elo K=24
                def exp(ra, rb):
                    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400))
                ea = exp(rx, rb)
                k = 24
                nr = int(round(rx + k * (score_red - ea)))
                nb = int(round(rb + k * ((1.0 - score_red) - (1.0 - ea))))

            set_rating(gs.red_id, nr, game="checkers")
            set_rating(gs.blue_id, nb, game="checkers")
        except Exception:
            pass

    if gs.is_private:
        end_private_game(gs)


@router.callback_query(F.data.startswith("ck|"))
async def board_click(cb: CallbackQuery):
    try:
        _, gid, rc = cb.data.split("|")
    except ValueError:
        await cb.answer("Bad data", show_alert=True)
        return

    gs = get_game(gid)
    if not gs:
        await cb.answer("Гру не знайдено.", show_alert=True)
        return

    # AI game: only red player exists
    if gs.vs_ai:
        if cb.from_user.id != gs.red_id:
            await cb.answer("Це не твоя гра.", show_alert=True)
            return
    else:
        # group lobby still waiting?
        if gs.blue_id == 0 and not gs.is_private:
            await cb.answer("Чекаємо другого гравця.", show_alert=True)
            return

        if cb.from_user.id not in (gs.red_id, gs.blue_id):
            await cb.answer("Це не твоя гра 😅", show_alert=True)
            return

    if gs.finished:
        await cb.answer("Гра завершена. Натисни «Нова гра».", show_alert=True)
        return

    # whose color is clicking
    if cb.from_user.id == gs.red_id:
        color = RED
    elif cb.from_user.id == gs.blue_id:
        color = BLUE
    else:
        color = RED  # vs ai

    if color != gs.turn:
        await cb.answer("Не твій хід.", show_alert=True)
        return

    r, c = unpack_sq(rc)
    gs.touch()

    moves_map = legal_moves(gs.board, gs.turn, forced_from=gs.forced_from)

    # 1) вибір шашки
    if gs.selected is None:
        if piece_color(gs.board[r][c]) != gs.turn:
            await cb.answer("Вибери свою шашку.", show_alert=False)
            return
        if (r, c) not in moves_map:
            await cb.answer("Цією шашкою зараз ходити не можна.", show_alert=False)
            return
        gs.selected = (r, c)
        await cb.answer()
        await _edit_game_messages(cb, gs)
        return

    # 2) хід/перевибір
    # перемикаємо вибір (тільки якщо немає примусового продовження взяття)
    if gs.forced_from is None and piece_color(gs.board[r][c]) == gs.turn and (r, c) in moves_map:
        gs.selected = (r, c)
        await cb.answer()
        await _edit_game_messages(cb, gs)
        return

    from_sq = gs.selected
    options = moves_map.get(from_sq, [])
    chosen = next((mv for mv in options if mv.to == (r, c)), None)
    if chosen is None:
        await cb.answer("Невірний хід.", show_alert=False)
        return

    gs.board = apply_step(gs.board, chosen)

    if chosen.captured:
        gs.forced_from = chosen.to if legal_moves(gs.board, gs.turn, forced_from=chosen.to) else None
        if gs.forced_from is None:
            gs.board = maybe_promote(gs.board, chosen.to)
            gs.turn *= -1
            gs.selected = None
        else:
            gs.selected = gs.forced_from
    else:
        gs.board = maybe_promote(gs.board, chosen.to)
        gs.turn *= -1
        gs.selected = None
        gs.forced_from = None

    # перемога: суперник без шашок або без ходів
    opp = gs.turn
    if count_pieces(gs.board, opp) == 0 or not has_any_moves(gs.board, opp):
        gs.finished = True
        gs.winner = -opp
        gs.selected = None
        gs.forced_from = None
        _finish_and_score(gs)
        await _tournament_hook(cb.bot, gs)
        await cb.answer()
        await _edit_game_messages(cb, gs)
        return

    await cb.answer()
    await _edit_game_messages(cb, gs)

    # AI response (if needed)
    if gs.vs_ai and gs.turn == BLUE and not gs.finished:
        await asyncio.sleep(0.2)
        gs.board, gs.turn = choose_turn(gs.board, BLUE, gs.ai_level)
        # check win after AI move
        opp = gs.turn
        if count_pieces(gs.board, opp) == 0 or not has_any_moves(gs.board, opp):
            gs.finished = True
            gs.winner = -opp
            _finish_and_score(gs)
        await _edit_game_messages(cb, gs)

@router.callback_query(F.data.startswith("ckc|"))
async def control_cb(cb: CallbackQuery):
    try:
        _, gid, action = cb.data.split("|")
    except ValueError:
        await cb.answer("Bad data", show_alert=True)
        return

    gs = get_game(gid)
    if not gs:
        await cb.answer("Гру не знайдено.", show_alert=True)
        return

    uid = cb.from_user.id
    if gs.vs_ai:
        if uid != gs.red_id:
            await cb.answer("Це не твоя гра.", show_alert=True)
            return
    else:
        if uid not in (gs.red_id, gs.blue_id):
            await cb.answer("Це не твоя гра.", show_alert=True)
            return

    if action == "reset":
        if gs.forced_from is not None:
            await cb.answer("Не можна скинути під час примусового взяття.", show_alert=True)
            return
        gs.selected = None
        await cb.answer("Скинуто.")

    elif action == "resign":
        color = RED if uid == gs.red_id else BLUE
        gs.finished = True
        gs.winner = -color
        gs.selected = None
        gs.forced_from = None
        _finish_and_score(gs)
        await cb.answer("Здача прийнята.")

    elif action == "new":
        gs.board = initial_board()
        gs.turn = RED
        gs.selected = None
        gs.forced_from = None
        gs.finished = False
        gs.winner = None
        await cb.answer("Нова гра!")

    else:
        await cb.answer("Невідома дія.", show_alert=True)
        return

    await _edit_game_messages(cb, gs)
