# app/admin_stats_router.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app import db, config

router = Router()

def _admins() -> set[int]:
    admins = getattr(config, "ADMIN_IDS", [])
    try:
        return {int(x) for x in admins}
    except Exception:
        return set()

@router.message(Command("stats"))
async def stats(msg: Message):
    if msg.from_user.id not in _admins():
        return await msg.answer("⛔ Доступ заборонено.")

    today = db.db_revenue_summary(days=1)
    week = db.db_revenue_summary(days=7)
    month = db.db_revenue_summary(days=30)

    by_sku_7 = db.db_revenue_by_sku(days=7)
    arena_7 = db.db_arena_revenue(days=7)

    text = (
        "📊 Доходи (PAID)\n\n"
        f"Сьогодні: {today['count']} оплат, {today['uah']:.2f} грн\n"
        f"7 днів: {week['count']} оплат, {week['uah']:.2f} грн\n"
        f"30 днів: {month['count']} оплат, {month['uah']:.2f} грн\n\n"
        "ТОП SKU (7 днів):\n"
    )
    for sku, cnt, uah in by_sku_7[:10]:
        text += f"• {sku}: {cnt} оплат, {uah:.2f} грн\n"

    text += f"\n🏆 Комісія арени (7 днів): {arena_7:.2f} грн"
    await msg.answer(text)
