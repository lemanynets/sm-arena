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

BP_REWARDS = {
    # level: {"free": {"type": "coins", "amount": 10}, "premium": {"type": "item", "id": "lootbox:bronze"}}
    5: {"free": {"type": "coins", "amount": 10}, "premium": {"type": "coins", "amount": 50}},
    10: {"free": {"type": "coins", "amount": 20}, "premium": {"type": "item", "id": "lootbox:bronze"}},
    15: {"free": {"type": "coins", "amount": 30}, "premium": {"type": "coins", "amount": 100}},
    20: {"free": {"type": "coins", "amount": 40}, "premium": {"type": "item", "id": "lootbox:gold"}},
    25: {"free": {"type": "coins", "amount": 50}, "premium": {"type": "coins", "amount": 200}},
    30: {"free": {"type": "coins", "amount": 100}, "premium": {"type": "item", "id": "skin:xo:3d"}},
}

def grant_bp_reward(user_id: int, reward: dict) -> str:
    rtype = reward.get("type")
    if rtype == "coins":
        amount = reward.get("amount", 0)
        db.add_coins(user_id, amount)
        return f"{amount} 🪙"
    elif rtype == "item":
        iid = reward.get("id")
        if db.has_item(user_id, iid):
            db.add_coins(user_id, 50)
            return f"50 🪙 (компенсація за {iid})"
        else:
            db.add_item(user_id, iid)
            return f"Предмет {iid}!"
    return ""

async def vip_bonus_loop(bot):
    """
    Deprecated loop from old VIP system.
    Leaving empty so main can still import and run it without crashing.
    """
    while True:
        await asyncio.sleep(86400)

