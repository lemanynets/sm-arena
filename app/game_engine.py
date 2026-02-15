from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple

WIN_LINES: List[Tuple[int, int, int]] = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]

def check_winner(board: str) -> Optional[str]:
    for a, b, c in WIN_LINES:
        if board[a] != "." and board[a] == board[b] == board[c]:
            return board[a]  # "X" або "O"
    if "." not in board:
        return "D"  # draw
    return None

def available_moves(board: str) -> List[int]:
    return [i for i, ch in enumerate(board) if ch == "."]

def apply_move(board: str, cell: int, mark: str) -> str:
    if cell < 0 or cell > 8:
        raise ValueError("cell out of range")
    if board[cell] != ".":
        raise ValueError("cell already taken")
    return board[:cell] + mark + board[cell+1:]

def ai_move_easy(board: str) -> int:
    # просто перший доступний хід
    return available_moves(board)[0]

def ai_move_normal(board: str) -> int:
    # 1) виграти якщо можна
    for m in available_moves(board):
        if check_winner(apply_move(board, m, "O")) == "O":
            return m
    # 2) заблокувати X
    for m in available_moves(board):
        if check_winner(apply_move(board, m, "X")) == "X":
            return m
    # 3) центр
    if board[4] == ".":
        return 4
    # 4) кут
    for m in [0, 2, 6, 8]:
        if board[m] == ".":
            return m
    # 5) будь-що
    return available_moves(board)[0]

def ai_move_hard(board: str) -> int:
    # міні-макс (ідеальна гра) — для 3x3 це швидко
    def score(b: str, turn: str) -> int:
        w = check_winner(b)
        if w == "O":
            return 10
        if w == "X":
            return -10
        if w == "D":
            return 0

        moves = available_moves(b)
        if turn == "O":
            best = -999
            for m in moves:
                best = max(best, score(apply_move(b, m, "O"), "X"))
            return best
        else:
            best = 999
            for m in moves:
                best = min(best, score(apply_move(b, m, "X"), "O"))
            return best

    best_move = None
    best_val = -999
    for m in available_moves(board):
        val = score(apply_move(board, m, "O"), "X")
        if val > best_val:
            best_val = val
            best_move = m
    return best_move if best_move is not None else available_moves(board)[0]
