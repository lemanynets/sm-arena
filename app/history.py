# app/history.py
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "sm_arena.db"

def _con():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    return con

def init_history():
    con = _con()
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS week_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            prize_pool INTEGER NOT NULL,
            top_json TEXT NOT NULL
        )
        """)
        con.commit()
    finally:
        con.close()

def save_week_snapshot(week_start_str: str, prize_pool: int, top_rows: list[dict]):
    init_history()
    con = _con()
    try:
        ts = int(datetime.now(timezone.utc).timestamp())
        con.execute(
            "INSERT INTO week_history (ts, week_start, prize_pool, top_json) VALUES (?, ?, ?, ?)",
            (ts, week_start_str, int(prize_pool), json.dumps(top_rows, ensure_ascii=False))
        )
        con.commit()
    finally:
        con.close()

def load_week_history(limit: int = 10) -> list[dict]:
    init_history()
    con = _con()
    try:
        cur = con.execute(
            "SELECT week_start, prize_pool, top_json, ts FROM week_history ORDER BY id DESC LIMIT ?",
            (int(limit),)
        )
        out = []
        for week_start, pool, top_json, ts in cur.fetchall():
            try:
                top = json.loads(top_json)
            except Exception:
                top = []
            out.append({"week_start": week_start, "pool": int(pool), "top": top, "ts": int(ts)})
        return out
    finally:
        con.close()
