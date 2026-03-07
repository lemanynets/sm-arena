# app/nardy_game/engine.py
"""
Short Backgammon (Короткі нарди) engine.

Board layout:
  Points 1-24.  WHITE moves 1→24 (bearing off at 25+), BLACK moves 24→1 (bearing off at 0-).

  Starting position (standard short nardi):
    White: 15 checkers starting on point 24 (stacked)? 
    Actually using the standard short nardi (Nard) variant popular in Ukraine/CIS:
      Standard short nardi (not long backgammon):
        Both players stack all 15 checkers on opponent's home board:
        White: all 15 on point 24.
        Black: all 15 on point 12.
      Then move towards bearing off.

  This is the "short nardi" variant:
    - No hitting / no bar (a key difference from Western backgammon)
    - You cannot land on an occupied point if opponent has checkers there.
    - You CAN build your own towers (stacks) of multiple checkers.

Board is a list of 26 integers:
  index 0   = White's bear-off tray  (count of white borne off)
  index 1-24 = points (positive = white checkers, negative = black checkers)
  index 25  = Black's bear-off tray  (count of black borne off)

WHITE = +1, BLACK = -1
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

WHITE = 1
BLACK = -1


def _sign(x: int) -> int:
    if x > 0: return 1
    if x < 0: return -1
    return 0


def starting_board() -> List[int]:
    """Returns the initial 26-element board (index 0 = white tray, 25 = black tray)."""
    board = [0] * 26
    # Short nardi starting position: White all 15 on point 24, Black all 15 on point 12
    board[24] = 15   # 15 white checkers on point 24
    board[12] = -15  # 15 black checkers on point 12
    return board


def roll_dice() -> Tuple[int, int]:
    return random.randint(1, 6), random.randint(1, 6)


def is_bearing_off(board: List[int], color: int) -> bool:
    """True if all of a player's checkers are in the home board (ready for bear-off)."""
    if color == WHITE:
        # White home board: points 19-24. White needs all remaining checkers there.
        total = sum(v for v in board[1:25] if v > 0)
        home = sum(v for v in board[19:25] if v > 0)
        return total == home
    else:
        # Black home board: points 1-6. Negative means black.
        total = sum(-v for v in board[1:25] if v < 0)
        home = sum(-v for v in board[1:7] if v < 0)
        return total == home


def legal_moves_for_die(board: List[int], color: int, die: int) -> List[Tuple[int, int]]:
    """
    Return list of (from_point, to_point) moves for one die value.
    from_point is 1-24. to_point can be 0 (black bear-off) or 25 (white bear-off).
    Short nardi rules: no hitting, can't land on opponent's point.
    """
    moves = []
    bearing = is_bearing_off(board, color)

    for pt in range(1, 25):
        count = board[pt]
        if _sign(count) != color:
            continue  # no checker of our color here

        if color == WHITE:
            dest = pt + die
            if dest <= 24:
                # must be empty or our own
                if _sign(board[dest]) != BLACK:
                    moves.append((pt, dest))
            elif bearing:
                # bear off
                if dest == 25:
                    moves.append((pt, 25))
                elif dest > 25:
                    # can bear off from highest occupied point
                    highest = max((p for p in range(1, 25) if board[p] > 0), default=0)
                    if pt == highest:
                        moves.append((pt, 25))
        else:  # BLACK
            dest = pt - die
            if dest >= 1:
                if _sign(board[dest]) != WHITE:
                    moves.append((pt, dest))
            elif bearing:
                if dest == 0:
                    moves.append((pt, 0))
                elif dest < 0:
                    lowest = min((p for p in range(1, 25) if board[p] < 0), default=25)
                    if pt == lowest:
                        moves.append((pt, 0))

    return moves


def legal_moves(board: List[int], color: int, dice: Tuple[int, int]) -> List[Tuple[int, int, int]]:
    """
    Return all unique (from, to, die_used) triples.
    Doubles give 4 moves.
    """
    d1, d2 = dice
    if d1 == d2:
        dies = [d1, d1, d1, d1]
    else:
        dies = [d1, d2]

    seen: set = set()
    result = []
    for die in set(dies):
        for move in legal_moves_for_die(board, color, die):
            key = (move[0], move[1])
            if key not in seen:
                seen.add(key)
                result.append((move[0], move[1], die))
    return result


def apply_move(board: List[int], color: int, frm: int, to: int) -> List[int]:
    """Apply a move and return new board (does NOT modify in place)."""
    b = board[:]
    b[frm] -= color
    if to == 25:   # white bear-off
        b[0] += 1
    elif to == 0:  # black bear-off
        b[25] += 1
    else:
        b[to] += color
    return b


def check_winner(board: List[int]) -> Optional[int]:
    """Return WHITE or BLACK if that side has borne off all 15, else None."""
    if board[0] >= 15:
        return WHITE
    if board[25] >= 15:
        return BLACK
    return None


def ai_move(board: List[int], color: int, dice: Tuple[int, int]) -> Tuple[List[int], List[Tuple[int, int]]]:
    """
    AI does greedy random single moves consuming one die at a time.
    Returns (new_board, list_of_(from,to) made).
    """
    b = board[:]
    d1, d2 = dice
    dice_left = [d1, d1, d1, d1] if d1 == d2 else [d1, d2]
    made: List[Tuple[int, int]] = []

    for die in dice_left:
        ms = legal_moves_for_die(b, color, die)
        if not ms:
            continue
        chosen = random.choice(ms)
        b = apply_move(b, color, chosen[0], chosen[1])
        made.append((chosen[0], chosen[1]))

    return b, made


# ---------------------------------------------------------------------------
# In-memory game state
# ---------------------------------------------------------------------------

@dataclass
class NardyGame:
    gid: str
    white_id: int
    white_name: str
    black_id: int = 0
    black_name: str = "AI"
    vs_ai: bool = True
    board: List[int] = field(default_factory=starting_board)
    turn: int = WHITE          # whose turn it is
    dice: Optional[Tuple[int, int]] = None
    dice_used: List[int] = field(default_factory=list)
    finished: bool = False
    winner: Optional[int] = None
    chat_id: int = 0
    message_id: int = 0
    # selected point for two-click move (first click = pick, second = dest)
    selected: Optional[int] = None

    def roll(self) -> Tuple[int, int]:
        self.dice = roll_dice()
        self.dice_used = []
        self.selected = None
        return self.dice

    def get_moves(self) -> List[Tuple[int, int, int]]:
        if not self.dice:
            return []
        return legal_moves(self.board, self.turn, self.dice)

    def make_move(self, frm: int, to: int, die: int) -> bool:
        """Apply one move. Returns True if successful."""
        valid = [(f, t, d) for f, t, d in self.get_moves() if f == frm and t == to]
        if not valid:
            return False
        self.board = apply_move(self.board, self.turn, frm, to)
        # Check win
        w = check_winner(self.board)
        if w is not None:
            self.finished = True
            self.winner = w
        return True


# ---------------------------------------------------------------------------
# Simple in-memory store
# ---------------------------------------------------------------------------
_GAMES: dict[str, NardyGame] = {}


def get_game(gid: str) -> Optional[NardyGame]:
    return _GAMES.get(gid)


def new_game(gid: str, white_id: int, white_name: str,
             vs_ai: bool = True, chat_id: int = 0) -> NardyGame:
    gs = NardyGame(
        gid=gid,
        white_id=white_id,
        white_name=white_name,
        vs_ai=vs_ai,
        chat_id=chat_id,
    )
    if vs_ai:
        gs.black_id = 0
        gs.black_name = "🤖 AI"
    _GAMES[gid] = gs
    return gs


def delete_game(gid: str) -> None:
    _GAMES.pop(gid, None)
