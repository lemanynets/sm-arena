# app/db.py
import sqlite3
import random
import uuid as _uuid
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time

_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "sm_arena.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_DEFAULT_DB_PATH)))

DEFAULT_RATING = 1000

# Default external links (can be changed via admin commands)
DEFAULT_NEWS_TITLE = "Новини"
DEFAULT_NEWS_URL = "https://t.me/Praca_czua"
DEFAULT_CHAT_TITLE = "Чатик"
DEFAULT_CHAT_URL = "https://t.me/Praca_czua/1"


def _con():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con

def set_skin_ck(user_id: int, skin: str):
    init_db()
    con = _con()
    try:
        con.execute("UPDATE users SET skin_ck=? WHERE user_id=?", (str(skin), int(user_id)))
        con.commit()
    finally:
        con.close()

def get_skin_ck(user_id: int) -> str:
    u = get_user(user_id)
    s = (u or {}).get("skin_ck") or "default"
    return str(s)

def _ensure_user_columns(con: sqlite3.Connection):
    """Add new columns safely."""
    cols = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
    wanted = {
        "skin_ck": "TEXT NOT NULL DEFAULT 'default'",
        "active_game": "TEXT NOT NULL DEFAULT 'xo'",
        "rating_ck": "INTEGER NOT NULL DEFAULT 1000",
        "total_wins_ck": "INTEGER NOT NULL DEFAULT 0",
        "total_games_ck": "INTEGER NOT NULL DEFAULT 0",
        "week_wins_ck": "INTEGER NOT NULL DEFAULT 0",
        "week_games_ck": "INTEGER NOT NULL DEFAULT 0",
        "coins": "INTEGER NOT NULL DEFAULT 60",
        "quest_mask": "INTEGER NOT NULL DEFAULT 0",
        "quest_mask_ck": "INTEGER NOT NULL DEFAULT 0",
"season_rating": "INTEGER NOT NULL DEFAULT 1000",
"season_rating_ck": "INTEGER NOT NULL DEFAULT 1000",
"season_wins": "INTEGER NOT NULL DEFAULT 0",
"season_games": "INTEGER NOT NULL DEFAULT 0",
"season_wins_ck": "INTEGER NOT NULL DEFAULT 0",
"season_games_ck": "INTEGER NOT NULL DEFAULT 0",
"ref_earned": "INTEGER NOT NULL DEFAULT 0",
"ref_count": "INTEGER NOT NULL DEFAULT 0",
"tourn_streak": "INTEGER NOT NULL DEFAULT 0",
"tourn_last_day": "TEXT NOT NULL DEFAULT ''",
"tourn_streak_ck": "INTEGER NOT NULL DEFAULT 0",
"tourn_last_day_ck": "TEXT NOT NULL DEFAULT ''",
"tourn_points": "INTEGER NOT NULL DEFAULT 0",
"tourn_points_ck": "INTEGER NOT NULL DEFAULT 0",
        "vip_last_daily_ts": "REAL",
        "vip_last_weekly_pack_ts": "REAL",
        "tourn_tickets": "INTEGER NOT NULL DEFAULT 0",
        "tourn_ticket_last_day": "TEXT NOT NULL DEFAULT ''",

    }
    for name, ddl in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")


def _ensure_week_history_columns(con: sqlite3.Connection):
    """Add optional columns to week_history."""
    cols = {row[1] for row in con.execute("PRAGMA table_info(week_history)").fetchall()}
    if "game" not in cols:
        # keep backward compatibility: existing rows become xo
        con.execute("ALTER TABLE week_history ADD COLUMN game TEXT NOT NULL DEFAULT 'xo'")


def _ensure_vip_columns(con: sqlite3.Connection):
    """Backward-compatible alias for old callers."""
    _ensure_user_columns(con)


def init_db():
    con = _con()
    try:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS meta(
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            lang TEXT,
            rating INTEGER NOT NULL DEFAULT 1000,
            total_wins INTEGER NOT NULL DEFAULT 0,
            total_games INTEGER NOT NULL DEFAULT 0,
            week_wins INTEGER NOT NULL DEFAULT 0,
            week_games INTEGER NOT NULL DEFAULT 0,
            vip_until REAL NOT NULL DEFAULT 0,
            skin TEXT NOT NULL DEFAULT 'default',
            updated_ts REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS banned(
            user_id INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS pair_stats(
            pair_key TEXT PRIMARY KEY,
            window_start REAL NOT NULL DEFAULT 0,
            count INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS week_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            prize_pool INTEGER NOT NULL,
            top_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS invites(
            token TEXT PRIMARY KEY,
            game TEXT NOT NULL,
            inviter_id INTEGER NOT NULL,
            created_ts REAL NOT NULL,
            used_by INTEGER,
            used_ts REAL
        );


        CREATE TABLE IF NOT EXISTS inventory(
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            purchased_ts REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, item_id)
        );

CREATE TABLE IF NOT EXISTS referrals(
    inviter_id INTEGER NOT NULL,
    invited_id INTEGER NOT NULL,
    created_ts REAL NOT NULL,
    activated_ts REAL,
    rewarded_ts REAL,
    PRIMARY KEY(invited_id)
);

CREATE TABLE IF NOT EXISTS season_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    season_start_ts REAL NOT NULL,
    season_end_ts REAL NOT NULL,
    top_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tournaments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL, -- REG/RUNNING/DONE/CANCELLED
    size INTEGER NOT NULL DEFAULT 8,
    created_ts REAL NOT NULL,
    started_ts REAL,
    ended_ts REAL,
    created_by INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tournament_players(
    tournament_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_ts REAL NOT NULL,
    seed INTEGER,
    PRIMARY KEY(tournament_id, user_id)
);

CREATE TABLE IF NOT EXISTS tournament_matches(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    round INTEGER NOT NULL,
    a_id INTEGER,
    b_id INTEGER,
    winner_id INTEGER,
    status TEXT NOT NULL, -- PENDING/PLAYING/DONE/BYE
    created_ts REAL NOT NULL,
    ended_ts REAL
);


CREATE TABLE IF NOT EXISTS tournament_rating(
    user_id INTEGER NOT NULL,
    game TEXT NOT NULL, -- xo/checkers/overall
    points INTEGER NOT NULL DEFAULT 0,
    updated_ts REAL NOT NULL,
    PRIMARY KEY(user_id, game)
);


        """)

        _ensure_user_columns(con)
        _ensure_week_history_columns(con)

        # welcome bonus for new users (and old accounts with 0 games)
        try:
            con.execute("UPDATE users SET coins=60 WHERE coins=0 AND total_games=0 AND total_games_ck=0")
        except Exception:
            pass

        # defaults
        _meta_set(con, "week_start_ts", str(time.time()))
        _meta_set(con, "prize_pool", _meta_get(con, "prize_pool", "100"))
        _meta_set(con, "season_start_ts", _meta_get(con, "season_start_ts", str(time.time())))
        _meta_set(con, "season_id", _meta_get(con, "season_id", "1"))
        _meta_set(con, "sponsor_text", _meta_get(con, "sponsor_text", ""))
        _meta_set(con, "sponsor_url", _meta_get(con, "sponsor_url", ""))
        # payments orders (LiqPay)
        con.execute("""CREATE TABLE IF NOT EXISTS orders(
            order_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            amount_minor INTEGER NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            created_ts REAL NOT NULL,
            paid_ts REAL
        );""")

        con.commit()
    finally:
        con.close()


def _meta_get(con, k: str, default: str = "") -> str:
    cur = con.execute("SELECT v FROM meta WHERE k=?", (k,))
    r = cur.fetchone()
    return str(r["v"]) if r else default


def _meta_set(con, k: str, v: str):
    con.execute(
        "INSERT INTO meta(k,v) VALUES(?,?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (k, str(v))
    )


# ---------- User upsert ----------
def upsert_user(user_id: int, username: str | None, first_name: str | None, lang: str | None):
    init_db()
    con = _con()
    try:
        now = time.time()
        con.execute("""
        INSERT INTO users(user_id, username, first_name, lang, updated_ts)
        VALUES(?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          username=excluded.username,
          first_name=excluded.first_name,
          lang=COALESCE(excluded.lang, users.lang),
          updated_ts=excluded.updated_ts
        """, (int(user_id), username or "", first_name or "", lang, now))
        con.commit()
    finally:
        con.close()


def set_lang(user_id: int, lang: str):
    init_db()
    con = _con()
    try:
        con.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, int(user_id)))
        con.commit()
    finally:
        con.close()


def get_lang(user_id: int) -> str | None:
    init_db()
    con = _con()
    try:
        r = con.execute("SELECT lang FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return str(r["lang"]) if r and r["lang"] else None
    finally:
        con.close()



def db_get_lang(user_id: int) -> str:
    """Compatibility alias for older modules expecting db_get_lang()."""
    lang = get_lang(user_id)
    return lang or "uk"



def get_user(user_id: int) -> dict | None:
    init_db()
    con = _con()
    try:
        r = con.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def _game_suffix(game: str) -> str:
    g = (game or "xo").lower()
    if g in ("xo", "tic", "tictactoe"):
        return ""
    if g in ("checkers", "ck", "shashky", "шашки"):
        return "_ck"
    # Chess currently reuses XO counters/ratings as safe fallback in shared flows.
    if g in ("chess", "ch", "шахи", "шахматы"):
        return ""
    raise ValueError("Unknown game")


def _norm_game(game: str) -> str:
    suf = _game_suffix(game)
    return "checkers" if suf == "_ck" else "xo"


def get_active_game(user_id: int) -> str:
    u = get_user(user_id) or {}
    g = (u.get("active_game") or "xo").strip().lower()
    return g if g in ("xo", "checkers", "chess") else "xo"


def set_active_game(user_id: int, game: str):
    init_db()
    con = _con()
    try:
        g = (game or "xo").strip().lower()
        if g in ("ck", "shashky", "шашки"):
            g = "checkers"
        elif g in ("ch", "шахи", "шахматы"):
            g = "chess"
        elif g in ("tic", "tictactoe"):
            g = "xo"
        if g not in ("xo", "checkers", "chess"):
            g = "xo"
        game_norm = g
        con.execute("UPDATE users SET active_game=? WHERE user_id=?", (game_norm, int(user_id)))
        con.commit()
    finally:
        con.close()


# Chat link stored in meta
def set_chat(title: str, url: str):
    init_db()
    con = _con()
    try:
        _meta_set(con, "chat_title", title or "")
        _meta_set(con, "chat_url", url or "")
        con.commit()
    finally:
        con.close()


def get_chat() -> dict:
    init_db()
    con = _con()
    try:
        return {
            "title": _meta_get(con, "chat_title", DEFAULT_CHAT_TITLE),
            "url": _meta_get(con, "chat_url", DEFAULT_CHAT_URL),
        }
    finally:
        con.close()

# News link stored in meta
def set_news(title: str, url: str):
    init_db()
    con = _con()
    try:
        _meta_set(con, "news_title", title or "")
        _meta_set(con, "news_url", url or "")
        con.commit()
    finally:
        con.close()


def get_news() -> dict:
    init_db()
    con = _con()
    try:
        return {
            "title": _meta_get(con, "news_title", DEFAULT_NEWS_TITLE),
            "url": _meta_get(con, "news_url", DEFAULT_NEWS_URL),
        }
    finally:
        con.close()

# Coins / Balance
def get_coins(user_id: int) -> int:
    u = get_user(user_id) or {}
    try:
        return int(u.get("coins", 0) or 0)
    except Exception:
        return 0


def set_coins(user_id: int, coins: int):
    init_db()
    con = _con()
    try:
        con.execute("UPDATE users SET coins=? WHERE user_id=?", (int(coins), int(user_id)))
        con.commit()
    finally:
        con.close()


def add_coins(user_id: int, delta: int) -> int:
    init_db()
    con = _con()
    try:
        con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (int(delta), int(user_id)))
        con.commit()
        cur = con.execute("SELECT coins FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return int(cur["coins"] or 0) if cur else 0
    finally:
        con.close()


# ---------- Spend / Inventory ----------
def try_spend_coins(user_id: int, amount: int) -> bool:
    """Atomically subtract coins if balance is enough."""
    init_db()
    amount = max(0, int(amount))
    con = _con()
    try:
        con.execute("BEGIN IMMEDIATE")
        r = con.execute("SELECT coins FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        bal = int(r["coins"] or 0) if r else 0
        if bal < amount:
            con.execute("ROLLBACK")
            return False
        con.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, int(user_id)))
        con.commit()
        return True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        con.close()


def has_item(user_id: int, item_id: str) -> bool:
    init_db()
    con = _con()
    try:
        r = con.execute(
            "SELECT 1 FROM inventory WHERE user_id=? AND item_id=?",
            (int(user_id), str(item_id)),
        ).fetchone()
        return bool(r)
    finally:
        con.close()


def add_item(user_id: int, item_id: str) -> None:
    init_db()
    con = _con()
    try:
        con.execute(
            "INSERT OR IGNORE INTO inventory(user_id, item_id, purchased_ts, active) VALUES(?,?,?,0)",
            (int(user_id), str(item_id), float(time.time())),
        )
        con.commit()
    finally:
        con.close()


def owned_item_ids(user_id: int) -> set[str]:
    init_db()
    con = _con()
    try:
        cur = con.execute("SELECT item_id FROM inventory WHERE user_id=? ORDER BY purchased_ts DESC", (int(user_id),))
        return {str(r["item_id"]) for r in cur.fetchall()}
    finally:
        con.close()


def get_inventory(user_id: int) -> list[dict]:
    init_db()
    con = _con()
    try:
        cur = con.execute(
            "SELECT item_id, purchased_ts, active FROM inventory WHERE user_id=? ORDER BY purchased_ts DESC",
            (int(user_id),),
        )
        out = []
        for r in cur.fetchall():
            out.append(
                {
                    "item_id": str(r["item_id"]),
                    "purchased_ts": float(r["purchased_ts"] or 0.0),
                    "active": int(r["active"] or 0),
                }
            )
        return out
    finally:
        con.close()


def set_active_item(user_id: int, item_id: str) -> None:
    """Marks item active; deactivates same-scope items by prefix skin:xo: or skin:checkers:."""
    init_db()
    con = _con()
    try:
        iid = str(item_id)
        prefix = None
        if iid.startswith("skin:xo:"):
            prefix = "skin:xo:%"
        elif iid.startswith("skin:checkers:"):
            prefix = "skin:checkers:%"

        if prefix:
            con.execute("UPDATE inventory SET active=0 WHERE user_id=? AND item_id LIKE ?", (int(user_id), prefix))
        con.execute("UPDATE inventory SET active=1 WHERE user_id=? AND item_id=?", (int(user_id), iid))
        con.commit()
    finally:
        con.close()



# Quests (bitmask per game: quest_mask / quest_mask_ck)
def get_quest_mask(user_id: int, game: str = "xo") -> int:
    u = get_user(user_id) or {}
    col = "quest_mask" + _game_suffix(game)
    try:
        return int(u.get(col, 0) or 0)
    except Exception:
        return 0


def set_quest_mask(user_id: int, mask: int, game: str = "xo"):
    init_db()
    con = _con()
    try:
        col = "quest_mask" + _game_suffix(game)
        con.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (int(mask), int(user_id)))
        con.commit()
    finally:
        con.close()




def get_rating(user_id: int, game: str = "xo") -> int:
    u = get_user(user_id)
    if not u:
        return DEFAULT_RATING
    suf = _game_suffix(game)
    key = "rating" + suf
    try:
        return int(u.get(key, DEFAULT_RATING))
    except Exception:
        return DEFAULT_RATING


def set_rating(user_id: int, rating: int, game: str = "xo"):
    init_db()
    con = _con()
    try:
        suf = _game_suffix(game)
        col = "rating" + suf
        con.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (int(rating), int(user_id)))
        con.commit()
    finally:
        con.close()


def bump_total(user_id: int, win: bool, game: str = "xo"):
    init_db()
    con = _con()
    try:
        suf = _game_suffix(game)
        games_col = "total_games" + suf
        wins_col = "total_wins" + suf
        con.execute(f"UPDATE users SET {games_col}={games_col}+1 WHERE user_id=?", (int(user_id),))
        if win:
            con.execute(f"UPDATE users SET {wins_col}={wins_col}+1 WHERE user_id=?", (int(user_id),))
        con.commit()
    finally:
        con.close()


def bump_weekly(user_id: int, win: bool, game: str = "xo"):
    init_db()
    con = _con()
    try:
        suf = _game_suffix(game)
        games_col = "week_games" + suf
        wins_col = "week_wins" + suf
        con.execute(f"UPDATE users SET {games_col}={games_col}+1 WHERE user_id=?", (int(user_id),))
        if win:
            con.execute(f"UPDATE users SET {wins_col}={wins_col}+1 WHERE user_id=?", (int(user_id),))
        con.commit()
    finally:
        con.close()


# ---------- Skins / VIP ----------
def set_skin(user_id: int, skin: str):
    init_db()
    con = _con()
    try:
        con.execute("UPDATE users SET skin=? WHERE user_id=?", (str(skin), int(user_id)))
        con.commit()
    finally:
        con.close()


def get_skin(user_id: int) -> str:
    u = get_user(user_id)
    s = (u or {}).get("skin") or "default"
    return str(s)


def vip_until(user_id: int) -> float:
    u = get_user(user_id)
    try:
        return float((u or {}).get("vip_until", 0.0) or 0.0)
    except Exception:
        return 0.0


def is_vip(user_id: int) -> bool:
    return time.time() < vip_until(user_id)


def add_vip_days(user_id: int, days: int) -> float:
    init_db()
    con = _con()
    try:
        now = time.time()
        cur = vip_until(user_id)
        base = cur if cur > now else now
        new_until = base + int(days) * 86400
        con.execute("UPDATE users SET vip_until=? WHERE user_id=?", (float(new_until), int(user_id)))
        con.commit()
        return float(new_until)
    finally:
        con.close()


# ---------- Sponsor / prize pool / week start ----------
def get_sponsor() -> dict:
    init_db()
    con = _con()
    try:
        return {
            "text": _meta_get(con, "sponsor_text", ""),
            "url": _meta_get(con, "sponsor_url", ""),
        }
    finally:
        con.close()


def set_sponsor(text: str, url: str):
    init_db()
    con = _con()
    try:
        _meta_set(con, "sponsor_text", text or "")
        _meta_set(con, "sponsor_url", url or "")
        con.commit()
    finally:
        con.close()


def get_prize_pool() -> int:
    init_db()
    con = _con()
    try:
        try:
            return int(_meta_get(con, "prize_pool", "100"))
        except Exception:
            return 100
    finally:
        con.close()


def set_prize_pool(val: int):
    init_db()
    con = _con()
    try:
        _meta_set(con, "prize_pool", str(max(0, int(val))))
        con.commit()
    finally:
        con.close()


def add_prize_pool(delta: int) -> int:
    cur = get_prize_pool()
    cur = max(0, cur + int(delta))
    set_prize_pool(cur)
    return cur


def get_week_start_ts() -> float:
    init_db()
    con = _con()
    try:
        try:
            return float(_meta_get(con, "week_start_ts", str(time.time())))
        except Exception:
            return time.time()
    finally:
        con.close()


def set_week_start_ts(ts: float):
    init_db()
    con = _con()
    try:
        _meta_set(con, "week_start_ts", str(float(ts)))
        con.commit()
    finally:
        con.close()


# ---------- Bans ----------
def ban_user(user_id: int):
    init_db()
    con = _con()
    try:
        con.execute("INSERT OR IGNORE INTO banned(user_id) VALUES(?)", (int(user_id),))
        con.commit()
    finally:
        con.close()


def unban_user(user_id: int):
    init_db()
    con = _con()
    try:
        con.execute("DELETE FROM banned WHERE user_id=?", (int(user_id),))
        con.commit()
    finally:
        con.close()


def is_banned(user_id: int) -> bool:
    init_db()
    con = _con()
    try:
        r = con.execute("SELECT 1 FROM banned WHERE user_id=?", (int(user_id),)).fetchone()
        return bool(r)
    finally:
        con.close()


# ---------- Anti-boost pair stats (PER GAME) ----------
def _pair_key(a: int, b: int, game: str = "xo") -> str:
    x, y = (a, b) if a < b else (b, a)
    g = _norm_game(game)
    return f"{g}:{x}:{y}"


def is_rated_pair_game(a: int, b: int, window_sec: int, max_rated: int, game: str = "xo") -> bool:
    init_db()
    con = _con()
    try:
        k = _pair_key(a, b, game=game)
        r = con.execute("SELECT window_start, count FROM pair_stats WHERE pair_key=?", (k,)).fetchone()
        if not r:
            return True
        ws = float(r["window_start"] or 0.0)
        cnt = int(r["count"] or 0)
        now = time.time()
        if now - ws >= window_sec:
            return True
        return cnt < max_rated
    finally:
        con.close()


def record_pair_game(a: int, b: int, window_sec: int, game: str = "xo") -> int:
    init_db()
    con = _con()
    try:
        k = _pair_key(a, b, game=game)
        now = time.time()
        r = con.execute("SELECT window_start, count, total FROM pair_stats WHERE pair_key=?", (k,)).fetchone()
        if not r:
            con.execute(
                "INSERT INTO pair_stats(pair_key, window_start, count, total) VALUES(?,?,?,?)",
                (k, now, 1, 1)
            )
            con.commit()
            return 1

        ws = float(r["window_start"] or 0.0)
        cnt = int(r["count"] or 0)
        tot = int(r["total"] or 0)

        if now - ws >= window_sec:
            cnt = 1
            ws = now
        else:
            cnt += 1
        tot += 1

        con.execute(
            "UPDATE pair_stats SET window_start=?, count=?, total=? WHERE pair_key=?",
            (ws, cnt, tot, k)
        )
        con.commit()
        return int(cnt)
    finally:
        con.close()


# ---------- TOP-100 рейтингу (фільтри: загальний / XO / Шашки) ----------
def get_top100(mode: str = "overall", limit: int = 100) -> list[dict]:
    """
    mode:
      - overall: rating + rating_ck
      - xo: rating
      - checkers: rating_ck
    """
    init_db()
    con = _con()
    try:
        mode = (mode or "overall").lower()
        lim = max(1, min(500, int(limit)))

        if mode in ("xo", "x", "tic"):
            cur = con.execute(
                """
                SELECT user_id, username, first_name, rating AS score, rating AS rating_xo, rating_ck AS rating_ck
                FROM users
                ORDER BY rating DESC, user_id ASC
                LIMIT ?
                """,
                (lim,),
            )
        elif mode in ("checkers", "ck", "shashky"):
            cur = con.execute(
                """
                SELECT user_id, username, first_name, rating_ck AS score, rating AS rating_xo, rating_ck AS rating_ck
                FROM users
                ORDER BY rating_ck DESC, user_id ASC
                LIMIT ?
                """,
                (lim,),
            )
        else:
            cur = con.execute(
                """
                SELECT user_id, username, first_name, (rating + rating_ck) AS score, rating AS rating_xo, rating_ck AS rating_ck
                FROM users
                ORDER BY (rating + rating_ck) DESC, user_id ASC
                LIMIT ?
                """,
                (lim,),
            )

        out = []
        for r in cur.fetchall():
            out.append(
                {
                    "user_id": int(r["user_id"]),
                    "username": (r["username"] or ""),
                    "first_name": (r["first_name"] or ""),
                    "score": int(r["score"] or 0),
                    "rating_xo": int(r["rating_xo"] or DEFAULT_RATING),
                    "rating_ck": int(r["rating_ck"] or DEFAULT_RATING),
                }
            )
        return out
    finally:
        con.close()


def get_season_top100(mode: str = "overall", limit: int = 100) -> list[dict]:
    """
    mode:
      - overall: season_rating + season_rating_ck
      - xo: season_rating
      - checkers: season_rating_ck
    """
    init_db()
    con = _con()
    try:
        mode = (mode or "overall").lower()
        lim = max(1, min(500, int(limit)))

        if mode in ("xo", "x", "tic"):
            cur = con.execute(
                """
                SELECT user_id, username, first_name,
                       season_rating AS score,
                       season_rating AS rating_xo,
                       season_rating_ck AS rating_ck
                FROM users
                ORDER BY season_rating DESC, user_id ASC
                LIMIT ?
                """,
                (lim,)
            )
        elif mode in ("checkers", "ck", "shashky"):
            cur = con.execute(
                """
                SELECT user_id, username, first_name,
                       season_rating_ck AS score,
                       season_rating AS rating_xo,
                       season_rating_ck AS rating_ck
                FROM users
                ORDER BY season_rating_ck DESC, user_id ASC
                LIMIT ?
                """,
                (lim,)
            )
        else:
            cur = con.execute(
                """
                SELECT user_id, username, first_name,
                       (season_rating + season_rating_ck) AS score,
                       season_rating AS rating_xo,
                       season_rating_ck AS rating_ck
                FROM users
                ORDER BY score DESC, user_id ASC
                LIMIT ?
                """,
                (lim,)
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


def list_all_user_ids() -> list[int]:
    init_db()
    con = _con()
    try:
        cur = con.execute("SELECT user_id FROM users ORDER BY user_id ASC")
        return [int(r["user_id"]) for r in cur.fetchall()]
    finally:
        con.close()

# ---------- Weekly TOP / ranks ----------
def get_weekly_top(limit: int = 10, game: str = "xo") -> list[dict]:
    init_db()
    con = _con()
    try:
        suf = _game_suffix(game)
        ww = "week_wins" + suf
        wg = "week_games" + suf
        rt = "rating" + suf
        cur = con.execute(f"""
            SELECT user_id, username, first_name, {ww} as week_wins, {wg} as week_games, {rt} as rating
            FROM users
            WHERE {wg} > 0 OR {ww} > 0
            ORDER BY {ww} DESC, {rt} DESC, {wg} ASC, user_id ASC
            LIMIT ?
        """, (int(limit),))
        out = []
        for r in cur.fetchall():
            out.append({
                "user_id": int(r["user_id"]),
                "username": (r["username"] or ""),
                "first_name": (r["first_name"] or ""),
                "week_wins": int(r["week_wins"] or 0),
                "week_games": int(r["week_games"] or 0),
                "rating": int(r["rating"] or DEFAULT_RATING),
            })
        return out
    finally:
        con.close()


def get_weekly_rank(user_id: int, game: str = "xo") -> int | None:
    init_db()
    con = _con()
    try:
        suf = _game_suffix(game)
        ww = "week_wins" + suf
        wg = "week_games" + suf
        rt = "rating" + suf
        cur = con.execute(f"""
            SELECT user_id
            FROM users
            WHERE {wg} > 0 OR {ww} > 0
            ORDER BY {ww} DESC, {rt} DESC, {wg} ASC, user_id ASC
        """)
        rank = 1
        for r in cur.fetchall():
            if int(r["user_id"]) == int(user_id):
                return rank
            rank += 1
        return None
    finally:
        con.close()


# ---------- Week reset + archive ----------
def _now_dt():
    return datetime.now(timezone.utc)


def reset_week_if_needed(week_len_days: int, top_n: int):
    """
    Архівує топи для XO і для Шашок окремими записами у week_history (з колонкою game).
    Якщо колонка game з якихось причин не додалась — все одно не впаде (запише як xo).
    """
    init_db()
    ws = datetime.fromtimestamp(get_week_start_ts(), tz=timezone.utc)
    now = _now_dt()
    if now - ws < timedelta(days=week_len_days):
        return False

    import json
    con = _con()
    try:
        ts = int(time.time())
        week_start_str = ws.strftime("%Y-%m-%d")
        pool = get_prize_pool()

        # 1) XO snapshot
        top_xo = get_weekly_top(top_n, game="xo")
        payload_xo = []
        for i, it in enumerate(top_xo, start=1):
            payload_xo.append({
                "rank": i,
                "user_id": it["user_id"],
                "wins": it["week_wins"],
                "games": it["week_games"],
                "rating": it["rating"],
                "username": it["username"],
                "first_name": it["first_name"],
            })

        # 2) Checkers snapshot
        top_ck = get_weekly_top(top_n, game="checkers")
        payload_ck = []
        for i, it in enumerate(top_ck, start=1):
            payload_ck.append({
                "rank": i,
                "user_id": it["user_id"],
                "wins": it["week_wins"],
                "games": it["week_games"],
                "rating": it["rating"],
                "username": it["username"],
                "first_name": it["first_name"],
            })

        # insert rows (supports new column game; if DB old, fallback silently)
        try:
            con.execute(
                "INSERT INTO week_history(ts, week_start, prize_pool, top_json, game) VALUES(?,?,?,?,?)",
                (ts, week_start_str, int(pool), json.dumps(payload_xo, ensure_ascii=False), "xo")
            )
            con.execute(
                "INSERT INTO week_history(ts, week_start, prize_pool, top_json, game) VALUES(?,?,?,?,?)",
                (ts, week_start_str, int(pool), json.dumps(payload_ck, ensure_ascii=False), "checkers")
            )
        except sqlite3.OperationalError:
            # old schema without game column
            con.execute(
                "INSERT INTO week_history(ts, week_start, prize_pool, top_json) VALUES(?,?,?,?)",
                (ts, week_start_str, int(pool), json.dumps(payload_xo, ensure_ascii=False))
            )

        # reset weekly counters for BOTH games
        con.execute("UPDATE users SET week_wins=0, week_games=0, week_wins_ck=0, week_games_ck=0, quest_mask=0, quest_mask_ck=0")

        new_ws = now
        _meta_set(con, "week_start_ts", str(new_ws.timestamp()))
        con.commit()
    finally:
        con.close()

    return True


def load_week_history(limit: int = 5, game: str = "xo") -> list[dict]:
    init_db()
    con = _con()
    try:
        import json
        out = []

        # if schema has game column — filter by game
        cols = {row[1] for row in con.execute("PRAGMA table_info(week_history)").fetchall()}
        if "game" in cols:
            cur = con.execute(
                "SELECT week_start, prize_pool, top_json, ts, game FROM week_history "
                "WHERE game=? ORDER BY id DESC LIMIT ?",
                (_norm_game(game), int(limit))
            )
        else:
            cur = con.execute(
                "SELECT week_start, prize_pool, top_json, ts FROM week_history ORDER BY id DESC LIMIT ?",
                (int(limit),)
            )

        for r in cur.fetchall():
            try:
                top = json.loads(r["top_json"] or "[]")
            except Exception:
                top = []
            out.append({
                "week_start": str(r["week_start"]),
                "pool": int(r["prize_pool"] or 0),
                "top": top,
                "ts": int(r["ts"] or 0),
                "game": str(r["game"]) if "game" in r.keys() else "xo",
            })
        return out
    finally:
        con.close()


# Invites (deep links) for "Play with friend"
def create_invite(inviter_id: int, game: str = "xo") -> str:
    init_db()
    import secrets
    token = secrets.token_hex(4)
    con = _con()
    try:
        con.execute(
            "INSERT OR REPLACE INTO invites(token, game, inviter_id, created_ts, used_by, used_ts) VALUES(?,?,?,?,NULL,NULL)",
            (token, _norm_game(game), int(inviter_id), float(time.time()))
        )
        con.commit()
        return token
    finally:
        con.close()


def consume_invite(token: str, joiner_id: int) -> dict | None:
    """Mark invite as used and return dict with inviter_id + game."""
    init_db()
    con = _con()
    try:
        r = con.execute(
            "SELECT token, game, inviter_id, used_by, created_ts FROM invites WHERE token=?",
            (str(token),)
        ).fetchone()
        if not r:
            return None
        if r["used_by"] is not None and int(r["used_by"]) != 0:
            return None
        inviter_id = int(r["inviter_id"])
        if inviter_id == int(joiner_id):
            return None
        con.execute(
            "UPDATE invites SET used_by=?, used_ts=? WHERE token=?",
            (int(joiner_id), float(time.time()), str(token))
        )
        con.commit()
        return {"inviter_id": inviter_id, "game": str(r["game"])}
    finally:
        con.close()


# ---------------- Seasons ----------------
SEASON_LENGTH_DAYS = 30

def get_season_meta() -> dict:
    init_db()
    con = _con()
    try:
        sid = int(_meta_get(con, "season_id", "1") or "1")
        start_ts = float(_meta_get(con, "season_start_ts", str(time.time())) or time.time())
        return {"season_id": sid, "season_start_ts": start_ts}
    finally:
        con.close()

def _season_end_ts(start_ts: float) -> float:
    return float(start_ts) + SEASON_LENGTH_DAYS * 86400

def reset_season_if_needed(top_n: int = 50) -> dict | None:
    """If season expired -> store history, bump season id, reset seasonal stats."""
    init_db()
    con = _con()
    try:
        sid = int(_meta_get(con, "season_id", "1") or "1")
        start_ts = float(_meta_get(con, "season_start_ts", str(time.time())) or time.time())
        end_ts = _season_end_ts(start_ts)
        now = time.time()
        if now < end_ts:
            return None

        # Build top lists per game and combined
        top_xo = con.execute(
            "SELECT user_id, username, first_name, season_rating AS r FROM users ORDER BY season_rating DESC LIMIT ?",
            (int(top_n),)
        ).fetchall()
        top_ck = con.execute(
            "SELECT user_id, username, first_name, season_rating_ck AS r FROM users ORDER BY season_rating_ck DESC LIMIT ?",
            (int(top_n),)
        ).fetchall()
        # combined: sum of season ratings
        top_all = con.execute(
            "SELECT user_id, username, first_name, (season_rating + season_rating_ck) AS r FROM users ORDER BY r DESC LIMIT ?",
            (int(top_n),)
        ).fetchall()

        payload = {
            "season_id": sid,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "top_all": [dict(row) for row in top_all],
            "top_xo": [dict(row) for row in top_xo],
            "top_ck": [dict(row) for row in top_ck],
        }
        con.execute(
            "INSERT INTO season_history(season_id, season_start_ts, season_end_ts, top_json) VALUES(?,?,?,?)",
            (int(sid), float(start_ts), float(end_ts), json.dumps(payload, ensure_ascii=False))
        )

        # bump season
        sid2 = sid + 1
        _meta_set(con, "season_id", str(sid2))
        _meta_set(con, "season_start_ts", str(now))

        # reset seasonal stats
        con.execute("UPDATE users SET season_rating=1000, season_rating_ck=1000, season_wins=0, season_games=0, season_wins_ck=0, season_games_ck=0")
        con.commit()
        return payload
    finally:
        con.close()

def get_season_rating(user_id: int, game: str) -> int:
    u = get_user(user_id) or {}
    if _game_suffix(game) == "_ck":
        return int(u.get("season_rating_ck", 1000) or 1000)
    return int(u.get("season_rating", 1000) or 1000)

def set_season_rating(user_id: int, game: str, rating: int):
    init_db()
    con = _con()
    try:
        if _game_suffix(game) == "_ck":
            con.execute("UPDATE users SET season_rating_ck=? WHERE user_id=?", (int(rating), int(user_id)))
        else:
            con.execute("UPDATE users SET season_rating=? WHERE user_id=?", (int(rating), int(user_id)))
        con.commit()
    finally:
        con.close()

def inc_season_games(user_id: int, game: str, win: bool = False):
    init_db()
    con = _con()
    try:
        if _game_suffix(game) == "_ck":
            con.execute("UPDATE users SET season_games_ck=season_games_ck+1, season_wins_ck=season_wins_ck+? WHERE user_id=?",
                        (1 if win else 0, int(user_id)))
        else:
            con.execute("UPDATE users SET season_games=season_games+1, season_wins=season_wins+? WHERE user_id=?",
                        (1 if win else 0, int(user_id)))
        con.commit()
    finally:
        con.close()


# ---------------- Referrals ----------------
REF_REQUIRED_RATED_GAMES = 3
REF_REWARD_COINS = 30

def try_attach_referral(invited_id: int, inviter_id: int) -> bool:
    """Attach referral only if invited has 0 games and no referral yet."""
    init_db()
    con = _con()
    try:
        u = con.execute("SELECT total_games, total_games_ck FROM users WHERE user_id=?", (int(invited_id),)).fetchone()
        if u and (int(u["total_games"] or 0) > 0 or int(u["total_games_ck"] or 0) > 0):
            return False
        # avoid self
        if int(invited_id) == int(inviter_id):
            return False
        # already has referral
        r = con.execute("SELECT inviter_id FROM referrals WHERE invited_id=?", (int(invited_id),)).fetchone()
        if r:
            return False
        con.execute("INSERT INTO referrals(inviter_id, invited_id, created_ts) VALUES(?,?,?)",
                    (int(inviter_id), int(invited_id), float(time.time())))
        con.execute("UPDATE users SET ref_count=ref_count+1 WHERE user_id=?", (int(inviter_id),))
        con.commit()
        return True
    finally:
        con.close()

def get_referrer(invited_id: int) -> int | None:
    init_db()
    con=_con()
    try:
        r=con.execute("SELECT inviter_id FROM referrals WHERE invited_id=?", (int(invited_id),)).fetchone()
        return int(r["inviter_id"]) if r else None
    finally:
        con.close()

def _rated_games_total(con, user_id: int) -> int:
    r = con.execute("SELECT total_games, total_games_ck FROM users WHERE user_id=?", (int(user_id),)).fetchone()
    if not r:
        return 0
    return int(r["total_games"] or 0) + int(r["total_games_ck"] or 0)

def try_pay_referral_reward(invited_id: int) -> tuple[int, int] | None:
    """If invited reached threshold rated games -> reward inviter once. Returns (inviter_id, coins) or None."""
    init_db()
    con = _con()
    try:
        ref = con.execute("SELECT inviter_id, activated_ts, rewarded_ts FROM referrals WHERE invited_id=?", (int(invited_id),)).fetchone()
        if not ref:
            return None
        if ref["rewarded_ts"]:
            return None
        games = _rated_games_total(con, invited_id)
        if games < REF_REQUIRED_RATED_GAMES:
            return None
        inviter_id = int(ref["inviter_id"])
        now = float(time.time())
        if not ref["activated_ts"]:
            con.execute("UPDATE referrals SET activated_ts=? WHERE invited_id=?", (now, int(invited_id)))
        con.execute("UPDATE users SET coins=coins+?, ref_earned=ref_earned+? WHERE user_id=?",
                    (int(REF_REWARD_COINS), int(REF_REWARD_COINS), int(inviter_id)))
        con.execute("UPDATE referrals SET rewarded_ts=? WHERE invited_id=?", (now, int(invited_id)))
        con.commit()
        return (inviter_id, int(REF_REWARD_COINS))
    finally:
        con.close()



def get_ref_stats(user_id: int) -> dict:
    init_db()
    con = _con()
    try:
        u = con.execute("SELECT ref_count, ref_earned FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return {"ref_count": int((u["ref_count"] if u else 0) or 0), "ref_earned": int((u["ref_earned"] if u else 0) or 0)}
    finally:
        con.close()



# ---------------- Tournaments (XO + Checkers, Daily) ----------------
TOURN_MIN_PLAYERS = 4

def _ensure_tournament_columns(con: sqlite3.Connection):
    cols = {row[1] for row in con.execute("PRAGMA table_info(tournaments)").fetchall()}
    wanted = {
        "entry_fee": "INTEGER NOT NULL DEFAULT 0",
        "prize_pool": "INTEGER NOT NULL DEFAULT 0",
        "reg_ends_ts": "REAL",
        "auto_daily": "INTEGER NOT NULL DEFAULT 0",
        "day_key": "TEXT NOT NULL DEFAULT ''",
        "remind_2m_sent": "INTEGER NOT NULL DEFAULT 0",
        "remind_30s_sent": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")


def _ensure_tournament_players_columns(con: sqlite3.Connection):
    cols = {row[1] for row in con.execute("PRAGMA table_info(tournament_players)").fetchall()}
    wanted = {
        "entry_kind": "TEXT NOT NULL DEFAULT 'coins'",  # coins|ticket
    }
    for name, ddl in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE tournament_players ADD COLUMN {name} {ddl}")

def _today_key_uzh(ts: float | None = None) -> str:
    ts = float(ts or time.time())
    # Approx for Europe/Uzhgorod without external tz lib: use localtime (server should be configured).
    lt = time.localtime(ts)
    return f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"

def _tourn_points_add(con: sqlite3.Connection, user_id: int, game: str, delta: int):
    g = "checkers" if _norm_game(game) == "checkers" else "xo"
    now = float(time.time())
    con.execute(
        "INSERT INTO tournament_rating(user_id, game, points, updated_ts) VALUES(?,?,?,?) "
        "ON CONFLICT(user_id, game) DO UPDATE SET points=points+excluded.points, updated_ts=excluded.updated_ts",
        (int(user_id), g, int(delta), now)
    )
    con.execute(
        "INSERT INTO tournament_rating(user_id, game, points, updated_ts) VALUES(?,?,?,?) "
        "ON CONFLICT(user_id, game) DO UPDATE SET points=points+excluded.points, updated_ts=excluded.updated_ts",
        (int(user_id), "overall", int(delta), now)
    )

def get_tourn_top100(game: str = "overall", limit: int = 100, offset: int = 0) -> list[dict]:
    init_db()
    g = str(game)
    if g not in ("xo", "checkers", "overall"):
        g = "overall"
    con = _con()
    try:
        rows = con.execute(
            "SELECT tr.user_id, tr.points, u.username, u.first_name "
            "FROM tournament_rating tr LEFT JOIN users u ON u.user_id=tr.user_id "
            "WHERE tr.game=? ORDER BY tr.points DESC, tr.updated_ts DESC LIMIT ? OFFSET ?",
            (g, int(limit), int(offset))
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def get_tourn_tickets(user_id: int) -> int:
    init_db()
    con=_con()
    try:
        _ensure_user_columns(con)
        r=con.execute("SELECT tourn_tickets FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return int((r["tourn_tickets"] if r else 0) or 0)
    finally:
        con.close()

def claim_vip_daily_ticket(user_id: int) -> bool:
    """VIP can claim 1 free tournament ticket per day."""
    if not is_vip(int(user_id)):
        return False
    init_db()
    con=_con()
    try:
        _ensure_user_columns(con)
        con.execute("BEGIN IMMEDIATE")
        day_key=_today_key_uzh()
        r=con.execute("SELECT tourn_ticket_last_day FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        last=str((r["tourn_ticket_last_day"] if r else "") or "")
        if last == day_key:
            con.execute("ROLLBACK"); return False
        con.execute("UPDATE users SET tourn_tickets=tourn_tickets+1, tourn_ticket_last_day=? WHERE user_id=?",
                    (day_key, int(user_id)))
        con.commit()
        return True
    except Exception:
        try: con.execute("ROLLBACK")
        except Exception: pass
        return False
    finally:
        con.close()

def buy_tourn_ticket(user_id: int, price_coins: int | None = None) -> bool:
    """Buy tournament ticket for coins (price defaults to TOURN_TICKET_PRICE)."""
    from app.config import TOURN_TICKET_PRICE
    price = int(price_coins if price_coins is not None else TOURN_TICKET_PRICE)
    if price <= 0:
        return False
    init_db()
    con=_con()
    try:
        _ensure_user_columns(con)
        con.execute("BEGIN IMMEDIATE")
        r=con.execute("SELECT coins FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        bal=int((r["coins"] if r else 0) or 0)
        if bal < price:
            con.execute("ROLLBACK"); return False
        con.execute("UPDATE users SET coins=coins-?, tourn_tickets=tourn_tickets+1 WHERE user_id=?",
                    (price, int(user_id)))
        con.commit()
        return True
    except Exception:
        try: con.execute("ROLLBACK")
        except Exception: pass
        return False
    finally:
        con.close()

def get_reg_open_tournaments() -> list[dict]:
    """REG tournaments whose reg_ends_ts is in the future."""
    init_db()
    con=_con()
    try:
        _ensure_tournament_columns(con)
        now=float(time.time())
        rows=con.execute(
            "SELECT * FROM tournaments WHERE status='REG' AND reg_ends_ts IS NOT NULL AND reg_ends_ts>? ORDER BY id",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def mark_tournament_reminder(tournament_id: int, which: str):
    """which in ('2m','30s')"""
    init_db()
    con=_con()
    try:
        _ensure_tournament_columns(con)
        col = "remind_2m_sent" if which=="2m" else "remind_30s_sent"
        con.execute(f"UPDATE tournaments SET {col}=1 WHERE id=?", (int(tournament_id),))
        con.commit()
    finally:
        con.close()


def create_tournament(game: str, title: str, size: int, created_by: int,
                     entry_fee: int = 0, reg_ends_ts: float | None = None,
                     auto_daily: bool = False, day_key: str = "") -> int:
    init_db()
    g = _norm_game(game)
    con = _con()
    try:
        _ensure_tournament_columns(con)
        # allow only one active tournament per game
        con.execute("UPDATE tournaments SET status='CANCELLED', ended_ts=? WHERE game=? AND status IN ('REG','RUNNING')",
                    (float(time.time()), g))
        cur = con.execute(
            "INSERT INTO tournaments(game, title, status, size, created_ts, created_by, entry_fee, prize_pool, reg_ends_ts, auto_daily, day_key) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (g, title.strip()[:64] or "Tournament", "REG", int(size), float(time.time()), int(created_by),
             int(entry_fee), 0, float(reg_ends_ts) if reg_ends_ts else None, 1 if auto_daily else 0, str(day_key or ""))
        )
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()

def get_active_tournament(game: str) -> dict | None:
    init_db()
    g = _norm_game(game)
    con = _con()
    try:
        _ensure_tournament_columns(con)
        r = con.execute("SELECT * FROM tournaments WHERE game=? AND status IN ('REG','RUNNING') ORDER BY id DESC LIMIT 1", (g,)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()

def get_tournament_by_id(tournament_id: int) -> dict | None:
    init_db()
    con=_con()
    try:
        r=con.execute("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()

def get_reg_expired_tournaments() -> list[dict]:
    """REG tournaments whose reg_ends_ts passed."""
    init_db()
    con = _con()
    try:
        _ensure_tournament_columns(con)
        now = float(time.time())
        rows = con.execute(
            "SELECT * FROM tournaments WHERE status='REG' AND reg_ends_ts IS NOT NULL AND reg_ends_ts<=? ORDER BY id",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def list_tournament_players(tournament_id: int) -> list[dict]:
    init_db()
    con = _con()
    try:
        rows = con.execute(
            "SELECT tp.user_id, u.username, u.first_name FROM tournament_players tp "
            "LEFT JOIN users u ON u.user_id=tp.user_id "
            "WHERE tp.tournament_id=? ORDER BY tp.joined_ts ASC",
            (int(tournament_id),)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def join_tournament(tournament_id: int, user_id: int) -> bool:
    """Join tournament (charges entry fee if any) with coins."""
    init_db()
    con = _con()
    try:
        _ensure_tournament_columns(con)
        _ensure_tournament_players_columns(con)
        con.execute("BEGIN IMMEDIATE")
        t = con.execute("SELECT status, size, entry_fee FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t or str(t["status"]) != "REG":
            con.execute("ROLLBACK"); return False

        # already joined?
        rj = con.execute(
            "SELECT 1 FROM tournament_players WHERE tournament_id=? AND user_id=?",
            (int(tournament_id), int(user_id))
        ).fetchone()
        if rj:
            con.execute("ROLLBACK"); return True

        cnt = con.execute(
            "SELECT COUNT(*) AS c FROM tournament_players WHERE tournament_id=?",
            (int(tournament_id),)
        ).fetchone()
        if cnt and int(cnt["c"]) >= int(t["size"]):
            con.execute("ROLLBACK"); return False

        fee = int(t["entry_fee"] or 0)
        if fee > 0:
            bal = con.execute("SELECT coins FROM users WHERE user_id=?", (int(user_id),)).fetchone()
            bal = int(bal["coins"] or 0) if bal else 0
            if bal < fee:
                con.execute("ROLLBACK"); return False

            con.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (fee, int(user_id)))
            con.execute("UPDATE tournaments SET prize_pool=prize_pool+? WHERE id=?", (fee, int(tournament_id)))

        con.execute(
            "INSERT OR IGNORE INTO tournament_players(tournament_id, user_id, joined_ts, entry_kind) VALUES(?,?,?,?)",
            (int(tournament_id), int(user_id), float(time.time()), "coins")
        )
        con.commit()
        return True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        con.close()



def join_tournament_ticket(tournament_id: int, user_id: int) -> bool:
    """Join tournament using 🎫 ticket (no coin charge at join time)."""
    init_db()
    con = _con()
    try:
        _ensure_tournament_columns(con)
        _ensure_tournament_players_columns(con)
        _ensure_user_columns(con)

        con.execute("BEGIN IMMEDIATE")
        t = con.execute("SELECT status, size, entry_fee FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t or str(t["status"]) != "REG":
            con.execute("ROLLBACK"); return False

        # already joined?
        rj = con.execute(
            "SELECT 1 FROM tournament_players WHERE tournament_id=? AND user_id=?",
            (int(tournament_id), int(user_id))
        ).fetchone()
        if rj:
            con.execute("ROLLBACK"); return True

        cnt = con.execute(
            "SELECT COUNT(*) AS c FROM tournament_players WHERE tournament_id=?",
            (int(tournament_id),)
        ).fetchone()
        if cnt and int(cnt["c"]) >= int(t["size"]):
            con.execute("ROLLBACK"); return False

        # ticket balance
        u = con.execute("SELECT tourn_tickets FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        tickets = int((u["tourn_tickets"] if u else 0) or 0)
        if tickets <= 0:
            con.execute("ROLLBACK"); return False

        fee = int(t["entry_fee"] or 0)
        # spend ticket
        con.execute("UPDATE users SET tourn_tickets=MAX(tourn_tickets-1,0) WHERE user_id=?", (int(user_id),))
        # tickets also fund the pool by fee (keeps pool intuitive)
        if fee > 0:
            con.execute("UPDATE tournaments SET prize_pool=prize_pool+? WHERE id=?", (fee, int(tournament_id)))

        con.execute(
            "INSERT OR IGNORE INTO tournament_players(tournament_id, user_id, joined_ts, entry_kind) VALUES(?,?,?,?)",
            (int(tournament_id), int(user_id), float(time.time()), "ticket")
        )
        con.commit()
        return True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        con.close()


def leave_tournament(tournament_id: int, user_id: int) -> bool:
    """Leave tournament before start. Refunds coins or 🎫 ticket depending on entry_kind."""
    init_db()
    con = _con()
    try:
        _ensure_tournament_columns(con)
        _ensure_tournament_players_columns(con)
        _ensure_user_columns(con)

        con.execute("BEGIN IMMEDIATE")
        t = con.execute("SELECT status, entry_fee FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t or str(t["status"]) != "REG":
            con.execute("ROLLBACK"); return False

        row = con.execute(
            "SELECT entry_kind FROM tournament_players WHERE tournament_id=? AND user_id=?",
            (int(tournament_id), int(user_id))
        ).fetchone()
        if not row:
            con.execute("ROLLBACK"); return True

        entry_kind = str((row["entry_kind"] if row else "") or "coins").strip() or "coins"
        fee = int(t["entry_fee"] or 0)

        con.execute("DELETE FROM tournament_players WHERE tournament_id=? AND user_id=?", (int(tournament_id), int(user_id)))

        if fee > 0:
            if entry_kind == "ticket":
                con.execute("UPDATE users SET tourn_tickets=tourn_tickets+1 WHERE user_id=?", (int(user_id),))
                con.execute("UPDATE tournaments SET prize_pool=MAX(prize_pool-?,0) WHERE id=?", (fee, int(tournament_id)))
            else:
                con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (fee, int(user_id)))
                con.execute("UPDATE tournaments SET prize_pool=MAX(prize_pool-?,0) WHERE id=?", (fee, int(tournament_id)))

        con.commit()
        return True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        con.close()

def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p

def _seed_players(con, tournament_id: int, game: str) -> list[int]:
    if _game_suffix(game) == "_ck":
        col = "rating_ck"
    else:
        col = "rating"
    rows = con.execute(
        f"SELECT tp.user_id FROM tournament_players tp LEFT JOIN users u ON u.user_id=tp.user_id "
        f"WHERE tp.tournament_id=? ORDER BY u.{col} DESC, tp.joined_ts ASC",
        (int(tournament_id),)
    ).fetchall()
    return [int(r["user_id"]) for r in rows]

def generate_bracket(tournament_id: int) -> list[dict]:
    init_db()
    con = _con()
    try:
        _ensure_tournament_columns(con)
        t = con.execute("SELECT game, status, size FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t or str(t["status"]) != "REG":
            return []
        game = str(t["game"])
        players = _seed_players(con, tournament_id, game)
        if len(players) < TOURN_MIN_PLAYERS:
            return []
        bracket_size = min(int(t["size"]), _next_pow2(len(players)))
        players = players[:bracket_size]
        target = _next_pow2(len(players))
        while len(players) < target:
            players.append(None)

        pairs=[]
        i=0
        j=len(players)-1
        while i<j:
            pairs.append((players[i], players[j]))
            i+=1; j-=1

        now=float(time.time())
        for a,b in pairs:
            if a is not None and b is not None:
                con.execute(
                    "INSERT INTO tournament_matches(tournament_id, round, a_id, b_id, status, created_ts) VALUES(?,?,?,?,?,?)",
                    (int(tournament_id), 1, int(a), int(b), "PENDING", now)
                )
            else:
                winner = a if b is None else b
                con.execute(
                    "INSERT INTO tournament_matches(tournament_id, round, a_id, b_id, winner_id, status, created_ts, ended_ts) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (int(tournament_id), 1, int(a) if a else None, int(b) if b else None, int(winner) if winner else None,
                     "BYE", now, now)
                )
        con.execute("UPDATE tournaments SET status='RUNNING', started_ts=? WHERE id=?", (now, int(tournament_id)))
        con.commit()
        return [dict(r) for r in con.execute("SELECT * FROM tournament_matches WHERE tournament_id=? ORDER BY round,id", (int(tournament_id),)).fetchall()]
    finally:
        con.close()

def get_pending_matches(tournament_id: int) -> list[dict]:
    init_db()
    con = _con()
    try:
        rows = con.execute("SELECT * FROM tournament_matches WHERE tournament_id=? AND status='PENDING' ORDER BY id",
                           (int(tournament_id),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def mark_match_playing(match_id: int):
    init_db()
    con=_con()
    try:
        con.execute("UPDATE tournament_matches SET status='PLAYING' WHERE id=?", (int(match_id),))
        con.commit()
    finally:
        con.close()

def set_match_result(match_id: int, winner_id: int):
    init_db()
    con=_con()
    try:
        now=float(time.time())
        con.execute("UPDATE tournament_matches SET status='DONE', winner_id=?, ended_ts=? WHERE id=?",
                    (int(winner_id), now, int(match_id)))
        con.commit()
    finally:
        con.close()

def get_tournament_match(match_id: int) -> dict | None:
    init_db()
    con=_con()
    try:
        r=con.execute("SELECT * FROM tournament_matches WHERE id=?", (int(match_id),)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()

def get_bracket_text(tournament_id: int) -> str:
    init_db()
    con=_con()
    try:
        t=con.execute("SELECT title, game, status FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t:
            return ""
        title=str(t["title"])
        rows=con.execute(
            "SELECT m.round, m.a_id, m.b_id, m.winner_id, m.status, ua.username AS a_u, ua.first_name AS a_f, "
            "ub.username AS b_u, ub.first_name AS b_f, uw.username AS w_u, uw.first_name AS w_f "
            "FROM tournament_matches m "
            "LEFT JOIN users ua ON ua.user_id=m.a_id "
            "LEFT JOIN users ub ON ub.user_id=m.b_id "
            "LEFT JOIN users uw ON uw.user_id=m.winner_id "
            "WHERE m.tournament_id=? ORDER BY m.round, m.id",
            (int(tournament_id),)
        ).fetchall()
        lines=[f"🏆 <b>{title}</b>"]
        cur_round=None
        for r in rows:
            if cur_round!=int(r["round"]):
                cur_round=int(r["round"])
                lines.append(f"\n<b>Раунд {cur_round}</b>")
            def name(u,f,uid):
                if uid is None: return "—"
                n=(u or "").strip()
                if n: return "@"+n
                return (f or "Player").strip()
            a=name(r["a_u"], r["a_f"], r["a_id"])
            b=name(r["b_u"], r["b_f"], r["b_id"])
            if r["status"]=="BYE":
                w=name(r["w_u"], r["w_f"], r["winner_id"])
                lines.append(f"{a} vs {b} → ✅ {w} (bye)")
            elif r["status"]=="DONE":
                w=name(r["w_u"], r["w_f"], r["winner_id"])
                lines.append(f"{a} vs {b} → 🏁 {w}")
            elif r["status"]=="PLAYING":
                lines.append(f"{a} vs {b} → 🔥 грають")
            else:
                lines.append(f"{a} vs {b} → ⏳ очікує")
        return "\n".join(lines)
    finally:
        con.close()

def _award_streak_and_pack(con: sqlite3.Connection, user_id: int, game: str, day_key: str) -> tuple[int,int,str|None]:
    """Returns (new_streak, bonus_coins, item_id_or_none)."""
    suf = _game_suffix(game)
    streak_col = "tourn_streak" + suf
    day_col = "tourn_last_day" + suf
    u = con.execute(f"SELECT {streak_col} AS s, {day_col} AS d FROM users WHERE user_id=?", (int(user_id),)).fetchone()
    prev_day = str((u["d"] if u else "") or "")
    prev_streak = int((u["s"] if u else 0) or 0)
    # compute if consecutive day
    new_streak = 1
    try:
        if prev_day:
            py = date.fromisoformat(prev_day)
            cd = date.fromisoformat(day_key)
            if cd == py:
                new_streak = prev_streak  # same day, don't bump
            elif cd == (py + datetime.timedelta(days=1)):
                new_streak = prev_streak + 1
            else:
                new_streak = 1
        else:
            new_streak = 1
    except Exception:
        new_streak = 1
    con.execute(f"UPDATE users SET {streak_col}=?, {day_col}=? WHERE user_id=?", (int(new_streak), str(day_key), int(user_id)))

    bonus_coins = 0
    bonus_item = None
    # streak reward exactly at 3,6,9,... to keep it fun
    if new_streak > 0 and new_streak % 3 == 0:
        from app.config import TOURN_STREAK_BONUS_COINS
        bonus_coins = int(TOURN_STREAK_BONUS_COINS)
        con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (bonus_coins, int(user_id)))

        # bonus pack: random premium skin for that game (if not owned)
        try:
            from app.shop_items import items_for_game
            owned = {r["item_id"] for r in con.execute("SELECT item_id FROM inventory WHERE user_id=?", (int(user_id),)).fetchall()}
            candidates = [it for it in items_for_game(game) if it.get("kind")=="skin" and it.get("value")!="default"]
            candidates = [it for it in candidates if it["item_id"] not in owned]
            if candidates:
                it = random.choice(candidates)
                bonus_item = str(it["item_id"])
                con.execute("INSERT OR IGNORE INTO inventory(user_id, item_id, purchased_ts, active) VALUES(?,?,?,0)",
                            (int(user_id), bonus_item, float(time.time())))
        except Exception:
            bonus_item = None

    return new_streak, bonus_coins, bonus_item

def _finalize_tournament(con: sqlite3.Connection, tournament_id: int):
    t = con.execute("SELECT game, prize_pool, entry_fee, day_key FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
    if not t:
        return
    game = str(t["game"])
    pool = int(t["prize_pool"] or 0)
    day_key = str(t["day_key"] or "") or _today_key_uzh()

    # champion / runner-up from last match
    last = con.execute("SELECT * FROM tournament_matches WHERE tournament_id=? ORDER BY round DESC, id DESC LIMIT 1",
                       (int(tournament_id),)).fetchone()
    if not last or not last["winner_id"]:
        return
    champion = int(last["winner_id"])
    runner = None
    a = last["a_id"]; b = last["b_id"]
    if a and b:
        runner = int(b) if int(a)==champion else int(a)

    # payouts
    from app.config import TOURN_PAYOUT_WINNER_PCT, TOURN_PAYOUT_RUNNER_PCT, TOURN_POINTS_JOIN, TOURN_POINTS_WIN, TOURN_POINTS_CHAMPION_BONUS, TOURN_POINTS_RUNNER_BONUS
    from app.config import (
        TOURN_PAYOUT_WINNER_PCT, TOURN_PAYOUT_RUNNER_PCT,
        TOURN_POINTS_JOIN, TOURN_POINTS_WIN, TOURN_POINTS_CHAMPION_BONUS, TOURN_POINTS_RUNNER_BONUS,
        ARENA_FEE_PCT,
    )
    arena_fee = int(pool * int(ARENA_FEE_PCT) / 100) if pool>0 and int(ARENA_FEE_PCT)>0 else 0
    net_pool = max(0, int(pool) - int(arena_fee))
    if arena_fee > 0:
        try:
            db_add_arena_revenue(arena_fee, reason=f"tournament_fee:{tournament_id}")
        except Exception:
            pass
    win_amt = int(net_pool * int(TOURN_PAYOUT_WINNER_PCT) / 100) if net_pool>0 else 0
    run_amt = int(net_pool * int(TOURN_PAYOUT_RUNNER_PCT) / 100) if net_pool>0 else 0

    if win_amt>0:
        con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (win_amt, champion))
    if runner and run_amt>0:
        con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (run_amt, runner))

    # points: join + win per match, plus bonuses
    players = [int(r["user_id"]) for r in con.execute("SELECT user_id FROM tournament_players WHERE tournament_id=?", (int(tournament_id),)).fetchall()]
    for uid in players:
        _tourn_points_add(con, uid, game, int(TOURN_POINTS_JOIN))

    wins = con.execute(
        "SELECT winner_id, COUNT(*) AS c FROM tournament_matches WHERE tournament_id=? AND status IN ('DONE','BYE') AND winner_id IS NOT NULL GROUP BY winner_id",
        (int(tournament_id),)
    ).fetchall()
    for r in wins:
        _tourn_points_add(con, int(r["winner_id"]), game, int(TOURN_POINTS_WIN) * int(r["c"] or 0))

    _tourn_points_add(con, champion, game, int(TOURN_POINTS_CHAMPION_BONUS))
    if runner:
        _tourn_points_add(con, runner, game, int(TOURN_POINTS_RUNNER_BONUS))

    # streak + bonus pack per participant
    for uid in players:
        _award_streak_and_pack(con, uid, game, day_key)

    # mark pool distributed (keep 0)
    con.execute("UPDATE tournaments SET prize_pool=0 WHERE id=?", (int(tournament_id),))

def advance_round_if_ready(tournament_id: int) -> bool:
    """When all matches in current max round are DONE/BYE -> create next round. Returns True if progressed/finished."""
    init_db()
    con=_con()
    try:
        _ensure_tournament_columns(con)
        r=con.execute("SELECT MAX(round) AS r FROM tournament_matches WHERE tournament_id=?", (int(tournament_id),)).fetchone()
        if not r or r["r"] is None:
            return False
        max_round=int(r["r"])
        n=con.execute("SELECT COUNT(*) AS c FROM tournament_matches WHERE tournament_id=? AND round=? AND status IN ('PENDING','PLAYING')",
                      (int(tournament_id), max_round)).fetchone()
        if n and int(n["c"])>0:
            return False
        winners=[int(x["winner_id"]) for x in con.execute(
            "SELECT winner_id FROM tournament_matches WHERE tournament_id=? AND round=? AND winner_id IS NOT NULL ORDER BY id",
            (int(tournament_id), max_round)).fetchall()]
        if len(winners)<=1:
            con.execute("UPDATE tournaments SET status='DONE', ended_ts=? WHERE id=?", (float(time.time()), int(tournament_id)))
            _finalize_tournament(con, tournament_id)
            con.commit()
            return True
        pairs=[]
        for i in range(0,len(winners),2):
            a=winners[i]
            b=winners[i+1] if i+1<len(winners) else None
            pairs.append((a,b))
        now=float(time.time())
        next_round=max_round+1
        for a,b in pairs:
            if b is None:
                con.execute(
                    "INSERT INTO tournament_matches(tournament_id, round, a_id, b_id, winner_id, status, created_ts, ended_ts) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (int(tournament_id), next_round, int(a), None, int(a), "BYE", now, now)
                )
            else:
                con.execute(
                    "INSERT INTO tournament_matches(tournament_id, round, a_id, b_id, status, created_ts) VALUES(?,?,?,?,?,?)",
                    (int(tournament_id), next_round, int(a), int(b), "PENDING", now)
                )
        con.commit()
        return True
    finally:
        con.close()


def cancel_tournament(tournament_id: int):
    """Cancel and refund coins/🎫 tickets to joined players."""
    init_db()
    con=_con()
    try:
        _ensure_tournament_columns(con)
        _ensure_tournament_players_columns(con)
        _ensure_user_columns(con)

        con.execute("BEGIN IMMEDIATE")
        t = con.execute("SELECT status, entry_fee FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not t:
            con.execute("ROLLBACK"); return

        fee = int(t["entry_fee"] or 0)
        if fee > 0:
            rows = con.execute(
                "SELECT user_id, entry_kind FROM tournament_players WHERE tournament_id=?",
                (int(tournament_id),)
            ).fetchall()
            for r in rows:
                uid = int(r["user_id"])
                ek = str((r["entry_kind"] or "coins")).strip() or "coins"
                if ek == "ticket":
                    con.execute("UPDATE users SET tourn_tickets=tourn_tickets+1 WHERE user_id=?", (uid,))
                else:
                    con.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (fee, uid))

        con.execute(
            "UPDATE tournaments SET status='CANCELLED', ended_ts=?, prize_pool=0 WHERE id=?",
            (float(time.time()), int(tournament_id))
        )
        con.commit()
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
    finally:
        con.close()

def create_order(user_id: int, sku: str, amount_minor: int, currency: str = "UAH") -> str:
    """Create NEW order and return order_id."""
    init_db()
    order_id = _uuid.uuid4().hex
    con = _con()
    try:
        con.execute(
            "INSERT INTO orders(order_id,user_id,sku,amount_minor,currency,status,created_ts) VALUES(?,?,?,?,?,'NEW',?)",
            (order_id, int(user_id), str(sku), int(amount_minor), str(currency), float(time.time())),
        )
        con.commit()
        return str(order_id)
    finally:
        con.close()

def get_order(order_id: str):
    init_db()
    con = _con()
    try:
        row = con.execute(
            "SELECT order_id,user_id,sku,amount_minor,currency,status FROM orders WHERE order_id=?",
            (str(order_id),),
        ).fetchone()
        return row
    finally:
        con.close()

def mark_order_paid(order_id: str) -> bool:
    """Idempotent: returns True only on NEW->PAID transition."""
    init_db()
    con = _con()
    try:
        row = con.execute("SELECT status FROM orders WHERE order_id=?", (str(order_id),)).fetchone()
        if not row:
            return False
        if str(row["status"]) != "NEW":
            return False
        con.execute(
            "UPDATE orders SET status='PAID', paid_ts=? WHERE order_id=?",
            (float(time.time()), str(order_id)),
        )
        con.commit()
        return True
    finally:
        con.close()

# ================== PAYMENTS STATS / VIP / ARENA ==================

def db_revenue_summary(days: int = 7) -> dict:
    """Revenue from LiqPay orders (UAH)."""
    init_db()
    con=_con()
    try:
        since = float(time.time()) - float(days) * 86400.0
        row = con.execute(
            """SELECT COUNT(*) AS c, COALESCE(SUM(amount_minor),0) AS s
               FROM orders
               WHERE status='PAID' AND paid_ts IS NOT NULL AND paid_ts >= ?""",
            (since,)
        ).fetchone()
        cnt = int(row['c'] or 0)
        uah = float(row['s'] or 0) / 100.0
        return {'count': cnt, 'uah': uah}
    finally:
        con.close()


def db_orders_status_counts(hours: int = 24) -> dict[str, int]:
    """Order counts grouped by status for last N hours."""
    init_db()
    con = _con()
    try:
        since = float(time.time()) - float(hours) * 3600.0
        rows = con.execute(
            """SELECT status, COUNT(*) AS c
               FROM orders
               WHERE created_ts >= ?
               GROUP BY status""",
            (since,),
        ).fetchall()
        out: dict[str, int] = {"total": 0}
        for r in rows:
            st = str(r["status"] or "")
            c = int(r["c"] or 0)
            out[st] = c
            out["total"] += c
        return out
    finally:
        con.close()

def db_revenue_by_sku(days: int = 7) -> list[tuple[str,int,float]]:
    init_db()
    con=_con()
    try:
        since = float(time.time()) - float(days) * 86400.0
        rows = con.execute(
            """SELECT sku, COUNT(*) AS c, COALESCE(SUM(amount_minor),0) AS s
               FROM orders
               WHERE status='PAID' AND paid_ts IS NOT NULL AND paid_ts >= ?
               GROUP BY sku
               ORDER BY s DESC""",
            (since,)
        ).fetchall()
        out=[]
        for r in rows:
            out.append((str(r['sku']), int(r['c'] or 0), float(r['s'] or 0)/100.0))
        return out
    finally:
        con.close()

def _ensure_arena_revenue_table(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS arena_revenue(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               amount_coins INTEGER NOT NULL,
               reason TEXT,
               created_ts REAL NOT NULL
           );"""
    )

def db_add_arena_revenue(amount_coins: int, reason: str = '') -> None:
    init_db()
    con=_con()
    try:
        _ensure_arena_revenue_table(con)
        con.execute(
            "INSERT INTO arena_revenue(amount_coins, reason, created_ts) VALUES(?,?,?)",
            (int(amount_coins), str(reason or ''), float(time.time()))
        )
        con.commit()
    finally:
        con.close()

def db_arena_revenue(days: int = 7) -> int:
    init_db()
    con=_con()
    try:
        _ensure_arena_revenue_table(con)
        since = float(time.time()) - float(days) * 86400.0
        row = con.execute(
            "SELECT COALESCE(SUM(amount_coins),0) AS s FROM arena_revenue WHERE created_ts >= ?",
            (since,)
        ).fetchone()
        return int(row['s'] or 0)
    finally:
        con.close()

def db_list_vip_users() -> list[tuple[int,int,int]]:
    init_db()
    con=_con()
    try:
        now=float(time.time())
        rows = con.execute(
            """SELECT user_id,
                       COALESCE(vip_last_daily_ts,0) AS last_daily,
                       COALESCE(vip_last_weekly_pack_ts,0) AS last_weekly
               FROM users
               WHERE vip_until IS NOT NULL AND vip_until > ?""",
            (now,)
        ).fetchall()
        return [(int(r['user_id']), int(r['last_daily'] or 0), int(r['last_weekly'] or 0)) for r in rows]
    finally:
        con.close()

def grant_vip_weekly_pack(user_id: int) -> None:
    """Gives 1 random skin item from shop (if not owned). If all owned -> give coins instead."""
    from app.shop_items import SHOP_ITEMS
    owned = owned_item_ids(int(user_id))
    candidates = [it['item_id'] for it in SHOP_ITEMS if str(it.get('item_id','')).startswith('skin:') and it.get('item_id') not in owned]
    if not candidates:
        add_coins(int(user_id), 30)
        return
    import random
    iid = random.choice(candidates)
    add_item(int(user_id), iid)
    set_active_item(int(user_id), iid)



def vip_mark_daily_paid(user_id: int) -> None:
    init_db()
    con=_con()
    try:
        _ensure_vip_columns(con)
        con.execute("UPDATE users SET vip_last_daily_ts=? WHERE user_id=?", (float(time.time()), int(user_id)))
        con.commit()
    finally:
        con.close()

def vip_mark_weekly_pack(user_id: int) -> None:
    init_db()
    con=_con()
    try:
        _ensure_vip_columns(con)
        con.execute("UPDATE users SET vip_last_weekly_pack_ts=? WHERE user_id=?", (float(time.time()), int(user_id)))
        con.commit()
    finally:
        con.close()
