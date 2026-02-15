# app/prizes.py
# Призовий фонд Weekly TOP для SM Arena

PRIZE_POOL = 100        # загальний фонд (умовні одиниці / Stars / $)
TOP_N = 10              # кількість призових місць

# Розподіл фонду у %, сума = 100
DISTRIBUTION = [35, 20, 12, 8, 6, 5, 4, 4, 3, 3]

def payouts(pool: int = PRIZE_POOL) -> list[int]:
    """
    Повертає список призів для місць 1..TOP_N
    Гарантує, що сума призів = pool
    """
    raw = [round(pool * p / 100) for p in DISTRIBUTION[:TOP_N]]
    diff = pool - sum(raw)
    if raw:
        raw[-1] += diff
        if raw[-1] < 0:
            raw[-1] = 0
    return raw
