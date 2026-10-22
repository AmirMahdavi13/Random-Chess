# -*- coding: utf-8 -*-
"""
Chess rules engine with pluggable movement patterns.

Every piece is a tuple (color, kind, pattern):
  - color  : WHITE / BLACK
  - kind   : what the piece looks like ('P','N','B','R','Q','K')
  - pattern: how the piece moves (same alphabet)

In classic chess pattern == kind for every piece.  In "Random Chess" the
back-rank pieces (everything except pawns and the king) receive a random
movement pattern taken from the other piece types; the assignment is
mirrored between the two armies so the game stays fair.

Board indexing: square = row * 8 + col, row 0 is rank 8 (top / black side),
col 0 is the 'a' file.  White pawns move towards row 0.
"""

import random

WHITE, BLACK = 0, 1
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 'P', 'N', 'B', 'R', 'Q', 'K'
BACK_RANK = (ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK)
PATTERN_KINDS = (KNIGHT, BISHOP, ROOK, QUEEN)

KNIGHT_OFFS = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
KING_OFFS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
ROOK_DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
BISHOP_DIRS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
ALL_DIRS = ROOK_DIRS + BISHOP_DIRS

NORMAL, DOUBLE_PUSH, EN_PASSANT, CASTLE = 0, 1, 2, 3

# corner square -> castling right lost when a move touches it
CORNER_RIGHTS = {63: 'K', 56: 'Q', 7: 'k', 0: 'q'}

FILES = 'abcdefgh'


def other(color):
    return 1 - color


class Board:
    def __init__(self):
        self.squares = [None] * 64
        self.turn = WHITE
        self.castling = frozenset()
        self.ep = None
        self.king_sq = [None, None]
        self.random_mode = False
        # file -> assigned pattern (Random Chess, for display purposes)
        self.pattern_map = {}

    # ---------------------------------------------------------------- setup

    def new_game(self, random_mode=False, seed=None):
        """Standard starting position; optionally shuffle movement patterns."""
        self.squares = [None] * 64
        for f, kind in enumerate(BACK_RANK):
            self.squares[56 + f] = (WHITE, kind, kind)
            self.squares[0 + f] = (BLACK, kind, kind)
        for f in range(8):
            self.squares[48 + f] = (WHITE, PAWN, PAWN)
            self.squares[8 + f] = (BLACK, PAWN, PAWN)
        self.king_sq[WHITE] = 60
        self.king_sq[BLACK] = 4
        self.turn = WHITE
        self.ep = None
        self.random_mode = random_mode
        self.pattern_map = {}
        self.castling = frozenset('KQkq')
        if random_mode:
            rng = random.Random(seed)
            for f, kind in enumerate(BACK_RANK):
                if kind in (PAWN, KING):
                    continue
                pat = rng.choice([p for p in PATTERN_KINDS if p != kind])
                self.pattern_map[f] = pat
                self.squares[56 + f] = (WHITE, kind, pat)
                self.squares[0 + f] = (BLACK, kind, pat)
            # rooks may no longer move like rooks -> castling is meaningless
            self.castling = frozenset()
        return self

    @classmethod
    def from_fen(cls, fen):
        b = cls()
        parts = fen.split()
        for i, row in enumerate(parts[0].split('/')):
            c = 0
            for ch in row:
                if ch.isdigit():
                    c += int(ch)
                else:
                    color = WHITE if ch.isupper() else BLACK
                    kind = ch.upper()
                    b.squares[i * 8 + c] = (color, kind, kind)
                    if kind == KING:
                        b.king_sq[color] = i * 8 + c
                    c += 1
        b.turn = WHITE if parts[1] == 'w' else BLACK
        b.castling = frozenset(parts[2]) - {'-'} if len(parts) > 2 else frozenset()
        ep = parts[3] if len(parts) > 3 else '-'
        b.ep = None if ep == '-' else (8 - int(ep[1])) * 8 + FILES.index(ep[0])
        return b

    # ------------------------------------------------------------- attacks

    def attacked(self, square, by):
        """Is `square` attacked by any piece of color `by`? (pattern based)"""
        sqs = self.squares
        r, c = divmod(square, 8)
        pr = r + 1 if by == WHITE else r - 1
        if 0 <= pr < 8:
            p = sqs[pr * 8 + c - 1] if c > 0 else None
            if p is not None and p[0] == by and p[2] == PAWN:
                return True
            p = sqs[pr * 8 + c + 1] if c < 7 else None
            if p is not None and p[0] == by and p[2] == PAWN:
                return True
        for dr, dc in KNIGHT_OFFS:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                p = sqs[rr * 8 + cc]
                if p is not None and p[0] == by and p[2] == KNIGHT:
                    return True
        for dr, dc in KING_OFFS:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                p = sqs[rr * 8 + cc]
                if p is not None and p[0] == by and p[2] == KING:
                    return True
        for dr, dc in ROOK_DIRS:
            rr, cc = r + dr, c + dc
            while 0 <= rr < 8 and 0 <= cc < 8:
                p = sqs[rr * 8 + cc]
                if p is not None:
                    if p[0] == by and (p[2] == ROOK or p[2] == QUEEN):
                        return True
                    break
                rr += dr
                cc += dc
        for dr, dc in BISHOP_DIRS:
            rr, cc = r + dr, c + dc
            while 0 <= rr < 8 and 0 <= cc < 8:
                p = sqs[rr * 8 + cc]
                if p is not None:
                    if p[0] == by and (p[2] == BISHOP or p[2] == QUEEN):
                        return True
                    break
                rr += dr
                cc += dc
        return False

    def is_check(self, color):
        return self.attacked(self.king_sq[color], other(color))

    # ------------------------------------------------------- move genotype

    def pseudo_moves(self, captures_only=False):
        """Pseudo-legal moves as (frm, to, promo, flag) tuples."""
        sqs = self.squares
        moves = []
        add = moves.append
        turn = self.turn
        ep = self.ep
        for frm in range(64):
            piece = sqs[frm]
            if piece is None or piece[0] != turn:
                continue
            color, kind, pat = piece
            r, c = divmod(frm, 8)

            if pat == PAWN:
                step = -1 if color == WHITE else 1
                last = 0 if color == WHITE else 7
                rr = r + step
                for dc in (-1, 1):
                    cc = c + dc
                    if 0 <= cc < 8:
                        to = rr * 8 + cc
                        tgt = sqs[to]
                        if tgt is not None and tgt[0] != color:
                            if rr == last:
                                for pk in (QUEEN, ROOK, BISHOP, KNIGHT):
                                    add((frm, to, pk, NORMAL))
                            else:
                                add((frm, to, None, NORMAL))
                        elif ep is not None and to == ep:
                            add((frm, to, None, EN_PASSANT))
                if not captures_only:
                    one = rr * 8 + c
                    if sqs[one] is None:
                        if rr == last:
                            for pk in (QUEEN, ROOK, BISHOP, KNIGHT):
                                add((frm, one, pk, NORMAL))
                        else:
                            add((frm, one, None, NORMAL))
                            if r == (6 if color == WHITE else 1):
                                two = (r + 2 * step) * 8 + c
                                if sqs[two] is None:
                                    add((frm, two, None, DOUBLE_PUSH))
                elif rr == last and sqs[rr * 8 + c] is None:
                    # quiet promotions are tactical enough for quiescence
                    for pk in (QUEEN, ROOK, BISHOP, KNIGHT):
                        add((frm, rr * 8 + c, pk, NORMAL))

            elif pat == KNIGHT:
                for dr, dc in KNIGHT_OFFS:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < 8 and 0 <= cc < 8:
                        to = rr * 8 + cc
                        tgt = sqs[to]
                        if tgt is None:
                            if not captures_only:
                                add((frm, to, None, NORMAL))
                        elif tgt[0] != color:
                            add((frm, to, None, NORMAL))

            elif pat == KING:
                for dr, dc in KING_OFFS:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < 8 and 0 <= cc < 8:
                        to = rr * 8 + cc
                        tgt = sqs[to]
                        if tgt is None:
                            if not captures_only:
                                add((frm, to, None, NORMAL))
                        elif tgt[0] != color:
                            add((frm, to, None, NORMAL))
                if (kind == KING and not captures_only and not self.random_mode
                        and self.castling):
                    self._add_castlings(r, moves)

            else:  # sliding patterns: B, R, Q
                if pat == ROOK:
                    dirs = ROOK_DIRS
                elif pat == BISHOP:
                    dirs = BISHOP_DIRS
                else:
                    dirs = ALL_DIRS
                for dr, dc in dirs:
                    rr, cc = r + dr, c + dc
                    while 0 <= rr < 8 and 0 <= cc < 8:
                        to = rr * 8 + cc
                        tgt = sqs[to]
                        if tgt is None:
                            if not captures_only:
                                add((frm, to, None, NORMAL))
                        else:
                            if tgt[0] != color:
                                add((frm, to, None, NORMAL))
                            break
                        rr += dr
                        cc += dc
        return moves

    def _add_castlings(self, home_row, moves):
        sqs = self.squares
        color = self.turn
        enemy = other(color)
        ks, qs = ('K', 'Q') if color == WHITE else ('k', 'q')
        rook = (color, ROOK, ROOK)
        if ks in self.castling and sqs[home_row * 8 + 7] == rook:
            if (sqs[home_row * 8 + 5] is None and sqs[home_row * 8 + 6] is None
                    and not self.attacked(home_row * 8 + 4, enemy)
                    and not self.attacked(home_row * 8 + 5, enemy)
                    and not self.attacked(home_row * 8 + 6, enemy)):
                moves.append((home_row * 8 + 4, home_row * 8 + 6, None, CASTLE))
        if qs in self.castling and sqs[home_row * 8 + 0] == rook:
            if (sqs[home_row * 8 + 1] is None and sqs[home_row * 8 + 2] is None
                    and sqs[home_row * 8 + 3] is None
                    and not self.attacked(home_row * 8 + 4, enemy)
                    and not self.attacked(home_row * 8 + 3, enemy)
                    and not self.attacked(home_row * 8 + 2, enemy)):
                moves.append((home_row * 8 + 4, home_row * 8 + 2, None, CASTLE))

    def legal_moves(self):
        moves = []
        turn = self.turn
        enemy = other(turn)
        for m in self.pseudo_moves():
            undo = self.make(m)
            if not self.attacked(self.king_sq[turn], enemy):
                moves.append(m)
            self.unmake(undo)
        return moves

    # -------------------------------------------------------- make / unmake

    def make(self, m):
        frm, to, promo, flag = m
        sqs = self.squares
        piece = sqs[frm]
        color = piece[0]
        prev_castling = self.castling
        prev_ep = self.ep
        captured = sqs[to]
        captured_sq = to
        if flag == EN_PASSANT:
            # the captured pawn sits one row behind the target square
            # (white captures upward -> pawn below target, black -> above)
            captured_sq = to + 8 if color == WHITE else to - 8
            captured = sqs[captured_sq]
            sqs[captured_sq] = None
        undo = (m, piece, captured, captured_sq, prev_castling, prev_ep)
        sqs[frm] = None
        sqs[to] = (color, promo, promo) if promo else piece
        if flag == CASTLE:
            home = 7 if color == WHITE else 0
            if to % 8 == 6:
                sqs[home * 8 + 5] = sqs[home * 8 + 7]
                sqs[home * 8 + 7] = None
            else:
                sqs[home * 8 + 3] = sqs[home * 8 + 0]
                sqs[home * 8 + 0] = None
        if piece[1] == KING:
            self.king_sq[color] = to
            if prev_castling:
                self.castling = prev_castling - ({'K', 'Q'} if color == WHITE else {'k', 'q'})
        if prev_castling:
            lost = None
            ch = CORNER_RIGHTS.get(frm)
            if ch:
                lost = {ch}
            ch = CORNER_RIGHTS.get(to)
            if ch:
                lost = {ch} if lost is None else lost | {ch}
            if lost:
                self.castling = self.castling - lost
        self.ep = (frm + to) // 2 if flag == DOUBLE_PUSH else None
        self.turn = 1 - color
        return undo

    def unmake(self, undo):
        m, piece, captured, captured_sq, castling, ep = undo
        frm, to, promo, flag = m
        sqs = self.squares
        color = piece[0]
        sqs[to] = None
        sqs[frm] = piece
        if captured is not None:
            sqs[captured_sq] = captured
        if flag == CASTLE:
            home = 7 if color == WHITE else 0
            if to % 8 == 6:
                sqs[home * 8 + 7] = sqs[home * 8 + 5]
                sqs[home * 8 + 5] = None
            else:
                sqs[home * 8 + 0] = sqs[home * 8 + 3]
                sqs[home * 8 + 3] = None
        if piece[1] == KING:
            self.king_sq[color] = frm
        self.castling = castling
        self.ep = ep
        self.turn = color

    # --------------------------------------------------------------- status

    def insufficient_material(self):
        minors = {WHITE: 0, BLACK: 0}
        bishops = {WHITE: [], BLACK: []}
        for i, p in enumerate(self.squares):
            if p is None or p[1] == KING:
                continue
            if p[1] == PAWN or p[2] in (ROOK, QUEEN):
                return False
            minors[p[0]] += 1
            if p[2] == BISHOP:
                r, c = divmod(i, 8)
                bishops[p[0]].append((r + c) % 2)
        if minors[WHITE] + minors[BLACK] <= 1:
            return True
        if (minors[WHITE] == 1 and minors[BLACK] == 1
                and len(bishops[WHITE]) == 1 and len(bishops[BLACK]) == 1
                and bishops[WHITE][0] == bishops[BLACK][0]):
            return True
        return False

    def status(self):
        """'playing' | 'checkmate' | 'stalemate' | 'material_draw'"""
        moves = self.legal_moves()
        if not moves:
            return 'checkmate' if self.is_check(self.turn) else 'stalemate'
        if self.insufficient_material():
            return 'material_draw'
        return 'playing'


def perft(board, depth):
    if depth == 0:
        return 1
    n = 0
    for m in board.legal_moves():
        undo = board.make(m)
        n += perft(board, depth - 1)
        board.unmake(undo)
    return n
