import html
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from app import config
from app.db import add_coins, add_vip_days, get_lang, get_order, mark_order_paid
from app.i18n import t
from app.liqpay_utils import b64decode_json, b64encode_json, liqpay_signature, verify_callback

log = logging.getLogger("sm-arena.payments")


def create_app(bot=None) -> FastAPI:
    app = FastAPI()
    app.state.bot = bot

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/pay/{order_id}", response_class=HTMLResponse)
    async def pay_page(order_id: str):
        row = get_order(order_id)
        if not row:
            log.warning("pay page order not found order_id=%s", order_id)
            return HTMLResponse("<h3>Order not found</h3>", status_code=404)

        if str(row["status"]) != "NEW":
            log.info("pay page order already processed order_id=%s status=%s", order_id, row["status"])
            return HTMLResponse("<h3>Order already processed</h3>", status_code=400)

        if not config.LIQPAY_PUBLIC_KEY or not config.LIQPAY_PRIVATE_KEY:
            log.error("pay page missing LiqPay keys order_id=%s", order_id)
            return HTMLResponse("<h3>LiqPay keys are not configured</h3>", status_code=500)

        if not config.WEBHOOK_BASE_URL:
            log.error("pay page missing WEBHOOK_BASE_URL order_id=%s", order_id)
            return HTMLResponse("<h3>WEBHOOK_BASE_URL is not configured</h3>", status_code=500)

        amount_uah = float(row["amount_minor"]) / 100.0
        sku = str(row["sku"])

        params = {
            "public_key": config.LIQPAY_PUBLIC_KEY,
            "version": "3",
            "action": "pay",
            "amount": f"{amount_uah:.2f}",
            "currency": "UAH",
            "description": f"SM_Arena: {sku}",
            "order_id": str(order_id),
            "server_url": f"{config.WEBHOOK_BASE_URL}/liqpay/callback",
            "result_url": f"{config.WEBHOOK_BASE_URL}/pay/success?order_id={order_id}",
        }

        data = b64encode_json(params)
        signature = liqpay_signature(config.LIQPAY_PRIVATE_KEY, data)
        log.info(
            "pay page generated order_id=%s user_id=%s sku=%s amount_minor=%s",
            order_id,
            row["user_id"],
            sku,
            row["amount_minor"],
        )

        return HTMLResponse(
            f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Redirecting...</title></head>
<body>
  <p>Redirecting to LiqPay checkout...</p>
  <form id="f" method="POST" action="https://www.liqpay.ua/api/3/checkout">
    <input type="hidden" name="data" value="{html.escape(data)}"/>
    <input type="hidden" name="signature" value="{html.escape(signature)}"/>
  </form>
  <script>document.getElementById('f').submit();</script>
</body></html>"""
        )

    @app.get("/pay/success", response_class=HTMLResponse)
    async def pay_success(order_id: str = ""):
        return HTMLResponse("<h3>Payment accepted. If credit did not arrive in 1-2 minutes, contact admin.</h3>")

    @app.post("/liqpay/callback")
    async def liqpay_callback(request: Request):
        rid = uuid.uuid4().hex[:10]
        try:
            form = await request.form()
            data_b64 = form.get("data")
            sig = form.get("signature")

            if not data_b64 or not sig:
                log.warning("callback bad request rid=%s", rid)
                return PlainTextResponse("bad request", status_code=400)

            if not verify_callback(config.LIQPAY_PRIVATE_KEY, data_b64, sig):
                log.warning("callback bad signature rid=%s", rid)
                return PlainTextResponse("forbidden", status_code=403)

            payload = b64decode_json(data_b64)

            order_id = payload.get("order_id")
            status = str(payload.get("status") or "")
            amount = payload.get("amount")
            currency = str(payload.get("currency") or "")

            if not order_id:
                log.warning("callback missing order_id rid=%s payload=%s", rid, payload)
                return PlainTextResponse("no order_id", status_code=400)

            row = get_order(str(order_id))
            if not row:
                log.warning("callback order not found rid=%s order_id=%s", rid, order_id)
                return PlainTextResponse("not found", status_code=404)

            # Non-success statuses are expected from LiqPay lifecycle; ignore without failing callback.
            if status not in ("success", "sandbox"):
                log.info(
                    "callback ignored status rid=%s order_id=%s status=%s",
                    rid,
                    order_id,
                    status,
                )
                return PlainTextResponse("ok", status_code=200)

            if amount not in (None, ""):
                try:
                    callback_minor = int(round(float(amount) * 100))
                    if callback_minor != int(row["amount_minor"]):
                        log.warning(
                            "callback amount mismatch rid=%s order_id=%s callback_minor=%s order_minor=%s",
                            rid,
                            order_id,
                            callback_minor,
                            row["amount_minor"],
                        )
                except Exception:
                    log.warning("callback amount parse failed rid=%s order_id=%s amount=%s", rid, order_id, amount)

            if currency and currency.upper() != str(row["currency"]).upper():
                log.warning(
                    "callback currency mismatch rid=%s order_id=%s callback_currency=%s order_currency=%s",
                    rid,
                    order_id,
                    currency,
                    row["currency"],
                )

            if not mark_order_paid(str(order_id)):
                log.info("callback duplicate order rid=%s order_id=%s", rid, order_id)
                return PlainTextResponse("ok", status_code=200)

            user_id = int(row["user_id"])
            sku = str(row["sku"])

            if sku.startswith("coins_"):
                coins, _uah = config.LIQPAY_COIN_PACKS.get(sku, (0, 0))
                if coins:
                    add_coins(user_id, int(coins))
                    log.info(
                        "callback paid coins rid=%s order_id=%s user_id=%s sku=%s coins=%s",
                        rid,
                        order_id,
                        user_id,
                        sku,
                        coins,
                    )
                else:
                    log.warning(
                        "callback unknown coin sku rid=%s order_id=%s user_id=%s sku=%s",
                        rid,
                        order_id,
                        user_id,
                        sku,
                    )
            elif sku == config.LIQPAY_VIP_SKU:
                add_vip_days(user_id, int(config.LIQPAY_VIP_DAYS))
                log.info(
                    "callback paid vip rid=%s order_id=%s user_id=%s sku=%s days=%s",
                    rid,
                    order_id,
                    user_id,
                    sku,
                    config.LIQPAY_VIP_DAYS,
                )
            else:
                log.warning(
                    "callback unknown sku rid=%s order_id=%s user_id=%s sku=%s",
                    rid,
                    order_id,
                    user_id,
                    sku,
                )

            bot = getattr(app.state, "bot", None)
            if bot:
                try:
                    lang = get_lang(user_id) or "en"
                    if sku.startswith("coins_"):
                        await bot.send_message(user_id, t(lang, "pay_success_coins"))
                    elif sku == config.LIQPAY_VIP_SKU:
                        await bot.send_message(
                            user_id,
                            t(lang, "pay_success_vip").format(days=config.LIQPAY_VIP_DAYS),
                        )
                except Exception:
                    log.warning("callback user notify failed rid=%s order_id=%s user_id=%s", rid, order_id, user_id)

            return PlainTextResponse("ok", status_code=200)
        except Exception:
            log.exception("callback internal error rid=%s", rid)
            return PlainTextResponse("internal error", status_code=500)

    return app
