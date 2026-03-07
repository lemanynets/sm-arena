import html
import logging
import uuid
import json
import hmac
import hashlib
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.db import (
    add_coins, add_vip_days, get_lang, get_order, mark_order_paid,
    get_user, get_coins, has_item, try_spend_coins, add_item
)
from app.i18n import t
from app.liqpay_utils import b64decode_json, b64encode_json, liqpay_signature, verify_callback
from app.shop_items import SHOP_ITEMS, get_item

log = logging.getLogger("sm-arena.web")

# TMA Validation Logic
def _validate_init_data(init_data_raw: str) -> dict | None:
    if not init_data_raw:
        return None
    try:
        params = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        check_hash = params.pop("hash", "")
        sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret_key, sorted_data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, check_hash):
            return None
        user_json = params.get("user", "{}")
        return json.loads(user_json)
    except Exception:
        return None

def create_app(bot=None) -> FastAPI:
    app = FastAPI(title="SM Arena Web API")
    app.state.bot = bot

    # --- TMA Static Files ---
    public_dir = Path(__file__).resolve().parent.parent / "public"
    if (public_dir / "static").exists():
        app.mount("/static", StaticFiles(directory=str(public_dir / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def serve_tma_index():
        index_path = public_dir / "index.html"
        if not index_path.exists():
            return HTMLResponse("Mini App Frontend missing", status_code=404)
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

    # --- TMA API Endpoints ---
    @app.get("/api/profile")
    async def api_profile(x_init_data: str = Header(None)):
        tg_user = _validate_init_data(x_init_data)
        if not tg_user:
            raise HTTPException(status_code=401, detail="Invalid session")
        uid = int(tg_user.get("id", 0))
        u = get_user(uid) or {}
        from app.db import is_vip
        return {
            "user_id": uid,
            "username": u.get("username", ""),
            "first_name": u.get("first_name", ""),
            "coins": int(u.get("coins", 0) or 0),
            "rating_xo": int(u.get("rating", 1000) or 1000),
            "rating_ck": int(u.get("rating_ck", 1000) or 1000),
            "bp_level": int(u.get("bp_level", 1) or 1),
            "is_vip": is_vip(uid),
        }

    @app.get("/api/shop")
    async def api_shop(x_init_data: str = Header(None)):
        tg_user = _validate_init_data(x_init_data)
        if not tg_user:
            raise HTTPException(status_code=401, detail="Invalid session")
        uid = int(tg_user.get("id", 0))
        
        items = []
        for it in SHOP_ITEMS:
            if it.get("kind") == "lootbox": continue
            items.append({
                "item_id": it["item_id"],
                "title": it["title"],
                "desc": it.get("desc", ""),
                "price": it.get("price", 0),
                "kind": it.get("kind", "skin"),
                "game": it.get("game", "xo"),
                "owned": has_item(uid, it["item_id"]),
            })
        return {"coins": get_coins(uid), "items": items}

    @app.post("/api/buy")
    async def api_buy(request: Request, x_init_data: str = Header(None)):
        tg_user = _validate_init_data(x_init_data)
        if not tg_user:
            raise HTTPException(status_code=401, detail="Invalid session")
        uid = int(tg_user.get("id", 0))
        
        body = await request.json()
        item_id = str(body.get("item_id", ""))
        it = get_item(item_id)
        if not it:
            raise HTTPException(status_code=400, detail="Unknown item")
        if has_item(uid, item_id):
            return {"ok": False, "error": "already_owned"}
        
        if not try_spend_coins(uid, int(it.get("price", 0) or 0)):
            return {"ok": False, "error": "not_enough_coins"}
        
        add_item(uid, item_id)
        return {"ok": True, "coins": get_coins(uid)}

    # --- LiqPay Webhook Endpoints ---
    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/pay/{order_id}", response_class=HTMLResponse)
    async def pay_page(order_id: str):
        row = get_order(order_id)
        if not row: return HTMLResponse("Order not found", status_code=404)
        if str(row["status"]) != "NEW": return HTMLResponse("Processed", status_code=400)
        
        amount_uah = float(row["amount_minor"]) / 100.0
        params = {
            "public_key": config.LIQPAY_PUBLIC_KEY,
            "version": "3",
            "action": "pay",
            "amount": f"{amount_uah:.2f}",
            "currency": "UAH",
            "description": f"SM_Arena: {row['sku']}",
            "order_id": str(order_id),
            "server_url": f"{config.WEBHOOK_BASE_URL}/liqpay/callback",
            "result_url": f"{config.WEBHOOK_BASE_URL}/pay/success?order_id={order_id}",
        }
        data = b64encode_json(params)
        sig = liqpay_signature(config.LIQPAY_PRIVATE_KEY, data)
        return HTMLResponse(f"""<form id="f" method="POST" action="https://www.liqpay.ua/api/3/checkout"><input type="hidden" name="data" value="{html.escape(data)}"/><input type="hidden" name="signature" value="{html.escape(sig)}"/></form><script>document.getElementById('f').submit();</script>""")

    @app.get("/pay/success", response_class=HTMLResponse)
    async def pay_success(order_id: str = ""):
        return HTMLResponse("Payment accepted. Check bot in 1 min.")

    @app.post("/liqpay/callback")
    async def liqpay_callback(request: Request):
        try:
            form = await request.form()
            data_b64, sig = form.get("data"), form.get("signature")
            if not verify_callback(config.LIQPAY_PRIVATE_KEY, data_b64, sig): return PlainTextResponse("forbidden", 403)
            
            payload = b64decode_json(data_b64)
            order_id = payload.get("order_id")
            if payload.get("status") not in ("success", "sandbox"): return PlainTextResponse("ok")
            
            if mark_order_paid(str(order_id)):
                row = get_order(str(order_id))
                uid, sku = int(row["user_id"]), str(row["sku"])
                if sku.startswith("coins_"):
                    add_coins(uid, int(config.LIQPAY_COIN_PACKS.get(sku, (0,0))[0]))
                elif sku == config.LIQPAY_VIP_SKU:
                    add_vip_days(uid, int(config.LIQPAY_VIP_DAYS))
                
                bot = app.state.bot
                if bot:
                    lang = get_lang(uid) or "en"
                    t_key = "pay_success_coins" if sku.startswith("coins_") else "pay_success_vip"
                    await bot.send_message(uid, t(lang, t_key).format(days=config.LIQPAY_VIP_DAYS))
            return PlainTextResponse("ok")
        except Exception:
            log.exception("callback error")
            return PlainTextResponse("error", 500)

    return app
