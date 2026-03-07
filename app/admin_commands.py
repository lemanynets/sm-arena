# app/admin_commands.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import asyncio

from app.config import ADMIN_IDS
from app.db import (
    init_db,
    ban_user,
    unban_user,
    set_sponsor,
    get_sponsor,
    add_prize_pool,
    set_prize_pool,
    get_prize_pool,
    set_chat,
    get_chat,
    set_news,
    get_news,
    list_all_user_ids,
    add_coins,
    get_coins,
)

router = Router()


def is_admin(uid: int) -> bool:
    try:
        return int(uid) in {int(x) for x in ADMIN_IDS}
    except Exception:
        return False


@router.message(Command("ban"))
async def cmd_ban(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Usage: /ban [user_id]")
        return

    try:
        uid = int(parts[1])
    except Exception:
        await m.answer("Bad user_id")
        return

    init_db()
    ban_user(uid)
    await m.answer(f"✅ Banned: {uid}")

@router.message(Command("givecoins"))
async def cmd_givecoins(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    parts = (m.text or "").split()
    if len(parts) < 3:
        await m.answer("Usage: /givecoins [user_id] [amount]")
        return

    try:
        uid = int(parts[1])
        amount = int(parts[2])
    except Exception:
        await m.answer("Bad user_id or amount")
        return

    init_db()
    add_coins(uid, amount)
    new_bal = get_coins(uid)
    await m.answer(f"✅ Added {amount} coins to {uid}. New balance: {new_bal}")


@router.message(Command("unban"))
async def cmd_unban(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Usage: /unban [user_id]")
        return

    try:
        uid = int(parts[1])
    except Exception:
        await m.answer("Bad user_id")
        return

    init_db()
    unban_user(uid)
    await m.answer(f"✅ Unbanned: {uid}")


@router.message(Command("sponsor"))
async def cmd_sponsor(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    # /sponsor TEXT | URL
    raw = (m.text or "").replace("/sponsor", "", 1).strip()

    init_db()
    if not raw:
        cur = get_sponsor()
        await m.answer(
            "Current sponsor:\n" + (cur.get("text", "") or "") + "\n" + (cur.get("url", "") or "")
        )
        return

    if "|" not in raw:
        await m.answer("Usage: /sponsor Text here | https://example.com")
        return

    text, url = [x.strip() for x in raw.split("|", 1)]
    if not text or not url:
        await m.answer("Usage: /sponsor Text here | https://example.com")
        return

    set_sponsor(text, url)
    await m.answer("✅ Sponsor updated")


@router.message(Command("pool"))
async def cmd_pool(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    parts = (m.text or "").split()

    init_db()
    if len(parts) < 2:
        cur = get_prize_pool()
        await m.answer(
            "Usage: /pool +100 | /pool -50 | /pool 1000\n" f"Current pool: {cur}"
        )
        return

    arg = parts[1].strip()

    try:
        if arg.startswith(("+", "-")):
            new_val = add_prize_pool(int(arg))
        else:
            new_val = max(0, int(arg))
            set_prize_pool(new_val)
    except Exception:
        await m.answer("Bad number")
        return

    await m.answer(f"✅ PRIZE_POOL = {new_val}")


@router.message(Command("chat"))
async def cmd_chat(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    # /chat Title | URL
    raw = (m.text or "").replace("/chat", "", 1).strip()
    init_db()

    if not raw:
        cur = get_chat()
        await m.answer(
            "Current chat:\n" + (cur.get("title", "") or "") + "\n" + (cur.get("url", "") or "")
        )
        return

    if "|" not in raw:
        await m.answer("Usage: /chat Title | https://t.me/your_chat")
        return

    title, url = [x.strip() for x in raw.split("|", 1)]
    if not url.startswith("http"):
        await m.answer("Bad URL")
        return

    set_chat(title or "Чатик", url)
    await m.answer("✅ Chat link updated")


@router.message(Command("news"))
async def cmd_news(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    # /news Title | URL
    raw = (m.text or "").replace("/news", "", 1).strip()
    init_db()

    if not raw:
        cur = get_news()
        await m.answer(
            "Current news:\n" + (cur.get("title", "") or "") + "\n" + (cur.get("url", "") or "")
        )
        return

    if "|" not in raw:
        await m.answer("Usage: /news Title | https://t.me/your_news")
        return

    title, url = [x.strip() for x in raw.split("|", 1)]
    if not url.startswith("http"):
        await m.answer("Bad URL")
        return

    set_news(title or "Новини", url)
    await m.answer("✅ News link updated")


@router.message(Command("links"))
async def cmd_links(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    init_db()
    chat = get_chat()
    news = get_news()
    await m.answer(
        "🔗 Links\n\n"
        f"📰 {news.get('title','')}: {news.get('url','')}\n"
        f"💬 {chat.get('title','')}: {chat.get('url','')}"
    )


@router.message(Command("givecoins"))
async def cmd_givecoins(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    init_db()
    parts = (m.text or "").split()
    target_id = None
    amount = None

    # /givecoins [user_id] [amount]
    if len(parts) >= 3:
        try:
            target_id = int(parts[1])
            amount = int(parts[2])
        except Exception:
            await m.answer("Usage: /givecoins [user_id] [amount]  OR reply: /givecoins [amount]")
            return

    # reply: /givecoins [amount]
    elif len(parts) >= 2 and m.reply_to_message and m.reply_to_message.from_user:
        try:
            target_id = int(m.reply_to_message.from_user.id)
            amount = int(parts[1])
        except Exception:
            await m.answer("Usage: /givecoins [user_id] [amount]  OR reply: /givecoins [amount]")
            return
    else:
        await m.answer("Usage: /givecoins [user_id] [amount]  OR reply: /givecoins [amount]")
        return

    add_coins(target_id, amount)
    await m.answer(f"✅ {target_id}: +{amount}🪙 (now {get_coins(target_id)}🪙)")


@router.message(Command("broadcast"))
async def cmd_broadcast(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    source = m.reply_to_message if m.reply_to_message else None
    text = (m.text or "").replace("/broadcast", "", 1).strip()

    if not source and not text:
        await m.answer("📢 <b>Як користуватися розсилкою:</b>\n\n"
                       "1. Відправ текст: <code>/broadcast Привіт усім!</code>\n"
                       "2. АБО перешли сюди будь-яке повідомлення (фото, відео, пост) і напиши у відповідь <code>/broadcast</code>\n\n"
                       "<i>Підтримується HTML розмітка.</i>", parse_mode="HTML")
        return

    init_db()
    uids = list_all_user_ids()
    ok = 0
    fail = 0

    progress = await m.answer(f"⏳ Починаю розсилку на {len(uids)} користувачів...")

    for i, uid in enumerate(uids):
        try:
            if source:
                await source.copy_to(chat_id=uid)
            else:
                await m.bot.send_message(uid, text, parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        
        if (i + 1) % 30 == 0:
            try:
                await progress.edit_text(f"⏳ Розсилка... {i+1}/{len(uids)}\n✅ Ок: {ok}\n❌ Помилок: {fail}")
            except Exception: pass
        
        await asyncio.sleep(0.04)

    await progress.edit_text(f"📣 <b>Розсилка завершена!</b>\n\n✅ Отримали: {ok}\n❌ Не отримали: {fail}\n👥 Всього: {len(uids)}", parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(m: Message):
    if not m.from_user or not is_admin(m.from_user.id):
        return

    init_db()
    from app.db import _con
    import time

    con = _con()
    try:
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 7 * 86400

        total_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        # Recent active = users with any coins change or registered in last 7d
        active_week = con.execute(
            "SELECT COUNT(*) FROM users WHERE rowid > (SELECT MAX(rowid)-1000 FROM users)"
        ).fetchone()[0]

        total_coins = con.execute("SELECT SUM(coins) FROM users").fetchone()[0] or 0
        vip_count = con.execute(
            "SELECT COUNT(*) FROM users WHERE vip_until > ?", (now,)
        ).fetchone()[0]

        top5 = con.execute(
            "SELECT first_name, username, coins FROM users ORDER BY coins DESC LIMIT 5"
        ).fetchall()

        top5_rating = con.execute(
            "SELECT first_name, username, rating FROM users ORDER BY rating DESC LIMIT 5"
        ).fetchall()

        orders_total = 0
        try:
            orders_total = con.execute(
                "SELECT COUNT(*) FROM orders WHERE status='PAID'"
            ).fetchone()[0]
        except Exception:
            pass

    finally:
        con.close()

    top5_txt = "\n".join(
        f"  {i+1}. {r['first_name'] or r['username'] or '?'}: {r['coins']}🪙"
        for i, r in enumerate(top5)
    )
    top5_r_txt = "\n".join(
        f"  {i+1}. {r['first_name'] or r['username'] or '?'}: {r['rating']} ELO"
        for i, r in enumerate(top5_rating)
    )

    text = (
        f"📊 <b>SM Arena — Статистика</b>\n\n"
        f"👥 Всього гравців: <b>{total_users}</b>\n"
        f"🔥 Активних (тиждень): <b>{active_week}</b>\n"
        f"💎 VIP підписок: <b>{vip_count}</b>\n"
        f"🪙 Монет в економіці: <b>{total_coins:,}</b>\n"
        f"💳 Оплачених замовлень: <b>{orders_total}</b>\n\n"
        f"<b>💰 Топ-5 за монетами:</b>\n{top5_txt}\n\n"
        f"<b>🏆 Топ-5 за рейтингом:</b>\n{top5_r_txt}"
    )
    await m.answer(text, parse_mode="HTML")
