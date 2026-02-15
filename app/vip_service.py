# app/vip_service.py
import asyncio
import time
import logging
import random

from app import config
from app import db
from app.shop_items import SHOP_ITEMS

log = logging.getLogger("vip")

DAY = 86400
WEEK = 7 * DAY

def _premium_item_ids() -> list[str]:
    # premium skins = everything except default; take from shop catalog
    ids = []
    for it in SHOP_ITEMS:
        iid = str(it.get("item_id"))
        if iid and iid.startswith("skin:") and not iid.endswith(":default"):
            ids.append(iid)
    return ids

def grant_weekly_pack(user_id: int) -> str:
    owned = db.owned_item_ids(user_id)
    candidates = [iid for iid in _premium_item_ids() if iid not in owned]
    if not candidates:
        # fallback: compensate with coins
        db.add_coins(user_id, int(getattr(config, "VIP_WEEKLY_PACK_FALLBACK_COINS", 30)))
        return "coins"
    iid = random.choice(candidates)
    db.add_item(user_id, iid)
    db.set_active_item(user_id, iid)
    return iid

async def vip_bonus_loop(bot):
    """
    Background loop:
    - daily coins for VIP users
    - weekly pack for VIP users
    """
    daily_coins = int(getattr(config, "VIP_DAILY_COINS", 10))
    weekly_enabled = bool(getattr(config, "VIP_WEEKLY_PACK_ENABLED", True))

    while True:
        try:
            now = int(time.time())
            vip_users = db.db_list_vip_users()  # (user_id, last_daily, last_weekly)

            for user_id, last_daily, last_weekly in vip_users:
                try:
                    # daily coins
                    if daily_coins > 0 and (not last_daily or now - int(last_daily) >= DAY):
                        db.add_coins(user_id, daily_coins)
                        db.vip_mark_daily_paid(user_id)
                        try:
                            await bot.send_message(user_id, f"⭐ VIP бонус: +{daily_coins}🪙 (щоденний)")
                        except Exception:
                            pass

                    # weekly pack
                    if weekly_enabled and (not last_weekly or now - int(last_weekly) >= WEEK):
                        res = grant_weekly_pack(user_id)
                        db.vip_mark_weekly_pack(user_id)
                        try:
                            if res == "coins":
                                await bot.send_message(user_id, "⭐ VIP бонус: +монети (усі скіни вже в інвентарі)")
                            else:
                                await bot.send_message(user_id, "⭐ VIP бонус: 🎁 +1 пак (щотижневий)")
                        except Exception:
                            pass
                except Exception as e:
                    log.warning("VIP bonus failed for %s: %s", user_id, e)

        except Exception as e:
            log.exception("vip_bonus_loop error: %s", e)

        await asyncio.sleep(60)
