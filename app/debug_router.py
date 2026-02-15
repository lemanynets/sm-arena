from aiogram import Router
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def start(m):
    await m.answer("✅ Бот живий. Роутери ще не підключені правильно.")
