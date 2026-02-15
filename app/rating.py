# app/rating.py
# Простий Elo-рейтинг для SM Arena

def expected_score(r_a: int, r_b: int) -> float:
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def update_elo(r_a: int, r_b: int, score_a: float, k: int = 24) -> tuple[int, int]:
    """
    score_a:
        1.0 -> A виграв
        0.5 -> нічия
        0.0 -> A програв
    """
    e_a = expected_score(r_a, r_b)
    e_b = expected_score(r_b, r_a)

    new_a = round(r_a + k * (score_a - e_a))
    new_b = round(r_b + k * ((1 - score_a) - e_b))

    return new_a, new_b
