# app/keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import SKINS, VIP_PLANS, VIP_COIN_PLANS
from app.i18n import t


# ---------- Skin rendering ----------
def _theme(skin: str):
    s = (skin or "default").lower()

    # default/classic
    if s in ("default", "classic"):
        return {
            "x": "❌",
            "o": "⭕",
            "e": "·",
            "hl": "🟩",
        }

    # 3d
    if s in ("3d", "three_d"):
        return {
            "x": "❎",
            "o": "🅾️",
            "e": "⬛",
            "hl": "🟦",
        }

    # neon
    if s in ("neon",):
        return {
            "x": "✖️",
            "o": "⚪",
            "e": "▫️",
            "hl": "🟪",
        }

    # mono/minimal
    if s in ("mono", "minimal"):
        return {
            "x": "X",
            "o": "O",
            "e": "·",
            "hl": "■",
        }

    # fallback
    return {
        "x": "❌",
        "o": "⭕",
        "e": "·",
        "hl": "🟩",
    }


def _cell_text(ch: str, highlight: bool, skin: str) -> str:
    th = _theme(skin)
    if highlight:
        return th["hl"]
    if ch == "X":
        return th["x"]
    if ch == "O":
        return th["o"]
    return th["e"]



# ---------- GAME SELECT ----------
def games_select_kb(lang: str, active_game: str = "xo") -> InlineKeyboardMarkup:
    g = (active_game or "xo").lower()
    xo_prefix = "✅ " if g == "xo" else ""
    ck_prefix = "✅ " if g == "checkers" else ""
    ch_prefix = "✅ " if g == "chess" else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{xo_prefix}{t(lang,'game_xo')}", callback_data="sm:game:xo")],
        [InlineKeyboardButton(text=f"{ck_prefix}{t(lang,'game_checkers')}", callback_data="sm:game:checkers")],
        [InlineKeyboardButton(text=f"{ch_prefix}{t(lang,'game_chess')}", callback_data="sm:game:chess")],
    ])


# ---------- UNIFIED GAME MENU (same for both games) ----------
def arena_menu_kb(
    lang: str,
    game: str,
    chat_url: str = "",
    news_url: str = "",
) -> InlineKeyboardMarkup:
    g = (game or "xo").lower()
    if g == "checkers":
        rated_cb = "sm:ck:play_pvp"
        bot_cb = "sm:ck:play_ai"
        game_badge = " (Checkers)"
    elif g == "chess":
        rated_cb = "sm:ch:play_pvp"
        bot_cb = "sm:ch:play_ai"
        game_badge = " (Chess)"
    else:
        rated_cb = "sm:menu:play_random"
        bot_cb = "sm:menu:play_ai"
        game_badge = " (XO)"
    rated_label = f"{t(lang, 'menu_rated')}{game_badge}"
    bot_label = f"{t(lang, 'menu_vs_bot')}{game_badge}"

    rows = [
        [InlineKeyboardButton(text=rated_label, callback_data=rated_cb)],
        [InlineKeyboardButton(text=bot_label, callback_data=bot_cb)],
        [InlineKeyboardButton(text=t(lang, "menu_friend"), callback_data="sm:menu:friend")],
        [InlineKeyboardButton(text=t(lang, "menu_add_group"), callback_data="sm:menu:add_group")],

        [
            InlineKeyboardButton(text=t(lang, "menu_quests"), callback_data="sm:menu:quests"),
            InlineKeyboardButton(text=t(lang, "menu_balance"), callback_data="sm:menu:balance"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_market"), callback_data="sm:menu:market"),
            InlineKeyboardButton(text=t(lang, "menu_settings2"), callback_data="sm:menu:settings"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_news2"), url=news_url) if news_url else InlineKeyboardButton(text=t(lang, "menu_news2"), callback_data="sm:menu:links"),
            InlineKeyboardButton(text=t(lang, "menu_chat2"), url=chat_url) if chat_url else InlineKeyboardButton(text=t(lang, "menu_chat2"), callback_data="sm:menu:links"),
        ],
        [
    InlineKeyboardButton(text=t(lang, "menu_tournaments"), callback_data="sm:tourn:home"),
    InlineKeyboardButton(text=t(lang, "menu_seasons"), callback_data="sm:season:home"),
],
[
    InlineKeyboardButton(text=t(lang, "menu_referral"), callback_data="sm:ref:home"),
    InlineKeyboardButton(text=t(lang, "menu_top100"), callback_data="sm:menu:top"),
],
[InlineKeyboardButton(text=t(lang, "menu_profile"), callback_data="sm:menu:profile")],
        [InlineKeyboardButton(text=t(lang, "menu_switch_game"), callback_data="sm:game:select")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "menu_lang"), callback_data="sm:menu:lang")],
        [InlineKeyboardButton(text=t(lang, "menu_skins"), callback_data="sm:menu:skins")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])


def market_menu_kb(lang: str) -> InlineKeyboardMarkup:
    # Shop + inventory (coins). VIP and donations are kept as separate sections.
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="sm:market:shop")],
        [InlineKeyboardButton(text="🎒 Інвентар", callback_data="sm:market:inv")],
        [InlineKeyboardButton(text=t(lang, "menu_vip"), callback_data="sm:menu:vip")],
        [InlineKeyboardButton(text=t(lang, "menu_donate"), callback_data="sm:menu:donate")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])

# ---------- MAIN MENU ----------
def main_menu_kb(lang: str, sponsor_text: str = "", sponsor_url: str = "", show_sponsor: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "menu_pvp"), callback_data="sm:menu:play_random")],
        [InlineKeyboardButton(text=t(lang, "menu_lobby"), callback_data="sm:menu:lobby")],
        [InlineKeyboardButton(text=t(lang, "menu_ai"), callback_data="sm:menu:play_ai")],
        [
            InlineKeyboardButton(text=t(lang, "menu_profile"), callback_data="sm:menu:profile"),
            InlineKeyboardButton(text=t(lang, "menu_top"), callback_data="sm:menu:top"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_vip"), callback_data="sm:menu:vip"),
            InlineKeyboardButton(text=t(lang, "menu_lang"), callback_data="sm:menu:lang"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_skins"), callback_data="sm:menu:skins"),
            InlineKeyboardButton(text=t(lang, "menu_donate"), callback_data="sm:menu:donate"),
        ],
        [InlineKeyboardButton(text=t(lang, "menu_rules"), callback_data="sm:menu:rules")],
    ]

    if show_sponsor and sponsor_text and sponsor_url:
        rows.append([InlineKeyboardButton(text=sponsor_text, url=sponsor_url)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- AI ----------
def ai_levels_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "ai_level_easy"), callback_data="sm:ai:start:easy")],
        [InlineKeyboardButton(text=t(lang, "ai_level_normal"), callback_data="sm:ai:start:normal")],
        [InlineKeyboardButton(text=t(lang, "ai_level_hard"), callback_data="sm:ai:start:hard")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])


# ---------- RANDOM PvP ----------
def random_side_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "want_x"), callback_data="sm:random:want:x"),
            InlineKeyboardButton(text=t(lang, "want_o"), callback_data="sm:random:want:o"),
        ],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")],
    ])


def searching_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="sm:random:cancel")]
    ])


# ---------- LANGUAGE ----------
def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Українська 🇺🇦", callback_data="sm:lang:set:uk"),
            InlineKeyboardButton(text="English 🇬🇧", callback_data="sm:lang:set:en"),
        ],
        [
            InlineKeyboardButton(text="Čeština 🇨🇿", callback_data="sm:lang:set:cs"),
            InlineKeyboardButton(text="Deutsch 🇩🇪", callback_data="sm:lang:set:de"),
        ],
        [
            InlineKeyboardButton(text="Polski 🇵🇱", callback_data="sm:lang:set:pl"),
            InlineKeyboardButton(text="Slovenčina 🇸🇰", callback_data="sm:lang:set:sk"),
        ],
        [
            InlineKeyboardButton(text="Magyar 🇭🇺", callback_data="sm:lang:set:hu"),
            InlineKeyboardButton(text="Română 🇷🇴", callback_data="sm:lang:set:ro"),
        ],
        [
            InlineKeyboardButton(text="Español 🇪🇸", callback_data="sm:lang:set:es"),
            InlineKeyboardButton(text="Français 🇫🇷", callback_data="sm:lang:set:fr"),
        ],
    ])


# ---------- DONATE / SKINS / VIP ----------
def donate_kb(lang: str, amounts) -> InlineKeyboardMarkup:
    rows = []
    for a in amounts:
        rows.append([InlineKeyboardButton(text=f"⭐ {int(a)}", callback_data=f"sm:donate:{int(a)}")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skins_kb(lang: str, current_skin: str, only_active: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if only_active:
        title_map = {str(k): str(v) for k, v in SKINS}
        cur_title = title_map.get(str(current_skin), str(current_skin))
        rows.append([InlineKeyboardButton(text=f"✅ {t(lang, 'skins_active')}: {cur_title}", callback_data="sm:skin:noop")])
        rows.append([InlineKeyboardButton(text=t(lang, "skins_show_all"), callback_data="sm:skins:all")])
        rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    for key, title in SKINS:
        mark = "✅ " if str(key) == str(current_skin) else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{title}", callback_data=f"sm:skin:set:{key}")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vip_kb(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for it in VIP_PLANS:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            days = int(it[0]); stars = int(it[1])
        elif isinstance(it, dict):
            days = int(it.get("days", 0)); stars = int(it.get("stars", 0))
        else:
            continue
        if days <= 0 or stars <= 0:
            continue
        rows.append([InlineKeyboardButton(text=f"Stars {days}d - {stars}", callback_data=f"sm:vip:buy:{days}:{stars}")])

    for it in VIP_COIN_PLANS:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            days = int(it[0]); coins = int(it[1])
        elif isinstance(it, dict):
            days = int(it.get("days", 0)); coins = int(it.get("coins", 0))
        else:
            continue
        if days <= 0 or coins <= 0:
            continue
        rows.append([InlineKeyboardButton(text=f"Coins {days}d - {coins}", callback_data=f"sm:vip:buycoins:{days}:{coins}")])

    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- BOARDS ----------
def board_kb(match_id: str, board: str, lang: str, highlight=set(), skin: str = "default") -> InlineKeyboardMarkup:
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            row.append(InlineKeyboardButton(
                text=_cell_text(board[i], i in highlight, skin),
                callback_data=f"sm:ai:move:{match_id}:{i}"
            ))
        rows.append(row)

    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def board_kb_pvp(match_id: str, board: str, lang: str, highlight=set(), extra_rows=None, skin: str = "default") -> InlineKeyboardMarkup:
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            row.append(InlineKeyboardButton(
                text=_cell_text(board[i], i in highlight, skin),
                callback_data=f"sm:pvp:move:{match_id}:{i}"
            ))
        rows.append(row)

    if extra_rows:
        rows.extend(extra_rows)

    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="sm:menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

