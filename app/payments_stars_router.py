import logging

from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import config, db
from app.i18n import detect_lang, t

router = Router()
log = logging.getLogger("sm-arena.payments.stars")

DEFAULT_STARS_PACKS = {
    "coins_50": (5000, 50),
    "coins_100": (10000, 100),
    "coins_250": (25000, 250),
    "coins_500": (50000, 500),
    "coins_1000": (100000, 1000),
}


def _lang(ev: Message | CallbackQuery | PreCheckoutQuery) -> str:
    return detect_lang(ev)


@router.callback_query(F.data == "sm:menu:stars")
async def cb_stars_menu(cb: CallbackQuery):
    lang = _lang(cb)
    coins = db.get_coins(cb.from_user.id)
    stars = coins // 100
    
    from app.keyboards import stars_menu_kb
    text = t(lang, "stars_balance").format(coins=coins, stars=stars)
    
    await cb.message.edit_text(
        f"<b>{t(lang, 'stars_title')}</b>\n\n{text}\n\n{t(lang, 'deposit_rate_info')}",
        parse_mode="HTML",
        reply_markup=stars_menu_kb(lang)
    )
    await cb.answer()


@router.callback_query(F.data == "sm:menu:stars_deposit")
async def cb_stars_deposit_select(cb: CallbackQuery):
    lang = _lang(cb)
    packs = getattr(config, "STARS_COIN_PACKS", DEFAULT_STARS_PACKS)
    amounts = sorted([v[1] for v in packs.values()])
    
    from app.keyboards import stars_deposit_kb
    await cb.message.edit_text(
        f"<b>{t(lang, 'deposit_stars')}</b>\n\n{t(lang, 'deposit_select_amount')}\n{t(lang, 'deposit_rate_info')}",
        parse_mode="HTML",
        reply_markup=stars_deposit_kb(lang, amounts)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("sm:stars:deposit:"))
async def cb_stars_deposit_invoice(cb: CallbackQuery, bot: Bot):
    lang = _lang(cb)
    stars_amount = int(cb.data.split(":")[-1])
    coins_amount = stars_amount * 100
    
    prices = [LabeledPrice(label=f"{coins_amount} Coins", amount=stars_amount)]
    
    await bot.send_invoice(
        chat_id=cb.message.chat.id,
        title=f"Deposit {coins_amount} Coins",
        description=f"Exchange {stars_amount} Stars for {coins_amount} internal coins in SM Arena.",
        payload=f"sm-stars-deposit-{stars_amount}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await cb.answer()


@router.callback_query(F.data == "sm:menu:stars_withdraw")
async def cb_stars_withdraw(cb: CallbackQuery):
    lang = _lang(cb)
    coins = db.get_coins(cb.from_user.id)
    
    if coins < 100:
        await cb.answer(t(lang, "withdrawal_error_balance"), show_alert=True)
        return
    
    stars = coins // 100
    db.add_coins(cb.from_user.id, -(stars * 100))
    db.create_withdrawal(cb.from_user.id, stars * 100, stars)
    
    await cb.message.edit_text(
        t(lang, "withdrawal_request_sent").format(coins=stars*100, stars=stars),
        reply_markup=InlineKeyboardBuilder().button(text=t(lang, "back"), callback_data="sm:menu:stars").as_markup()
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
    
    if payload.startswith("sm-stars-deposit-"):
        stars = int(payload.split("-")[-1])
        coins = stars * 100
        new_bal = db.add_coins(user_id, coins)
        await msg.answer(f"✅ {t(lang, 'pay_success_coins').format(coins=coins)}\nTotal balance: {new_bal} 🪙")
    
    # Legacy support
    elif payload.startswith("stars-coins-"):
        sku = payload.replace("stars-coins-", "")
        packs = getattr(config, "STARS_COIN_PACKS", DEFAULT_STARS_PACKS)
        if sku in packs:
            coins = packs[sku][0]
            db.add_coins(user_id, coins)
            await msg.answer(f"✅ Coins credited!")
    elif payload.startswith("stars-vip-"):
        days = int(payload.replace("stars-vip-", ""))
        db.add_vip_days(user_id, days)
        await msg.answer(f"✅ VIP status activated!")
