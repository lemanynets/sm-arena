import random

def test_lootbox(chances, iterations=1000, out=None):
    results = {}
    for _ in range(iterations):
        roll = random.random()
        cumulative = 0.0
        won_name = "Nothing"
        for prob, l_id, l_name in chances:
            cumulative += prob
            if roll <= cumulative:
                won_name = l_name
                break
        results[won_name] = results.get(won_name, 0) + 1
        
    for k, v in results.items():
        out.write(f"{k}: {v/iterations*100:.2f}%\n")

with open("gacha_results.txt", "w", encoding="utf-8") as out:
    out.write("--- Bronze Box ---\n")
    bronze = [
        (0.60, "coins:20", "20 Золотих Монет 🪙"),
        (0.20, "coins:60", "60 Золотих Монет 🪙"),
        (0.15, "skin:xo:mono", "🎨 XO: Mono (Звичайний)"),
        (0.05, "skin:checkers:neon", "🎨 Шашки: Neon (Рідкісний)"),
    ]
    test_lootbox(bronze, 10000, out)

    out.write("\n--- Gold Box ---\n")
    gold = [
        (0.40, "coins:150", "150 Золотих Монет 🪙"),
        (0.30, "coins:300", "300 Золотих Монет 🪙"),
        (0.15, "skin:xo:3d", "🎨 XO: 3D (Легендарний)"),
        (0.15, "skin:checkers:3d", "🎨 Шашки: 3D (Легендарний)"),
    ]
    test_lootbox(gold, 10000, out)
