# app/config.py
import os
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file() -> dict[str, str]:
    vals: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return vals
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


_ENV_FILE_VALUES = _read_env_file()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is not None and str(v).strip() != "":
        return str(v)
    return _ENV_FILE_VALUES.get(name, default)

# ================== TELEGRAM ==================
# ĐťĐ• ĐżŃĐ±Đ»Ń–Đą Ń‚ĐľĐşĐµĐ˝ Đ˝Ń–Đ´Đµ (Ń‡Đ°Ń‚Đ¸/ŃĐşŃ€Ń–Đ˝Đ¸/ĐłŃ–Ń‚Ń…Đ°Đ±).
# Đ ĐµĐşĐľĐĽĐµĐ˝Đ´ĐľĐ˛Đ°Đ˝Đľ: Đ·Đ±ĐµŃ€Ń–ĐłĐ°Ń‚Đ¸ Ń‚ĐľĐşĐµĐ˝ Ń Đ·ĐĽŃ–Đ˝Đ˝Ń–Đą ŃĐµŃ€ĐµĐ´ĐľĐ˛Đ¸Ń‰Đ° BOT_TOKEN.
# ĐŻĐşŃ‰Đľ Đ·Đ°ĐżŃŃĐşĐ°Ń”Ń Đ»ĐľĐşĐ°Đ»ŃŚĐ˝Đľ Ń– Ń…ĐľŃ‡ĐµŃ .env â€” ĐżĐľĐşĐ»Đ°Đ´Đ¸ BOT_TOKEN Ń Ń„Đ°ĐąĐ» .env Đ˛ ĐşĐľŃ€ĐµĐ˝Ń– ĐżŃ€ĐľŃ”ĐşŃ‚Ń.

BOT_TOKEN = _env("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "âťŚ BOT_TOKEN is not set. Set environment variable BOT_TOKEN or put BOT_TOKEN=... into .env in project root."
    )

# đź‘‘ ĐĐ”ĐśĐ†ĐťĐ
# ĐśĐľĐ¶Đ˝Đ° ĐżĐµŃ€ĐµĐ˛Đ¸Đ·Đ˝Đ°Ń‡Đ¸Ń‚Đ¸ Ń‡ĐµŃ€ĐµĐ· .env: ADMIN_IDS=123,456
ADMIN_IDS = [
    8148164304,  # Đ’ŃŹŃ‡ĐµŃĐ»Đ°Đ˛
]
_admin_env = _env("ADMIN_IDS", "").strip()
if _admin_env:
    try:
        ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip()]
    except Exception:
        pass

# ================== GAME / UI ==================
# ================== LINKS ==================
DEFAULT_NEWS_TITLE = "ĐťĐľĐ˛Đ¸Đ˝Đ¸"
DEFAULT_NEWS_URL = "https://t.me/sm_arena"
DEFAULT_CHAT_TITLE = "Đ§Đ°Ń‚Đ¸Đş"
DEFAULT_CHAT_URL = "https://t.me/SM_Arena_chat"

DEFAULT_SKIN = "default"

# ĐšĐ»ŃŽŃ‡Ń– ĐĽĐ°ŃŽŃ‚ŃŚ Đ·Đ±Ń–ĐłĐ°Ń‚Đ¸ŃŃŹ Đ· Ń‚Đ¸ĐĽ, Ń‰Đľ ĐżŃ–Đ´Ń‚Ń€Đ¸ĐĽŃŃ” keyboards.py (_theme)
SKINS = [
    ("default", "Classic"),
    ("3d", "3D"),
    ("neon", "Neon"),
    ("mono", "Mono"),
]

# ================== VIP ==================
# (days, stars)
VIP_PLANS = [
    (7, 50),
    (30, 150),
]
# (days, coins)
VIP_COIN_PLANS = [
    (7, 200),
    (30, 700),
]

VIP_FALLBACK_AI_SEC = 10
NONVIP_FALLBACK_AI_SEC = 25

# ================== RATING / SEASONS ==================
DEFAULT_RATING = 1000
SEASON_LENGTH_DAYS = 30
SOFT_RESET_FACTOR = 0.5

# ================== WEEKLY TOP / PRIZES ==================
TOP_N = 100
DEFAULT_PRIZE_POOL = 100

# ================== ANTI-BOOST ==================
ANTI_BOOST_WINDOW_HOURS = 6
ANTI_BOOST_MAX_RATED = 3

# ================== PVP ==================
PVP_INACTIVITY_SEC = 60

# ================== LIMITS ==================
CLICK_RATE_LIMIT_SEC = 0.4

# ================== TOURNAMENTS (DAILY) ==================
# Daily tournaments time is in Europe/Uzhgorod (server local time should match, but we compute offset-safe).
DAILY_TOURNAMENT_HOUR = 20  # 20:00
DAILY_TOURNAMENT_MINUTE = 0
TOURN_REG_MINUTES = 10
TOURN_DAILY_SIZE = 8
TOURN_ENTRY_FEE = 20  # đźŞ™
TOURN_TICKET_PRICE = 20  # đźŽ« ĐşĐ˛Đ¸Ń‚ĐľĐş Đ˝Đ° Đ˛Ń…Ń–Đ´ (Đ·Đ° Đ·Đ°ĐĽĐľĐ˛Ń‡ŃĐ˛Đ°Đ˝Đ˝ŃŹĐĽ = entry fee)
TOURN_REMIND_2M_SEC = 120  # Đ˝Đ°ĐłĐ°Đ´ŃĐ˛Đ°Đ˝Đ˝ŃŹ Đ·Đ° 2 Ń…Đ˛ Đ´Đľ ĐşŃ–Đ˝Ń†ŃŹ Ń€ĐµŃ”ŃŃ‚Ń€Đ°Ń†Ń–Ń—
TOURN_REMIND_30S_SEC = 30   # Đ˝Đ°ĐłĐ°Đ´ŃĐ˛Đ°Đ˝Đ˝ŃŹ Đ·Đ° 30 ŃĐµĐş Đ´Đľ ĐşŃ–Đ˝Ń†ŃŹ Ń€ĐµŃ”ŃŃ‚Ń€Đ°Ń†Ń–Ń—
TOURN_PAYOUT_WINNER_PCT = 70
TOURN_PAYOUT_RUNNER_PCT = 30
TOURN_POINTS_JOIN = 10
TOURN_POINTS_WIN = 20
TOURN_POINTS_CHAMPION_BONUS = 60
TOURN_POINTS_RUNNER_BONUS = 30
TOURN_TECH_LOSS_SEC = 60  # anti-afk in tournament matches
TOURN_STREAK_TARGET = 3
TOURN_STREAK_BONUS_COINS = 30

ARENA_FEE_PCT = 10  # % ĐşĐľĐĽŃ–ŃŃ–ŃŹ Đ°Ń€ĐµĐ˝Đ¸ Đ· ĐżŃ€Đ¸Đ·ĐľĐ˛ĐľĐłĐľ Ń„ĐľĐ˝Đ´Ń
VIP_DAILY_COINS = 10
VIP_WEEKLY_PACK_ENABLED = True
VIP_WEEKLY_PACK_FALLBACK_COINS = 30

# ================== DONATE ==================
DONATE_AMOUNTS = [10, 25, 50, 100]


# ---------------- Payments (LiqPay Checkout) ----------------
LIQPAY_PUBLIC_KEY = _env("LIQPAY_PUBLIC_KEY", "")
LIQPAY_PRIVATE_KEY = _env("LIQPAY_PRIVATE_KEY", "")

# Public base URL of your webhook server (must be HTTPS for LiqPay callbacks)
_RAILWAY_PUBLIC_DOMAIN = _env("RAILWAY_PUBLIC_DOMAIN", "").strip()
_WEBHOOK_DEFAULT = f"https://{_RAILWAY_PUBLIC_DOMAIN}" if _RAILWAY_PUBLIC_DOMAIN else ""
WEBHOOK_BASE_URL = _env("WEBHOOK_BASE_URL", _WEBHOOK_DEFAULT)

WEBHOOK_HOST = _env("WEBHOOK_HOST", "0.0.0.0")
# Railway and similar platforms expose dynamic HTTP port in PORT.
WEBHOOK_PORT = int(_env("PORT", _env("WEBHOOK_PORT", "8080")))

PAY_CURRENCY = "UAH"

# Coin packs (coins, price_uah)
LIQPAY_COIN_PACKS = {
    "coins_50": (50, 19),
    "coins_200": (200, 69),
    "coins_500": (500, 159),
    "coins_1200": (1200, 249),
}

LIQPAY_VIP_SKU = "vip_30d"
LIQPAY_VIP_PRICE_UAH = 79
LIQPAY_VIP_DAYS = 30
