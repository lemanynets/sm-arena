import logging

from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import config, db
from app.i18n import detect_lang, t

router = Router()
log = logging.getLogger("sm-arena.payments.stars")

DEFAULT_STARS_PACKS = {
    "coins_50": (50, 25),
    "coins_200": (200, 100),
    "coins_500": (500, 250),
    "coins_1200": (1200, 600),
}


def _lang(ev: Message | CallbackQuery | PreCheckoutQuery) -> str:
    return detect_lang(ev)


@router.callback_query(F.data.startswith("stars:coins:"))
async def cb_pay_stars_coins(cb: CallbackQuery, bot: Bot):
    lang = _lang(cb)
    packs = getattr(config, "STARS_COIN_PACKS", DEFAULT_STARS_PACKS)
    sku = cb.data.split(":")[-1]

    if sku not in packs:
        await cb.answer(t(lang, "pay_unknown_pack"), show_alert=True)
        return

    coins, price_stars = packs[sku]

    prices = [LabeledPrice(label=f"{coins} Coins", amount=price_stars)]

    await bot.send_invoice(
        chat_id=cb.message.chat.id,
        title=f"Buy {coins} Coins",
        description=f"Package of {coins} internal coins for SM Arena.",
        payload=f"stars-coins-{sku}",
        provider_token="",  # Must be empty for Telegram Stars
        currency="XTR",
        prices=prices,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("stars:vip:"))
async def cb_pay_stars_vip(cb: CallbackQuery, bot: Bot):
    parts = cb.data.split(":")
    if len(parts) >= 4:
        days = int(parts[2])
        stars = int(parts[3])
    else:
        await cb.answer("Error parsing VIP pack", show_alert=True)
        return

    prices = [LabeledPrice(label=f"VIP {days} days", amount=stars)]

    await bot.send_invoice(
        chat_id=cb.message.chat.id,
        title=f"VIP Access ({days} days)",
        description=f"Premium VIP status for {days} days in SM Arena.",
        payload=f"stars-vip-{days}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await cb.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(msg: Message):
    lang = _lang(msg)
    payload = msg.successful_payment.invoice_payload
    user_id = msg.from_user.id
    amount = msg.successful_payment.total_amount

    log.info("Successful payment: user_id=%s payload=%s amount=%s XTR", user_id, payload, amount)

    if payload.startswith("stars-coins-"):
        sku = payload.replace("stars-coins-", "")
        packs = getattr(config, "STARS_COIN_PACKS", DEFAULT_STARS_PACKS)
        if sku in packs:
            coins = packs[sku][0]
            new_bal = db.add_coins(user_id, coins)
            await msg.answer(f"✅ {t(lang, 'pay_success_coins').format(coins=coins)}\nПоточний баланс: {new_bal} 🪙")
        else:
            await msg.answer("Pack not found after payment. Contact admin.")

    elif payload.startswith("stars-vip-"):
        days = int(payload.replace("stars-vip-", ""))
        db.add_vip_days(user_id, days)
        await msg.answer(f"✅ VIP статус активовано на {days} днів!")
