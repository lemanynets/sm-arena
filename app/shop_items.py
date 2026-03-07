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

    # Lootboxes
    {
        "item_id": "lootbox:bronze",
        "title": "📦 Бронзова Скриня",
        "desc": "Може містити звичайні скіни або трохи монет. Шанс на Рарку - 5%!",
        "price": 50,
        "game": "xo", # Shows everywhere visually
        "kind": "lootbox",
        "loot_table": [
            (0.60, "coins:20", "20 Золотих Монет 🪙"),
            (0.20, "coins:60", "60 Золотих Монет 🪙"),
            (0.15, "skin:xo:mono", "🎨 XO: Mono (Звичайний)"),
            (0.05, "skin:checkers:neon", "🎨 Шашки: Neon (Рідкісний)"),
        ]
    },
    {
        "item_id": "lootbox:gold",
        "title": "🥇 Золота Скриня",
        "desc": "Преміальний лутбокс. Шанси: 70% на багато монет, 30% на легендарні скіни!",
        "price": 250,
        "game": "xo",
        "kind": "lootbox",
        "loot_table": [
            (0.40, "coins:150", "150 Золотих Монет 🪙"),
            (0.30, "coins:300", "300 Золотих Монет 🪙"),
            (0.15, "skin:xo:3d", "🎨 XO: 3D (Легендарний)"),
            (0.15, "skin:checkers:3d", "🎨 Шашки: 3D (Легендарний)"),
        ]
    },
    # Board skins (XO)
    {
        "item_id": "skin_board:xo:wood",
        "title": "🪵 XO Дошка: Wood",
        "desc": "Дерев'яний фон для ігрового поля.",
        "price": 80,
        "game": "xo",
        "kind": "skin_board",
        "value": "wood",
    },
    {
        "item_id": "skin_board:xo:neon",
        "title": "🌌 XO Дошка: Neon",
        "desc": "Неоновий фон для ігрового поля.",
        "price": 80,
        "game": "xo",
        "kind": "skin_board",
        "value": "neon",
    },
    # Cell skins (XO)
    {
        "item_id": "skin_cell:xo:ocean",
        "title": "🌊 XO Клітинки: Ocean Blue",
        "desc": "Синій колір порожніх клітинок.",
        "price": 60,
        "game": "xo",
        "kind": "skin_cell",
        "value": "ocean",
    },
    # Board skins (Checkers)
    {
        "item_id": "skin_board:checkers:wood",
        "title": "🪵 Шашки Дошка: Wood",
        "desc": "Дерев'яний фон для шашкового поля.",
        "price": 80,
        "game": "checkers",
        "kind": "skin_board",
        "value": "wood",
    },
    {
        "item_id": "skin_board:checkers:neon",
        "title": "🌌 Шашки Дошка: Neon",
        "desc": "Неоновий фон для шашкового поля.",
        "price": 80,
        "game": "checkers",
        "kind": "skin_board",
        "value": "neon",
    },
    # Cell skins (Checkers)
    {
        "item_id": "skin_cell:checkers:ocean",
        "title": "🌊 Шашки Клітинки: Ocean",
        "desc": "Синій колір темних клітинок.",
        "price": 60,
        "game": "checkers",
        "kind": "skin_cell",
        "value": "ocean",
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
