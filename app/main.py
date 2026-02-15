# app/main.py
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
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
    log = logging.getLogger("sm-arena")

    while True:
        try:
            uv_cfg = uvicorn.Config(app=app, host=host, port=port, log_level="info", reload=False)
            server = uvicorn.Server(uv_cfg)
            log.info("Webhook server: http://%s:%s", host, port)
            await server.serve()
            log.warning("Webhook server stopped; restarting in 3s")
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            raise
        except BaseException:
            log.exception("Webhook server crashed; restarting in 5s")
            await asyncio.sleep(5)


async def _polling_loop(dp: Dispatcher, bot: Bot, log: logging.Logger) -> None:
    while True:
        try:
            log.info("Starting polling...")
            await dp.start_polling(bot)
            log.warning("Polling stopped; restarting in 3s")
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Polling crashed; retrying in 5s")
            await asyncio.sleep(5)


async def main() -> None:
    _load_env()
    setup_logging()
    log = logging.getLogger("sm-arena")
    log.info("Starting SM Arena bot")
    log.info(
        "Config flags: BOT_TOKEN=%s LIQPAY_PUBLIC_KEY=%s LIQPAY_PRIVATE_KEY=%s WEBHOOK_BASE_URL=%s WEBHOOK_PORT=%s",
        "set" if bool(getattr(config, "BOT_TOKEN", "").strip()) else "missing",
        "set" if bool(getattr(config, "LIQPAY_PUBLIC_KEY", "").strip()) else "missing",
        "set" if bool(getattr(config, "LIQPAY_PRIVATE_KEY", "").strip()) else "missing",
        "set" if bool(getattr(config, "WEBHOOK_BASE_URL", "").strip()) else "missing",
        getattr(config, "WEBHOOK_PORT", ""),
    )

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
    polling_task = asyncio.create_task(_polling_loop(dp, bot, log))
    asyncio.create_task(daily_tournament_loop(bot))
    asyncio.create_task(tournament_registrar_loop(bot))
    asyncio.create_task(vip_bonus_loop(bot))

    try:
        await _run_webhook_server(bot)
    finally:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task


if __name__ == "__main__":
    asyncio.run(main())
