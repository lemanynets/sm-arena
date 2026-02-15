from __future__ import annotations

import random
from typing import List, Tuple

from .engine import (
    RED, BLUE, piece_color, is_king,
    legal_moves, apply_step, maybe_promote,
    count_pieces, has_any_moves
)

def _eval(board, perspective: int) -> int:
    score = 0
    for r in range(8):
        for c in range(8):
            v = board[r][c]
            if v == 0:
                continue
            val = 3 if abs(v) == 2 else 1
            score += val if piece_color(v) == perspective else -val
    return score

def _gen_turn_end_states(board, color: int, forced_from=None) -> List:
    # returns list of boards after full turn (including multi-capture)
    res = []
    moves_map = legal_moves(board, color, forced_from=forced_from)
    for fr, steps in moves_map.items():
        for step in steps:
            b2 = apply_step(board, step)
            if step.captured:
                cont = legal_moves(b2, color, forced_from=step.to)
                if cont:
                    res.extend(_gen_turn_end_states(b2, color, forced_from=step.to))
                else:
                    res.append(maybe_promote(b2, step.to))
            else:
                res.append(maybe_promote(b2, step.to))
    return res

def _terminal(board, turn: int) -> int | None:
    # returns winner color if terminal else None
    if count_pieces(board, turn) == 0 or not has_any_moves(board, turn):
        return -turn
    return None

def _minimax(board, turn: int, depth: int, alpha: int, beta: int, perspective: int) -> int:
    winner = _terminal(board, turn)
    if winner is not None:
        # big score for win/loss
        return 10_000 if winner == perspective else -10_000
    if depth <= 0:
        return _eval(board, perspective)

    maximizing = (turn == perspective)
    if maximizing:
        best = -10**9
        for b2 in _gen_turn_end_states(board, turn):
            val = _minimax(b2, -turn, depth - 1, alpha, beta, perspective)
            if val > best:
                best = val
            if best > alpha:
                alpha = best
            if beta <= alpha:
                break
        return best
    else:
        best = 10**9
        for b2 in _gen_turn_end_states(board, turn):
            val = _minimax(b2, -turn, depth - 1, alpha, beta, perspective)
            if val < best:
                best = val
            if best < beta:
                beta = best
            if beta <= alpha:
                break
        return best

def choose_turn(board, color: int, level: str = "easy"):
    """
    Returns a board after AI full turn (including capture chains) and next turn color.
    """
    states = _gen_turn_end_states(board, color)
    if not states:
        return board, -color  # no moves, caller will treat as lose

    if level == "easy":
        b2 = random.choice(states)
        return b2, -color

    # normal: best 1-ply
    if level == "normal":
        best = None
        best_val = -10**9
        for b2 in states:
            v = _eval(b2, color)
            if v > best_val:
                best_val = v
                best = b2
        return best, -color

    # hard: minimax depth 2 (AI + opponent)
    best = None
    best_val = -10**9
    for b2 in states:
        v = _minimax(b2, -color, depth=2, alpha=-10**9, beta=10**9, perspective=color)
        if v > best_val:
            best_val = v
            best = b2
    return best, -color
