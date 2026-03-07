"""
app/web_app.py — Telegram Mini App (TMA) support

Runs an embedded aiohttp HTTP server that serves:
  GET /             → public/index.html (the Mini App frontend)
  GET /api/profile  → JSON user profile (validated via Telegram initData)
  GET /api/shop     → JSON shop items list
  POST /api/buy     → buy a shop item (validate initData, spend coins)

Telegram initData validation uses HMAC-SHA-256 with BOT_TOKEN.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
from pathlib import Path
from typing import Any

from aiohttp import web

from app.config import BOT_TOKEN
from app.shop_items import SHOP_ITEMS


# ---------------------------------------------------------------------------
# Telegram initData validation
# ---------------------------------------------------------------------------
def _validate_init_data(init_data_raw: str) -> dict | None:
    """Return parsed user dict from initData, or None if invalid."""
    try:
        params = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        check_hash = params.pop("hash", "")
        sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret_key, sorted_data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, check_hash):
            return None
        user_json = params.get("user", "{}")
        return json.loads(user_json)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


async def serve_index(request: web.Request):
    index = PUBLIC_DIR / "index.html"
    if not index.exists():
        raise web.HTTPNotFound(text="index.html not found")
    return web.FileResponse(index)


async def api_profile(request: web.Request):
    init_data = request.headers.get("X-Init-Data", "")
    tg_user = _validate_init_data(init_data)
    if not tg_user:
        raise web.HTTPUnauthorized(text="Bad initData")
    uid = int(tg_user.get("id", 0))

    from app.db import get_user, get_coins, is_vip
    u = get_user(uid) or {}
    data = {
        "user_id": uid,
        "username": u.get("username", ""),
        "first_name": u.get("first_name", ""),
        "coins": int(u.get("coins", 0) or 0),
        "rating_xo": int(u.get("rating", 1000) or 1000),
        "rating_ck": int(u.get("rating_ck", 1000) or 1000),
        "bp_level": int(u.get("bp_level", 1) or 1),
        "is_vip": is_vip(uid),
    }
    return web.json_response(data)


async def api_shop(request: web.Request):
    init_data = request.headers.get("X-Init-Data", "")
    tg_user = _validate_init_data(init_data)
    if not tg_user:
        raise web.HTTPUnauthorized(text="Bad initData")
    uid = int(tg_user.get("id", 0))

    from app.db import get_coins, has_item
    coins = get_coins(uid)
    items = []
    for it in SHOP_ITEMS:
        if it.get("kind") == "lootbox":
            continue    # lootboxes are in separate section in bot
        items.append({
            "item_id": it["item_id"],
            "title": it["title"],
            "desc": it.get("desc", ""),
            "price": it.get("price", 0),
            "kind": it.get("kind", "skin"),
            "game": it.get("game", "xo"),
            "owned": has_item(uid, it["item_id"]),
        })
    return web.json_response({"coins": coins, "items": items})


async def api_buy(request: web.Request):
    init_data = request.headers.get("X-Init-Data", "")
    tg_user = _validate_init_data(init_data)
    if not tg_user:
        raise web.HTTPUnauthorized(text="Bad initData")
    uid = int(tg_user.get("id", 0))

    body = await request.json()
    item_id = str(body.get("item_id", ""))

    from app.shop_items import get_item
    from app.db import try_spend_coins, has_item, add_item, get_coins

    it = get_item(item_id)
    if not it:
        raise web.HTTPBadRequest(text="Unknown item")
    if has_item(uid, item_id):
        return web.json_response({"ok": False, "error": "already_owned"})

    price = int(it.get("price", 0) or 0)
    ok = try_spend_coins(uid, price)
    if not ok:
        return web.json_response({"ok": False, "error": "not_enough_coins"})

    add_item(uid, item_id)
    return web.json_response({"ok": True, "coins": get_coins(uid)})


# ---------------------------------------------------------------------------
# App factory (called from main bot startup)
# ---------------------------------------------------------------------------
def make_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/",              serve_index)
    app.router.add_get("/api/profile",   api_profile)
    app.router.add_get("/api/shop",      api_shop)
    app.router.add_post("/api/buy",      api_buy)
    if PUBLIC_DIR.exists():
        app.router.add_static("/static/", path=str(PUBLIC_DIR / "static"), name="static")
    return app
