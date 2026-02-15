# app/main.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from app import config
from app.logging_setup import setup_logging

# Routers
from app.handlers_menu import router as menu_router
from app.payments_liqpay_router import router as liqpay_payments_router
from app.admin_commands import router as admin_router
from app.admin_stats_router import router as admin_stats_router
from app.checkers_game.router import router as checkers_router

# Background loops
from app.tournament_service import daily_tournament_loop, tournament_registrar_loop
from app.vip_service import vip_bonus_loop

# Webhook server (FastAPI)
import uvicorn
from app.liqpay_webhook import create_app as create_liqpay_app


def _load_env() -> None:
    """Load .env from project root reliably."""
    root_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=root_env)


async def _run_webhook_server(bot: Bot) -> None:
    """Run FastAPI server for LiqPay callbacks and /pay."""
    app = create_liqpay_app(bot=bot)
    host = (config.WEBHOOK_HOST or "0.0.0.0").strip() if hasattr(config, "WEBHOOK_HOST") else "0.0.0.0"
    port = int(getattr(config, "WEBHOOK_PORT", 8080) or 8080)

    uv_cfg = uvicorn.Config(app=app, host=host, port=port, log_level="info", reload=False)
    server = uvicorn.Server(uv_cfg)
    logging.getLogger("sm-arena").info("Webhook server: http://%s:%s", host, port)
    await server.serve()


async def main() -> None:
    _load_env()
    setup_logging()
    log = logging.getLogger("sm-arena")
    log.info("Starting SM Arena bot")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    @dp.error()
    async def on_dispatch_error(event: ErrorEvent):
        upd = event.update
        cb_data = getattr(getattr(upd, "callback_query", None), "data", None)
        msg_text = getattr(getattr(upd, "message", None), "text", None)
        log.exception(
            "Unhandled update error update_id=%s callback_data=%s message_text=%s",
            getattr(upd, "update_id", None),
            cb_data,
            msg_text,
            exc_info=event.exception,
        )
        return True

    dp.include_router(menu_router)
    dp.include_router(checkers_router)
    dp.include_router(liqpay_payments_router)
    dp.include_router(admin_router)
    dp.include_router(admin_stats_router)

    # background tasks
    asyncio.create_task(_run_webhook_server(bot))
    asyncio.create_task(daily_tournament_loop(bot))
    asyncio.create_task(tournament_registrar_loop(bot))
    asyncio.create_task(vip_bonus_loop(bot))

    log.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
