
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Iterable

SIZE = 8

# board cell values:
# 0 empty
# 1 red man, 2 red king
# -1 blue man, -2 blue king
RED = 1
BLUE = -1

def is_dark(r: int, c: int) -> bool:
    return (r + c) % 2 == 1

def piece_color(v: int) -> int:
    if v > 0:
        return RED
    if v < 0:
        return BLUE
    return 0

def is_king(v: int) -> bool:
    return abs(v) == 2

@dataclass(frozen=True)
class StepMove:
    fr: Tuple[int, int]
    to: Tuple[int, int]
    captured: Tuple[Tuple[int, int], ...] = ()

def initial_board() -> List[List[int]]:
    b = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
    # Blue at top (0..2), Red at bottom (5..7)
    for r in range(0, 3):
        for c in range(SIZE):
            if is_dark(r, c):
                b[r][c] = -1
    for r in range(5, 8):
        for c in range(SIZE):
            if is_dark(r, c):
                b[r][c] = 1
    return b

def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < SIZE and 0 <= c < SIZE

DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

def _man_simple_dirs(color: int) -> Iterable[Tuple[int, int]]:
    # red moves up, blue moves down
    return [(-1, -1), (-1, 1)] if color == RED else [(1, -1), (1, 1)]

def list_captures_for_piece(board: List[List[int]], r: int, c: int) -> List[StepMove]:
    v = board[r][c]
    col = piece_color(v)
    if col == 0:
        return []

    res: List[StepMove] = []

    # man capture: jump any direction
    if not is_king(v):
        for dr, dc in DIRS:
            r1, c1 = r + dr, c + dc
            r2, c2 = r + 2 * dr, c + 2 * dc
            if not in_bounds(r2, c2):
                continue
            if board[r2][c2] != 0:
                continue
            if not in_bounds(r1, c1):
                continue
            mid = board[r1][c1]
            if mid != 0 and piece_color(mid) == -col:
                res.append(StepMove((r, c), (r2, c2), ((r1, c1),)))
        return res

    # king capture: along diagonal, jump exactly one enemy, land beyond
    for dr, dc in DIRS:
        rr, cc = r + dr, c + dc
        enemy_pos: Optional[Tuple[int, int]] = None
        while in_bounds(rr, cc):
            cell = board[rr][cc]
            if cell == 0:
                if enemy_pos is not None:
                    res.append(StepMove((r, c), (rr, cc), (enemy_pos,)))
                rr += dr
                cc += dc
                continue

            if piece_color(cell) == col:
                break

            if enemy_pos is not None:
                break
            enemy_pos = (rr, cc)
            rr += dr
            cc += dc

    return res

def list_simple_moves_for_piece(board: List[List[int]], r: int, c: int) -> List[StepMove]:
    v = board[r][c]
    col = piece_color(v)
    if col == 0:
        return []

    res: List[StepMove] = []

    if not is_king(v):
        for dr, dc in _man_simple_dirs(col):
            rr, cc = r + dr, c + dc
            if in_bounds(rr, cc) and board[rr][cc] == 0:
                res.append(StepMove((r, c), (rr, cc), ()))
        return res

    # king simple move: any empty along diagonal
    for dr, dc in DIRS:
        rr, cc = r + dr, c + dc
        while in_bounds(rr, cc) and board[rr][cc] == 0:
            res.append(StepMove((r, c), (rr, cc), ()))
            rr += dr
            cc += dc

    return res

def any_capture_exists(board: List[List[int]], color: int) -> bool:
    for r in range(SIZE):
        for c in range(SIZE):
            if piece_color(board[r][c]) == color and list_captures_for_piece(board, r, c):
                return True
    return False

def legal_moves(
    board: List[List[int]],
    color: int,
    forced_from: Optional[Tuple[int, int]] = None
) -> Dict[Tuple[int, int], List[StepMove]]:
    moves: Dict[Tuple[int, int], List[StepMove]] = {}

    if forced_from is not None:
        r, c = forced_from
        if piece_color(board[r][c]) != color:
            return {}
        caps = list_captures_for_piece(board, r, c)
        if caps:
            moves[(r, c)] = caps
        return moves

    must_capture = any_capture_exists(board, color)
    for r in range(SIZE):
        for c in range(SIZE):
            if piece_color(board[r][c]) != color:
                continue
            pm = list_captures_for_piece(board, r, c) if must_capture else list_simple_moves_for_piece(board, r, c)
            if pm:
                moves[(r, c)] = pm

    return moves

def apply_step(board: List[List[int]], mv: StepMove) -> List[List[int]]:
    b = [row[:] for row in board]
    fr_r, fr_c = mv.fr
    to_r, to_c = mv.to
    piece = b[fr_r][fr_c]
    b[fr_r][fr_c] = 0
    b[to_r][to_c] = piece
    for cr, cc in mv.captured:
        b[cr][cc] = 0
    return b

def maybe_promote(board: List[List[int]], last_to: Tuple[int, int]) -> List[List[int]]:
    b = [row[:] for row in board]
    r, c = last_to
    v = b[r][c]
    if abs(v) != 1:
        return b
    if v == 1 and r == 0:
        b[r][c] = 2
    elif v == -1 and r == SIZE - 1:
        b[r][c] = -2
    return b

def count_pieces(board: List[List[int]], color: int) -> int:
    return sum(1 for r in range(SIZE) for c in range(SIZE) if piece_color(board[r][c]) == color)

def has_any_moves(board: List[List[int]], color: int) -> bool:
    return bool(legal_moves(board, color))
