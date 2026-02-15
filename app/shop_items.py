# app/shop_items.py
"""Static catalog for the in-bot shop.

Item id scheme:
  skin:xo:<skin_key>
  skin:checkers:<skin_key>

Prices are in coins (🪙).
"""

from __future__ import annotations

SHOP_PRICE_DEFAULT = 60

# IMPORTANT: skin keys must be present in app/config.py -> SKINS
SHOP_ITEMS: list[dict] = [
    # XO skins
    {
        "item_id": "skin:xo:3d",
        "title": "🎨 XO: 3D",
        "desc": "Обʼємні емодзі для хрестиків-нуликів.",
        "price": SHOP_PRICE_DEFAULT,
        "game": "xo",
        "kind": "skin",
        "value": "3d",
    },
    {
        "item_id": "skin:xo:neon",
        "title": "🎨 XO: Neon",
        "desc": "Неонова тема (яскраві ходи).",
        "price": SHOP_PRICE_DEFAULT,
        "game": "xo",
        "kind": "skin",
        "value": "neon",
    },
    {
        "item_id": "skin:xo:mono",
        "title": "🎨 XO: Mono",
        "desc": "Мінімалістична тема (X/O).",
        "price": SHOP_PRICE_DEFAULT,
        "game": "xo",
        "kind": "skin",
        "value": "mono",
    },

    # Checkers skins
    {
        "item_id": "skin:checkers:3d",
        "title": "🎨 Шашки: 3D",
        "desc": "Солодкі фішки + корона для дамки.",
        "price": SHOP_PRICE_DEFAULT,
        "game": "checkers",
        "kind": "skin",
        "value": "3d",
    },
    {
        "item_id": "skin:checkers:neon",
        "title": "🎨 Шашки: Neon",
        "desc": "Неонова тема (кольорові фішки).",
        "price": SHOP_PRICE_DEFAULT,
        "game": "checkers",
        "kind": "skin",
        "value": "neon",
    },
    {
        "item_id": "skin:checkers:minimal",
        "title": "🎨 Шашки: Minimal",
        "desc": "Суворий мінімалізм (R/B).",
        "price": SHOP_PRICE_DEFAULT,
        "game": "checkers",
        "kind": "skin",
        "value": "minimal",
    },
]

def items_for_game(game: str) -> list[dict]:
    g = (game or "xo").lower()
    return [it for it in SHOP_ITEMS if (it.get("game") or "xo").lower() == g]

def get_item(item_id: str) -> dict | None:
    iid = str(item_id)
    for it in SHOP_ITEMS:
        if str(it.get("item_id")) == iid:
            return it
    return None
