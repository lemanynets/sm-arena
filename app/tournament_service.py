
# app/tournament_service.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from aiogram import Bot

from app import db
from app.config import (
    DAILY_TOURNAMENT_HOUR, DAILY_TOURNAMENT_MINUTE,
    TOURN_REG_MINUTES, TOURN_DAILY_SIZE, TOURN_ENTRY_FEE,
    TOURN_TECH_LOSS_SEC,
)

# For XO UI
from app.keyboards import board_kb_pvp
from app.i18n import t
from app.db import db_get_lang, get_skin, get_skin_ck

# For Checkers UI
from app.checkers_game.ui import build_board_kb, render_text
from app.checkers_game.engine import RED, BLUE
from app.checkers_game.storage import create_private_match, STORE

@dataclass
class _BotWrap:
    bot: Bot

# ---------- XO tournament match start ----------
async def start_xo_tournament_match(bot: Bot, a_id: int, b_id: int, tournament_id: int, tmatch_id: int):
    match_id = str(uuid.uuid4())[:8]
    board = "........."

    a_lang = db_get_lang(a_id) or "en"
    b_lang = db_get_lang(b_id) or "en"

    ma = await bot.send_message(
        a_id,
        f"🏆 {t(a_lang,'tourn_match_found')}",
        reply_markup=board_kb_pvp(match_id, board, a_lang, skin=get_skin(a_id), show_controls=False)
    )
    mb = await bot.send_message(
        b_id,
        f"🏆 {t(b_lang,'tourn_match_found')}",
        reply_markup=board_kb_pvp(match_id, board, b_lang, skin=get_skin(b_id), show_controls=False)
    )

    # Inject into handlers_menu PVP registry
    from app.handlers_menu import PVP_MATCHES, set_pvp_timer
    PVP_MATCHES[match_id] = {
        "board": board,
        "x": a_id,
        "o": b_id,
        "turn": "X",
        "status": "playing",
        "last_move": time.time(),
        "x_chat": a_id,
        "o_chat": b_id,
        "x_msg": ma.message_id,
        "o_msg": mb.message_id,
        "x_lang": a_lang,
        "o_lang": b_lang,
        "tournament_id": int(tournament_id),
        "tmatch_id": int(tmatch_id),
        "tourn_techloss": 1,
    }
    set_pvp_timer(match_id, _BotWrap(bot))  # reuse watchdog

# ---------- Checkers tournament match start ----------
async def start_checkers_tournament_match(bot: Bot, a_id: int, b_id: int, tournament_id: int, tmatch_id: int):
    # Names
    au = db.get_user(a_id) or {}
    bu = db.get_user(b_id) or {}
    a_name = (("@"+au.get("username")) if (au.get("username") or "").strip() else (au.get("first_name") or "Player")).strip()
    b_name = (("@"+bu.get("username")) if (bu.get("username") or "").strip() else (bu.get("first_name") or "Player")).strip()

    gs = create_private_match(a_id, a_name, b_id, b_name, tournament_id=int(tournament_id), tmatch_id=int(tmatch_id))

    # Send initial boards
    # Each player sees their own perspective with skins
    a_lang = db.db_get_lang(a_id) or "en"
    b_lang = db.db_get_lang(b_id) or "en"
    skin_a = get_skin_ck(a_id)
    skin_b = get_skin_ck(b_id)

    text_a = "🏆 Турнір: матч знайдено!"
    text_b = "🏆 Турнір: матч знайдено!"

    msg_a = await bot.send_message(a_id, text_a + "\n" + render_text(gs.red_name, gs.blue_name, gs.turn, gs.selected, gs.forced_from is not None, gs.winner), reply_markup=build_board_kb(gs, a_lang, skin=skin_a))
    msg_b = await bot.send_message(b_id, text_b + "\n" + render_text(gs.red_name, gs.blue_name, gs.turn, gs.selected, gs.forced_from is not None, gs.winner), reply_markup=build_board_kb(gs, b_lang, skin=skin_b))

    gs.red_chat_id = a_id if gs.red_id == a_id else b_id
    gs.blue_chat_id = b_id if gs.blue_id == b_id else a_id
    # set message ids
    if gs.red_id == a_id:
        gs.red_message_id = msg_a.message_id
        gs.blue_message_id = msg_b.message_id
    else:
        gs.red_message_id = msg_b.message_id
        gs.blue_message_id = msg_a.message_id

    # Start anti-afk watchdog for this checkers game
    asyncio.create_task(_checkers_watchdog(bot, gs.gid))


async def _checkers_watchdog(bot: Bot, gid: str):
    try:
        while True:
            await asyncio.sleep(5)
            gs = STORE.games.get(gid)
            if not gs or gs.finished:
                return
            if (time.time() - gs.last_activity) < TOURN_TECH_LOSS_SEC:
                continue

            # tech loss: current turn player loses
            loser_color = gs.turn
            winner_color = BLUE if loser_color == RED else RED
            gs.finished = True
            gs.winner = winner_color

            # Determine winner user id
            winner_uid = gs.red_id if winner_color == RED else gs.blue_id
            loser_uid = gs.blue_id if winner_color == RED else gs.red_id

            # Update UI
            try:
                await bot.send_message(winner_uid, "⏳ Турнір: суперник не прийшов — тех. перемога ✅")
            except Exception:
                pass
            try:
                await bot.send_message(loser_uid, "⏳ Турнір: ти не зробив хід — тех. поразка ❌")
            except Exception:
                pass

            # Tournament hook
            if gs.tmatch_id and gs.tournament_id:
                try:
                    db.set_match_result(int(gs.tmatch_id), int(winner_uid))
                    db.advance_round_if_ready(int(gs.tournament_id))
                except Exception:
                    pass

            # End game clean
            from app.checkers_game.storage import end_private_game
            end_private_game(gs)
            return
    except asyncio.CancelledError:
        return


# ---------- Tournament engine ----------
async def run_pending_for_tournament(bot: Bot, tournament_id: int):
    t = db.get_tournament_by_id(tournament_id)
    if not t:
        return
    game = str(t["game"])
    pend = db.get_pending_matches(tournament_id)
    for m in pend:
        a = int(m["a_id"]); b = int(m["b_id"])
        db.mark_match_playing(int(m["id"]))
        if game == "checkers":
            await start_checkers_tournament_match(bot, a, b, tournament_id, int(m["id"]))
        else:
            await start_xo_tournament_match(bot, a, b, tournament_id, int(m["id"]))

async def close_and_start_if_ready(bot: Bot, t: dict):
    tid = int(t["id"])
    game = str(t["game"])
    players = db.list_tournament_players(tid)
    if len(players) < db.TOURN_MIN_PLAYERS:
        db.cancel_tournament(tid)
        # refunds handled in db.cancel_tournament
        return
    matches = db.generate_bracket(tid)
    if not matches:
        db.cancel_tournament(tid)
        return
    await run_pending_for_tournament(bot, tid)


async def tournament_registrar_loop(bot: Bot):
    """Checks registration windows, sends reminders, and starts/cancels tournaments automatically."""
    from app.config import TOURN_REMIND_2M_SEC, TOURN_REMIND_30S_SEC
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    def _rem_kb():
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Турніри", callback_data="sm:tourn:home")]
        ])

    async def _notify(tinfo: dict, left_sec: int):
        tid = int(tinfo["id"])
        game = str(tinfo.get("game") or "")
        label = "❌⭕ XO" if game != "checkers" else "♟️ Шашки"
        pool = int(tinfo.get("prize_pool") or 0)
        size = int(tinfo.get("size") or 0)
        fee = int(tinfo.get("entry_fee") or 0)
        # participants count
        try:
            players = db.list_tournament_players(tid)
        except Exception:
            players = []
        cnt = len(players)

        msg = (
            f"⏳ {label}: реєстрація закінчиться через <b>{max(0,left_sec)//60:02d}:{max(0,left_sec)%60:02d}</b>\n"
            f"Учасники: <b>{cnt}/{size}</b> | Вхід: <b>{fee}🪙</b> або 🎫 | Фонд: <b>{pool}🪙</b>"
        )
        for p in players:
            uid = int(p.get("user_id") or 0)
            if not uid:
                continue
            try:
                await bot.send_message(uid, msg, reply_markup=_rem_kb())
            except Exception:
                pass

    while True:
        try:
            # reminders for REG tournaments
            try:
                regs = db.get_reg_open_tournaments()
            except Exception:
                regs = []
            now = time.time()

            for tinfo in regs:
                try:
                    tid = int(tinfo["id"])
                    left = int(float(tinfo["reg_ends_ts"]) - now)
                    if left <= 0:
                        continue

                    # 2m reminder
                    if int(tinfo.get("remind_2m_sent") or 0) == 0 and left <= int(TOURN_REMIND_2M_SEC):
                        await _notify(tinfo, left)
                        try:
                            db.mark_tournament_reminder(tid, "2m")
                        except Exception:
                            pass

                    # 30s reminder
                    if int(tinfo.get("remind_30s_sent") or 0) == 0 and left <= int(TOURN_REMIND_30S_SEC):
                        await _notify(tinfo, left)
                        try:
                            db.mark_tournament_reminder(tid, "30s")
                        except Exception:
                            pass

                except Exception:
                    pass

            # start/cancel when reg ends
            expired = db.get_reg_expired_tournaments()
            for t in expired:
                await close_and_start_if_ready(bot, t)
        except Exception:
            pass

        await asyncio.sleep(10)

def _next_daily_ts() -> float:
    # Uses local time of server; recommend Europe/Uzhgorod on VPS.
    now = time.time()
    lt = time.localtime(now)
    target = time.struct_time((
        lt.tm_year, lt.tm_mon, lt.tm_mday,
        DAILY_TOURNAMENT_HOUR, DAILY_TOURNAMENT_MINUTE, 0,
        lt.tm_wday, lt.tm_yday, lt.tm_isdst
    ))
    target_ts = time.mktime(target)
    if target_ts <= now:
        target_ts += 24 * 3600
    return target_ts

async def daily_tournament_loop(bot: Bot):
    """Creates daily tournaments for XO and Checkers at configured time."""
    while True:
        try:
            target_ts = _next_daily_ts()
            await asyncio.sleep(max(1, target_ts - time.time()))
            # create tournaments
            reg_end = time.time() + TOURN_REG_MINUTES * 60
            day_key = db._today_key_uzh(time.time())
            for game, title in (("xo", f"🏆 Daily XO {day_key}"), ("checkers", f"🏆 Daily Checkers {day_key}")):
                db.create_tournament(
                    game, title, TOURN_DAILY_SIZE, created_by=0,
                    entry_fee=TOURN_ENTRY_FEE, reg_ends_ts=reg_end,
                    auto_daily=True, day_key=day_key
                )
        except Exception:
            pass
        await asyncio.sleep(1)
