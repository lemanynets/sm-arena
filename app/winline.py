# app/winline.py

from typing import Optional, List, Tuple

WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]

def get_winline(board: str) -> Optional[Tuple[str, List[int]]]:
    """
    Returns (winner, [idx, idx, idx]) where winner is 'X' or 'O'
    If no winning line -> None
    """
    for a, b, c in WIN_LINES:
        if board[a] != "." and board[a] == board[b] == board[c]:
            return board[a], [a, b, c]
    return None
