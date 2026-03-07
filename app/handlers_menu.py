# app/handlers_menu.py
import uuid
import asyncio
import time
import secrets
import string
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from aiogram import Bot, Router, F
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest

from app.keyboards import (
    main_menu_kb,
    games_select_kb,
    arena_menu_kb,
    settings_menu_kb,
    market_menu_kb,
    ai_levels_kb,
    random_side_kb,
    searching_kb,
    language_kb,
    donate_kb,
    skins_kb,
    vip_kb,
    board_kb,
    board_kb_pvp,
)
from app.game_engine import apply_move, check_winner, ai_move_easy, ai_move_normal, ai_move_hard
from app.i18n import t, detect_lang
from app.rating import update_elo
from app.winline import get_winline
from app.shop_items import items_for_game, get_item

from app import config
from app.config import (
    ADMIN_IDS,
    SEASON_LENGTH_DAYS,
    SOFT_RESET_FACTOR,
    ANTI_BOOST_WINDOW_HOURS,
    ANTI_BOOST_MAX_RATED,
    PVP_INACTIVITY_SEC,
    CLICK_RATE_LIMIT_SEC,
    TOP_N,
    DONATE_AMOUNTS,
    DEFAULT_SKIN,
    SKINS,
    VIP_COIN_PLANS,
    VIP_FALLBACK_AI_SEC,
    NONVIP_FALLBACK_AI_SEC,
)

from app.db import (
    init_db,
    upsert_user,
    get_user,
    get_rating,
    set_rating,
    set_lang as db_set_lang,
    get_lang as db_get_lang,
    set_skin as db_set_skin,
    get_skin,
    is_vip,
    add_vip_days,
    add_prize_pool,
    get_prize_pool,
    get_sponsor,
    get_active_game,
    set_active_game,
    get_chat,
    get_news,
    set_skin_ck,
    get_skin_ck,
    set_skin_board,
    get_skin_board,
    set_skin_cell,
    get_skin_cell,
    set_skin_board_ck,
    get_skin_board_ck,
    set_skin_cell_ck,
    get_skin_cell_ck,
    get_coins,
    add_coins,
    get_quest_mask,
    set_quest_mask,
    create_invite,
    consume_invite,
    reset_week_if_needed,
    get_weekly_top,
    get_weekly_rank,
    load_week_history,
    bump_total,
    bump_weekly,
    is_banned,
    is_rated_pair_game,
    record_pair_game,    try_spend_coins,
    has_item,
    add_item,
    owned_item_ids,
    get_inventory,
    set_active_item,
    get_top100,
    reset_season_if_needed,
    get_season_meta,
    get_season_rating,
    set_season_rating,
    inc_season_games,
    add_bp_xp,
    is_shadowbanned,
    try_pay_referral_reward,
    try_attach_referral,
    get_ref_stats,
    get_season_top100,
    create_tournament,
    get_active_tournament,
    list_tournament_players,
    join_tournament,
    leave_tournament,
    generate_bracket,
    get_pending_matches,
    mark_match_playing,
    set_match_result,
    advance_round_if_ready,
    get_bracket_text,
    cancel_tournament,

)

_tma_url: str = ""

def set_tma_url(url: str):
    global _tma_url
    _tma_url = url

router = Router()

WIN_EMOJI = "🎉🎊🥳🏆🔥"
LOSE_EMOJI = "😢💔🥲"
DRAW_EMOJI = "🤝😌"

ANTI_BOOST_WINDOW_SEC = ANTI_BOOST_WINDOW_HOURS * 60 * 60
SEASON_LEN = timedelta(days=SEASON_LENGTH_DAYS)

AI_MATCHES = {}

# queues split by VIP for priority matchmaking
WAIT_X_VIP, WAIT_O_VIP = [], []
WAIT_X, WAIT_O = [], []
WAIT_TASKS = {}

PVP_MATCHES = {}
PVP_TIMER_TASKS = {}

LAST_CLICK = {}

# ---- helpers ----
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def click_ok(uid: int) -> bool:
    now = time.time()
    if now - LAST_CLICK.get(uid, 0.0) < CLICK_RATE_LIMIT_SEC:
        return False
    LAST_CLICK[uid] = now
    return True

async def safe_edit_text(message, text: str, reply_markup=None, **kwargs):
    """Edit message text safely (ignores Telegram 'message is not modified')."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

def ensure_user(cb_or_msg):
    u = cb_or_msg.from_user
    # lang: stored or detected
    lang = db_get_lang(u.id) or detect_lang(getattr(u, "language_code", None))
    upsert_user(u.id, getattr(u, "username", None), getattr(u, "first_name", None), lang)
    # seasons: rotate if needed
    try:
        reset_season_if_needed(top_n=50)
    except Exception:
        pass
    return lang

def menu_kb(lang: str, uid: int):
    g = get_active_game(uid)
    chat = get_chat()
    news = get_news()
    return arena_menu_kb(lang, g, chat_url=chat.get('url',''), news_url=news.get('url',''))

def compute_highlight(board: str) -> set[int]:
    wl = get_winline(board)
    if not wl:
        return set()
    _, line = wl
    return set(line)

def best_match(opponents: list, target_rating: int):
    if not opponents:
        return None
    best_i = 0
    best_diff = abs(int(opponents[0].get("rating", 1000)) - target_rating)
    for i, it in enumerate(opponents[1:], start=1):
        diff = abs(int(it.get("rating", 1000)) - target_rating)
        if diff < best_diff:
            best_i = i
            best_diff = diff
    return opponents.pop(best_i)

def is_in_queue(uid: int) -> bool:
    allq = WAIT_X_VIP + WAIT_O_VIP + WAIT_X + WAIT_O
    return any(it["user_id"] == uid for it in allq)

def remove_from_queue(uid: int) -> None:
    global WAIT_X_VIP, WAIT_O_VIP, WAIT_X, WAIT_O
    WAIT_X_VIP = [it for it in WAIT_X_VIP if it["user_id"] != uid]
    WAIT_O_VIP = [it for it in WAIT_O_VIP if it["user_id"] != uid]
    WAIT_X = [it for it in WAIT_X if it["user_id"] != uid]
    WAIT_O = [it for it in WAIT_O if it["user_id"] != uid]

def cancel_wait_task(uid: int):
    task = WAIT_TASKS.pop(uid, None)
    if task and not task.done():
        task.cancel()

def cancel_pvp_timer(match_id: str):
    task = PVP_TIMER_TASKS.pop(match_id, None)
    if task and not task.done():
        task.cancel()

def set_pvp_timer(match_id: str, cb: CallbackQuery):
    cancel_pvp_timer(match_id)
    PVP_TIMER_TASKS[match_id] = asyncio.create_task(pvp_inactivity_watchdog(match_id, cb))

async def pvp_inactivity_watchdog(match_id: str, cb: CallbackQuery):
    try:
        while True:
            await asyncio.sleep(5)
            m = PVP_MATCHES.get(match_id)
            if not m or m.get("status") != "playing":
                return
            if time.time() - m["last_move"] < PVP_INACTIVITY_SEC:
                continue

            # Tournament anti-AFK: tech loss for the player who didn't move
            if m.get("tmatch_id") and m.get("tournament_id"):
                loser_turn = m.get("turn")  # "X" or "O"
                winner_turn = "O" if loser_turn == "X" else "X"
                winner_id = int(m.get("x")) if winner_turn == "X" else int(m.get("o"))
                loser_id = int(m.get("o")) if winner_turn == "X" else int(m.get("x"))

                m["status"] = "finished"
                cancel_pvp_timer(match_id)

                try:
                    x_chat = m.get("x_chat"); o_chat = m.get("o_chat")
                    x_msg = m.get("x_msg"); o_msg = m.get("o_msg")
                    if x_chat and x_msg:
                        await cb.bot.edit_message_text(chat_id=x_chat, message_id=x_msg, text="⏳ Турнір: тех. поразка (inactive)")
                    if o_chat and o_msg:
                        await cb.bot.edit_message_text(chat_id=o_chat, message_id=o_msg, text="⏳ Турнір: тех. поразка (inactive)")
                except Exception:
                    pass

                try:
                    set_match_result(int(m["tmatch_id"]), winner_id)
                    advance_round_if_ready(int(m["tournament_id"]))
                    try:
                        from app.tournament_service import run_pending_for_tournament
                        await run_pending_for_tournament(cb.bot, int(m["tournament_id"]))
                    except Exception:
                        pass
                    try:
                        await cb.bot.send_message(winner_id, "🏆 Турнір: тех. перемога ✅")
                    except Exception:
                        pass
                    try:
                        await cb.bot.send_message(loser_id, "🏆 Турнір: тех. поразка ❌")
                    except Exception:
                        pass
                except Exception:
                    pass
                return

            m["status"] = "canceled"
            cancel_pvp_timer(match_id)

            # Try to update BOTH players (if we have their message ids)
            try:
                x_chat = m.get("x_chat")
                o_chat = m.get("o_chat")
                x_msg = m.get("x_msg")
                o_msg = m.get("o_msg")
                if x_chat and x_msg:
                    await cb.bot.edit_message_text(chat_id=x_chat, message_id=x_msg, text="⏳ PvP canceled (inactive)")
                if o_chat and o_msg:
                    await cb.bot.edit_message_text(chat_id=o_chat, message_id=o_msg, text="⏳ PvP canceled (inactive)")
            except Exception:
                pass
            return
    except asyncio.CancelledError:
        return


def donate_invoice(uid: int, stars: int, lang: str):
    prices = [LabeledPrice(label="SM Arena donation", amount=int(stars))]
    payload = f"SM_ARENA_DONATE:{uid}:{stars}:{int(time.time())}"
    return prices, payload

@router.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)

@router.message(F.successful_payment)
async def on_success_payment(m: Message):
    init_db()
    lang = ensure_user(m)

    sp = m.successful_payment
    payload = (sp.invoice_payload or "")

    if payload.startswith("SM_ARENA_DONATE"):
        stars = 0
        try:
            stars = int(payload.split(":")[2])
        except Exception:
            stars = int(getattr(sp, "total_amount", 0) or 0)
        if stars > 0:
            pool = add_prize_pool(stars)
            await m.answer(f"✅ +{stars}⭐  | pool={pool}")
        return

# ---- commands ----
@router.message(Command("id"))
async def cmd_id(m: Message):
    lang = ensure_user(m)
    await m.answer(t(lang, "id_text").format(id=m.from_user.id))

@router.message(Command("vip"))
async def cmd_vip(m: Message):
    lang = ensure_user(m)
    if is_vip(m.from_user.id):
        date = datetime.fromtimestamp(add_vip_days(m.from_user.id, 0), tz=timezone.utc).strftime("%Y-%m-%d")
        text = t(lang, "vip_status_on").format(date=date)
    else:
        text = t(lang, "vip_status_off")
    await m.answer(f"{t(lang,'vip_title')}\n\n{text}", reply_markup=vip_kb(lang))

@router.message(CommandStart())
async def start(m: Message):
    init_db()
    lang = ensure_user(m)

    # weekly reset + archive
    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    # deep-link payload
    payload = ""
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) > 1:
        payload = parts[1].strip()

    # referral payload: /start ref_<inviter_id>
    if payload.startswith("ref_"):
        try:
            inviter_id = int(payload[4:])
            attached = try_attach_referral(m.from_user.id, inviter_id)
            if attached:
                await m.answer("🤝 Рефералка активована! Тобі нараховано +50 🪙. Твій запрошувач отримає 100 🪙 після того, як ти зіграєш 3 рейтингові гри.")
        except Exception:
            pass

    if payload.startswith("inv_"):
        token = payload[4:]
        await _handle_invite_start(m, token, lang)
        return

    # Delete the /start command to keep chat clean
    try:
        await m.delete()
    except Exception:
        pass

    active = get_active_game(m.from_user.id)
    await m.answer(
        f"{t(lang,'brand_title')}\n{t(lang,'choose_game')}\n\n{t(lang,'choose_game_hint')}",
        reply_markup=games_select_kb(lang, active)
    )

# ---- Menu callbacks ----
@router.callback_query(F.data == "sm:menu:home")
async def menu_home(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    g = get_active_game(cb.from_user.id)
    if g == "checkers":
        g_title = t(lang, "game_checkers")
    elif g == "chess":
        g_title = t(lang, "game_chess")
    else:
        g_title = t(lang, "game_xo")
    await safe_edit_text(
        cb.message,
        f"{t(lang,'brand_title')}\n{g_title}\n\n{t(lang,'menu_quick_hint')}",
        reply_markup=menu_kb(lang, cb.from_user.id)
    )
    await cb.answer()



# ---------- GAME SELECT / COMMON MENUS ----------
BOT_USERNAME_CACHE = None

async def _get_bot_username(bot) -> str:
    global BOT_USERNAME_CACHE
    if BOT_USERNAME_CACHE:
        return BOT_USERNAME_CACHE
    me = await bot.get_me()
    BOT_USERNAME_CACHE = (me.username or "").strip()
    return BOT_USERNAME_CACHE


@router.callback_query(F.data == "sm:game:select")
async def game_select(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    active = get_active_game(cb.from_user.id)
    await safe_edit_text(
        cb.message,
        f"{t(lang,'brand_title')}\n{t(lang,'choose_game')}\n\n{t(lang,'choose_game_hint')}",
        reply_markup=games_select_kb(lang, active)
    )
    await cb.answer()


@router.callback_query(F.data == "sm:game:xo")
async def game_choose_xo(cb: CallbackQuery):
    # IMPORTANT: do not call menu_home() here because it has its own click_ok()
    # and would ignore the first click (double rate-limit).
    if not click_ok(cb.from_user.id):
        await cb.answer()
        return
    init_db()
    lang = ensure_user(cb)
    set_active_game(cb.from_user.id, "xo")

    # keep weekly reset consistent with /start
    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    await safe_edit_text(
        cb.message,
        f"{t(lang,'brand_title')}\n{t(lang,'game_xo')}\n\n{t(lang,'menu_quick_hint')}",
        reply_markup=menu_kb(lang, cb.from_user.id),
    )
    await cb.answer()


@router.callback_query(F.data == "sm:game:checkers")
async def game_choose_checkers(cb: CallbackQuery):
    # IMPORTANT: do not call menu_home() here because it has its own click_ok()
    # and would ignore the first click (double rate-limit).
    if not click_ok(cb.from_user.id):
        await cb.answer()
        return
    init_db()
    lang = ensure_user(cb)
    set_active_game(cb.from_user.id, "checkers")

    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    await safe_edit_text(
        cb.message,
        f"{t(lang,'brand_title')}\n{t(lang,'game_checkers')}\n\n{t(lang,'menu_quick_hint')}",
        reply_markup=menu_kb(lang, cb.from_user.id),
    )
    await cb.answer()


@router.callback_query(F.data == "sm:game:chess")
async def game_choose_chess(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer()
        return
    init_db()
    lang = ensure_user(cb)
    set_active_game(cb.from_user.id, "chess")

    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    await safe_edit_text(
        cb.message,
        f"{t(lang,'brand_title')}\n{t(lang,'game_chess')}\n\n{t(lang,'menu_quick_hint')}",
        reply_markup=menu_kb(lang, cb.from_user.id),
    )
    await cb.answer()

@router.callback_query(F.data == "sm:menu:settings")
async def menu_settings(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)
    await safe_edit_text(cb.message, f"{t(lang,'settings_title')}", reply_markup=settings_menu_kb(lang))
    await cb.answer()


@router.callback_query(F.data == "sm:menu:market")
async def menu_market(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)
    try:
        from app.main import _TMA_URL as _tma_url
    except Exception:
        _tma_url = ""
    await safe_edit_text(cb.message, f"{t(lang,'market_title')}", reply_markup=market_menu_kb(lang, tma_url=_tma_url))
    await cb.answer()

@router.callback_query(F.data == "sm:menu:coins")
async def menu_coins(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)

    packs = getattr(config, "STARS_COIN_PACKS", {
        "coins_50": (50, 25),
        "coins_200": (200, 100),
        "coins_500": (500, 250),
        "coins_1200": (1200, 600),
    })

    rows = []
    for sku, (coins, stars) in packs.items():
        rows.append([InlineKeyboardButton(text=f"{coins} 🪙 за ⭐️ {stars} Stars", callback_data=f"stars:coins:{sku}")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:market")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    text = "💳 <b>Купівля Монет</b>\nОплачуй швидко і безпечно прямо в Telegram зірками (Stars)! 👇"
    if lang == "en":
        text = "💳 <b>Buy Coins</b>\nPay quickly and securely right in Telegram using Stars! 👇"
        
    await safe_edit_text(cb.message, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()

# =========================
# SHOP / INVENTORY (coins)
# =========================
def _market_nav_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="sm:menu:market")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])


def _game_title(lang: str, g: str) -> str:
    game = (g or "xo").lower()
    if game == "checkers":
        return t(lang, "game_checkers")
    if game == "chess":
        return t(lang, "game_chess")
    return t(lang, "game_xo")


def _skin_allowed(user_id: int, game: str, skin: str) -> bool:
    # default/classic are always available; VIP can use all; otherwise must own via shop
    k = (skin or "default").lower()
    if k in ("default", "classic"):
        return True
    if is_vip(user_id):
        return True
    gid = "checkers" if (game or "xo") == "checkers" else "xo"
    return has_item(user_id, f"skin:{gid}:{k}")


@router.callback_query(F.data == "sm:market:shop")
async def market_shop(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    g = get_active_game(cb.from_user.id)
    coins = get_coins(cb.from_user.id)
    owned = owned_item_ids(cb.from_user.id)

    items = items_for_game(g)

    lines = [
        "🛍 <b>Магазин</b>",
        f"🎮 Гра: <b>{_game_title(lang, g)}</b>",
        f"💰 Баланс: <b>{coins}</b> 🪙",
        "",
        "Вибери товар:",
    ]

    rows = []
    for it in items:
        iid = it["item_id"]
        price = int(it.get("price", 0) or 0)
        if iid in owned:
            prefix = "✅ "
        else:
            prefix = f"{price}🪙 "
        rows.append([InlineKeyboardButton(text=f"{prefix}{it['title']}", callback_data=f"sm:market:item:{iid}")])

    rows.append([InlineKeyboardButton(text="🎒 Інвентар", callback_data="sm:market:inv")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sm:menu:market")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("sm:market:item:"))
async def market_item(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    iid = cb.data[len("sm:market:item:"):]
    it = get_item(iid)
    if not it:
        await cb.answer("Невідомий товар"); return

    g = get_active_game(cb.from_user.id)
    coins = get_coins(cb.from_user.id)
    owned = has_item(cb.from_user.id, iid)
    if it.get("kind") == "lootbox":
        owned = False  # Lootboxes are never "owned", you just open them

    item_game = (it.get("game") or "xo").lower()
    cur_skin = get_skin_ck(cb.from_user.id) if item_game == "checkers" else get_skin(cb.from_user.id)

    lines = [
        f"🛍 <b>{it.get('title')}</b>",
        f"{it.get('desc','')}",
        "",
        f"💰 Баланс: <b>{coins}</b> 🪙"
    ]

    if owned:
        lines.append("Статус: ✅ <b>куплено</b>")
        if (it.get("kind") == "skin") and (str(it.get("value")) == str(cur_skin)):
            lines.append("Активовано: ✅")
    elif it.get("kind") == "lootbox":
        lines.append(f"Ціна відкриття: <b>{int(it.get('price',0))}</b> 🪙")
    else:
        lines.append("Статус: ⛔ <b>не куплено</b>")

    rows = []
    if owned:
        rows.append([InlineKeyboardButton(text="✅ Активувати", callback_data=f"sm:market:activate:{iid}")])
    else:
        btn_text = f"🎁 Відкрити за {int(it.get('price',0))}🪙" if it.get("kind") == "lootbox" else f"🛒 Купити за {int(it.get('price',0))}🪙"
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"sm:market:buy:{iid}")])

    rows.append([InlineKeyboardButton(text="⬅️ До магазину", callback_data="sm:market:shop")])
    rows.append([InlineKeyboardButton(text="🎒 Інвентар", callback_data="sm:market:inv")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("sm:market:buy:"))
async def market_buy(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    iid = cb.data[len("sm:market:buy:"):]
    it = get_item(iid)
    if not it:
        await cb.answer("Невідомий товар"); return

    if it.get("kind") != "lootbox" and has_item(cb.from_user.id, iid):
        await cb.answer("Вже куплено"); 
        await market_item(cb)
        return

    price = int(it.get("price", 0) or 0)
    ok = try_spend_coins(cb.from_user.id, price)
    if not ok:
        await cb.answer("Недостатньо монет 🪙", show_alert=True)
        return

    import random
    if it.get("kind") == "lootbox":
        chances = it.get("loot_table", [])
        roll = random.random()
        cumulative = 0.0
        won_id, won_name = None, "Нічого"
        for prob, l_id, l_name in chances:
            cumulative += prob
            if roll <= cumulative:
                won_id, won_name = l_id, l_name
                break
                
        if won_id and won_id.startswith("coins:"):
            coins_won = int(won_id.split(":")[1])
            add_coins(cb.from_user.id, coins_won)
            await cb.answer(f"🎉 Ти відкрив скриню!\n\nТвій приз: {won_name}", show_alert=True)
        elif won_id and won_id.startswith("skin:"):
            if has_item(cb.from_user.id, won_id):
                add_coins(cb.from_user.id, 50)
                await cb.answer(f"🎉 Скриня дала: {won_name}, але він вже є.\nКомпенсація: 50🪙", show_alert=True)
            else:
                add_item(cb.from_user.id, won_id)
                await cb.answer(f"🎉 Ти відкрив скриню!\n\nТвій приз: {won_name}", show_alert=True)
        else:
            await cb.answer("Скриня виявилась порожньою...", show_alert=True)
            
        await market_item(cb)
        return

    add_item(cb.from_user.id, iid)

    # auto-activate on purchase
    if it.get("kind") == "skin":
        g = (it.get("game") or "xo").lower()
        skin = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_ck(cb.from_user.id, skin)
        else:
            db_set_skin(cb.from_user.id, skin)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_board":
        g = (it.get("game") or "xo").lower()
        val = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_board_ck(cb.from_user.id, val)
        else:
            set_skin_board(cb.from_user.id, val)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_cell":
        g = (it.get("game") or "xo").lower()
        val = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_cell_ck(cb.from_user.id, val)
        else:
            set_skin_cell(cb.from_user.id, val)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_chess_board":
        from app.db import set_skin_chess_board
        set_skin_chess_board(cb.from_user.id, str(it.get("value") or "classic"))
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_chess_pieces":
        from app.db import set_skin_chess_pieces
        set_skin_chess_pieces(cb.from_user.id, str(it.get("value") or "classic"))
        set_active_item(cb.from_user.id, iid)

    await cb.answer("✅ Куплено та активовано!")
    await market_item(cb)


@router.callback_query(F.data.startswith("sm:market:activate:"))
async def market_activate(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    ensure_user(cb)

    iid = cb.data[len("sm:market:activate:"):]
    it = get_item(iid)
    if not it:
        await cb.answer("Невідомий товар"); return

    if not has_item(cb.from_user.id, iid):
        await cb.answer("Спочатку купи 🛒", show_alert=True)
        return

    if it.get("kind") == "skin":
        g = (it.get("game") or "xo").lower()
        skin = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_ck(cb.from_user.id, skin)
        else:
            db_set_skin(cb.from_user.id, skin)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_board":
        g = (it.get("game") or "xo").lower()
        val = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_board_ck(cb.from_user.id, val)
        else:
            set_skin_board(cb.from_user.id, val)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_cell":
        g = (it.get("game") or "xo").lower()
        val = str(it.get("value") or "default")
        if g == "checkers":
            set_skin_cell_ck(cb.from_user.id, val)
        else:
            set_skin_cell(cb.from_user.id, val)
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_chess_board":
        from app.db import set_skin_chess_board
        set_skin_chess_board(cb.from_user.id, str(it.get("value") or "classic"))
        set_active_item(cb.from_user.id, iid)
    elif it.get("kind") == "skin_chess_pieces":
        from app.db import set_skin_chess_pieces
        set_skin_chess_pieces(cb.from_user.id, str(it.get("value") or "classic"))
        set_active_item(cb.from_user.id, iid)

    await cb.answer("✅ Активовано")
    await market_item(cb)


@router.callback_query(F.data == "sm:market:inv")
async def market_inventory(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    g = get_active_game(cb.from_user.id)
    coins = get_coins(cb.from_user.id)
    inv = get_inventory(cb.from_user.id)

    cur_xo = get_skin(cb.from_user.id)
    cur_ck = get_skin_ck(cb.from_user.id)

    lines = [
        "🎒 <b>Інвентар</b>",
        f"💰 Баланс: <b>{coins}</b> 🪙",
        "",
        f"🎨 Поточні скіни:  XO=<b>{cur_xo}</b> | Шашки=<b>{cur_ck}</b>",
        "",
    ]

    if not inv:
        lines.append("Порожньо. Купи щось у магазині 🙂")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Магазин", callback_data="sm:market:shop")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="sm:menu:market")],
        ])
        await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
        await cb.answer()
        return

    rows = []
    for row in inv[:25]:  # keep UI light
        iid = row["item_id"]
        it = get_item(iid)
        title = it["title"] if it else iid
        rows.append([InlineKeyboardButton(text=f"➡️ {title}", callback_data=f"sm:market:item:{iid}")])

    rows.append([InlineKeyboardButton(text="🛍 Магазин", callback_data="sm:market:shop")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sm:menu:market")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "sm:menu:balance")
async def menu_balance(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    coins = get_coins(cb.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "menu_coins"), callback_data="sm:menu:coins")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])
    await safe_edit_text(cb.message, f"{t(lang,'menu_balance')}: <b>{coins}</b> 🪙", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "sm:menu:links")
async def menu_links(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)
    chat = get_chat()
    news = get_news()
    lines = [
        "🔗 <b>Links</b>",
        "",
        f"📰 {news.get('title','')}: {news.get('url','')}",
        f"💬 {chat.get('title','')}: {chat.get('url','')}",
    ]
    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=_back_home_kb(lang))
    await cb.answer()



@router.callback_query(F.data == "sm:menu:friend")
async def menu_friend(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    g = get_active_game(cb.from_user.id)
    token = create_invite(cb.from_user.id, g)

    uname = await _get_bot_username(cb.bot)
    link = f"https://t.me/{uname}?start=inv_{token}" if uname else ""
    share_url = f"https://t.me/share/url?url={link}&text={t(lang,'invite_title')}" if link else ""

    rows = []
    if link:
        rows.append([InlineKeyboardButton(text="🔗 Link", url=link)])
    if share_url:
        rows.append([InlineKeyboardButton(text="📩 Share", url=share_url)])
    rows.append([InlineKeyboardButton(text=t(lang,'back'), callback_data="sm:menu:home")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await safe_edit_text(
        cb.message,
        f"{t(lang,'invite_title')}\n\n{t(lang,'invite_link_text')}\n{link}",
        reply_markup=kb
    )
    await cb.answer()


@router.callback_query(F.data == "sm:menu:quests")
async def menu_quests(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    g = get_active_game(cb.from_user.id)
    u = get_user(cb.from_user.id) or {}
    suf = "_ck" if g == "checkers" else ""
    week_games = int(u.get("week_games" + suf, 0) or 0)
    week_wins = int(u.get("week_wins" + suf, 0) or 0)
    rating = int(u.get("rating" + suf, 1000) or 1000)

    mask = get_quest_mask(cb.from_user.id, game=g)

    quests = [
        ("1", 1, 10, "🕹 Зіграти 3 PvP гри за тиждень", week_games >= 3),
        ("2", 2, 15, "🏆 Виграти 1 PvP гру за тиждень", week_wins >= 1),
        ("3", 4, 25, "🔥 Зіграти 10 PvP ігор за тиждень", week_games >= 10),
        ("4", 8, 40, "👑 Виграти 5 PvP ігор за тиждень", week_wins >= 5),
        ("5", 16, 30, "📈 Підняти рейтинг до 1100+", rating >= 1100),
        ("6", 32, 60, "🚀 Підняти рейтинг до 1300+", rating >= 1300),
    ]

    lines = [
        f"🎯 <b>{t(lang,'quests_title')}</b> ({_game_title(lang, g)})",
        "",
        f"Прогрес тижня: {week_wins}W / {week_games}G | Рейтинг: <b>{rating}</b>",
        "",
    ]

    kb_rows = []
    for qid, bit, reward, title, done in quests:
        claimed = bool(mask & bit)
        status = "✅" if done else "⏳"
        cl = " (забрано)" if claimed else ""
        lines.append(f"{qid}) {title} — {status}{cl}  <i>(+{reward}🪙)</i>")

        if done and not claimed:
            kb_rows.append([InlineKeyboardButton(text=f"🎁 Забрати #{qid} (+{reward}🪙)", callback_data=f"sm:quest:claim:{qid}")])

    lines.append("")
    lines.append(f"{t(lang,'menu_balance')}: <b>{get_coins(cb.from_user.id)}</b> 🪙")

    kb_rows.append([InlineKeyboardButton(text=t(lang,'back'), callback_data="sm:menu:home")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("sm:quest:claim:"))
async def quest_claim(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    ensure_user(cb)

    g = get_active_game(cb.from_user.id)
    qid = cb.data.split(":")[-1].strip()

    # map quest -> (bit, reward, predicate)
    u = get_user(cb.from_user.id) or {}
    suf = "_ck" if g == "checkers" else ""
    week_games = int(u.get("week_games" + suf, 0) or 0)
    week_wins = int(u.get("week_wins" + suf, 0) or 0)
    rating = int(u.get("rating" + suf, 1000) or 1000)

    rules = {
        "1": (1, 10, week_games >= 3),
        "2": (2, 15, week_wins >= 1),
        "3": (4, 25, week_games >= 10),
        "4": (8, 40, week_wins >= 5),
        "5": (16, 30, rating >= 1100),
        "6": (32, 60, rating >= 1300),
    }
    if qid not in rules:
        await cb.answer("Unknown quest"); return

    bit, reward, done = rules[qid]
    mask = get_quest_mask(cb.from_user.id, game=g)

    if mask & bit:
        await cb.answer("Already claimed"); return
    if not done:
        await cb.answer("Not completed"); return

    set_quest_mask(cb.from_user.id, mask | bit, game=g)
    add_coins(cb.from_user.id, reward)
    await cb.answer(f"+{reward}🪙", show_alert=False)

    await menu_quests(cb)


# ---------- LOBBY (who is searching for PvP right now) ----------
def _queue_snapshot() -> list[dict]:
    items = []
    for q, side, vip_flag in (
        (WAIT_X_VIP, "x", True),
        (WAIT_O_VIP, "o", True),
        (WAIT_X, "x", False),
        (WAIT_O, "o", False),
    ):
        for it in q:
            items.append({
                "user_id": it.get("user_id"),
                "side": it.get("side") or side,
                "vip": bool(it.get("vip", vip_flag)),
                "ts": float(it.get("ts", time.time())),
                "lang": it.get("lang") or "en",
            })
    items.sort(key=lambda x: x["ts"])
    return items

def _find_queue_entry(uid: int):
    # returns (entry, side)
    for q, side in (
        (WAIT_X_VIP, "x"),
        (WAIT_O_VIP, "o"),
        (WAIT_X, "x"),
        (WAIT_O, "o"),
    ):
        for it in q:
            if it.get("user_id") == uid:
                return it, (it.get("side") or side)
    return None, None

def _display_name(user_id: int) -> str:
    u = get_user(user_id) or {}
    username = (u.get("username") or "").strip()
    first_name = (u.get("first_name") or "").strip()
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return f"Player {str(user_id)[-4:]}"

def _lobby_kb(lang: str, items: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    # show up to 12 players
    for it in items[:12]:
        uid = int(it["user_id"])
        name = _display_name(uid)
        side = "❌" if it["side"] == "x" else "⭕"
        vip = "💎" if it.get("vip") else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{vip}{side} {name}",
                callback_data=f"sm:lobby:challenge:{uid}"
            )
        ])

    rows.append([
        InlineKeyboardButton(text=t(lang, "lobby_refresh"), callback_data="sm:menu:lobby"),
        InlineKeyboardButton(text=t(lang, "lobby_go_pvp"), callback_data="sm:menu:play_random"),
    ])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data == "sm:menu:lobby")
async def menu_lobby(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    items = _queue_snapshot()
    if not items:
        await safe_edit_text(cb.message, t(lang, "lobby_empty"), reply_markup=_lobby_kb(lang, []))
        await cb.answer()
        return

    now = time.time()
    lines = [t(lang, "lobby_title"), ""]
    for it in items[:12]:
        uid = int(it["user_id"])
        name = _display_name(uid)
        side_txt = "X" if it["side"] == "x" else "O"
        wait_s = int(max(0, now - float(it["ts"])))
        vip = "💎 " if it.get("vip") else ""
        lines.append(f"• {vip}{name} — {side_txt} — {t(lang,'lobby_wait')} {wait_s}s")

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=_lobby_kb(lang, items))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:lobby:challenge:"))
async def lobby_challenge(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    try:
        target_uid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("Bad request", show_alert=True); return

    if target_uid == cb.from_user.id:
        await cb.answer("🙃 Не можна кинути виклик самому собі", show_alert=True)
        return

    entry, target_side = _find_queue_entry(target_uid)
    if not entry:
        await cb.answer("⏳ Гравець вже не в черзі", show_alert=True)
        # refresh lobby
        items = _queue_snapshot()
        await safe_edit_text(cb.message, t(lang, "lobby_empty") if not items else t(lang, "lobby_title"), reply_markup=_lobby_kb(lang, items))
        return

    # remove opponent from queue + cancel its fallback
    remove_from_queue(target_uid)
    cancel_wait_task(target_uid)

    # also remove challenger from queue if they were queued
    remove_from_queue(cb.from_user.id)
    cancel_wait_task(cb.from_user.id)

    # build challenger entry from current lobby message
    challenger_uid = cb.from_user.id
    challenger_entry = {
        "user_id": challenger_uid,
        "chat_id": cb.message.chat.id,
        "message_id": cb.message.message_id,
        "lang": lang,
        "ts": time.time(),
        "rating": get_rating(challenger_uid),
        "vip": is_vip(challenger_uid),
        "side": "o" if target_side == "x" else "x",
    }

    # Decide sides based on target preference
    if target_side == "x":
        x_user = entry
        o_user = challenger_entry
    else:
        x_user = challenger_entry
        o_user = entry

    await start_pvp_match(cb, x_user=x_user, o_user=o_user)
    await cb.answer()

@router.callback_query(F.data == "sm:menu:lang")
async def menu_lang(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)
    await safe_edit_text(cb.message, t(lang, "choose_lang"), reply_markup=language_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("sm:lang:set:"))
async def set_lang_cb(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    code = cb.data.split(":")[-1]
    upsert_user(cb.from_user.id, cb.from_user.username, cb.from_user.first_name, code)
    db_set_lang(cb.from_user.id, code)
    g = get_active_game(cb.from_user.id)
    if g == "checkers":
        g_title = t(code, "game_checkers")
    elif g == "chess":
        g_title = t(code, "game_chess")
    else:
        g_title = t(code, "game_xo")
    await safe_edit_text(cb.message, f"{t(code,'brand_title')}\n{g_title}", reply_markup=menu_kb(code, cb.from_user.id))
    await cb.answer(t(code, "lang_saved"), show_alert=False)

@router.callback_query(F.data == "sm:menu:rules")
async def menu_rules(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    lang = ensure_user(cb)
    await safe_edit_text(cb.message, t(lang, "rules_text"), reply_markup=menu_kb(lang, cb.from_user.id))
    await cb.answer()

# ---- Profile / TOP / History ----
def _back_home_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")]
    ])

@router.callback_query(F.data == "sm:menu:profile")
async def menu_profile(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    u = get_user(cb.from_user.id) or {}
    username = (u.get("username") or "").strip()
    first_name = (u.get("first_name") or "").strip()
    coins = int(u.get("coins", 0) or 0)

    # XO
    rating_xo = int(u.get("rating", 1000) or 1000)
    total_w_xo = int(u.get("total_wins", 0) or 0)
    total_g_xo = int(u.get("total_games", 0) or 0)
    week_w_xo = int(u.get("week_wins", 0) or 0)
    week_g_xo = int(u.get("week_games", 0) or 0)
    rank_xo = get_weekly_rank(cb.from_user.id, game="xo")
    rank_xo_txt = str(rank_xo) if rank_xo is not None else "—"

    # Checkers
    rating_ck = int(u.get("rating_ck", 1000) or 1000)
    total_w_ck = int(u.get("total_wins_ck", 0) or 0)
    total_g_ck = int(u.get("total_games_ck", 0) or 0)
    week_w_ck = int(u.get("week_wins_ck", 0) or 0)
    week_g_ck = int(u.get("week_games_ck", 0) or 0)
    rank_ck = get_weekly_rank(cb.from_user.id, game="checkers")
    rank_ck_txt = str(rank_ck) if rank_ck is not None else "—"

    g = get_active_game(cb.from_user.id)
    if g == "checkers":
        g_title = t(lang, "game_checkers")
    elif g == "chess":
        g_title = t(lang, "game_chess")
    else:
        g_title = t(lang, "game_xo")

    lines = [f"👤 <b>{t(lang,'profile_title')}</b>", f"🎮 Активна гра: <b>{g_title}</b>"]
    if username:
        lines.append(f"{t(lang,'profile_username')}: <b>@{username}</b>")
    if first_name:
        lines.append(f"{t(lang,'profile_name')}: <b>{first_name}</b>")
    lines.append(f"{t(lang,'profile_id')}: <code>{cb.from_user.id}</code>")
    lines.append(f"{t(lang,'menu_balance')}: <b>{coins}</b> 🪙")
    lines.append("")
    lines.append(f"{t(lang,'game_xo')}")
    lines.append(f"   {t(lang,'profile_rating')}: <b>{rating_xo}</b> | {t(lang,'profile_rank')}: <b>{rank_xo_txt}</b>")
    lines.append(f"   {t(lang,'profile_total')}: <b>{total_w_xo}</b>/{total_g_xo} | {t(lang,'profile_week')}: <b>{week_w_xo}</b>/{week_g_xo}")
    lines.append("")
    lines.append(f"{t(lang,'game_checkers')}")
    lines.append(f"   {t(lang,'profile_rating')}: <b>{rating_ck}</b> | {t(lang,'profile_rank')}: <b>{rank_ck_txt}</b>")
    lines.append(f"   {t(lang,'profile_total')}: <b>{total_w_ck}</b>/{total_g_ck} | {t(lang,'profile_week')}: <b>{week_w_ck}</b>/{week_g_ck}")

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=_back_home_kb(lang))
    await cb.answer()

@router.callback_query(F.data == "sm:menu:top")
async def menu_top(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    # default: overall, page 0
    await show_top100(cb, mode="overall", page=0)
    await cb.answer()


@router.callback_query(F.data.startswith("sm:top:mode:"))
async def top_mode(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    parts = cb.data.split(":")
    # sm:top:mode:<mode>:<page>
    mode = parts[3] if len(parts) > 3 else "overall"
    try:
        page = int(parts[4]) if len(parts) > 4 else 0
    except Exception:
        page = 0
    await show_top100(cb, mode=mode, page=page)
    await cb.answer()


async def show_top100(cb: CallbackQuery, mode: str = "overall", page: int = 0):
    lang = ensure_user(cb)
    mode = (mode or "overall").lower()
    page = max(0, int(page))

    per_page = 20
    top = get_top100(mode=mode, limit=100)

    title_map = {
        "overall": "🏆 Топ-100 (Загальний)",
        "xo": "🏆 Топ-100 (XO)",
        "checkers": "🏆 Топ-100 (Шашки)",
    }
    title = title_map.get(mode, title_map["overall"])

    if not top:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Топ тижня", callback_data="sm:top:weekly")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
        ])
        await safe_edit_text(cb.message, f"{title}\n\nПоки що порожньо.", reply_markup=kb)
        return

    start = page * per_page
    end = start + per_page
    chunk = top[start:end]

    # current user rank
    my_rank = None
    for i, it in enumerate(top, start=1):
        if int(it["user_id"]) == int(cb.from_user.id):
            my_rank = i
            break

    lines = [f"{title}", ""]
    if my_rank:
        lines.append(f"Твій ранг: <b>#{my_rank}</b>")
        lines.append("")

    for idx, it in enumerate(chunk, start=start + 1):
        nm = (it.get("username") or "").strip()
        disp = f"@{nm}" if nm else ((it.get("first_name") or "").strip() or f"ID{it.get('user_id')}")
        score = int(it.get("score") or 0)
        marker = "👉 " if int(it["user_id"]) == int(cb.from_user.id) else ""
        lines.append(f"{marker}{idx}. <b>{disp}</b> — <b>{score}</b>")

    has_prev = page > 0
    has_next = end < len(top)

    # filters + paging
    row_filters = [
        InlineKeyboardButton(text="Загальний" + (" ✅" if mode == "overall" else ""), callback_data="sm:top:mode:overall:0"),
        InlineKeyboardButton(text="XO" + (" ✅" if mode == "xo" else ""), callback_data="sm:top:mode:xo:0"),
        InlineKeyboardButton(text="Шашки" + (" ✅" if mode == "checkers" else ""), callback_data="sm:top:mode:checkers:0"),
    ]

    row_nav = []
    if has_prev:
        row_nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"sm:top:mode:{mode}:{page-1}"))
    if has_next:
        row_nav.append(InlineKeyboardButton(text="➡️", callback_data=f"sm:top:mode:{mode}:{page+1}"))

    rows = [row_filters]
    if row_nav:
        rows.append(row_nav)

    rows.append([InlineKeyboardButton(text="📅 Топ тижня", callback_data="sm:top:weekly")])
    rows.append([InlineKeyboardButton(text=t(lang, "top_history"), callback_data="sm:top:history")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "sm:top:weekly")
async def top_weekly(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    game = get_active_game(cb.from_user.id)
    top = get_weekly_top(TOP_N, game=game)
    pool = get_prize_pool()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "top_history"), callback_data="sm:top:history")],
        [InlineKeyboardButton(text="🏆 Топ-100", callback_data="sm:menu:top")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")]
    ])

    if not top:
        await safe_edit_text(cb.message, f"🏆 <b>{t(lang,'top_title')}</b>\n\n{t(lang,'top_empty')}", reply_markup=kb)
        await cb.answer(); return

    lines = [f"🏆 <b>{t(lang,'top_title')}</b>", f"{t(lang,'prize_pool')}: <b>{pool}</b> ⭐", ""]
    for i, it in enumerate(top, start=1):
        name = it["username"].strip()
        if name:
            disp = f"@{name}"
        else:
            disp = (it["first_name"] or f"ID{it['user_id']}").strip()
        lines.append(f"{i}. <b>{disp}</b> — {it['week_wins']}W / {it['week_games']}G — <i>{it['rating']}</i>")

    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "sm:top:history")
async def top_history(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    game = get_active_game(cb.from_user.id)
    hist = load_week_history(limit=5, game=game)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:top")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")]
    ])

    if not hist:
        await safe_edit_text(cb.message, f"📚 <b>{t(lang,'top_history')}</b>\n\n{t(lang,'no_history')}", reply_markup=kb)
        await cb.answer(); return

    lines = [f"📚 <b>{t(lang,'top_history')}</b>\n"]
    for h in hist:
        lines.append(f"— <b>{h['week_start']}</b> | pool=<b>{h['pool']}</b> ⭐")
        top = h.get("top", [])
        for it in top[:3]:
            nm = (it.get("username") or "").strip()
            disp = f"@{nm}" if nm else (it.get("first_name") or f"ID{it.get('user_id')}")
            lines.append(f"   {it.get('rank')}. {disp} — {it.get('wins')}W")
        lines.append("")

    await safe_edit_text(cb.message, "\n".join(lines).strip(), reply_markup=kb)
    await cb.answer()

# ---- Skins / donate / vip menus ----
@router.callback_query(F.data == "sm:menu:skins")
async def menu_skins(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    g = get_active_game(cb.from_user.id)
    cur = get_skin_ck(cb.from_user.id) if g == "checkers" else get_skin(cb.from_user.id)
    await safe_edit_text(
        cb.message,
        f"{t(lang, 'menu_skins')}\n\n{t(lang, 'skins_only_active')}",
        reply_markup=skins_kb(lang, cur, only_active=True),
    )
    await cb.answer()

@router.callback_query(F.data == "sm:skins:all")
async def menu_skins_all(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    g = get_active_game(cb.from_user.id)
    cur = get_skin_ck(cb.from_user.id) if g == "checkers" else get_skin(cb.from_user.id)
    await safe_edit_text(cb.message, t(lang, "menu_skins"), reply_markup=skins_kb(lang, cur))
    await cb.answer()

@router.callback_query(F.data == "sm:skin:noop")
async def skin_noop(cb: CallbackQuery):
    await cb.answer()

@router.callback_query(F.data.startswith("sm:skin:set:"))
async def set_skin_cb(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    skin = cb.data.split(":")[-1]
    valid = {k for k, _ in SKINS}
    if skin not in valid:
        await cb.answer()
        return

    g = get_active_game(cb.from_user.id)

    # lock premium skins behind shop (or VIP)
    if not _skin_allowed(cb.from_user.id, g, skin):
        await cb.answer("Цей скін треба купити в 🛍 Магазині", show_alert=True)
        return

    if g == "checkers":
        set_skin_ck(cb.from_user.id, skin)
        if has_item(cb.from_user.id, f"skin:checkers:{skin}"):
            set_active_item(cb.from_user.id, f"skin:checkers:{skin}")
    else:
        db_set_skin(cb.from_user.id, skin)
        if has_item(cb.from_user.id, f"skin:xo:{skin}"):
            set_active_item(cb.from_user.id, f"skin:xo:{skin}")

    cur = get_skin_ck(cb.from_user.id) if g == "checkers" else get_skin(cb.from_user.id)
    await safe_edit_text(
        cb.message,
        f"{t(lang, 'menu_skins')}\n\n{t(lang, 'skins_only_active')}",
        reply_markup=skins_kb(lang, cur, only_active=True),
    )
    await cb.answer()

@router.callback_query(F.data == "sm:menu:donate")
async def menu_donate(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    await safe_edit_text(cb.message, "⭐ Donate", reply_markup=donate_kb(lang, DONATE_AMOUNTS))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:donate:"))
async def donate_pick(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    stars = int(cb.data.split(":")[-1])
    prices, payload = donate_invoice(cb.from_user.id, stars, lang)
    await cb.bot.send_invoice(
        chat_id=cb.message.chat.id,
        title="SM Arena ⭐ Donation",
        description=f"Support prize pool with {stars} Telegram Stars",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await cb.answer()

@router.callback_query(F.data == "sm:menu:vip")
async def menu_vip(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    
    from app.db import get_bp_state
    import json
    
    bp_xp, bp_level, claims_f_str, claims_p_str = get_bp_state(cb.from_user.id)
    c_free = json.loads(claims_f_str)
    c_prem = json.loads(claims_p_str)
    
    is_premium = is_vip(cb.from_user.id)
    
    if is_premium:
        date = datetime.fromtimestamp(add_vip_days(cb.from_user.id, 0), tz=timezone.utc).strftime("%Y-%m-%d")
        vip_txt = t(lang, "vip_status_on").format(date=date)
    else:
        vip_txt = t(lang, "vip_status_off")
        
    text = f"🛡 <b>Battle Pass</b> (Сезон)\n\n"
    text += f"⚜️ Рівень: <b>{bp_level}</b>\n"
    text += f"✨ Досвід: <b>{bp_xp}/100</b> XP до наступного рівня\n\n"
    text += f"💎 Статус: {vip_txt}\n\n"
    text += "(Грай та вигравай матчі, щоб піднімати рівень!)"

    from app.keyboards import bp_kb
    await safe_edit_text(cb.message, text, reply_markup=bp_kb(lang, bp_level, c_free, c_prem, is_premium))
    await cb.answer()

@router.callback_query(F.data == "sm:menu:vip_buy")
async def menu_vip_buy(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    
    if is_vip(cb.from_user.id):
        date = datetime.fromtimestamp(add_vip_days(cb.from_user.id, 0), tz=timezone.utc).strftime("%Y-%m-%d")
        text = t(lang, "vip_status_on").format(date=date)
    else:
        text = t(lang, "vip_status_off")
        
    await safe_edit_text(cb.message, f"💎 Здобудь VIP (Premium Battle Pass)\n\n{text}", reply_markup=vip_kb(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:bp:claim:"))
async def bp_claim(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    
    parts = cb.data.split(":")
    claim_type = parts[3] # "free" or "premium"
    level = int(parts[4])
    
    from app.db import get_bp_state, claim_bp_reward
    from app.vip_service import BP_REWARDS, grant_bp_reward
    
    bp_xp, bp_level, _, _ = get_bp_state(cb.from_user.id)
    is_premium = is_vip(cb.from_user.id)
    
    if level > bp_level:
        await cb.answer("❌ Рівень ще не досягнуто!", show_alert=True)
        return
        
    if claim_type == "premium" and not is_premium:
        await cb.answer("❌ Ця нагорода лише для VIP (Premium)!", show_alert=True)
        return
        
    reward = BP_REWARDS.get(level, {}).get(claim_type)
    if not reward:
        await cb.answer("❌ Нагороди не існує!", show_alert=True)
        return
        
    success = claim_bp_reward(cb.from_user.id, level, is_premium=(claim_type=="premium"))
    if not success:
        await cb.answer("⛔ Вже отримано!", show_alert=True)
        return
        
    msg = grant_bp_reward(cb.from_user.id, reward)
    await cb.answer(f"🎉 Отримано: {msg}", show_alert=True)
    await menu_vip(cb)

@router.callback_query(F.data == "sm:bp:noop")
async def bp_noop(cb: CallbackQuery):
    await cb.answer("🔒 Рівень ще заблоковано! Грай та заробляй XP.", show_alert=True)

@router.callback_query(F.data.startswith("sm:vip:buycoins:"))
async def vip_buy_coins(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    try:
        _, _, _, days_s, coins_s = cb.data.split(":")
        days = int(days_s)
        coins = int(coins_s)
    except Exception:
        await cb.answer("Invalid VIP plan", show_alert=True)
        return

    allowed_plans = {(int(d), int(c)) for d, c in VIP_COIN_PLANS if int(d) > 0 and int(c) > 0}
    if (days, coins) not in allowed_plans:
        await cb.answer("Unknown VIP plan", show_alert=True)
        return

    if not try_spend_coins(cb.from_user.id, coins):
        await cb.answer("Недостатньо монет 🪙", show_alert=True)
        return

    until = add_vip_days(cb.from_user.id, days)
    date = datetime.fromtimestamp(until, tz=timezone.utc).strftime("%Y-%m-%d")
    bal = get_coins(cb.from_user.id)
    text = t(lang, "vip_status_on").format(date=date)

    await safe_edit_text(
        cb.message,
        f"{t(lang,'vip_title')}\n\n{text}\n\n💰 Баланс: <b>{bal}</b> 🪙",
        reply_markup=vip_kb(lang),
    )
    await cb.answer("VIP активовано ✅", show_alert=True)

# ---- AI mode ----
@router.callback_query(F.data == "sm:menu:play_ai")
async def menu_ai(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    await safe_edit_text(cb.message, t(lang, "choose_ai"), reply_markup=ai_levels_kb(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:ai:start:"))
async def ai_start(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    level = cb.data.split(":")[-1]
    match_id = str(uuid.uuid4())[:8]
    board = "........."
    AI_MATCHES[match_id] = {"level": level, "board": board, "user_id": cb.from_user.id, "status": "playing"}
    await safe_edit_text(cb.message, 
        f"🤖 AI ({level}) — {t(lang,'your_move')}",
        reply_markup=board_kb(match_id, board, lang, highlight=set(), skin=get_skin(cb.from_user.id))
    )
    await cb.answer()

def result_text(w: str, level: str, lang: str) -> str:
    if w == "X": return f"{t(lang,'you_win')} (AI {level})"
    if w == "O": return f"{t(lang,'you_lose')} (AI {level})"
    return f"{t(lang,'draw')} (AI {level})"

@router.callback_query(F.data.startswith("sm:ai:move:"))
async def ai_move(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    parts = cb.data.split(":")
    match_id = parts[3]
    cell = int(parts[4])

    state = AI_MATCHES.get(match_id)
    if not state:
        await cb.answer("Game expired", show_alert=True); return
    if state.get("status") != "playing":
        await cb.answer("Game ended. Start a new one.", show_alert=True); return

    board = state["board"]; level = state["level"]
    try:
        board = apply_move(board, cell, "X")
    except Exception:
        await cb.answer("Cell taken"); return
    state["board"] = board

    w = check_winner(board)
    if w:
        hl = set() if w == "D" else compute_highlight(board)
        await safe_edit_text(cb.message, 
            result_text(w, level, lang),
            reply_markup=board_kb(match_id, board, lang, highlight=hl, skin=get_skin(cb.from_user.id))
        )
        # emoji must be inside same message -> append to text, no send_message
        extra = WIN_EMOJI if w == "X" else (LOSE_EMOJI if w == "O" else DRAW_EMOJI)
        await safe_edit_text(cb.message, 
            result_text(w, level, lang) + f"\n\n{extra}",
            reply_markup=board_kb(match_id, board, lang, highlight=hl, skin=get_skin(cb.from_user.id))
        )
        return

    ai_cell = ai_move_easy(board) if level == "easy" else (ai_move_normal(board) if level == "normal" else ai_move_hard(board))
    board = apply_move(board, ai_cell, "O")
    state["board"] = board

    w = check_winner(board)
    if w:
        hl = set() if w == "D" else compute_highlight(board)
        extra = WIN_EMOJI if w == "X" else (LOSE_EMOJI if w == "O" else DRAW_EMOJI)
        await safe_edit_text(cb.message, 
            result_text(w, level, lang) + f"\n\n{extra}",
            reply_markup=board_kb(match_id, board, lang, highlight=hl, skin=get_skin(cb.from_user.id))
        )
        return

    await safe_edit_text(cb.message, 
        f"🤖 AI ({level}) — {t(lang,'your_move')}",
        reply_markup=board_kb(match_id, board, lang, highlight=set(), skin=get_skin(cb.from_user.id))
    )
    await cb.answer()

@router.callback_query(F.data.startswith("sm:ai:ctrl:"))
async def ai_control(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    parts = (cb.data or "").split(":")
    if len(parts) < 5:
        await cb.answer("Bad request", show_alert=True); return
    match_id = parts[3]
    action = parts[4]

    state = AI_MATCHES.get(match_id)
    if not state:
        await cb.answer("Game expired", show_alert=True); return
    if int(state.get("user_id") or 0) != int(cb.from_user.id):
        await cb.answer("Not your game", show_alert=True); return

    level = str(state.get("level") or "normal")

    if action in ("reset", "new"):
        board = "........."
        state["board"] = board
        state["status"] = "playing"
        await safe_edit_text(
            cb.message,
            f"🤖 AI ({level}) — {t(lang,'your_move')}",
            reply_markup=board_kb(match_id, board, lang, highlight=set(), skin=get_skin(cb.from_user.id)),
        )
        await cb.answer("Reset." if action == "reset" else "New game!")
        return

    if action == "resign":
        state["status"] = "ended"
        board = str(state.get("board") or ".........")
        await safe_edit_text(
            cb.message,
            "Game ended by resignation.",
            reply_markup=board_kb(match_id, board, lang, highlight=set(), skin=get_skin(cb.from_user.id)),
        )
        await cb.answer("Resigned.")
        return

    await cb.answer("Unknown action", show_alert=True)

# ---- PvP random matchmaking (VIP first) ----
@router.callback_query(F.data == "sm:menu:play_random")
async def menu_random(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    if is_banned(cb.from_user.id):
        await cb.answer("Banned", show_alert=True); return
    if is_in_queue(cb.from_user.id):
        await cb.answer("Already searching"); return

    await safe_edit_text(cb.message, t(lang, "choose_side"), reply_markup=random_side_kb(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("sm:random:want:"))
async def random_want(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    reset_week_if_needed(week_len_days=5, top_n=TOP_N)

    uid = cb.from_user.id
    if is_banned(uid):
        await cb.answer("Banned", show_alert=True); return
    if is_in_queue(uid):
        await cb.answer("Already searching"); return

    side = cb.data.split(":")[-1]  # x/o
    cancel_wait_task(uid)

    entry = {
        "user_id": uid,
        "chat_id": cb.message.chat.id,
        "message_id": cb.message.message_id,
        "lang": lang,
        "ts": time.time(),
        "rating": get_rating(uid),
        "vip": is_vip(uid),
        "side": side,
    }

    def pop_best(q, target):
        return best_match(q, target) if q else None

    if side == "x":
        other = pop_best(WAIT_O_VIP, entry["rating"]) if entry["vip"] else None
        if not other:
            other = pop_best(WAIT_O, entry["rating"]) if entry["vip"] else pop_best(WAIT_O_VIP, entry["rating"]) or pop_best(WAIT_O, entry["rating"])
        if other:
            cancel_wait_task(other["user_id"])
            await start_pvp_match(cb, x_user=entry, o_user=other)
            await cb.answer()
            return
        (WAIT_X_VIP if entry["vip"] else WAIT_X).append(entry)
    else:
        other = pop_best(WAIT_X_VIP, entry["rating"]) if entry["vip"] else None
        if not other:
            other = pop_best(WAIT_X, entry["rating"]) if entry["vip"] else pop_best(WAIT_X_VIP, entry["rating"]) or pop_best(WAIT_X, entry["rating"])
        if other:
            cancel_wait_task(other["user_id"])
            await start_pvp_match(cb, x_user=other, o_user=entry)
            await cb.answer()
            return
        (WAIT_O_VIP if entry["vip"] else WAIT_O).append(entry)

    fallback_sec = VIP_FALLBACK_AI_SEC if entry["vip"] else NONVIP_FALLBACK_AI_SEC
    await safe_edit_text(cb.message, f"🔎 Searching… ({fallback_sec}s)", reply_markup=searching_kb(lang))
    await cb.answer()
    WAIT_TASKS[uid] = asyncio.create_task(random_fallback_to_ai(cb, uid, entry["chat_id"], entry["message_id"], fallback_sec))

@router.callback_query(F.data == "sm:random:cancel")
async def random_cancel(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    remove_from_queue(cb.from_user.id)
    cancel_wait_task(cb.from_user.id)
    await safe_edit_text(cb.message, f"{t(lang,'brand_title')}\n{t(lang,'choose')}", reply_markup=menu_kb(lang, cb.from_user.id))
    await cb.answer("Canceled")

async def random_fallback_to_ai(cb: CallbackQuery, uid: int, chat_id: int, msg_id: int, sec: int):
    try:
        await asyncio.sleep(sec)
    except asyncio.CancelledError:
        return
    if not is_in_queue(uid):
        return
    remove_from_queue(uid)
    lang = db_get_lang(uid) or "en"
    try:
        await cb.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="🤖 No opponents. Starting AI…")
    except Exception:
        pass
    # start normal AI in same message
    match_id = str(uuid.uuid4())[:8]
    board = "........."
    AI_MATCHES[match_id] = {"level": "normal", "board": board, "user_id": uid, "status": "playing"}
    await cb.bot.edit_message_text(
        chat_id=chat_id, message_id=msg_id,
        text=f"🤖 AI (normal) — {t(lang,'your_move')}",
        reply_markup=board_kb(match_id, board, lang, highlight=set(), skin=get_skin(uid))
    )

# PvP start / move handlers could be kept as you already had;
# For brevity, this build focuses on Profile/TOP/SQLite persistence and leaves PvP mechanics minimal.
async def start_pvp_match(cb: CallbackQuery, x_user: dict, o_user: dict):
    match_id = str(uuid.uuid4())[:8]
    board = "........."

    # Store everything needed to update BOTH players on each move
    PVP_MATCHES[match_id] = {
        "board": board,
        "x": x_user["user_id"],
        "o": o_user["user_id"],
        "turn": "X",
        "status": "playing",
        "last_move": time.time(),

        "x_chat": x_user["chat_id"],
        "o_chat": o_user["chat_id"],
        "x_msg": x_user["message_id"],
        "o_msg": o_user["message_id"],
        "x_lang": x_user.get("lang") or "en",
        "o_lang": o_user.get("lang") or "en",
    }

    set_pvp_timer(match_id, cb)

    async def _edit(chat_id: int, msg_id: int, text: str, kb):
        try:
            await cb.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
        except Exception:
            return

    turn_txt = "❌ (X)"
    await _edit(
        chat_id=x_user["chat_id"], msg_id=x_user["message_id"],
        text=f"✅ Found! {turn_txt}",
        kb=board_kb_pvp(match_id, board, x_user.get("lang") or "en", highlight=set(), skin=get_skin(x_user["user_id"]))
    )
    await _edit(
        chat_id=o_user["chat_id"], msg_id=o_user["message_id"],
        text=f"✅ Found! {turn_txt}",
        kb=board_kb_pvp(match_id, board, o_user.get("lang") or "en", highlight=set(), skin=get_skin(o_user["user_id"]))
    )


@router.callback_query(F.data.startswith("sm:pvp:move:"))
async def pvp_move(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    parts = cb.data.split(":")  # sm:pvp:move:<match_id>:<cell>
    if len(parts) < 5:
        await cb.answer("Bad request", show_alert=True); return
    match_id = parts[3]
    cell = int(parts[4])

    m = PVP_MATCHES.get(match_id)
    if not m or m.get("status") != "playing":
        await cb.answer("Game ended", show_alert=True); return

    uid = cb.from_user.id
    if uid not in (m["x"], m["o"]):
        await cb.answer("Not your game", show_alert=True); return

    my_mark = "X" if uid == m["x"] else "O"
    if m["turn"] != my_mark:
        await cb.answer("Not your turn"); return

    # apply move
    try:
        new_board = apply_move(m["board"], cell, my_mark)
    except Exception:
        await cb.answer("Cell taken"); return

    m["board"] = new_board
    m["turn"] = "O" if my_mark == "X" else "X"
    m["last_move"] = time.time()
    set_pvp_timer(match_id, cb)

    w = check_winner(new_board)
    hl = set() if not w or w == "D" else compute_highlight(new_board)

    async def _edit(chat_id: int, msg_id: int, text: str, kb):
        try:
            await cb.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
        except Exception:
            return

    # current turn text
    turn_txt = "❌ (X)" if m["turn"] == "X" else "⭕ (O)"

    # update ongoing game
    if not w:
        await _edit(
            m.get("x_chat"), m.get("x_msg"),
            f"🎮 PvP | {turn_txt}",
            board_kb_pvp(match_id, new_board, m.get("x_lang","en"), highlight=set(), skin=get_skin(m["x"]), show_controls=not bool(m.get("tmatch_id")))
        )
        await _edit(
            m.get("o_chat"), m.get("o_msg"),
            f"🎮 PvP | {turn_txt}",
            board_kb_pvp(match_id, new_board, m.get("o_lang","en"), highlight=set(), skin=get_skin(m["o"]), show_controls=not bool(m.get("tmatch_id")))
        )
        await cb.answer()
        return

    # finished
    m["status"] = "ended"
    cancel_pvp_timer(match_id)

    x_id, o_id = m["x"], m["o"]

    sb_x = is_shadowbanned(x_id)
    sb_o = is_shadowbanned(o_id)
    rated = is_rated_pair_game(x_id, o_id, ANTI_BOOST_WINDOW_SEC, ANTI_BOOST_MAX_RATED)

    # stats
    if not sb_x:
        bump_total(x_id, win=(w == "X"))
        bump_weekly(x_id, win=(w == "X"))
        inc_season_games(x_id, "xo", win=(w == "X"))
        if rated:
            add_bp_xp(x_id, 20 if w == "X" else 10)
        # Arena hook
        from app.arena_mode import report_win as _ar_win, report_loss as _ar_loss
        if w == "X":
            _ar_win(x_id)
        elif w != "D":
            _ar_loss(x_id)

    if not sb_o:
        bump_total(o_id, win=(w == "O"))
        bump_weekly(o_id, win=(w == "O"))
        inc_season_games(o_id, "xo", win=(w == "O"))
        if rated:
            add_bp_xp(o_id, 20 if w == "O" else 10)

    # referrals (reward when invited played enough rated games)
    for uid in (x_id, o_id):
        paid = try_pay_referral_reward(uid)
        if paid:
            inviter_id, coins_paid = paid
            try:
                await cb.bot.send_message(inviter_id, f"🤝 Рефералка: +{coins_paid} 🪙 (твій друг зіграв 3 рейтингові гри)")
            except Exception:
                pass

    # tournament hook
    tmatch_id = m.get("tmatch_id")
    tournament_id = m.get("tournament_id")
    if tmatch_id and tournament_id and w in ("X","O"):
        winner_id = x_id if w == "X" else o_id
        try:
            set_match_result(int(tmatch_id), int(winner_id))
            advance_round_if_ready(int(tournament_id))
            try:
                await cb.bot.send_message(x_id, "🏆 Турнір: результат матчу зараховано ✅")
            except Exception:
                pass
            try:
                await cb.bot.send_message(o_id, "🏆 Турнір: результат матчу зараховано ✅")
            except Exception:
                pass
        except Exception:
            pass

    rating_note_x = rating_note_o = ""
    if w != "D":
        if rated:
            rx, ro = get_rating(x_id), get_rating(o_id)
            score_x = 1.0 if w == "X" else 0.0
            nx, no = update_elo(rx, ro, score_x)
            
            if not sb_x:
                set_rating(x_id, nx)
            if not sb_o:
                set_rating(o_id, no)
                
            # сезонний Elo (не ламає глобальний рейтинг)
            srx, sro = get_season_rating(x_id, "xo"), get_season_rating(o_id, "xo")
            nsx, nso = update_elo(srx, sro, score_x)
            if not sb_x:
                set_season_rating(x_id, "xo", nsx)
            if not sb_o:
                set_season_rating(o_id, "xo", nso)
                
            record_pair_game(x_id, o_id, ANTI_BOOST_WINDOW_SEC)
            rating_note_x = f"\n\n📈 Elo: {rx} → {nx}"
            rating_note_o = f"\n\n📈 Elo: {ro} → {no}"
            
            if sb_x: rating_note_x = "\n\n⚠️ Unrated (shadowban)"
            if sb_o: rating_note_o = "\n\n⚠️ Unrated (shadowban)"
        else:
            rating_note_x = rating_note_o = "\n\n⚠️ Unrated (anti-boost)"

    # results per player
    if w == "D":
        text_x = f"{t(m.get('x_lang','en'), 'draw')}{rating_note_x}\n\n{DRAW_EMOJI}"
        text_o = f"{t(m.get('o_lang','en'), 'draw')}{rating_note_o}\n\n{DRAW_EMOJI}"
    else:
        x_win = (w == "X")
        o_win = (w == "O")
        text_x = f"{t(m.get('x_lang','en'), 'you_win' if x_win else 'you_lose')}{rating_note_x}\n\n{WIN_EMOJI if x_win else LOSE_EMOJI}"
        text_o = f"{t(m.get('o_lang','en'), 'you_win' if o_win else 'you_lose')}{rating_note_o}\n\n{WIN_EMOJI if o_win else LOSE_EMOJI}"

    await _edit(
        m.get("x_chat"), m.get("x_msg"),
        text_x,
        board_kb_pvp(match_id, new_board, m.get("x_lang","en"), highlight=hl, skin=get_skin(x_id), show_controls=not bool(m.get("tmatch_id")))
    )
    await _edit(
        m.get("o_chat"), m.get("o_msg"),
        text_o,
        board_kb_pvp(match_id, new_board, m.get("o_lang","en"), highlight=hl, skin=get_skin(o_id), show_controls=not bool(m.get("tmatch_id")))
    )
    await cb.answer()


@router.callback_query(F.data.startswith("sm:pvp:ctrl:"))
async def pvp_control(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    ensure_user(cb)

    parts = (cb.data or "").split(":")
    if len(parts) < 5:
        await cb.answer("Bad request", show_alert=True); return
    match_id = parts[3]
    action = parts[4]

    m = PVP_MATCHES.get(match_id)
    if not m:
        await cb.answer("Game ended", show_alert=True); return

    uid = cb.from_user.id
    if uid not in (m.get("x"), m.get("o")):
        await cb.answer("Not your game", show_alert=True); return

    # Keep tournament flow strict.
    if m.get("tmatch_id"):
        await cb.answer("Unavailable in tournament match", show_alert=True); return

    async def _edit(chat_id: int, msg_id: int, text: str, kb):
        try:
            await cb.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
        except Exception:
            return

    if action == "reset":
        await cb.answer("Reset.")
        return

    if action == "new":
        m["board"] = "........."
        m["turn"] = "X"
        m["status"] = "playing"
        m["last_move"] = time.time()
        set_pvp_timer(match_id, cb)
        turn_txt = "❌ (X)"
        await _edit(
            m.get("x_chat"),
            m.get("x_msg"),
            f"🎮 PvP | {turn_txt}",
            board_kb_pvp(match_id, m["board"], m.get("x_lang", "en"), highlight=set(), skin=get_skin(m["x"]), show_controls=True),
        )
        await _edit(
            m.get("o_chat"),
            m.get("o_msg"),
            f"🎮 PvP | {turn_txt}",
            board_kb_pvp(match_id, m["board"], m.get("o_lang", "en"), highlight=set(), skin=get_skin(m["o"]), show_controls=True),
        )
        await cb.answer("New game!")
        return

    if action == "resign":
        m["status"] = "ended"
        cancel_pvp_timer(match_id)
        x_id = int(m["x"])
        o_id = int(m["o"])
        x_text = "You lose (resigned)." if uid == x_id else "You win (opponent resigned)."
        o_text = "You lose (resigned)." if uid == o_id else "You win (opponent resigned)."
        board = str(m.get("board") or ".........")
        await _edit(
            m.get("x_chat"),
            m.get("x_msg"),
            x_text,
            board_kb_pvp(match_id, board, m.get("x_lang", "en"), highlight=set(), skin=get_skin(x_id), show_controls=True),
        )
        await _edit(
            m.get("o_chat"),
            m.get("o_msg"),
            o_text,
            board_kb_pvp(match_id, board, m.get("o_lang", "en"), highlight=set(), skin=get_skin(o_id), show_controls=True),
        )
        await cb.answer("Resigned.")
        return

    await cb.answer("Unknown action", show_alert=True)


# ---------------- Referrals UI ----------------
@router.callback_query(F.data == "sm:ref:home")
async def ref_home(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    bot_username = await _get_bot_username(cb.bot)
    link = f"https://t.me/{bot_username}?start=ref_{cb.from_user.id}" if bot_username else f"/start ref_{cb.from_user.id}"
    st = get_ref_stats(cb.from_user.id)
    text = (
        f"{t(lang,'ref_title')}\n\n"
        f"{t(lang,'ref_link')}\n<code>{link}</code>\n\n"
        + t(lang,'ref_stats').format(n=st['ref_count'], c=st['ref_earned'])
        + f"\n\n{t(lang,'ref_rules')}"
    )
    share_url = f"https://t.me/share/url?url={link}&text=" + t(lang, 'ref_share_text')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запросити друзів (Поділитись)", url=share_url)],
        [InlineKeyboardButton(text="🏆 Топ рефоводів", callback_data="sm:ref:top")],
        [InlineKeyboardButton(text="⬅️", callback_data="sm:menu:home")],
    ])
    await safe_edit_text(cb.message, text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "sm:ref:top")
async def ref_top(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    # Pull top 10 referrers from DB ordered by ref_count desc
    con = __import__('app.db', fromlist=['_con'])._con()
    try:
        rows = con.execute(
            "SELECT user_id, username, first_name, ref_count, ref_earned "
            "FROM users WHERE ref_count > 0 ORDER BY ref_count DESC LIMIT 10"
        ).fetchall()
    finally:
        con.close()

    lines = ["🏆 <b>Топ рефоводів</b>\n"]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, row in enumerate(rows, start=1):
        uid, uname, fname, rcount, rearn = row
        name = ("@" + uname) if (uname or "").strip() else (fname or "Гравець")
        badge = medals.get(i, f"{i:02d}.")
        lines.append(f"{badge} {name} — <b>{rcount}</b> рефералів / <b>{rearn}</b>🪙")

    if not rows:
        lines.append("Ще нікого немає 😢\nЗапрошуй друзів першим!")

    lines.append("\n💎 Топ-3 щотижня отримають VIP + Преміум Скриню!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="sm:ref:home")]
    ])
    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()


# ---------------- Seasons UI ----------------
@router.callback_query(F.data == "sm:season:home")
async def season_home(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    meta = get_season_meta()
    sid = int(meta["season_id"])
    start_ts = float(meta["season_start_ts"])
    end_ts = start_ts + 30 * 86400
    days_left = max(0, int((end_ts - time.time() + 86399) // 86400))
    text = f"{t(lang,'season_title')}\n\n<b>{t(lang,'season_current')} #{sid}</b>\n{t(lang,'season_days_left')}: <b>{days_left}</b>\n\n{t(lang,'season_top')}:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Overall", callback_data="sm:season:top:overall"),
         InlineKeyboardButton(text="❌⭕", callback_data="sm:season:top:xo"),
         InlineKeyboardButton(text="♟️", callback_data="sm:season:top:checkers")],
        [InlineKeyboardButton(text="⬅️", callback_data="sm:menu:home")]
    ])
    await safe_edit_text(cb.message, text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("sm:season:top:"))
async def season_top(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    mode = cb.data.split(":")[-1]
    rows = get_season_top100(mode=mode, limit=30)
    title = "🏆 Overall" if mode=="overall" else ("❌⭕ XO" if mode=="xo" else "♟️ Checkers")
    lines=[f"{t(lang,'season_title')} — <b>{title}</b>\n"]
    for i,r in enumerate(rows, start=1):
        name = ("@"+r["username"]) if (r.get("username") or "").strip() else (r.get("first_name") or "Player")
        lines.append(f"{i:02d}. {name} — <b>{int(r['score'])}</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️", callback_data="sm:season:home")]
    ])
    await safe_edit_text(cb.message, "\n".join(lines), reply_markup=kb)
    await cb.answer()

# ---------------- Tournaments UI (Daily XO + Checkers) ----------------
def _tourn_dual_kb(
    lang: str,
    is_admin_user: bool,
    xo_t: dict | None,
    xo_joined: bool,
    ck_t: dict | None,
    ck_joined: bool,
) -> InlineKeyboardMarkup:
    rows = []
    # XO
    if xo_t:
        tid = int(xo_t["id"])
        status = str(xo_t.get("status") or "")
        if status == "REG":
            rows.append([InlineKeyboardButton(
                text=(t(lang,'tourn_leave') if xo_joined else t(lang,'tourn_join')) + " ❌⭕",
                callback_data=f"sm:tourn:{'leave' if xo_joined else 'join'}:{tid}"
            )])
            rows.append([
                InlineKeyboardButton(text=t(lang,'tourn_players')+" ❌⭕", callback_data=f"sm:tourn:players:{tid}"),
                InlineKeyboardButton(text=t(lang,'tourn_bracket')+" ❌⭕", callback_data=f"sm:tourn:bracket:{tid}"),
            ])
        else:
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_bracket')+" ❌⭕", callback_data=f"sm:tourn:bracket:{tid}")])
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_players')+" ❌⭕", callback_data=f"sm:tourn:players:{tid}")])
            if is_admin_user:
                rows.append([InlineKeyboardButton(text="▶️ Run pending ❌⭕", callback_data=f"sm:tourn:run:{tid}")])
        if is_admin_user and status == "REG":
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_admin_cancel')+" ❌⭕", callback_data=f"sm:tourn:cancel:{tid}")])
    else:
        if is_admin_user:
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_admin_create')+" ❌⭕", callback_data="sm:tourn:create:xo")])

    # Checkers
    if ck_t:
        tid = int(ck_t["id"])
        status = str(ck_t.get("status") or "")
        if status == "REG":
            rows.append([InlineKeyboardButton(
                text=(t(lang,'tourn_leave') if ck_joined else t(lang,'tourn_join')) + " ♟️",
                callback_data=f"sm:tourn:{'leave' if ck_joined else 'join'}:{tid}"
            )])
            rows.append([
                InlineKeyboardButton(text=t(lang,'tourn_players')+" ♟️", callback_data=f"sm:tourn:players:{tid}"),
                InlineKeyboardButton(text=t(lang,'tourn_bracket')+" ♟️", callback_data=f"sm:tourn:bracket:{tid}"),
            ])
        else:
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_bracket')+" ♟️", callback_data=f"sm:tourn:bracket:{tid}")])
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_players')+" ♟️", callback_data=f"sm:tourn:players:{tid}")])
            if is_admin_user:
                rows.append([InlineKeyboardButton(text="▶️ Run pending ♟️", callback_data=f"sm:tourn:run:{tid}")])
        if is_admin_user and status == "REG":
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_admin_cancel')+" ♟️", callback_data=f"sm:tourn:cancel:{tid}")])
    else:
        if is_admin_user:
            rows.append([InlineKeyboardButton(text=t(lang,'tourn_admin_create')+" ♟️", callback_data="sm:tourn:create:checkers")])

    rows.append([InlineKeyboardButton(text="⬅️", callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _tourn_text_block(lang: str, tinfo: dict | None, label: str) -> str:
    from app.config import DAILY_TOURNAMENT_HOUR, DAILY_TOURNAMENT_MINUTE, TOURN_PAYOUT_WINNER_PCT, TOURN_PAYOUT_RUNNER_PCT
    # ARENA_FEE_PCT is optional; default 10 if not present
    try:
        from app.config import ARENA_FEE_PCT
        fee_pct = int(ARENA_FEE_PCT)
    except Exception:
        fee_pct = 10

    if not tinfo:
        return f"{label}: <b>нема активного</b> (наступний о <b>{DAILY_TOURNAMENT_HOUR:02d}:{DAILY_TOURNAMENT_MINUTE:02d}</b>)"

    status = str(tinfo.get("status") or "")
    size = int(tinfo.get("size") or 0)
    fee = int(tinfo.get("entry_fee") or 0)
    pool = int(tinfo.get("prize_pool") or 0)
    arena_fee = int(pool * fee_pct / 100) if pool > 0 and fee_pct > 0 else 0
    net_pool = max(0, pool - arena_fee)
    win = int(net_pool * int(TOURN_PAYOUT_WINNER_PCT) / 100) if net_pool > 0 else 0
    run = int(net_pool * int(TOURN_PAYOUT_RUNNER_PCT) / 100) if net_pool > 0 else 0

    # participants
    try:
        players = list_tournament_players(int(tinfo["id"]))
        cnt = len(players)
    except Exception:
        cnt = 0

    # reg timer
    timer = ""
    if status == "REG" and tinfo.get("reg_ends_ts"):
        try:
            left = int(float(tinfo["reg_ends_ts"]) - time.time())
            if left < 0:
                left = 0
            timer = f" | реєстрація <b>{left//60:02d}:{left%60:02d}</b>"
        except Exception:
            timer = ""

    return (
        f"{label}: <b>{status}</b> | учасники <b>{cnt}/{size}</b>\n"
        f"🎫 Вхід: <b>{fee}🪙</b> | 💰 Фонд: <b>{pool}🪙</b> (net {net_pool}🪙; комісія {fee_pct}% = {arena_fee}🪙)\n"
        f"🏅 Призи: 🥇 <b>{win}🪙</b> / 🥈 <b>{run}🪙</b>{timer}"
    )


@router.callback_query(F.data == "sm:tourn:home")
async def tourn_home(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)

    xo_t = get_active_tournament("xo")
    ck_t = get_active_tournament("checkers")

    is_admin_user = is_admin(cb.from_user.id)

    xo_joined = False
    ck_joined = False
    try:
        if xo_t:
            xo_joined = any(int(p["user_id"]) == int(cb.from_user.id) for p in list_tournament_players(int(xo_t["id"])))
        if ck_t:
            ck_joined = any(int(p["user_id"]) == int(cb.from_user.id) for p in list_tournament_players(int(ck_t["id"])))
    except Exception:
        pass

    header = f"{t(lang,'tourn_title')}\n\n"
    body = []
    body.append(_tourn_text_block(lang, xo_t, "❌⭕ XO"))
    body.append("")
    body.append(_tourn_text_block(lang, ck_t, "♟️ Шашки"))

    text = header + "\n".join(body)

    kb = _tourn_dual_kb(lang, is_admin_user, xo_t, xo_joined, ck_t, ck_joined)
    await safe_edit_text(cb.message, text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("sm:tourn:create"))
async def tourn_create(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("nope"); return
    init_db()
    lang = ensure_user(cb)
    parts = cb.data.split(":")
    # sm:tourn:create or sm:tourn:create:xo/checkers
    g = parts[-1] if len(parts) >= 4 else get_active_game(cb.from_user.id)
    tid = create_tournament(g, f"SM Arena Tournament #{int(time.time())%10000}", 8, cb.from_user.id, entry_fee=20)
    await cb.answer("OK")
    await tourn_home(cb)


@router.callback_query(F.data.startswith("sm:tourn:join:"))
async def tourn_join(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    tid = int(cb.data.split(":")[-1])

    ok = join_tournament(tid, cb.from_user.id)
    if not ok:
        # explain most common reasons
        from app.db import get_tournament_by_id
        tinfo = get_tournament_by_id(tid)
        if not tinfo or str(tinfo.get("status")) != "REG":
            await cb.answer("Реєстрація закрита ⛔", show_alert=True)
        else:
            fee = int(tinfo.get("entry_fee") or 0)
            u = get_user(cb.from_user.id) or {}
            bal = int(u.get("coins") or 0)
            if bal < fee:
                await cb.answer(f"Не вистачає монет: потрібно {fee}🪙", show_alert=True)
            else:
                await cb.answer("Не вдалося увійти (турнір повний?)", show_alert=True)
    else:
        await cb.answer("✅")
    await tourn_home(cb)


@router.callback_query(F.data.startswith("sm:tourn:leave:"))
async def tourn_leave(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    tid = int(cb.data.split(":")[-1])
    ok = leave_tournament(tid, cb.from_user.id)
    await cb.answer("✅" if ok else "❌")
    await tourn_home(cb)


@router.callback_query(F.data.startswith("sm:tourn:players:"))
async def tourn_players(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang=ensure_user(cb)
    tid=int(cb.data.split(":")[-1])
    pl=list_tournament_players(tid)
    lines=[f"{t(lang,'tourn_title')} — {t(lang,'tourn_players')}\n"]
    for i,p in enumerate(pl, start=1):
        name=("@"+p["username"]) if (p.get("username") or "").strip() else (p.get("first_name") or "Player")
        lines.append(f"{i}. {name}")
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️", callback_data="sm:tourn:home")]])
    await safe_edit_text(cb.message,"\n".join(lines),reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("sm:tourn:bracket:"))
async def tourn_bracket(cb: CallbackQuery):
    if not click_ok(cb.from_user.id):
        await cb.answer(); return
    init_db()
    lang=ensure_user(cb)
    tid=int(cb.data.split(":")[-1])
    txt=get_bracket_text(tid) or "—"
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️", callback_data="sm:tourn:home")]])
    await safe_edit_text(cb.message, txt, reply_markup=kb)
    await cb.answer()

class _BotWrap:
    def __init__(self, bot: Bot):
        self.bot = bot

async def _start_tourn_pvp(bot: Bot, a_id: int, b_id: int, tournament_id: int, tmatch_id: int):
    match_id=str(uuid.uuid4())[:8]
    board="........."
    # send messages
    a_lang = db_get_lang(a_id) or "en"
    b_lang = db_get_lang(b_id) or "en"
    ma = await bot.send_message(a_id, f"🏆 {t(a_lang,'tourn_match_found')}", reply_markup=board_kb_pvp(match_id, board, a_lang, skin=get_skin(a_id), show_controls=False))
    mb = await bot.send_message(b_id, f"🏆 {t(b_lang,'tourn_match_found')}", reply_markup=board_kb_pvp(match_id, board, b_lang, skin=get_skin(b_id), show_controls=False))
    PVP_MATCHES[match_id]={
        "board": board,
        "x": a_id,
        "o": b_id,
        "turn":"X",
        "status":"playing",
        "last_move": time.time(),
        "x_chat": a_id,
        "o_chat": b_id,
        "x_msg": ma.message_id,
        "o_msg": mb.message_id,
        "x_lang": a_lang,
        "o_lang": b_lang,
        "tournament_id": int(tournament_id),
        "tmatch_id": int(tmatch_id),
    }
    set_pvp_timer(match_id, _BotWrap(bot))

@router.callback_query(F.data.startswith("sm:tourn:start:"))
async def tourn_start(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("nope"); return
    init_db()
    lang=ensure_user(cb)
    tid=int(cb.data.split(":")[-1])
    matches=generate_bracket(tid)
    if not matches:
        await cb.answer(t(lang,'tourn_need_players'))
        return
    await cb.answer("OK")
    # start all pending
    pend=get_pending_matches(tid)
    for m in pend:
        a=int(m["a_id"]); b=int(m["b_id"])
        mark_match_playing(int(m["id"]))
        await _start_tourn_pvp(cb.bot, a, b, tid, int(m["id"]))
    await cb.bot.send_message(cb.from_user.id, t(lang,'tourn_started'))
    await tourn_home(cb)

@router.callback_query(F.data.startswith("sm:tourn:run:"))
async def tourn_run_pending(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("nope"); return
    init_db()
    tid=int(cb.data.split(":")[-1])
    pend=get_pending_matches(tid)
    for m in pend:
        mark_match_playing(int(m["id"]))
        await _start_tourn_pvp(cb.bot, int(m["a_id"]), int(m["b_id"]), tid, int(m["id"]))
    await cb.answer("OK")

@router.callback_query(F.data.startswith("sm:tourn:cancel:"))
async def tourn_cancel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("nope"); return
    init_db()
    tid=int(cb.data.split(":")[-1])
    cancel_tournament(tid)
    await cb.answer("OK")
    await tourn_home(cb)


# =====================================================================
# ⚔️  ARENA MODE  (Hearthstone-style)
# =====================================================================
from app.arena_mode import (
    ARENA_ENTRY_FEE, ARENA_MAX_WINS, ARENA_MAX_LOSSES,
    get_session as arena_get_session,
    start_session as arena_start_session,
    end_session as arena_end_session,
)
import app.arena_mode as _arena

def _arena_kb(lang: str, session=None) -> InlineKeyboardMarkup:
    rows = []
    if session and not session.finished:
        rows.append([InlineKeyboardButton(text="🏆 Почати наступний бій", callback_data="sm:arena:play")])
        rows.append([InlineKeyboardButton(text="🚪 Вийти з Арени", callback_data="sm:arena:quit")])
    elif not session:
        rows.append([InlineKeyboardButton(text=f"⚔️ Увійти в Арену ({ARENA_ENTRY_FEE}🪙)", callback_data="sm:arena:enter")])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sm:arena:home")
async def arena_home(cb: CallbackQuery):
    if not click_ok(cb.from_user.id): await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    s = arena_get_session(cb.from_user.id)

    if s and s.finished:
        # claim reward
        reward_id = s.reward_id or ""
        reward_label = s.reward_label or "Нагорода"
        arena_end_session(cb.from_user.id)
        if reward_id.startswith("coins:"):
            amt = int(reward_id.split(":")[1])
            add_coins(cb.from_user.id, amt)
        elif reward_id.startswith("lootbox:"):
            add_item(cb.from_user.id, reward_id)
        # bonus 200 coins for perfect 10-0
        if s and s.wins >= ARENA_MAX_WINS:
            add_coins(cb.from_user.id, 200)
        text = (
            f"⚔️ <b>Арена завершена!</b>\n\n"
            f"🏆 Перемог: <b>{s.wins if s else 0}/{ARENA_MAX_WINS}</b>\n"
            f"💀 Поразок: <b>{s.losses if s else 0}/{ARENA_MAX_LOSSES}</b>\n\n"
            f"🎁 Нагорода: <b>{reward_label}</b>"
        )
        await safe_edit_text(cb.message, text, reply_markup=_arena_kb(lang))
        await cb.answer("🎉 Нагороду отримано!")
        return

    if s:
        text = (
            f"⚔️ <b>Арена</b>\n\n"
            f"🏆 Перемог: <b>{s.wins}/{ARENA_MAX_WINS}</b>\n"
            f"💀 Поразок: <b>{s.losses}/{ARENA_MAX_LOSSES}</b>\n\n"
            f"Продовжуй битися або вийди!"
        )
    else:
        text = (
            f"⚔️ <b>Режим Арени</b>\n\n"
            f"Вхід: <b>{ARENA_ENTRY_FEE} 🪙</b>\n"
            f"Ціль: {ARENA_MAX_WINS} перемог або до 3 поразок.\n"
            f"Чим більше перемог — тим крутіша нагорода!\n\n"
            f"🥇 5+ перемог → Бронзова скриня\n"
            f"🏆 10 перемог → Золота скриня + 200 монет"
        )
    await safe_edit_text(cb.message, text, reply_markup=_arena_kb(lang, s))
    await cb.answer()


@router.callback_query(F.data == "sm:arena:enter")
async def arena_enter(cb: CallbackQuery):
    if not click_ok(cb.from_user.id): await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    uid = cb.from_user.id

    if arena_get_session(uid):
        await cb.answer("⚔️ Ти вже в Арені!", show_alert=True)
        return

    if not try_spend_coins(uid, ARENA_ENTRY_FEE):
        await cb.answer(f"Недостатньо монет! Потрібно {ARENA_ENTRY_FEE}🪙", show_alert=True)
        return

    g = get_active_game(uid)
    arena_start_session(uid, game=g)
    await cb.answer(f"⚔️ Ти увійшов в Арену! Удачі!")
    await arena_home(cb)


@router.callback_query(F.data == "sm:arena:quit")
async def arena_quit(cb: CallbackQuery):
    if not click_ok(cb.from_user.id): await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    s = arena_get_session(cb.from_user.id)
    if s:
        # partial reward for early quit
        wins = s.wins
        from app.arena_mode import _get_reward
        rid, rlabel = _get_reward(wins)
        arena_end_session(cb.from_user.id)
        if rid.startswith("coins:"):
            add_coins(cb.from_user.id, int(rid.split(":")[1]))
        elif rid.startswith("lootbox:"):
            add_item(cb.from_user.id, rid)
        await cb.answer(f"Ти вийшов. Нагорода: {rlabel}")
    await arena_home(cb)


@router.callback_query(F.data == "sm:arena:play")
async def arena_play(cb: CallbackQuery):
    """Queue the arena player for a random match; hook result back."""
    if not click_ok(cb.from_user.id): await cb.answer(); return
    init_db()
    lang = ensure_user(cb)
    s = arena_get_session(cb.from_user.id)
    if not s or s.finished:
        await arena_home(cb); return

    # Re-use random queue – player is tagged with arena session so game end can report
    uid = cb.from_user.id
    if is_in_queue(uid):
        await cb.answer("Вже в черзі ⏳"); return

    remove_from_queue(uid)
    entry: dict = {
        "user_id": uid,
        "chat_id": cb.message.chat.id,
        "message_id": cb.message.message_id,
        "lang": lang,
        "ts": time.time(),
        "rating": get_rating(uid),
        "vip": is_vip(uid),
        "side": "x",
        "arena": True,   # flag so match result can be fed back
    }
    (WAIT_X_VIP if entry["vip"] else WAIT_X).append(entry)
    await safe_edit_text(cb.message, f"⚔️ Арена | Пошук суперника...", reply_markup=searching_kb(lang))
    await cb.answer()
    WAIT_TASKS[uid] = asyncio.create_task(random_fallback_to_ai(cb, uid, entry["chat_id"], entry["message_id"], 30))

