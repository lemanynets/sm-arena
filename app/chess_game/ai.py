from __future__ import annotations

import random

import chess


_PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def _material_eval(board: chess.Board, side: bool) -> int:
    score = 0
    for piece_type, val in _PIECE_VALUE.items():
        score += len(board.pieces(piece_type, side)) * val
        score -= len(board.pieces(piece_type, not side)) * val
    return score


def _position_eval(board: chess.Board, side: bool) -> int:
    if board.is_checkmate():
        # If side to move is checkmated => terrible for side.
        return -100_000 if board.turn == side else 100_000
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0

    score = _material_eval(board, side)
    # tiny mobility bonus
    mobility = board.legal_moves.count()
    score += mobility if board.turn == side else -mobility
    if board.is_check():
        score += 25 if board.turn != side else -25
    return score


def _tactical_score(board: chess.Board, move: chess.Move) -> int:
    score = 0
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        if captured:
            score += _PIECE_VALUE.get(captured.piece_type, 0) * 8
    if move.promotion:
        score += _PIECE_VALUE.get(move.promotion, 0) * 4

    board.push(move)
    if board.is_checkmate():
        score += 200_000
    elif board.is_check():
        score += 50
    board.pop()
    return score


def _choose_normal(board: chess.Board, legal: list[chess.Move]) -> chess.Move:
    scored: list[tuple[int, chess.Move]] = []
    for mv in legal:
        scored.append((_tactical_score(board, mv), mv))
    best = max(s for s, _ in scored)
    candidates = [mv for s, mv in scored if s == best]
    return random.choice(candidates)


def _choose_hard(board: chess.Board, legal: list[chess.Move]) -> chess.Move:
    side = board.turn
    best_score = -10**9
    best_moves: list[chess.Move] = []

    for mv in legal:
        board.push(mv)
        if board.is_checkmate():
            score = 200_000
        else:
            opp_moves = list(board.legal_moves)
            if not opp_moves:
                score = _position_eval(board, side)
            else:
                worst_reply = 10**9
                for omv in opp_moves:
                    board.push(omv)
                    val = _position_eval(board, side)
                    board.pop()
                    if val < worst_reply:
                        worst_reply = val
                score = worst_reply

        board.pop()
        score += _tactical_score(board, mv)

        if score > best_score:
            best_score = score
            best_moves = [mv]
        elif score == best_score:
            best_moves.append(mv)

    return random.choice(best_moves) if best_moves else random.choice(legal)


def choose_move(board: chess.Board, level: str = "easy") -> chess.Move | None:
    legal = list(board.legal_moves)
    if not legal:
        return None

    lv = (level or "easy").lower()
    if lv == "hard":
        return _choose_hard(board, legal)
    if lv == "normal":
        return _choose_normal(board, legal)
    return random.choice(legal)
