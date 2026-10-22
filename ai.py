# -*- coding: utf-8 -*-
"""
Chess bot: negamax with alpha-beta pruning, iterative deepening and a
capture-only quiescence search.  Three difficulty levels:

  easy   - greedy 1-ply evaluation with randomness and occasional blunders
  medium - 2-ply alpha-beta + quiescence
  hard   - iterative deepening up to depth 4 with a time budget

Evaluation values pieces by their movement PATTERN (a knight that moves
like a queen is worth queen-ish material), which also makes the bot work
in Random Chess mode without any special casing.
"""

import random
import time

from engine import WHITE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, EN_PASSANT

INF = 10 ** 9
MATE = 100_000

VAL = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 0}

# Piece-square tables, oriented with row 0 = rank 8 (white's point of view);
# for black the index is mirrored with i ^ 56.
PAWN_PST = (
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
)
KING_PST = (
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
)
CENTER_PST = (
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 10, 15, 15, 10, 5, -10,
    -10, 5, 10, 15, 15, 10, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
)
# rooks and queens care less about the center
HALF_CENTER = tuple(v // 2 for v in CENTER_PST)

PST = {PAWN: PAWN_PST, KNIGHT: CENTER_PST, BISHOP: CENTER_PST,
       ROOK: HALF_CENTER, QUEEN: HALF_CENTER, KING: KING_PST}

LEVELS = {  # max_depth, time budget (seconds)
    'easy': (1, 0.3),
    'medium': (2, 1.5),
    'hard': (4, 3.2),
}


class SearchTimeout(Exception):
    pass


def evaluate(board):
    """Static evaluation from the perspective of the side to move."""
    sqs = board.squares
    score = 0
    for i in range(64):
        p = sqs[i]
        if p is None:
            continue
        color, kind, pat = p
        v = VAL[pat] + PST[pat][i if color == WHITE else i ^ 56]
        score += v if color == WHITE else -v
    return score if board.turn == WHITE else -score


class AI:
    def __init__(self, board):
        self.board = board
        self.deadline = 0.0
        self.nodes = 0

    # ------------------------------------------------------------ interface

    def choose_move(self, level):
        b = self.board
        moves = b.legal_moves()
        if not moves:
            return None
        if level == 'easy':
            return self._easy(moves)
        max_depth, budget = LEVELS[level]
        random.shuffle(moves)  # variety among equal moves
        return self._search(moves, max_depth, budget)

    # -------------------------------------------------------------- levels

    def _easy(self, moves):
        """Greedy + jitter + occasional deliberate blunder."""
        b = self.board
        if random.random() < 0.25:
            return random.choice(moves)
        best, best_score = moves[0], -INF
        for m in moves:
            undo = b.make(m)
            score = -evaluate(b) + random.randint(0, 90)
            b.unmake(undo)
            if score > best_score:
                best, best_score = m, score
        return best

    def _search(self, moves, max_depth, budget):
        b = self.board
        self.deadline = time.time() + budget
        self.nodes = 0
        best = moves[0]
        try:
            for depth in range(1, max_depth + 1):
                alpha, current = -INF, None
                for m in moves:
                    undo = b.make(m)
                    try:
                        score = -self._negamax(depth - 1, -INF, -alpha, 1)
                    finally:
                        b.unmake(undo)
                    if score > alpha:
                        alpha, current = score, m
                best = current
                moves.remove(best)
                moves.insert(0, best)  # best-first ordering for next depth
                if alpha > MATE - 1000:
                    break  # forced mate found
        except SearchTimeout:
            pass  # keep the best move from the last completed depth
        return best

    # -------------------------------------------------------------- search

    def _check_time(self):
        if (self.nodes & 511) == 0 and time.time() > self.deadline:
            raise SearchTimeout()

    def _negamax(self, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_time()
        b = self.board
        if depth == 0:
            return self._qsearch(alpha, beta, 6)
        moves = b.legal_moves()
        if not moves:
            return -(MATE - ply) if b.is_check(b.turn) else 0
        moves.sort(key=self._order_key, reverse=True)
        best = -INF
        for m in moves:
            undo = b.make(m)
            try:
                score = -self._negamax(depth - 1, -beta, -alpha, ply + 1)
            finally:
                b.unmake(undo)
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        return best

    def _qsearch(self, alpha, beta, depth):
        self.nodes += 1
        self._check_time()
        b = self.board
        stand = evaluate(b)
        if stand >= beta:
            return stand
        if stand > alpha:
            alpha = stand
        if depth == 0:
            return alpha
        moves = self._ordered(b.pseudo_moves(True))
        turn = b.turn
        enemy = 1 - turn
        best = stand
        for m in moves:
            undo = b.make(m)
            if b.attacked(b.king_sq[turn], enemy):
                b.unmake(undo)
                continue
            try:
                score = -self._qsearch(-beta, -alpha, depth - 1)
            finally:
                b.unmake(undo)
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        return best

    # ------------------------------------------------------------- ordering

    def _order_key(self, m):
        frm, to, promo, flag = m
        b = self.board
        victim = b.squares[to]
        vic = VAL[victim[2]] if victim is not None else (VAL[PAWN] if flag == EN_PASSANT else 0)
        atk = VAL[b.squares[frm][2]] // 10
        bonus = 800 if promo == QUEEN else (400 if promo else 0)
        return vic * 10 - atk + bonus

    def _ordered(self, moves):
        moves.sort(key=self._order_key, reverse=True)
        return moves
