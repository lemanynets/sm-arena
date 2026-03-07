"""
app/push_service.py — Background push notification service

Sends reminders to players:
- Daily bonus reminder at 18:00 (for those who haven't claimed it)
- Pre-tournament reminder 5 minutes before start
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger("sm-arena.push")

# Remember who we've already notified today (in-memory — resets on restart)
_notified_daily: set[int] = set()
_notified_tourn: set[int] = set()
_last_tourn_notify_day: str = ""


async def push_daily_bonus_remind(bot) -> None:
    """Send daily bonus reminder to players who haven't claimed it today."""
    from app.db import list_all_user_ids, get_user
    try:
        uids = list_all_user_ids()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sent = 0
        for uid in uids:
            if uid in _notified_daily:
                continue
            try:
                u = get_user(uid) or {}
                last_ts = u.get("vip_last_daily_ts") or 0
                last_date = datetime.fromtimestamp(float(last_ts), tz=timezone.utc).strftime("%Y-%m-%d") if last_ts else ""
                if last_date != today:
                    await bot.send_message(
                        uid,
                        "🎁 <b>Твій щоденний бонус чекає!</b>\n"
                        "Відкрий бота та збери свої монети. 🪙",
                        parse_mode="HTML",
                    )
                    _notified_daily.add(uid)
                    sent += 1
                    await asyncio.sleep(0.05)
            except Exception:
                pass
        if sent:
            log.info("push_daily_bonus: notified %d users", sent)
    except Exception:
        log.exception("push_daily_bonus error")


async def push_tournament_remind(bot, tournament_id: str, minutes_left: int) -> None:
    """Notify all tournament registrants about upcoming start."""
    global _notified_tourn, _last_tourn_notify_day
    from app.db import get_tournament_registrants
    try:
        registrants = get_tournament_registrants(tournament_id) or []
        sent = 0
        for uid in registrants:
            if uid in _notified_tourn:
                continue
            try:
                await bot.send_message(
                    uid,
                    f"🏆 <b>Турнір стартує через {minutes_left} хв!</b>\n"
                    "Будь готовий до першої гри. ⚔️",
                    parse_mode="HTML",
                )
                _notified_tourn.add(uid)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        if sent:
            log.info("push_tournament_remind: notified %d users, tid=%s", sent, tournament_id)
    except Exception:
        log.exception("push_tournament_remind error")


async def push_loop(bot) -> None:
    """Background loop running push notification checks."""
    global _notified_daily
    log.info("Push notification service started")

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            # Reset daily notifications at midnight UTC
            today = now_utc.strftime("%Y-%m-%d")

            # Daily bonus reminder: 16:00 UTC (18:00 Kyiv)
            if now_utc.hour == 16 and now_utc.minute == 0:
                await push_daily_bonus_remind(bot)
                await asyncio.sleep(60)  # Don't re-trigger for this minute
                continue

            # Clean up daily set at midnight
            if now_utc.hour == 0 and now_utc.minute == 0:
                _notified_daily.clear()
                log.info("push_loop: reset daily notification set")

        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("push_loop error")

        await asyncio.sleep(30)  # Check every 30 seconds
