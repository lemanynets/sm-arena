# app/payments_liqpay_router.py
import logging
import os

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import config, db
from app.i18n import detect_lang, t

router = Router()
log = logging.getLogger("sm-arena.payments")


def uah_to_minor(uah: int) -> int:
    return int(uah) * 100


def _lang(ev: Message | CallbackQuery) -> str:
    return detect_lang(ev)


def _base_url() -> str:
    base = (os.getenv("WEBHOOK_BASE_URL") or getattr(config, "WEBHOOK_BASE_URL", "") or "").strip()
    if base.endswith("/"):
        base = base[:-1]
    return base


def _pay_url(order_id: str) -> str:
    base = _base_url()
    return f"{base}/pay/{order_id}" if base else ""


@router.message(Command("pay"))
async def cmd_pay(msg: Message):
    lang = _lang(msg)
    if not _base_url():
        await msg.answer(
            f"{t(lang, 'pay_not_configured')}\n\n"
            f"{t(lang, 'pay_need_webhook_line')}:\n"
            "WEBHOOK_BASE_URL=https://your-domain-or-ngrok\n\n"
            f"{t(lang, 'pay_restart_bot')}"
        )
        return
    await msg.answer(t(lang, "pay_enabled"))


@router.message(Command("paydiag"))
async def cmd_paydiag(msg: Message):
    if int(msg.from_user.id) not in set(getattr(config, "ADMIN_IDS", [])):
        return

    has_public = bool(getattr(config, "LIQPAY_PUBLIC_KEY", "").strip())
    has_private = bool(getattr(config, "LIQPAY_PRIVATE_KEY", "").strip())
    has_webhook = bool(_base_url())
    stats = db.db_orders_status_counts(hours=24)
    revenue = db.db_revenue_summary(days=1)

    await msg.answer(
        "Pay diagnostics (24h)\n"
        f"- LIQPAY_PUBLIC_KEY: {'set' if has_public else 'missing'}\n"
        f"- LIQPAY_PRIVATE_KEY: {'set' if has_private else 'missing'}\n"
        f"- WEBHOOK_BASE_URL: {'set' if has_webhook else 'missing'}\n"
        f"- Orders total: {stats.get('total', 0)}\n"
        f"- Orders NEW: {stats.get('NEW', 0)}\n"
        f"- Orders PAID: {stats.get('PAID', 0)}\n"
        f"- Revenue 24h: {revenue.get('uah', 0.0):.2f} UAH ({revenue.get('count', 0)} paid)"
    )


@router.message(Command("coins"))
@router.message(F.text.in_({"Coins", "🪙 Монети"}))
async def coins_menu(msg: Message):
    lang = _lang(msg)
    packs = getattr(
        config,
        "LIQPAY_COIN_PACKS",
        {
            "coins_50": (50, 19),
            "coins_200": (200, 69),
            "coins_500": (500, 159),
            "coins_1200": (1200, 249),
        },
    )
    base = _base_url()

    kb = InlineKeyboardBuilder()
    for sku, (coins, price_uah) in packs.items():
        kb.button(text=f"{coins} coins - {price_uah} UAH", callback_data=f"liqpay:coins:{sku}")
    kb.adjust(1)

    text = t(lang, "pay_choose_pack")
    if not base:
        text += f"\n\n{t(lang, 'pay_webhook_warning')}"
    await msg.answer(text, reply_markup=kb.as_markup())


@router.message(Command("vip"))
@router.message(F.text.in_({"VIP", "⭐ VIP"}))
async def vip_menu(msg: Message):
    lang = _lang(msg)
    sku = getattr(config, "LIQPAY_VIP_SKU", "vip_30d")
    price_uah = int(getattr(config, "LIQPAY_VIP_PRICE_UAH", 79))
    days = int(getattr(config, "LIQPAY_VIP_DAYS", 30))

    vip_daily = int(getattr(config, "VIP_DAILY_COINS", 10))
    vip_discount = int(getattr(config, "VIP_SHOP_DISCOUNT_PCT", 10))

    base = _base_url()

    kb = InlineKeyboardBuilder()
    kb.button(text=f"Buy VIP {days} days - {price_uah} UAH", callback_data=f"liqpay:vip:{sku}")
    kb.adjust(1)

    text = (
        f"{t(lang, 'pay_vip_title').format(days=days)}\n\n"
        f"- +{vip_daily} coins daily\n"
        "- +1 weekly pack\n"
        f"- {vip_discount}% shop discount\n\n"
        f"{t(lang, 'pay_vip_price').format(price=price_uah)}"
    )
    if not base:
        text += f"\n\n{t(lang, 'pay_webhook_warning')}"
    await msg.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("liqpay:coins:"))
async def cb_pay_coins(cb: CallbackQuery):
    lang = _lang(cb)
    packs = getattr(
        config,
        "LIQPAY_COIN_PACKS",
        {
            "coins_50": (50, 19),
            "coins_200": (200, 69),
            "coins_500": (500, 159),
            "coins_1200": (1200, 249),
        },
    )
    if not _base_url():
        await cb.answer(t(lang, "pay_missing_webhook"), show_alert=True)
        return

    sku = cb.data.split(":")[-1]
    if sku not in packs:
        log.warning("coins pack not found user_id=%s sku=%s", cb.from_user.id, sku)
        await cb.answer(t(lang, "pay_unknown_pack"), show_alert=True)
        return

    coins, price_uah = packs[sku]
    order_id = db.create_order(cb.from_user.id, sku, uah_to_minor(price_uah), "UAH")
    log.info(
        "order created kind=coins order_id=%s user_id=%s sku=%s amount_uah=%s",
        order_id,
        cb.from_user.id,
        sku,
        price_uah,
    )
    url = _pay_url(order_id)

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "pay_btn"), url=url)
    kb.adjust(1)

    await cb.message.answer(
        f"{t(lang, 'pay_pack_summary').format(coins=coins, price=price_uah)}\n"
        f"{t(lang, 'pay_press_button')}",
        reply_markup=kb.as_markup(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("liqpay:vip:"))
async def cb_pay_vip(cb: CallbackQuery):
    lang = _lang(cb)
    if not _base_url():
        await cb.answer(t(lang, "pay_missing_webhook"), show_alert=True)
        return

    sku = getattr(config, "LIQPAY_VIP_SKU", "vip_30d")
    price_uah = int(getattr(config, "LIQPAY_VIP_PRICE_UAH", 79))
    days = int(getattr(config, "LIQPAY_VIP_DAYS", 30))

    order_id = db.create_order(cb.from_user.id, sku, uah_to_minor(price_uah), "UAH")
    log.info(
        "order created kind=vip order_id=%s user_id=%s sku=%s amount_uah=%s",
        order_id,
        cb.from_user.id,
        sku,
        price_uah,
    )
    url = _pay_url(order_id)

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "pay_btn"), url=url)
    kb.adjust(1)

    await cb.message.answer(
        f"{t(lang, 'pay_vip_title').format(days=days)}\n"
        f"{t(lang, 'pay_vip_price').format(price=price_uah)}\n"
        f"{t(lang, 'pay_press_button')}",
        reply_markup=kb.as_markup(),
    )
    await cb.answer()
