# app/storage.py
import json
import os
from typing import Any, Dict

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")


def _safe_int_dict(d: Dict[str, Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for k, v in (d or {}).items():
        try:
            out[int(k)] = int(v)
        except Exception:
            continue
    return out


def _safe_pair_stats(d: Dict[str, Any]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for k, v in (d or {}).items():
        try:
            if not isinstance(v, dict) or ":" not in k:
                continue
            a, b = k.split(":")
            int(a); int(b)
            out[k] = {
                "count": int(v.get("count", 0)),
                "window_start": float(v.get("window_start", 0.0)),
                "total": int(v.get("total", 0)),
            }
        except Exception:
            continue
    return out


def _safe_user_settings(d: Dict[str, Any]) -> Dict[int, dict]:
    out: Dict[int, dict] = {}
    for k, v in (d or {}).items():
        try:
            uid = int(k)
            if not isinstance(v, dict):
                continue
            out[uid] = {
                "skin": str(v.get("skin", "classic")),
                "vip_until": float(v.get("vip_until", 0.0) or 0.0),
            }
        except Exception:
            continue
    return out


def _safe_promo_codes(d: Dict[str, Any]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for code, v in (d or {}).items():
        try:
            if not isinstance(v, dict):
                continue
            out[str(code)] = {
                "type": str(v.get("type", "")),
                "value": str(v.get("value", "")),
                "uses_left": int(v.get("uses_left", 0)),
            }
        except Exception:
            continue
    return out


def load_state() -> dict:
    if not os.path.exists(DATA_PATH):
        return {
            "USER_RATING": {},
            "TOTAL_WINS": {},
            "TOTAL_GAMES": {},
            "USER_WINS": {},
            "USER_GAMES": {},
            "WEEK_START_TS": None,
            "PAIR_STATS": {},
            "BANNED_USERS": [],
            "SEASON_START_TS": None,
            "SEASON_ID": 1,
            "PRIZE_POOL": None,
            "USER_SETTINGS": {},
            "SPONSOR": {"text": "", "url": ""},
            "PROMO_CODES": {},
        }

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
    except Exception:
        raw = {}

    sponsor = raw.get("SPONSOR", {})
    if not isinstance(sponsor, dict):
        sponsor = {"text": "", "url": ""}

    return {
        "USER_RATING": _safe_int_dict(raw.get("USER_RATING", {})),
        "TOTAL_WINS": _safe_int_dict(raw.get("TOTAL_WINS", {})),
        "TOTAL_GAMES": _safe_int_dict(raw.get("TOTAL_GAMES", {})),
        "USER_WINS": _safe_int_dict(raw.get("USER_WINS", {})),
        "USER_GAMES": _safe_int_dict(raw.get("USER_GAMES", {})),
        "WEEK_START_TS": raw.get("WEEK_START_TS"),
        "PAIR_STATS": _safe_pair_stats(raw.get("PAIR_STATS", {})),
        "BANNED_USERS": list(raw.get("BANNED_USERS", [])) if isinstance(raw.get("BANNED_USERS", []), list) else [],
        "SEASON_START_TS": raw.get("SEASON_START_TS"),
        "SEASON_ID": int(raw.get("SEASON_ID", 1) or 1),
        "PRIZE_POOL": raw.get("PRIZE_POOL"),
        "USER_SETTINGS": _safe_user_settings(raw.get("USER_SETTINGS", {})),
        "SPONSOR": {"text": str(sponsor.get("text", "")), "url": str(sponsor.get("url", ""))},
        "PROMO_CODES": _safe_promo_codes(raw.get("PROMO_CODES", {})),
    }


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

    sponsor = state.get("SPONSOR", {}) or {}
    if not isinstance(sponsor, dict):
        sponsor = {"text": "", "url": ""}

    payload = {
        "USER_RATING": {str(k): int(v) for k, v in state.get("USER_RATING", {}).items()},
        "TOTAL_WINS": {str(k): int(v) for k, v in state.get("TOTAL_WINS", {}).items()},
        "TOTAL_GAMES": {str(k): int(v) for k, v in state.get("TOTAL_GAMES", {}).items()},
        "USER_WINS": {str(k): int(v) for k, v in state.get("USER_WINS", {}).items()},
        "USER_GAMES": {str(k): int(v) for k, v in state.get("USER_GAMES", {}).items()},
        "WEEK_START_TS": state.get("WEEK_START_TS"),
        "PAIR_STATS": state.get("PAIR_STATS", {}),
        "BANNED_USERS": list(state.get("BANNED_USERS", [])),
        "SEASON_START_TS": state.get("SEASON_START_TS"),
        "SEASON_ID": int(state.get("SEASON_ID", 1) or 1),
        "PRIZE_POOL": state.get("PRIZE_POOL"),
        "USER_SETTINGS": {str(k): v for k, v in state.get("USER_SETTINGS", {}).items()},
        "SPONSOR": {"text": str(sponsor.get("text", "")), "url": str(sponsor.get("url", ""))},
        "PROMO_CODES": state.get("PROMO_CODES", {}),
    }

    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)
